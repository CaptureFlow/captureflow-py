import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from redis import Redis

from src.utils.call_graph import CallGraph
from src.utils.orchestration import Orchestrator


@pytest.fixture
def sample_trace_json():
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


@pytest.fixture
def mock_redis_client(sample_trace_json):
    mock_client = MagicMock(spec=Redis)
    encoded_trace = json.dumps(sample_trace_json).encode("utf-8")
    # Return the same encoded sample trace for each key for simplicity
    mock_client.get.side_effect = lambda key: (
        encoded_trace if key in ["trace1", "trace2", "trace3"] else None
    )
    mock_client.scan_iter.return_value = ["trace1", "trace2", "trace3"]
    return mock_client


@pytest.fixture
def mock_repo_helper():
    mock_helper = MagicMock()
    mock_helper.enrich_callgraph_with_github_context.return_value = None
    return mock_helper


def test_build_graphs_from_redis(
    mock_repo_helper, mock_redis_client, mock_openai_helper, sample_trace_json
):
    with patch(
        "src.utils.orchestration.RepoHelper", return_value=mock_repo_helper
    ), patch("src.utils.orchestration.OpenAIHelper", return_value=mock_openai_helper):
        orchestrator = Orchestrator(
            redis_client=mock_redis_client,
            repo_url="https://github.com/NickKuts/capture_flow",
        )

        call_graphs = orchestrator.build_graphs_from_redis(
            mock_redis_client, "https://github.com/NickKuts/capture_flow"
        )

        # Assertions
        assert isinstance(call_graphs, list)
        assert all(isinstance(graph, CallGraph) for graph in call_graphs)
        assert len(call_graphs) == 3  # Since we mocked three traces

        # Verify Redis client interaction
        mock_redis_client.scan_iter.assert_called_once_with(
            match="https://github.com/NickKuts/capture_flow:*"
        )
        assert mock_redis_client.get.call_count == 3
