import json
import logging
from typing import Any, Dict, List

from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.integrations.github_integration import RepoHelper
from src.utils.integrations.openai_integration import OpenAIHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExceptionPatcher:
    def __init__(self, redis_client: Redis, repo_url: str):
        self.redis_client = redis_client
        self.repo_url = repo_url
        self.repo_helper = RepoHelper(repo_url)
        self.gpt_helper = OpenAIHelper()

    def run(self):
        graphs = self.build_graphs_from_redis()
        self.enrich_graphs_with_github_context(graphs)

        # Here we need to fetch top-level exception node details
        #   + all nodes that also propagated the exception
        #       + input_values
        #   + N parent node levels for context
        #       + input_valuess
        #   + M child node levels for context
        #       + input_values
        for graph in graphs:
            exception_chains = self.select_exception_sequences(graph)
            logger.info("1");

            if not exception_chains:
                logger.info("No exception chains found in this graph.")
                continue
            else:
                logger.info(f"Found a graph that contained unhandled exception chain {exception_chains}")

            logger.info("2");
            for exception_chain in exception_chains:

                logger.info("3");
                context = self.fetch_exception_context(graph, exception_chain)
                logger.info("4");
                prompt = self.generate_fix_prompt_based_on_context(context)
                logger.info("5");
                # gpt_response = self.gpt_helper.call_chatgpt(prompt)
                mock_response_json_str = json.dumps(
                    {
                        "confidence": 5,
                        "function_name": "calculate_avg",
                        "change_reasoning": "Just a mock response.",
                    }
                )
                logger.info("6");
                gpt_response = f"{mock_response_json_str}\n```python\ndef example()```"

                try:
                    logger.info("7");
                    json_str = self.extract_json_simple(gpt_response)
                    logger.info("8");
                    if json_str:
                        gpt_response_dict = json.loads(json_str)
                        change_reasoning = gpt_response_dict.get("change_reasoning", "")
                        function_name = gpt_response_dict.get("function_name", "")
                        logger.info("9");
                        code_block = self.gpt_helper.extract_first_code_block(gpt_response)
                        logger.info("X");

                        matched_node_ids = graph.find_node_by_fname(function_name)
                        logger.info("HEHEHEHE");
                        if matched_node_ids:
                            matches_node_id = matched_node_ids[0]

                            logger.info("10");
                            self.repo_helper.create_pull_request_with_new_function(
                                graph.graph.nodes[matches_node_id],
                                context,
                                code_block,
                                change_reasoning,
                                self.gpt_helper,
                            )
                    else:
                        logger.error("Failed to extract JSON from GPT response.")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.exception(f"Error processing GPT response: {e}")

    def extract_json_simple(self, text):
        try:
            start_index, end_index = text.index("{"), text.rindex("}") + 1
            json_str = text[start_index:end_index]
            return json_str
        except ValueError:
            return None

    def build_graphs_from_redis(self) -> List[CallGraph]:
        graphs = []
        search_pattern = f"{self.repo_url}:*"
        for key in self.redis_client.scan_iter(match=search_pattern):
            log_data_json = self.redis_client.get(key)
            if log_data_json:
                log_data = json.loads(log_data_json.decode("utf-8"))
                graphs.append(CallGraph(json.dumps(log_data)))
        return graphs

    def enrich_graphs_with_github_context(self, graphs: List[CallGraph]):
        for graph in graphs:
            self.repo_helper.enrich_callgraph_with_github_context(graph)

    def select_exception_sequences(self, graph: CallGraph) -> List[List[str]]:
        """
        Collects sequences of nodes involved in the propagation of the same exception type.
        It identifies nodes where exceptions were raised and follows the propagation path 
        through adjacent nodes sharing the same exception type, forming sequences.

        Example:
            Consider a function call graph where arrows indicate the call direction, and nodes are labeled 
            with their function names. Nodes with exceptions have an asterisk (*) next to them, 
            and the exception type is indicated in brackets.

                      a
                      |
                      b* [Exception X]
                    /   \
                    c    d* [Exception X]
                    |
                    e

            The exception chain we want to extract is [b*, d*]

        Args:
            graph (CallGraph): The graph containing nodes with exception information.

        Returns:
            List[List[str]]: Lists of node ID sequences. Each list represents a chain of
                            exception propagation for a specific exception type within the graph.
        """
        exception_sequences = []

        # Identify nodes where exceptions were raised.
        raised_exception_nodes = [
            (node_id, data) for node_id, data in graph.graph.nodes(data=True) if data.get("did_raise")
        ]
        visited = set()

        for start_node, start_data in raised_exception_nodes:
            if start_node in visited:
                continue

            current_sequence = [start_node]
            visited.add(start_node)

            # Adjacent nodes with same exception_type => part of same exception propagation chain
            start_exception_type = start_data["unhandled_exception"]["type"]

            for neighbor in list(graph.graph.predecessors(start_node)) + list(graph.graph.successors(start_node)):
                if neighbor in visited:
                    continue

                neighbor_data = graph.graph.nodes[neighbor]
                if (
                    neighbor_data.get("did_raise")
                    and neighbor_data["unhandled_exception"]["type"] == start_exception_type
                ):
                    current_sequence.append(neighbor)
                    visited.add(neighbor)

            # There are quite a lot if internal (invisible) exception chains happening inside libraries
            # There is no point in refactoring them => prune and skip if needed
            pruned_sequence = [node for node in current_sequence if graph.graph.nodes[node].get("tag") != "STDLIB"]
            if len(pruned_sequence) >= 1:
                exception_sequences.append(current_sequence)

        return exception_sequences

    def fetch_exception_context(self, graph: CallGraph, exception_chain: List[str]) -> Dict[str, Any]:
        """
        Gathers contextual information for nodes involved in exception propagation, including details
        about the exception nodes, and any relevant context from non-exceptional ancestors and descendants.

        Example:
            Given an exception propagating from 'b' to 'd' in the following call graph:

                          a
                          |
                          b* [Exception X]
                        /   \
                       c     d* [Exception X]
                       |
                       e

            This method provides detailed context for the exception chain ['b*', 'd*'], 
            and includes information about 'a', 'c' for a comprehensive view.

        Args:
            graph (CallGraph): The call graph object containing nodes, function calls, and exception information.
            exception_chain (List[str]): A list of node IDs representing the sequence of exception propagation.

        Returns:
            Dict[str, Any]: A dictionary with detailed context about each node in the exception chain,
                            including the node's details, immediate non-exceptional ancestors, and descendants.
                            This provides a holistic view of the functions leading to and affected by the exception.
        """
        chain_context = {"exception_nodes": []}

        for node_id in exception_chain:
            node_data = graph.graph.nodes[node_id]
            node_context = {
                "node_details": self.format_node_details(node_data, include_code=True),
                "context_parents": [],
                "context_children": [],
            }

            # Add parents only if they are not part of the exception chain
            for parent_id in graph.graph.predecessors(node_id):
                if parent_id not in exception_chain:
                    parent_data = graph.graph.nodes[parent_id]
                    node_context["context_parents"].append(self.format_node_details(parent_data, include_code=True))

            # Add any children called by this node that are not part of the exception chain
            for child_id in graph.graph.successors(node_id):
                if child_id not in exception_chain:
                    child_data = graph.graph.nodes[child_id]
                    node_context["context_children"].append(self.format_node_details(child_data, include_code=True))

            chain_context["exception_nodes"].append(node_context)

        return chain_context

    def format_node_details(self, node_data: Dict[str, Any], include_code: bool = False) -> Dict[str, Any]:
        """
        Prepares detailed information of a node for further analysis.

        This method differentiates between nodes that ended with an exception and those that
        completed execution normally, providing either exception details or return values accordingly.

        Example output structure:
            {
                "function_name": "example_function",
                "file_line": "example.py:42",
                "arguments": {"arg1": "value1", "arg2": "value2"},
                "exception_info": {"type": "ValueError", "value": "An error occurred"},
                "function_implementation": "def example_function(arg1, arg2): pass",
                "file_content": "def example_function(arg1, arg2): pass\n..."
            }
        """
        details = {
            "function_name": node_data.get("function"),
            "file_line": node_data.get("file_line", "unknown"),
            "arguments": node_data.get("arguments", {}),
            "exception_info": node_data.get("unhandled_exception"),
            "return_value": node_data.get("return_value"),
            "function_implementation": (
                node_data.get("github_function_implementation").get("content", "Not available")
                if isinstance(node_data.get("github_function_implementation"), dict) and include_code
                else "Not available"
            ),
            "file_content": node_data.get("github_file_content", "Not available") if include_code else None,
        }

        # Clean up None values
        return {key: value for key, value in details.items() if value is not None}

    def fetch_parents(
        self, graph: CallGraph, node_id: str, depth: int, include_code: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Recursively fetches parent nodes up to a certain depth, including their code.
        """
        if depth == 0:
            return []
        parents = []
        for predecessor in graph.graph.predecessors(node_id):
            parent_data = graph.graph.nodes[predecessor]
            parents.append(self.format_node_details(parent_data, include_code))
            parents.extend(self.fetch_parents(graph, predecessor, depth - 1, include_code))
        return parents

    def fetch_children(
        self, graph: CallGraph, node_id: str, depth: int, include_code: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Recursively fetches child nodes up to a certain depth, including their code.
        """
        if depth == 0:
            return []
        children = []
        for successor in graph.graph.successors(node_id):
            child_data = graph.graph.nodes[successor]
            children.append(self.format_node_details(child_data, include_code))
            children.extend(self.fetch_children(graph, successor, depth - 1, include_code))
        return children

    def generate_fix_prompt_based_on_context(self, context: Dict[str, Any]) -> str:
        exception_chain_details = "Exception Chain Analysis:\nBelow is the sequence of functions leading to and including the exception, along with their inputs, outputs, and implementation details:\n"

        for index, node_context in enumerate(context["exception_nodes"]):
            node_details = node_context["node_details"]
            is_last_node = index == len(context["exception_nodes"]) - 1

            function_header = (
                f"\n{'-'*20}\nFunction: {node_details['function_name']} at {node_details['file_line']}\n{'-'*20}"
            )
            exception_info = (
                f"Exception Type: {node_details['exception_info']['type']} - {node_details['exception_info']['value']}"
            )
            inputs = f"Inputs (serialization method described at the end):\n{json.dumps(node_details['arguments'], indent=2, default=str)}"
            outputs = (
                f"Outputs:\n{json.dumps(node_details.get('return_value', 'No return value'), indent=2, default=str)}"
            )
            implementation = f"Function Implementation:\n```python\n{node_details['function_implementation']}\n```"

            node_summary = f"{function_header}\n{exception_info}\n{inputs}\n{outputs}\n{implementation}"

            if is_last_node:
                node_summary += "\n(This function is where the exception was raised and propagated.)"

            additional_context_summary = ""
            if node_context["context_children"]:
                additional_context_summary = "\nAdditional context from called functions:\n" + "\n".join(
                    f"- {child['function_name']} at {child['file_line']}:\n  Inputs: {json.dumps(child['arguments'], indent=2, default=str)}\n  Outputs: {json.dumps(child.get('return_value', 'No return value'), indent=2, default=str)}\n  Implementation snippet:\n```python\n{child['function_implementation']}\n```"
                    for child in node_context["context_children"]
                )

            exception_chain_details += f"{node_summary}{additional_context_summary}\n"

        serialization_method_description = """
            Serialization method for input/output values:
            ```python
            def _serialize_variable(self, value: Any) -> Dict[str, Any]:
                try:
                    json_value = json.dumps(value)
                except Exception as e:
                    json_value = str(value)
                return {"python_type": str(type(value)), "json_serialized": json_value}
            ```
        """

        formatting_commands = """
            Please provide me two things: JSON of this form
            1. "confidence" that new code is going to resolve such exceptions (1 to 5)
            2. "function_name" that best to be updated to resolve exception.
            3. "change_reasoning" why do you think change is going to address exception.
            and new proposed function code right escaped with ```python ...``` after it.
            Here's example output:
            {
                "confidence": 5,
                "function_name": "do_stuff",
                "change_reasoning": "to fix above exception the most correct thing is ..."
            }
            ```python
            def do_stuff():
                pass # new implementation
            ```
        """

        prompt = f"{exception_chain_details}\n{serialization_method_description}\n{formatting_commands}"
        return prompt


if __name__ == "__main__":
    import redis

    redis_client = redis.Redis.from_url("redis://localhost:6379/0")
    repo_url = "https://github.com/CaptureFlow/captureflow-py"

    bug_orchestrator = ExceptionPatcher(redis_client=redis_client, repo_url=repo_url)
    bug_orchestrator.run()
