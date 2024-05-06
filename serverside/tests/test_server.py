import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.server import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_redis(mocker):
    mock_redis = MagicMock()
    mocker.patch("src.server.redis", new=mock_redis)
    return mock_redis


@pytest.fixture
def sample_trace():
    trace_path = Path(__file__).parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


@pytest.fixture
def sample_trace_with_exception():
    trace_path = Path(__file__).parent / "assets" / "sample_trace_with_exception.json"
    with open(trace_path) as f:
        return json.load(f)


def normalize_trace_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes trace data by ensuring optional fields are present and correctly formatted.
    """

    if "output" not in data:
        data["output"] = None

    return data


def test_store_trace_log(client, mock_redis, sample_trace):
    repo_url = "https://github.com/NickKuts/capture_flow"
    response = client.post("/api/v1/traces", params={"repository-url": repo_url}, json=sample_trace)

    assert response.status_code == 200
    assert response.json() == {"message": "Trace log saved successfully"}

    # Verify Redis 'set' was called
    assert mock_redis.set.called, "Redis 'set' method was not called"
    called_args, _ = mock_redis.set.call_args
    key_passed_to_redis, json_data_passed_to_redis = called_args

    expected_key = f"{repo_url}:{sample_trace['invocation_id']}"
    assert key_passed_to_redis == expected_key, "Key passed to Redis does not match expected format"

    # Deserialize & normalize
    actual_data = json.loads(json_data_passed_to_redis)
    actual_data = normalize_trace_data(actual_data)
    expected_data = normalize_trace_data(sample_trace)

    # Compare normalized data
    assert actual_data == expected_data, "Normalized data passed to Redis does not match expected data"


def test_store_trace_log_with_exception(client, mock_redis, sample_trace_with_exception):
    repo_url = "https://github.com/NickKuts/capture_flow"
    response = client.post("/api/v1/traces", params={"repository-url": repo_url}, json=sample_trace_with_exception)

    assert response.status_code == 200
    assert response.json() == {"message": "Trace log saved successfully"}

    # Verify Redis 'set' was called
    assert mock_redis.set.called, "Redis 'set' method was not called"
    called_args, _ = mock_redis.set.call_args
    key_passed_to_redis, json_data_passed_to_redis = called_args

    expected_key = f"{repo_url}:{sample_trace_with_exception['invocation_id']}"
    assert key_passed_to_redis == expected_key, "Key passed to Redis does not match expected format"

    # Deserialize & normalize
    actual_data = json.loads(json_data_passed_to_redis)
    actual_data = normalize_trace_data(actual_data)
    expected_data = normalize_trace_data(sample_trace_with_exception)

    # Compare normalized data
    assert actual_data == expected_data, "Normalized data passed to Redis does not match expected data"
