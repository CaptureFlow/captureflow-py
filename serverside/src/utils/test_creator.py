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

            all_interactions = []
            function_context = []
            self.analyze_graph_for_interactions_and_context(graph, entry_point_node_id, all_interactions, function_context)

            test_prompt = self.generate_test_prompt(function_context, all_interactions, graph, entry_point_node_id)

            print("TEST PROMPT = ", test_prompt)

            gpt_response = self.gpt_helper.call_chatgpt(test_prompt)
            pytest_full_code = self.gpt_helper.extract_first_code_block(gpt_response)

            print("Pytest code = ", pytest_full_code)

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
            f"If there are no interactions, then interactions array must be empty.\n"
            f"Also make sure to name exact line/function where external interaction that will likely need to get mocked happens, add it to 'details'\n\n"
            f"```python\n{function_implementation}\n```"
        )
        response = self.gpt_helper.call_chatgpt(prompt)
        print("RESPONSE = ", response)
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

    def analyze_graph_for_interactions_and_context(self, graph: CallGraph, node_id: str, interactions: List[Dict[str, Any]], function_context: List[str]):
        node_data = graph.graph.nodes[node_id]
        print("NODE DATA START = ", node_data)
        if node_data["tag"] == "STDLIB" or "github_function_implementation" not in node_data or node_data["github_function_implementation"] == "not_found":
            return

        node_interactions = self.analyze_external_interactions_with_chatgpt(node_data)
        interactions.extend(node_interactions)

        function_context.append(f"Function '{node_data['function']}' defined in '{node_data.get('github_file_path', 'unknown')}' at line {node_data.get('github_function_implementation', {}).get('start_line', 'unknown')} should consider the following details for mocking: {json.dumps(node_interactions)}")

        for successor in graph.graph.successors(node_id):
            self.analyze_graph_for_interactions_and_context(graph, successor, interactions, function_context)
    
    def generate_test_prompt(self, function_context, all_interactions, graph, entry_point_node_id):
        entry_point_data = graph.graph.nodes[entry_point_node_id]

        # Generate mock instructions, ensuring to handle missing or empty 'mock_idea'
        mock_instructions = "\n".join(
            interaction.get('mock_idea', 'No specific mock instructions provided.')
            for interaction in all_interactions
            if 'mock_idea' in interaction and interaction['mock_idea'].strip()
        )

        # TODO, replace 'mock_code' (broken) instruction, line by line
        # TODO, provide some guidance on how to import WSGI.app (route to server:app)
        # TODO, instead of just sending endpoint, send full function where it's defined

        function_name = entry_point_data["function"]
        file_path = entry_point_data.get("github_file_path", "unknown")
        line_number = entry_point_data.get("github_function_implementation", {}).get("start_line", "unknown")
        function_implementation = entry_point_data.get("github_function_implementation", {}).get("content", "Not available")
        arguments = json.dumps(entry_point_data.get("arguments", {}), indent=2)
        expected_output = entry_point_data["return_value"].get("json_serialized", "No output captured")
        context_details = "\n".join(function_context)

        prompt = (
            f"Write a complete pytest file for testing the WSGI app entry point '{function_name}' defined in '{file_path}' at line {line_number}. "
            f"Function implementation:\n{function_implementation}\n"
            f"Arguments: {arguments}\n"
            f"Expected output: {expected_output}\n"
            "Context and external interactions:\n"
            f"{context_details}\n"
            "External interactions to mock (follow the instructions below):\n"
            f"{mock_instructions}\n"
            "Include necessary imports, setup any needed fixtures, and define test functions with assertions based on the expected output. "
            "Ensure the test file adheres to Python best practices and pytest conventions."
        )

        return prompt


if __name__ == "__main__":
    import redis

    redis_client = redis.Redis.from_url("redis://localhost:6379/0")
    repo_url = "https://github.com/CaptureFlow/captureflow-py"
    test_creator = TestCoverageCreator(redis_client=redis_client, repo_url=repo_url)
    test_creator.run()
