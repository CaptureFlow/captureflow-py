import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Load Mock JSON Payloads
with open("generate_bugfix_mr_mock_data.json", "r") as f:
    mock_generate_bugfix_mr_data = json.load(f)

with open("_build_index_mock_data.json", "r") as f:
    mock_build_index_data = json.load(f)

with open("enrich_node_with_github_data_mock_data.json", "r") as f:
    mock_enrich_node_data = json.load(f)

# Mock Redis Connection
mock_redis_connection = MagicMock()


# Patch the methods with mock data
@patch("src.utils.integrations.github_integration.RepoHelper._build_index", return_value=mock_build_index_data)
@patch(
    "src.utils.integrations.github_integration.RepoHelper.enrich_node_with_github_data",
    return_value=mock_enrich_node_data,
)
@patch("src.utils.integrations.github_integration.RepoHelper._get_repo_by_url", return_value=None)
@patch("src.utils.integrations.redis_integration.get_redis_connection", return_value=mock_redis_connection)
def test_generate_bugfix_mr(
    mock_build_index, mock_enrich_node_with_github_data, mock_get_repo_by_url, mock_redis_connection
):
    from src.server import app

    client = TestClient(app)
    response = client.post("/api/v1/merge-requests/bugfix?repository-url=https://github.com/CaptureFlow/captureflow-py")

    print("RESPONSE = ", response.json())

    # Validate the response
    assert response.status_code == 200
    assert response.json() == {"message": "MR generation process started successfully"}

    # Optional: Add assertions to verify that the mocked methods were called if needed
    # mock_get_repo_by_url.assert_called_once()
