import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from captureflow.tracer import Tracer

app = FastAPI()
tracer = Tracer(mode="local")

@app.get("/add/{x}/{y}")
@tracer.trace_endpoint
async def add(x: int, y: int):
    return {"result": x + y}

@pytest.mark.asyncio
async def test_trace_endpoint_fastapi():
    with patch('captureflow.tracer.Tracer._write_trace_log') as mock_log:
        with TestClient(app) as client:
            response = client.get("/add/2/3")
            assert response.status_code == 200
            assert response.json() == {"result": 5}

        mock_log.assert_called_once()
        log_data = mock_log.call_args[0][0]

        assert log_data["endpoint"] == "add"

        assert "x" in log_data["input"]["kwargs"] and "y" in log_data["input"]["kwargs"]

        assert log_data["input"]["kwargs"]["x"]["json_serialized"] == '2'
        assert log_data["input"]["kwargs"]["y"]["json_serialized"] == '3'

        assert len(log_data["execution_trace"]) > 0
        assert log_data["execution_trace"][0]["event"] == "call"
        assert log_data["output"]["result"]["json_serialized"] == '{"result": 5}'
