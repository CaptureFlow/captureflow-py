import json
import socket
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.call_graph import CallGraph
from src.utils.test_creator import TestCoverageCreator

@pytest.fixture(autouse=True)
def disable_network_access():
    with patch('socket.socket') as mock_socket, patch('socket.create_connection') as mock_create_conn:
        mock_socket.side_effect = Exception("Network access not allowed during tests!")
        mock_create_conn.side_effect = Exception("Network access not allowed during tests!")
        yield

@pytest.fixture
def sample_trace_json():
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)

@pytest.fixture
def mock_redis_client(sample_trace_json):
    with patch("redis.Redis") as MockRedis:
        mock_redis = MockRedis()
        mock_redis.scan_iter.return_value = ['key:1']
        mock_redis.get.return_value = json.dumps(sample_trace_json).encode("utf-8")
        yield mock_redis

@pytest.fixture
def mock_openai_helper():
    with patch("src.utils.integrations.openai_integration.OpenAIHelper") as MockOpenAIHelper:
        mock_helper = MockOpenAIHelper()
        mock_helper.call_chatgpt.side_effect = [
            json.dumps(
                {
                    "interactions": [
                        {"type": "DB_INTERACTION", "details": "Mock DB query", "mock_idea": "mock_db_query()"}
                    ]
                }
            ),  # Second call for INTERNAL function
            "```python\ndef test_calculate_average(): assert True```",  # Second call for generating full pytest code
        ]
        mock_helper.extract_first_code_block.return_value = "def test_calculate_average(): assert True"
        yield mock_helper

@pytest.fixture
def github_data_mapping():
    return {
        "calculate_average": {
            "github_file_path": "/path/to/function.py",
            "github_function_implementation": {
                "start_line": 10,
                "end_line": 20,
                "content": "def calculate_average(): pass",
            },
            "github_file_content": "import numpy\ndef calculcate_average(): pass"
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
    with patch("src.utils.test_creator.RepoHelper", return_value=mock_repo_helper), \
         patch("src.utils.test_creator.OpenAIHelper", return_value=mock_openai_helper):

        test_creator = TestCoverageCreator(redis_client=mock_redis_client, repo_url="http://sample.repo.url")
        test_creator.run()

        # Check interactions for each ChatGPT call
        interaction_call = mock_openai_helper.call_chatgpt.call_args_list[0]
        test_generation_call = mock_openai_helper.call_chatgpt.call_args_list[1]

        assert "Analyze the following Python code" in interaction_call[0][0]
        assert "Write a complete pytest file" in test_generation_call[0][0]

        # Ensure the correct handling of responses
        assert mock_openai_helper.extract_first_code_block.called
        pytest_code = mock_openai_helper.extract_first_code_block.return_value
        assert "def test_calculate_average(): assert True" == pytest_code.strip()

        # Check if enriched GitHub data & mocking hints were considered in the prompt
        assert "Write a complete pytest file for testing the WSGI app entry point 'calculate_average'" in test_generation_call[0][0]
        assert "External interactions to mock (follow the instructions below):\nmock_db_query()" in test_generation_call[0][0]
