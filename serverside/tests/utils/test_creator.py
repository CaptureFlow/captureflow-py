import json
import socket
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.call_graph import CallGraph
from src.utils.integrations.github_integration import RepoHelper
from src.utils.integrations.openai_integration import OpenAIHelper
from src.utils.test_creator import TestCoverageCreator


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
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


@pytest.fixture
def mock_redis_client(sample_trace_json):
    with patch("redis.Redis") as MockRedis:
        mock_redis_client = MockRedis()
        mock_redis_client.scan_iter.return_value = [f"key:{i}" for i in range(1)]
        mock_redis_client.get.side_effect = lambda k: json.dumps(sample_trace_json).encode("utf-8")
        yield mock_redis_client


@pytest.fixture
def mock_openai_helper():
    with patch("src.utils.integrations.openai_integration.OpenAIHelper") as MockOpenAIHelper:
        mock_helper = MockOpenAIHelper()
        mock_helper.call_chatgpt.side_effect = [
            json.dumps(
                {
                    "interactions": [
                        {"type": "DB_INTERACTION", "details": "Mock DB query", "mock_code": "mock_db_query()"}
                    ]
                }
            ),  # Second call for INTERNAL function
            "```python\ndef test_calculate_average(): assert True```",  # Second call for generating full pytest code
        ]
        mock_helper.extract_pytest_code.return_value = "def test_calculate_average(): assert True"
        yield mock_helper


@pytest.fixture
def github_data_mapping():
    return {
        "calculate_average": {
            "github_file_path": "/path/to/calculate_average.py",
            "github_function_implementation": {
                "start_line": 1,
                "end_line": 5,
                "content": "def calculate_average(values): return sum(values) / len(values)",
            },
            "github_file_content": "import numpy\n def calculate_average(values): return sum(values) / len(values)",
        }
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


def test_test_coverage_creator_run(mock_redis_client, mock_openai_helper, mock_repo_helper):
    with patch("src.utils.test_creator.RepoHelper", return_value=mock_repo_helper), patch(
        "src.utils.test_creator.OpenAIHelper", return_value=mock_openai_helper
    ):
        test_creator = TestCoverageCreator(redis_client=mock_redis_client, repo_url="http://sample.repo.url")
        test_creator.run()

        external_interactions_call = mock_openai_helper.call_chatgpt.call_args_list[0][0][0]
        pytest_generation_call = mock_openai_helper.call_chatgpt.call_args_list[1][0][0]

        assert "Analyze the following Python code" in external_interactions_call
        assert "Write a complete pytest file" in pytest_generation_call

        # Validate the call to extract_pytest_code
        pytest_code = mock_openai_helper.extract_pytest_code(mock_openai_helper.call_chatgpt.return_value)
        expected_pytest_code = "def test_calculate_average(): assert True"
        assert pytest_code.strip() == expected_pytest_code.strip()

        # Check that the enriched GitHub data was used in the prompt
        enriched_data_used = "def calculate_average(values): return sum(values) / len(values)" in pytest_generation_call
        assert enriched_data_used