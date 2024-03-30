import json
import socket
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.call_graph import CallGraph
from src.utils.exception_patcher import ExceptionPatcher


@pytest.fixture(autouse=True)
def disable_network_access():
    def guard(*args, **kwargs):
        raise Exception("Network access not allowed during tests!")

    orig_socket = socket.socket
    orig_create_connection = socket.create_connection
    socket.socket = guard
    socket.create_connection = guard

    yield

    socket.socket = orig_socket
    socket.create_connection = orig_create_connection


@pytest.fixture
def sample_trace_json():
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace_with_exception.json"
    with open(trace_path) as f:
        return json.load(f)


@pytest.fixture
def mock_redis_client(sample_trace_json):
    with patch("redis.Redis") as MockRedis:
        mock_redis_client = MockRedis()
        mock_redis_client.scan_iter.return_value = [f"key:{i}" for i in range(3)]
        mock_redis_client.get.side_effect = lambda k: json.dumps(sample_trace_json).encode("utf-8")
        yield mock_redis_client


@pytest.fixture
def mock_openai_helper():
    with patch("src.utils.integrations.openai_integration.OpenAIHelper") as MockOpenAIHelper:
        mock_helper = MockOpenAIHelper()
        # Here you should define the behavior of call_chatgpt, e.g. returning a fake response
        mock_helper.call_chatgpt.return_value = """
        ```json
        {"confidence": 5, "function_name": "calculate_avg", "new_function_code": "def dummy_function(): pass\\n", "change_reasoning": "Just a mock response."}
        ```
        """
        yield mock_helper


@pytest.fixture
def github_data_mapping():
    return {
        "calculate_average": {
            "github_file_path": "/path/to/calculate_average.py",
            "github_function_implementation": {
                "start_line": 1,
                "end_line": 5,
                "content": "def calculate_average(): pass",
            },
            "github_file_content": "import numpy\ndef calculate_average(): pass",
        },
        "calculate_sum": {
            "github_file_path": "/path/to/calculate_sum.py",
            "github_function_implementation": {
                "start_line": 1,
                "end_line": 5,
                "content": "def calculate_sum(): pass",
            },
            "github_file_content": "import numpy\ndef calculate_sum(): pass",
        },
    }


@pytest.fixture
def mock_repo_helper(github_data_mapping):
    def mock_enrich_callgraph_with_github_context(callgraph: CallGraph) -> None:
        for node_id in callgraph.graph.nodes:
            node = callgraph.graph.nodes[node_id]
            if "function" in node:
                enriched_node = github_data_mapping.get(node["function"])
                if enriched_node:
                    callgraph.graph.nodes[node_id].update(enriched_node)

    mock_instance = Mock()
    mock_instance._get_repo_by_url.return_value = Mock(html_url="http://sample.repo.url")
    mock_instance.enrich_callgraph_with_github_context.side_effect = mock_enrich_callgraph_with_github_context

    return mock_instance


def test_bug_orchestrator_run(mock_redis_client, mock_openai_helper, mock_repo_helper):
    with patch("src.utils.exception_patcher.RepoHelper", return_value=mock_repo_helper), patch(
        "src.utils.exception_patcher.OpenAIHelper", return_value=mock_openai_helper
    ):
        orchestrator = ExceptionPatcher(redis_client=mock_redis_client, repo_url="http://sample.repo.url")
        orchestrator.run()

        # Call arguments for mock_openai_helper.call_chatgpt
        actual_prompt = mock_openai_helper.call_chatgpt.call_args[0][0]

        assert "Exception Chain Analysis:" in actual_prompt
        assert "Function: calculate_average" in actual_prompt
        assert "Function: calculate_avg" in actual_prompt
        assert "ZeroDivisionError - division by zero" in actual_prompt
        assert "Please output new production implementation of a single function" in actual_prompt
        expected_function_implementation_snippets = ["def calculate_average(): pass", "def calculate_sum(): pass"]
        for snippet in expected_function_implementation_snippets:
            assert snippet in actual_prompt

        # Validate the call to create_pull_request_with_new_function
        mock_repo_helper.create_pull_request_with_new_function.assert_called()
        called_args = mock_repo_helper.create_pull_request_with_new_function.call_args[0]
        node_arg = called_args[0]

        # Validate key fields of the node argument
        assert node_arg.get("function") == "calculate_avg"
        assert node_arg.get("did_raise") is True
        assert node_arg.get("unhandled_exception").get("type") == "ZeroDivisionError"
        assert node_arg.get("unhandled_exception").get("value") == "division by zero"

        new_function_code = called_args[1]
        expected_new_function_code = "def dummy_function(): pass"
        assert new_function_code.strip() == expected_new_function_code.strip()
