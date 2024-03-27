import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.server import app, redis


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_redis(mocker):
    # Mock the get_redis_connection utility function
    mock_redis = MagicMock()
    mocker.patch("src.server.redis", new=mock_redis)
    return mock_redis


@pytest.fixture
def sample_trace():
    trace_path = Path(__file__).parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


def normalize_trace_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes trace data by ensuring optional fields are present even if they were
    originally missing, setting them to None. This makes comparison between expected
    and actual data agnostic to the presence of optional fields with None values.
    """
    # Ensure 'arguments' and 'return_value' are in every execution trace item
    for item in data.get("execution_trace", []):
        if "arguments" not in item:
            item["arguments"] = None
        if "return_value" not in item:
            item["return_value"] = None
    return data


def test_store_trace_log(client, mock_redis, sample_trace):
    repo_url = "https://github.com/NickKuts/capture_flow"
    response = client.post("/api/v1/traces", params={"repository-url": repo_url}, json=sample_trace)

    assert response.status_code == 200
    assert response.json() == {"message": "Trace log saved successfully"}

    # Verify Redis 'set' was called
    assert mock_redis.set.called, "Redis 'set' method was not called"

    # Retrieve the key and JSON data passed to mock_redis.set
    called_args, _ = mock_redis.set.call_args
    key_passed_to_redis, json_data_passed_to_redis = called_args

    # Expected key format now includes the repository URL
    expected_key = f"{repo_url}:{sample_trace['invocation_id']}"
    assert key_passed_to_redis == expected_key, "Key passed to Redis does not match expected format"

    # Deserialize and normalize the data for comparison
    actual_data = json.loads(json_data_passed_to_redis)
    actual_data = normalize_trace_data(actual_data)
    expected_data = normalize_trace_data(sample_trace)

    # Compare normalized data
    assert actual_data == expected_data, "Normalized data passed to Redis does not match expected data"
