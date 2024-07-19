"""
This test verifies that Redis spans include command and arguments:
    'redis.command' in span.attributes
    'redis.command.args' in span.attributes
"""

import pytest
import redis
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
redis_client = redis.Redis(host="localhost", port=6379, db=0)


def perform_redis_operations():
    # Two operations [SET, GET] for test
    redis_client.set("test_key", "test_value")
    value = redis_client.get("test_key")
    return value.decode("utf-8") if value else None


@app.get("/")
async def read_root():
    # Redis operations
    redis_value = perform_redis_operations()
    return {"message": "Hello World", "redis_value": redis_value}


def test_redis_instrumentation(span_exporter):
    client = TestClient(app)

    # Make a request to the FastAPI server
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["redis_value"] == "test_value"

    # Retrieve the spans
    spans = span_exporter.get_finished_spans()
    redis_spans = [span for span in spans if span.attributes.get("db.system") == "redis"]

    assert len(redis_spans) >= 2, "Expected at least two Redis spans"

    set_span = None
    get_span = None

    for span in redis_spans:
        if span.name == "SET":
            set_span = span
        elif span.name == "GET":
            get_span = span

    assert set_span is not None, "SET span not found"
    assert get_span is not None, "GET span not found"

    # Validate SET span
    assert set_span.name == "SET"
    assert set_span.attributes["redis.command"] == "SET"
    assert set_span.attributes["redis.command.args"] == "('test_key', 'test_value')"
    assert set_span.attributes["db.statement"] == "SET ? ?"
    assert set_span.attributes["db.system"] == "redis"
    assert set_span.attributes["net.peer.name"] == "localhost"
    assert set_span.attributes["net.peer.port"] == 6379
    assert set_span.attributes["redis.response"] == "True"

    # Validate GET span
    assert get_span.name == "GET"
    assert get_span.attributes["redis.command"] == "GET"
    assert get_span.attributes["redis.command.args"] == "('test_key',)"
    assert get_span.attributes["db.statement"] == "GET ?"
    assert get_span.attributes["db.system"] == "redis"
    assert get_span.attributes["net.peer.name"] == "localhost"
    assert get_span.attributes["net.peer.port"] == 6379
    assert get_span.attributes["redis.response"] == "b'test_value'"


if __name__ == "__main__":
    pytest.main([__file__])
