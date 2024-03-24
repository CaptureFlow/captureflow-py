import ast
import base64
import logging
import uuid

from typing import Any, Dict, List, Optional
from github import GithubIntegration, Repository

from src.config import GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_BASE64
from src.utils.call_graph import CallGraph
from src.utils.integrations.openai_integration import OpenAIHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DefinitionVisitor(ast.NodeVisitor):
    """Used to expose definitions met via self.definitions field"""

    def __init__(self):
        self.definitions = []

    def visit_ClassDef(self, node):
        self.definitions.append(("class", node))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.definitions.append(("function", node))
        self.generic_visit(node)


class RepoHelper:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.github_integration = self._get_integration()
        self.gh_repo = self._get_repo_by_url(repo_url)
        self.index = self._build_index()

    def _get_integration(self) -> GithubIntegration:
        APP_ID = GITHUB_APP_ID
        PRIVATE_KEY = base64.b64decode(GITHUB_APP_PRIVATE_KEY_BASE64).decode("utf-8")
        return GithubIntegration(APP_ID, PRIVATE_KEY)

    def _get_repo_by_url(self, repo_url: str) -> Optional[Repository.Repository]:
        installations = self.github_integration.get_installations()

        for installation in installations:
            for repo in installation.get_repos():
                if repo.html_url == repo_url:
                    return repo
        raise ValueError(
            f"No matching installation was found for {repo_url}. Maybe the app is not installed yet."
        )

    def enrich_callgraph_with_github_context(self, callgraph: CallGraph) -> None:
        for node_id in callgraph.graph.nodes:
            node = callgraph.graph.nodes[node_id]
            if "function" in node:
                # Attempt to enrich the node with GitHub data
                enriched_node = self.enrich_node_with_github_data(node)
                # Update the node with enriched data if any
                if enriched_node:
                    callgraph.graph.nodes[node_id].update(enriched_node)

    def _build_index(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        index = {"class": {}, "function": {}}
        contents = self.gh_repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self.gh_repo.get_contents(file_content.path))
            elif file_content.name.endswith(".py"):
                self._process_python_file(file_content, index)
        return index

    def _process_python_file(self, file_content, index) -> None:
        try:
            file_data = file_content.decoded_content.decode("utf-8")
            tree = ast.parse(file_data, filename=file_content.path)
            visitor = DefinitionVisitor()
            visitor.visit(tree)
            for symbol_type, node in visitor.definitions:
                symbol_name = node.name
                if symbol_name not in index[symbol_type]:
                    index[symbol_type][symbol_name] = []
                index[symbol_type][symbol_name].append(
                    {
                        "file_path": file_content.path,
                        "line_start": node.lineno,
                        "line_end": (
                            node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno
                        ),
                        "content": "\n".join(
                            file_data.splitlines()[
                                node.lineno
                                - 1 : (
                                    node.end_lineno
                                    if hasattr(node, "end_lineno")
                                    else node.lineno
                                )
                            ]
                        ),
                    }
                )
        except Exception as e:
            logger.exception(f"Error processing {file_content.path}: {e}")

    def lookup_index(
        self, symbol_name: str, symbol_type: str
    ) -> Optional[Dict[str, Any]]:
        return self.index.get(symbol_type, {}).get(symbol_name)

    def enrich_node_with_github_data(self, node):
        """
        Enriches node attributes with:
            - file path from GitHub
            - function implementation from GitHub (start_line, end_line, content)
            - whole file content from GitHub
        """
        symbol_name = node["function"]
        symbol_type = "function"  # Assuming all nodes in the graph are functions for simplification

        # Use the lookup_index method to find the function in the index
        defs = self.lookup_index(symbol_name, symbol_type)

        if not defs:
            node["github_file_path"] = "not_found"
            node["github_function_implementation"] = "not_found"
            node["github_file_content"] = "not_found"
            return

        # For simplicity, take the first definition (if multiple are found, this may need refinement)
        def_info = defs[0]

        # Load the whole file content
        try:
            file_content = self.gh_repo.get_contents(
                def_info["file_path"]
            ).decoded_content.decode("utf-8")
        except Exception as e:
            logger.exception(
                f"Error fetching file content for {def_info['file_path']}: {e}"
            )
            file_content = "Error loading file content"

        # Update the node with GitHub data
        node.update(
            {
                "github_file_path": def_info["file_path"],
                "github_function_implementation": {
                    "start_line": def_info["line_start"],
                    "end_line": def_info["line_end"],
                    "content": def_info["content"],
                },
                "github_file_content": file_content,
            }
        )

    def create_pull_request_with_new_function(
        self, node, new_implementation: str, gpt_helper: OpenAIHelper
    ):
        """
        Update the implementation of a specific function based on node information,
        commit the changes to a new branch, and create a pull request.
        """
        file_path = node["github_file_path"]
        function_name = node["function"]
        start_line = node["github_function_implementation"]["start_line"]
        end_line = node["github_function_implementation"]["end_line"]
        content = self.gh_repo.get_contents(file_path, ref="main")
        source_code_lines = content.decoded_content.decode("utf-8").splitlines()

        # Replace old function implementation with new content within the source code lines
        new_code_lines = (
            source_code_lines[: start_line - 1]
            + new_implementation.splitlines()
            + source_code_lines[end_line:]
        )
        updated_source_code = "\n".join(new_code_lines)

        fix_styles_query = gpt_helper.generate_after_insert_style_query(
            updated_source_code, function_name
        )
        updated_source_code = gpt_helper.extract_first_code_block(
            gpt_helper.call_chatgpt(fix_styles_query)
        )

        # Create a new branch for this update
        new_branch_name = f"update-{function_name}-{uuid.uuid4().hex}"
        base_sha = self.gh_repo.get_branch("main").commit.sha
        self.gh_repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=base_sha)

        # Commit the updated file to the new branch
        commit_message = f"Update implementation of {function_name}"
        self.gh_repo.update_file(
            file_path,
            commit_message,
            updated_source_code,
            content.sha,
            branch=new_branch_name,
        )

        # Create a pull request from the new branch to the main branch
        pr_title = f"Improve {function_name} implementation"
        pr_body = "This pull request updates the implementation of `{function_name}` for better performance/readability."
        pr = self.gh_repo.create_pull(
            title=pr_title, body=pr_body, head=new_branch_name, base="main"
        )
        logger.info(f"Pull request created: {pr.html_url}")
