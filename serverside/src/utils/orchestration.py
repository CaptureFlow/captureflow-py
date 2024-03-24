import json
import logging

from typing import Any, Dict, List, Optional, Tuple
from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.integrations.github_integration import RepoHelper
from src.utils.integrations.openai_integration import OpenAIHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Orchestrator:
    def __init__(self, redis_client: Redis, repo_url: str):
        self.repo_url = repo_url

        self.redis_client = redis_client
        self.repo_helper = RepoHelper(repo_url)
        self.gpt_helper = OpenAIHelper()

    def run(self):
        # Build call graphs from logs
        graphs = self.build_graphs_from_redis(self.redis_client, self.repo_url)
        function_name = None

        # Enrich call graphs with GitHub context
        for graph in graphs:
            self.repo_helper.enrich_callgraph_with_github_context(graph)

        improvement_candidates = self.find_improvement_candidates(graphs, top_n=5)

        for function_name, score in improvement_candidates.items():
            if score == 10:
                function_name = function_name
                break

        if not function_name:
            raise Exception("There is no function that can be easily improved.")

        # Improve and validate the function implementation
        votes, new_implementation, node_changed = self.improve_and_validate(
            graphs, function_name
        )

        # Decide whether to create a pull request based on the validation outcome
        if self.should_create_pull_request(votes):
            logger.info("Majority approval received. Creating a pull request...")
            self.repo_helper.create_pull_request_with_new_function(
                node_changed, new_implementation, self.gpt_helper
            )
        else:
            logger.warn("Insufficient approval for changes. No pull request created.")

    def find_improvement_candidates(
        self, graphs: List[CallGraph], top_n: int = 5
    ) -> Dict[str, float]:
        N_APPEARANCES = 1
        function_nodes = {}

        for graph in graphs:
            for node_id, attrs in graph.graph.nodes(data=True):
                if (
                    "function" in attrs
                    and attrs["tag"] == "INTERNAL"
                    and "github_function_implementation" in attrs
                ):
                    function_name = attrs["function"]
                    if (
                        function_name not in function_nodes
                        or function_nodes[function_name]["count"] < N_APPEARANCES
                    ):
                        function_nodes[function_name] = {"node": attrs, "count": 1}
                    else:
                        function_nodes[function_name]["count"] += 1

        # Filter candidates based on N_APPEARANCES threshold
        preselected_candidates = {
            fn: data
            for fn, data in function_nodes.items()
            if data["count"] >= N_APPEARANCES
        }

        # Score candidates using GPT and collect results
        candidate_scores = {}
        for candidate, data in preselected_candidates.items():
            node = data["node"]
            prompt = self.gpt_helper.generate_initial_scoring_query(node)
            gpt_response = self.gpt_helper.call_chatgpt(prompt)

            # Attempt to parse the GPT response into a dictionary
            try:
                gpt_response_dict = json.loads(gpt_response)
            except json.JSONDecodeError:
                logger.exception(
                    f"Failed to decode GPT response for {candidate}: {gpt_response}"
                )
                continue  # Skip to the next candidate if parsing fails

            # Only store scores for candidates marked as easy to optimize
            if gpt_response_dict.get("easy_to_optimize") == "EASY_TO_OPTIMIZE":
                # Directly use the quality score from the GPT response for candidates considered easy to improve
                candidate_scores[candidate] = gpt_response_dict.get(
                    "quality_score", 0
                )  # Default to 0 if not available

        # Assuming you want to proceed only with candidates having a specific minimum quality score,
        # for example, keep only those with scores > 5
        final_candidates = {
            fn: score for fn, score in candidate_scores.items() if score > 5
        }

        # Sort and return the top N scored candidates based on their quality score
        top_candidates = dict(
            sorted(final_candidates.items(), key=lambda item: item[1], reverse=True)[
                :top_n
            ]
        )

        return top_candidates

    def improve_and_validate(
        self, graphs: List[CallGraph], function_name: str
    ) -> Tuple[Dict[str, int], Optional[str], Optional[Any]]:
        nodes = extract_function_info(graphs, function_name)

        if not nodes:
            logger.warning("No nodes found for the function:", function_name)
            return {}, None, None

        prompt = self.gpt_helper.generate_improvement_query(graphs[0], nodes[0])
        response_text = self.gpt_helper.call_chatgpt(prompt)
        new_implementation = self.gpt_helper.extract_first_code_block(response_text)

        if new_implementation:
            logger.warning("New implementation extracted. Validating...")
            votes = validate_graphs(
                graphs, new_implementation, function_name, self.gpt_helper
            )
            logger.info("Validation votes:", votes)
            return votes, new_implementation, nodes[0]
        else:
            logger.exception(
                "Failed to extract a new implementation from GPT's response."
            )
            return {"yes": 0, "maybe": 0, "no": 1}, None, None

    def should_create_pull_request(self, votes: Dict[str, int]) -> bool:
        total_votes = sum(votes.values())
        yes_percentage = (votes["yes"] / total_votes) * 100 if total_votes > 0 else 0
        return yes_percentage > 90

    @staticmethod
    def build_graphs_from_redis(redis_client: Redis, repo_name: str) -> List[CallGraph]:
        graphs = []
        # Construct the search pattern for keys related to `repo_name`
        search_pattern = f"{repo_name}:*"

        # Fetch all keys matching the pattern
        for key in redis_client.scan_iter(match=search_pattern):
            log_data_json = redis_client.get(key)
            if log_data_json:
                log_data = json.loads(log_data_json.decode("utf-8"))
                graphs.append(CallGraph(json.dumps(log_data)))
        return graphs


def extract_function_info(graphs, function_name):
    nodes = []
    for graph in graphs:
        for node_id, node in graph.graph.nodes(data=True):
            if node.get("function") == function_name:
                nodes.append(node)
    return nodes


def validate_graphs(
    graphs: List[CallGraph],
    new_implementation: str,
    function_name: str,
    gpt_helper: OpenAIHelper,
) -> Dict[str, int]:
    yes_votes, maybe_votes, no_votes = 0, 0, 0

    for graph in graphs:
        for node_id, node in graph.graph.nodes(data=True):
            if node.get("function") == function_name and node.get("tag") == "INTERNAL":
                updated_node = node.copy()
                updated_node["github_function_implementation"] = {
                    "content": new_implementation
                }
                simulation_q = gpt_helper.generate_simulation_query(graph, updated_node)
                answer = gpt_helper.call_chatgpt(simulation_q)

                if "MUST_WORK" in answer:
                    yes_votes += 1
                elif "MAYBE_WORK" in answer:
                    maybe_votes += 1
                elif "DOESNT_WORK" in answer:
                    no_votes += 1

    return {"yes": yes_votes, "maybe": maybe_votes, "no": no_votes}


if __name__ == "__main__":

    def load_sample_trace(log_file_path):
        with open(log_file_path, "r") as file:
            return json.load(file)

    def insert_sample_trace_into_redis(redis_client, repo_url, sample_trace_data):
        # Construct a unique key for each sample trace. You might want to use a more sophisticated key scheme.
        trace_key_1 = f"{repo_url}:sample_trace_1"
        trace_key_2 = f"{repo_url}:sample_trace_2"

        # Convert the sample trace data to a JSON string
        sample_trace_json = json.dumps(sample_trace_data)

        # Insert the sample trace data into Redis under two different keys
        redis_client.set(trace_key_1, sample_trace_json)
        redis_client.set(trace_key_2, sample_trace_json)

    REPO_URL = "https://github.com/NickKuts/capture_flow"
    sample_trace_data = load_sample_trace(
        "/Users/nikitakutc/projects/captureflow-py/serverside/tests/assets/sample_trace.json"
    )

    from src.config import REDIS_URL

    redis_client = Redis(REDIS_URL)

    # Insert the sample trace data into Redis
    insert_sample_trace_into_redis(redis_client, REPO_URL, sample_trace_data)

    # Now, construct the Orchestrator with the Redis client and the repository URL
    orchestrator = Orchestrator(redis_client, REPO_URL)

    # Run the orchestrator to process the inserted trace data
    orchestrator.run()
