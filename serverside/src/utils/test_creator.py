import json
import logging
from typing import Any, Dict, List, Optional

from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.integrations.github_integration import RepoHelper
from src.utils.integrations.openai_integration import OpenAIHelper

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
            entry_point_node_id = self.select_function_to_cover(graph)
            if entry_point_node_id is None:
                logger.info("No entry point function was selected for coverage.")
                continue

            # Generate test prompt by analyzing the CallGraph from the entry point node
            test_prompt = self.generate_test_prompt(graph, entry_point_node_id)
            gpt_response = self.gpt_helper.call_chatgpt(test_prompt)
            pytest_full_code = self.extract_full_pytest_code(gpt_response)

            if pytest_full_code:
                logger.info(
                    f"Generated full pytest code for {graph.graph.nodes[entry_point_node_id]['function']}:\n{pytest_full_code}"
                )
                test_file_name = f"captureflow_tests/test_{graph.graph.nodes[entry_point_node_id]['function'].replace(' ', '_').lower()}.py"
                self.repo_helper.create_pull_request_with_test(
                    test_file_name, pytest_full_code, graph.graph.nodes[entry_point_node_id]["function"]
                )
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

    def select_function_to_cover(self, graph: CallGraph) -> Optional[str]:
        # Select the first non-stdlib node as the entry point for testing.
        # TODO: Replace with a way to get endpoint
        for node_id, data in graph.graph.nodes(data=True):
            if data.get("tag") != "STDLIB":
                return node_id
        return None

    def analyze_external_interactions_with_chatgpt(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        function_implementation = node_data.get("github_function_implementation", {}).get("content", "Not available")
        json_example = {
            "interactions": [
                {
                    "type": "DB_INTERACTION | API_CALL",
                    "details": "Query to SQLite database for user data",
                    "mock_idea": 'with patch("sqlite3.connect") as mock_connect: mock_cursor = mock_connect.return_value.cursor.return_value; mock_cursor.fetchall.return_value = [(10,), (20,)]',
                }
            ]
        }
        prompt = (
            f"Analyze the following Python code and identify any external interactions such as database queries, "
            f"API calls, or file operations. For each interaction, return a JSON formatted list with the type of interaction, "
            f"details, and suggestions for how to mock these interactions in a pytest environment. Use the following format for your response:\n"
            f"{json.dumps(json_example)}"
            f"If there are no interactions => interactions array must be empty\n\n"
            f"```python\n{function_implementation}\n```"
        )
        response = self.gpt_helper.call_chatgpt(prompt)
        interactions = self.parse_interaction_response(response)
        return interactions

    def parse_interaction_response(self, response: str) -> List[Dict[str, Any]]:
        try:
            start_index = response.index("{")
            end_index = response.rindex("}") + 1
            json_str = response[start_index:end_index]
            interaction_data = json.loads(json_str)
            return interaction_data.get("interactions", [])
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode interaction response from ChatGPT: {e}")
            return []

    def analyze_graph_for_interactions(self, graph: CallGraph, node_id: str, interactions: List[Dict[str, Any]]):
        node_data = graph.graph.nodes[node_id]

        # We are not interested in scanning Python/Library methods
        # If such method does contain external call, we need to identify it on the caller level
        if (
            node_data["tag"] == "STDLIB"
            or ("github_function_implementation" not in node_data)
            or node_data["github_function_implementation"] == "not_found"
        ):
            return []

        node_interactions = self.analyze_external_interactions_with_chatgpt(node_data)
        interactions.extend(node_interactions)

        # Recursively analyze all child nodes
        for successor in graph.graph.successors(node_id):
            self.analyze_graph_for_interactions(graph, successor, interactions)

    def generate_test_prompt(self, graph: CallGraph, entry_point_node_id: str) -> str:
        entry_point_data = graph.graph.nodes[entry_point_node_id]
        all_interactions = []
        self.analyze_graph_for_interactions(graph, entry_point_node_id, all_interactions)

        # TODO, replace 'mock_code' (broken) instruction, line by line
        # TODO, also send context of all functions that were called by a given function including path
        # TODO, provide some guidance on how to import WSGI.app (route to server:app)
        # TODO, instead of just sending endpoint, send full function where it's defined

        mock_instructions = "\n".join(
            [f"{interaction['mock_code']}" for interaction in all_interactions if "mock_code" in interaction]
        )

        function_name = entry_point_data["function"]
        file_path = entry_point_data.get("github_file_path", "unknown")
        line_number = entry_point_data.get("github_function_implementation", {}).get("start_line", "unknown")
        function_implementation = entry_point_data.get("github_function_implementation", {}).get(
            "content", "Not available"
        )
        arguments = json.dumps(entry_point_data.get("arguments", {}), indent=2)
        expected_output = entry_point_data["return_value"].get("json_serialized", "No output captured")

        prompt = (
            f"Write a complete pytest file for testing the WSGI app entry point '{function_name}' defined in '{file_path}' at line {line_number}. "
            f"Function implementation:\n{function_implementation}\n"
            f"Arguments: {arguments}\n"
            f"Expected output: {expected_output}\n"
            "External interactions to mock (follow the instructions below):\n"
            f"{mock_instructions}\n"
            "Include necessary imports, setup any needed fixtures, and define test functions with assertions based on the expected output. "
            "Ensure the test file adheres to Python best practices and pytest conventions."
        )

        return prompt

    def extract_full_pytest_code(self, text: str) -> Optional[str]:
        """Extracts a full pytest file from the provided response."""
        try:
            start_index = text.index("import pytest")
            end_index = text.rfind("```") if "```" in text else len(text)
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
