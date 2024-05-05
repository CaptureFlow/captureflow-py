import json
import logging
import os
from typing import Any, Dict, List, Optional

from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.docker_executor import DockerExecutor
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
        self.docker_executor = DockerExecutor(repo_url)

    def run(self):
        graphs = self.build_graphs_from_redis()

        for graph in graphs:
            self.repo_helper.enrich_callgraph_with_github_context(graph)
            endpoint_invoked = self.determine_invoked_endpoint(graph)
            
            print("ENDPOINT INVOKED = ", endpoint_invoked)

            if endpoint_invoked:
                app_path = self.repo_helper.identify_app_for_endpoint(endpoint_invoked)
                print("APP PATH = ", app_path)
                if app_path:
                    self.process_endpoint(graph, endpoint_invoked, app_path)
                else:
                    logger.error(f"App path could not be determined for endpoint {endpoint_invoked['function']}")
            else:
                logger.info("No endpoint was clearly invoked in this trace.")

    def process_endpoint(self, graph, endpoint_invoked, app_path):
        logger.info(f"Processing endpoint {endpoint_invoked['function']} in app at {app_path}")
        initial_test_output = self.docker_executor.execute_with_new_files({})
        endpoint_coverage = self.calculate_endpoint_coverage(initial_test_output)

        entry_point_node_id = self.select_function_to_cover(graph, endpoint_coverage)
        print("ENDPOINT TO COVER = ", entry_point_node_id)
        if entry_point_node_id:
            all_interactions, function_context = [], []
            self.analyze_graph_for_interactions_and_context(graph, entry_point_node_id, all_interactions, function_context)
            desired_test_path = "serverside/tests/test_app.py"
            prompt = self.generate_test_prompt(function_context, all_interactions, graph, entry_point_node_id, app_path, desired_test_path)
            print("PROMPT = ", prompt)
            pytest_full_code = self.generate_and_test_pytest_code(prompt, entry_point_node_id, initial_test_output, desired_test_path)

            if pytest_full_code:
                test_file_name = f"serverside/tests/test_{graph.graph.nodes[entry_point_node_id]['function'].replace(' ', '_').lower()}.py"
                self.repo_helper.create_pull_request_with_test(test_file_name, pytest_full_code, graph.graph.nodes[entry_point_node_id]["function"])
            else:
                logger.error("Failed to generate or validate pytest code.")
        else:
            logger.error("No suitable entry point function was selected for coverage improvement.")

    def build_graphs_from_redis(self) -> List[CallGraph]:
        graphs = []
        search_pattern = f"{self.repo_url}:*"
        for key in self.redis_client.scan_iter(match=search_pattern):
            log_data_json = self.redis_client.get(key)
            if log_data_json:
                log_data = json.loads(log_data_json.decode("utf-8"))
                graphs.append(CallGraph(json.dumps(log_data)))
        return graphs
    
    def generate_and_test_pytest_code(self, prompt, entry_point_node_id, initial_test_output, desired_test_path="serverside/tests/test_app.py"):
        gpt_response = self.gpt_helper.call_chatgpt(prompt)
        pytest_full_code = self.gpt_helper.extract_first_code_block(gpt_response)
        if pytest_full_code:
            logger.info(f"Generated full pytest code for function {entry_point_node_id}:\n{pytest_full_code}")
            new_test_files = {desired_test_path: pytest_full_code}
            modified_test_output = self.docker_executor.execute_with_new_files(new_test_files)

            # After updating the tests, compare the coverage to see the improvements
            test_diff = self.compare_test_coverage(initial_test_output, modified_test_output)
            logger.info(f"Test coverage difference: {test_diff}")

            # Return the full pytest code for additional actions (like creating files or PRs)
            return pytest_full_code
        else:
            logger.error("Failed to generate valid pytest code from GPT response.")
            return None

    
    def determine_invoked_endpoint(self, graph):
        """
        Determine which endpoint was invoked based on the call graph. Assumes each node might have information
        like 'github_file_path' and function name that can be mapped to known endpoints.
        """
        for node_id, data in graph.graph.nodes(data=True):
            for endpoint in self.repo_helper.get_fastapi_endpoints():
                if data.get('github_file_path') == endpoint['file_path'] and data.get('function') == endpoint['function']:
                    return endpoint
        return None

    def calculate_endpoint_coverage(self, test_output):
        """ Calculate and return coverage data for each endpoint, ordered by uncovered percentage. """
        endpoints = self.repo_helper.get_fastapi_endpoints()
        endpoint_coverage = []

        for endpoint in endpoints:
            uncovered_lines = self.calculate_uncovered_lines(endpoint, test_output)
            total_lines = endpoint['line_end'] - endpoint['line_start'] + 1
            coverage_percent = 100 - (uncovered_lines / total_lines * 100)
            endpoint_coverage.append((endpoint, coverage_percent))

        endpoint_coverage.sort(key=lambda x: x[1])  # Sort by coverage percentage
        return endpoint_coverage

    def calculate_uncovered_lines(self, endpoint, test_output):
        """ Calculate the number of uncovered lines for a given endpoint based on test output. """
        uncovered_lines = 0
        for file_path, coverage_data in test_output.test_coverage.items():
            if file_path == endpoint['file_path']:
                uncovered_lines += len([line for line in coverage_data.missing_lines if endpoint['line_start'] <= line <= endpoint['line_end']])
        return uncovered_lines
    
    def select_function_to_cover(self, graph: CallGraph, endpoint_coverage) -> Optional[str]:
        """ Select the least covered FastAPI endpoint function from the graph. """
        least_covered = None
        min_coverage = float('inf')
        for endpoint, coverage in endpoint_coverage:
            for node_id, data in graph.graph.nodes(data=True):
                if data.get("function") == endpoint["function"] and coverage < min_coverage:
                    least_covered = node_id
                    min_coverage = coverage

        return least_covered
    
    def compare_test_coverage(self, initial_output, modified_output):
        """ Compare initial and modified test coverage and log the differences. """
        coverage_diff = {}
        for file_path, initial_data in initial_output.test_coverage.items():
            if file_path in modified_output.test_coverage:
                new_data = modified_output.test_coverage[file_path]
                previous = initial_data.coverage
                new = new_data.coverage
                change = new - previous
                coverage_diff[file_path] = {'previous': previous, 'new': new, 'change': change}
                logger.info(f"Coverage for {file_path}: {previous}% -> {new}% (Change: {change}%)")
            else:
                coverage_diff[file_path] = {'previous': initial_data.coverage, 'new': 'N/A', 'change': 'N/A'}

        return coverage_diff

    def analyze_external_interactions_with_chatgpt(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        function_implementation = node_data.get("github_function_implementation", {}).get("content", "Not available")
        json_example = {
            "interactions": [
                {
                    "type": "DB_INTERACTION | API_CALL",
                    "details": "Query to SQLite database for user data at line 14",
                    "mock_idea": 'with patch("sqlite3.connect") as mock_connect: mock_cursor = mock_connect.return_value.cursor.return_value; mock_cursor.fetchall.return_value = [(10,), (20,)]',
                    "certainty": "high",
                }
            ]
        }
        prompt = (
            f"Please analyze the provided Python code snippet to identify any external interactions such as database queries, "
            f"API calls, or file operations. For each detected interaction, return a JSON formatted list describing the interaction. "
            f"Each interaction should include the type, detailed description, and suggested mocking strategy if applicable. "
            f"Please classify the certainty of each interaction as 'high', 'medium', or 'low'. Based on the certainty, "
            f"provide appropriate mock ideas or indicate if mocking is not certain. Use the following response format:\n"
            f"{json.dumps(json_example, indent=2)}\n"
            f"If no external interactions are detected, please return an empty interactions array.\n"
            f"Additionally, indicate the specific functions where these interactions occur.\n\n"
            f"```python\n{function_implementation}\n```"
        )

        # Call ChatGPT and get the response
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

    def analyze_graph_for_interactions_and_context(
        self, graph: CallGraph, node_id: str, interactions: List[Dict[str, Any]], function_context: List[str]
    ):
        node_data = graph.graph.nodes[node_id]
        if (
            node_data["tag"] == "STDLIB"
            or "github_function_implementation" not in node_data
            or node_data["github_function_implementation"] == "not_found"
        ):
            return

        node_interactions = self.analyze_external_interactions_with_chatgpt(node_data)
        interactions.extend(node_interactions)

        function_context.append(
            f"Function '{node_data['function']}' defined in '{node_data.get('github_file_path', 'unknown')}' at line {node_data.get('github_function_implementation', {}).get('start_line', 'unknown')} with this implementation {node_data.get('github_function_implementation', {}).get('content', 'Not available')} should consider the following details for mocking (if needed at all): {json.dumps(node_interactions)}"
        )

        for successor in graph.graph.successors(node_id):
            self.analyze_graph_for_interactions_and_context(graph, successor, interactions, function_context)

    def generate_import_statement(self, app_path, desired_test_path):
        # Define the root module name (folder before 'tests')
        test_dir = os.path.dirname(desired_test_path)
        root_module = os.path.basename(os.path.dirname(test_dir))

        # Get the relative path from the test directory to the app file, excluding the root module from the path
        relative_path_from_root = os.path.relpath(app_path, start=os.path.join(test_dir, '..'))

        # Normalize the path for use in an import statement
        normalized_import_path = relative_path_from_root.replace(os.path.sep, '.').rstrip('.py')

        # Form the import statement
        import_statement = f"from {root_module}.{normalized_import_path} import your_fastapi_instance"

        return import_statement

    def generate_test_prompt(self, function_context, all_interactions, graph, entry_point_node_id, app_path, desired_test_path):
        entry_point_data = graph.graph.nodes[entry_point_node_id]

        import_statement = self.generate_import_statement(app_path, desired_test_path)

        # Load the pytest template from the resources directory
        template_path = os.path.join(os.path.dirname(__file__), "resources", "pytest_template.py")
        with open(template_path, "r") as file:
            pytest_template = file.read()

        # Generate mock instructions only for high-certainty interactions
        mock_instructions = "\n".join(
            interaction["mock_idea"]
            for interaction in all_interactions
            if interaction.get("certainty", "low") == "high" and "mock_idea" in interaction
        )

        # TODO, implement a way to find where fastAPI app is located
        # TODO, assume you have an input (desired_test_location)
        # TODO, construct path to import fastAPI app from desired_test_location

        function_implementation = entry_point_data.get("github_function_implementation", {}).get(
            "content", "Not available"
        )
        full_function_content = entry_point_data.get(
            "github_file_content", "Function content not available"
        )  # Retrieve full function content
        arguments = json.dumps(entry_point_data.get("arguments", {}), indent=2)
        expected_output = entry_point_data["return_value"].get("json_serialized", "No output captured")
        context_details = "\n".join(function_context)

        prompt = (
            f"Write a complete pytest file for testing the FastAPI app located at '{app_path}', specifically the endpoint "
            f"'{entry_point_data['function']}' defined in '{entry_point_data['github_file_path']}' at line {entry_point_data['github_function_implementation']['start_line']}. "
            f"Import the application using: {import_statement}\n"
            f"Full function implementation from the source file:\n{full_function_content}\n"
            f"Function implementation snippet:\n{function_implementation}\n"
            f"Arguments: {arguments}\n"
            f"Expected output: {expected_output}\n"
            "Context and external interactions:\n"
            f"{context_details}\n"
            "External interactions to mock (follow the instructions below):\n"
            f"{mock_instructions}\n"
            f"\n# --- Start of the Pytest Template ---\n{pytest_template}\n# --- End of the Pytest Template ---\n"
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
