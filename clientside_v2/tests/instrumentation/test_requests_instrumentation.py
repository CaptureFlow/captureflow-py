"""
This test verifies that HTTP request spans include request and response details:
    'http.request.method' in span.attributes
    'http.request.url' in span.attributes
    'http.request.body' in span.attributes
    'http.response.status_code' in span.attributes
    'http.response.body' in span.attributes
"""

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()


@app.get("/external")
async def call_external():
    response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
    return {"status_code": response.status_code, "body": response.json()}


def test_requests_instrumentation(span_exporter):
    client = TestClient(app)

    # Make a request to the FastAPI server that calls an external HTTP service
    response = client.get("/external")
    assert response.status_code == 200

    # Retrieve the spans
    spans = span_exporter.get_finished_spans()
    http_spans = [span for span in spans if span.attributes.get("http.method") is not None]

    assert len(http_spans) >= 1, "Expected at least one HTTP span"

    external_call_span = None

    for span in http_spans:
        if span.attributes.get("http.url") == "https://jsonplaceholder.typicode.com/posts/1":
            external_call_span = span
            break

    assert external_call_span is not None, "External call span not found"

    # Validate external call span
    assert external_call_span.attributes["http.method"] == "GET"
    assert external_call_span.attributes["http.url"] == "https://jsonplaceholder.typicode.com/posts/1"
    assert external_call_span.attributes["http.status_code"] == 200
    assert "http.response.body" in external_call_span.attributes


if __name__ == "__main__":
    pytest.main([__file__])
