import json
import logging
from typing import Dict, Any, List, Optional

from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.integrations.openai_integration import OpenAIHelper
from src.utils.integrations.github_integration import RepoHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCoverageCreator:
    def __init__(self, redis_client: Redis, repo_url: str):
        self.redis_client = redis_client
        self.repo_url = repo_url
        self.gpt_helper = OpenAIHelper()
        self.repo_helper = RepoHelper(repo_url)

    def run(self):
        graphs = self.build_graphs_from_redis()
        for graph in graphs:
            self.repo_helper.enrich_callgraph_with_github_context(graph)
            non_stdlib_nodes = self.select_non_stdlib_nodes(graph)
            if not non_stdlib_nodes:
                logger.info("No suitable non-stdlib nodes found for generating tests.")
                continue

            selected_node_id = self.select_function_to_cover(non_stdlib_nodes)
            if selected_node_id is None:
                logger.info("No function was selected for coverage.")
                continue
            
            node_data = graph.graph.nodes[selected_node_id]
            test_prompt = self.generate_test_prompt(node_data)
            gpt_response = self.gpt_helper.call_chatgpt(test_prompt)
            pytest_full_code = self.extract_full_pytest_code(gpt_response)

            if pytest_full_code:
                logger.info(f"Generated full pytest code for {node_data['function']}:\n{pytest_full_code}")
                # Submit the pull request with the full pytest code
                test_file_name = f"captureflow_tests/test_{node_data['function'].replace(' ', '_').lower()}.py"
                self.repo_helper.create_pull_request_with_test(test_file_name, pytest_full_code, node_data['function'])
            else:
                logger.error("Failed to generate valid full pytest code.")


    def build_graphs_from_redis(self) -> List[CallGraph]:
        graphs = []
        search_pattern = f"{self.repo_url}:*"
        for key in self.redis_client.scan_iter(match=search_pattern):
            log_data_json = self.redis_client.get(key)
            if log_data_json:
                log_data = json.loads(log_data_json.decode("utf-8"))
                graphs.append(CallGraph(json.dumps(log_data)))
        return graphs

    def select_non_stdlib_nodes(self, graph: CallGraph) -> List[str]:
        return [
            node_id for node_id, data in graph.graph.nodes(data=True)
            if data.get('tag') != 'STDLIB'
        ]

    def select_function_to_cover(self, non_stdlib_nodes: List[str]) -> Optional[str]:
        """Selects the first function from the list of non-stdlib nodes for test coverage."""
        return non_stdlib_nodes[0] if non_stdlib_nodes else None

    def generate_test_prompt(self, node_data: Dict[str, Any]) -> str:
        function_name = node_data['function']
        file_path = node_data.get('github_file_path', 'unknown')
        function_implementation = node_data.get('github_function_implementation', {}).get('content', 'Not available')

        prompt = (
            f"Write a complete pytest file for testing the function '{function_name}' defined at {file_path}. "
            f"Here's the function implementation:\n{function_implementation}\n"
            "Include necessary imports, setup any needed fixtures, and define at least one test function with assertions."
            "Ensure the test file adheres to Python best practices and pytest conventions."
        )
        return prompt

    def extract_full_pytest_code(self, text: str) -> Optional[str]:
        """Extracts a full pytest file from the provided response."""
        try:
            start_index = text.index("import pytest")
            end_index = text.rfind("```") if '```' in text else len(text)
            full_pytest_code = text[start_index:end_index].strip()
            return full_pytest_code
        except ValueError:
            return None


if __name__ == "__main__":
    import redis

    redis_client = redis.Redis.from_url("redis://localhost:6379/0")
    repo_url = "https://github.com/CaptureFlow/captureflow-py"

    test_creator = TestCoverageCreator(redis_client=redis_client, repo_url=repo_url)
    test_creator.run()
