# Necessary imports
import pytest
import json
from fastapi.testclient import TestClient
from mock import MagicMock, patch
from src.server import app

# Initialize Test Client
client = TestClient(app)

# Mock JSON Payloads
with open("interactions/generate_bugfix_mr_mock_data.json", "r") as f:
    mock_generate_bugfix_mr_data = json.load(f)

with open("interactions/_get_repo_by_url_mock_data.json", "r") as f:
    mock_get_repo_by_url_data = json.load(f)

with open("interactions/_build_index_mock_data.json", "r") as f:
    mock_build_index_data = json.load(f)

with open("interactions/_create_openai_client_mock_data.json", "r") as f:
    mock_create_openai_client_data = json.load(f)

with open("interactions/run_mock_data.json", "r") as f:
    mock_run_data = json.load(f)

with open("interactions/build_graphs_from_redis_mock_data.json", "r") as f:
    mock_build_graphs_from_redis_data = json.load(f)

with open("interactions/enrich_node_with_github_data_mock_data.json", "r") as f:
    mock_enrich_node_data = json.load(f)


# We define a single test function for the endpoint
@patch.multiple('src.server',
                _get_repo_by_url = mock_get_repo_by_url_data,
                _build_index = mock_build_index_data,
                _create_openai_client = mock_create_openai_client_data,
                run = mock_run_data,
                build_graphs_from_redis = mock_build_graphs_from_redis_data,
                enrich_node_with_github_data = mock_enrich_node_data)
def test_generate_bugfix_mr():

    # Generate Bugfix MR
    response = client.post(
        "/generate_bugfix_mr",
        json={
            "args": [],
            "kwargs": {
                "repo_url": "https://github.com/CaptureFlow/captureflow-py"
                }
            }
        )

    # Validate response
    assert response.status_code == 200
    assert response.json() == {"message": "MR generation process started successfully"}
