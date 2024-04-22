import json
import logging
from typing import Any, Dict, List, Optional

from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.integrations.github_integration import RepoHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FunctionUsageAnalyzer:
    def __init__(self, redis_client: Redis, repo_url: str):
        self.redis_client = redis_client
        self.repo_url = repo_url
        self.repo_helper = RepoHelper(repo_url)

    def get_usage_context(self, file_path: str, function_name: str) -> Dict[str, Any]:
        """Fetch all occurrences where the specified function is called, including its parents and the returned values."""
        all_graphs = self.fetch_all_graphs()
        usage_context = {"calls": [], "implementation": self.fetch_function_implementation(file_path, function_name)}

        for graph in all_graphs:
            for node, attrs in graph.graph.nodes(data=True):
                if attrs["function"] == function_name and attrs.get("file_line", "").startswith(file_path):
                    for parent_id in graph.graph.predecessors(node):
                        parent_attrs = graph.graph.nodes[parent_id]
                        call_details = {
                            "caller_function": parent_attrs["function"],
                            "caller_file_line": parent_attrs["file_line"],
                            "arguments": attrs["arguments"],
                            "return_value": attrs["return_value"],
                        }
                        usage_context["calls"].append(call_details)

        return usage_context

    def fetch_all_graphs(self) -> List[CallGraph]:
        """Retrieve all call graphs from Redis."""
        graphs = []
        search_pattern = f"{self.repo_url}:*"
        for key in self.redis_client.scan_iter(match=search_pattern):
            log_data_json = self.redis_client.get(key)
            if log_data_json:
                log_data = json.loads(log_data_json.decode("utf-8"))
                graphs.append(CallGraph(json.dumps(log_data)))
        return graphs

    def fetch_function_implementation(self, file_path: str, function_name: str) -> Optional[str]:
        """Fetch the current implementation of a function from the GitHub repository."""
        return self.repo_helper.get_function_implementation(file_path, function_name)


if __name__ == "__main__":
    import redis

    redis_client = redis.Redis.from_url("redis://localhost:6379/0")
    repo_url = "https://github.com/YourOrg/YourRepo"

    analyzer = FunctionUsageAnalyzer(redis_client=redis_client, repo_url=repo_url)
    file_path = "src/example_module.py"
    function_name = "example_function"
    usage_context = analyzer.get_usage_context(file_path, function_name)
    print(json.dumps(usage_context, indent=2))
