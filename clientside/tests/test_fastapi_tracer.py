import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.captureflow.tracer import Tracer

app = FastAPI()

tracer = Tracer(
    repo_url="https://github.com/DummyUser/DummyRepo",
    server_base_url="http://127.0.0.1:8000",
)


@app.get("/add/{x}/{y}")
@tracer.trace_endpoint
async def add(x: int, y: int):
    return {"result": x + y}


@pytest.mark.asyncio
async def test_trace_endpoint_fastapi():
    with patch("src.captureflow.tracer.Tracer._send_trace_log") as mock_log:
        with TestClient(app) as client:
            response = client.get("/add/2/3")
            assert response.status_code == 200
            assert response.json() == {"result": 5}

        mock_log.assert_called_once()
        log_data = mock_log.call_args[0][0]  # Get the context data passed to _send_trace_log

        assert log_data["endpoint"] == "add"

        assert "x" in log_data["input"]["kwargs"] and "y" in log_data["input"]["kwargs"]
        assert log_data["input"]["kwargs"]["x"]["json_serialized"] == json.dumps(2)  # Use json.dumps for consistency
        assert log_data["input"]["kwargs"]["y"]["json_serialized"] == json.dumps(3)

        assert len(log_data["execution_trace"]) > 0
        assert log_data["execution_trace"][0]["event"] == "call"
        assert log_data["output"]["result"]["json_serialized"] == json.dumps({"result": 5})

        # Additional checks for type information
        assert log_data["input"]["kwargs"]["x"]["python_type"] == "<class 'int'>"
        assert log_data["input"]["kwargs"]["y"]["python_type"] == "<class 'int'>"
        assert log_data["output"]["result"]["python_type"] == "<class 'dict'>"


@app.get("/divide/{x}/{y}")
@tracer.trace_endpoint
async def divide(x: int, y: int):
    return {"result": x / y}


@pytest.mark.asyncio
async def test_trace_endpoint_with_exception():
    with patch("src.captureflow.tracer.Tracer._send_trace_log") as mock_log:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/divide/10/0")
            assert response.status_code == 500

        mock_log.assert_called_once()
        log_data = mock_log.call_args[0][0]

        assert log_data["endpoint"] == "divide"
        assert "x" in log_data["input"]["kwargs"] and "y" in log_data["input"]["kwargs"]
        assert log_data["input"]["kwargs"]["x"]["json_serialized"] == json.dumps(10)
        assert log_data["input"]["kwargs"]["y"]["json_serialized"] == json.dumps(0)

        exception_events = [e for e in log_data["execution_trace"] if e["event"] == "exception"]
        assert len(exception_events) > 0, "Exception event not found in the execution trace"
        exception_event = exception_events[0]
        assert "ZeroDivisionError" in exception_event["exception_info"]["type"], "Expected ZeroDivisionError"
        assert "division by zero" in exception_event["exception_info"]["value"], "Expected 'division by zero' message"
