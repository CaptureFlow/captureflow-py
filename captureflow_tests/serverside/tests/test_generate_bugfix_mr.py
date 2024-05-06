import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import src.server

# load mock data
with open('interactions/_get_repo_by_url_mock_data.json', 'r') as file:
    get_repo_mock_data = json.load(file)
# repeat the above for other interactions/mock data files as needed

# define mock functions
def mock_get_repo_by_url(url):
    return get_repo_mock_data
# repeat the above and modify as per need for other interactions

# use patch decorator to replace actual functions with mock
@patch('src.server._get_repo_by_url', new=mock_get_repo_by_url)
# repeat the above for other interactions in the target function
def test_generate_bugfix_mr():
    client = TestClient(src.server.app)
    response = client.post(
        "/generate_bugfix_mr",
        json={
            "args": [],
            "kwargs": {
                "repo_url": "https://github.com/CaptureFlow/captureflow-py"
            }
        },
    )
    assert response.status_code == 200
    assert response.json() == {"message": "MR generation process started successfully"}

def test_get_repo_by_url():
    result = src.server._get_repo_by_url("https://github.com/CaptureFlow/captureflow-py")
    assert result == get_repo_mock_data
# repeat the above for other interaction functions as needed
