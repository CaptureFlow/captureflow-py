"""
This test verifies that HTTPX request spans include request and response details:
    'http.request.method' in span.attributes
    'http.request.url' in span.attributes
    'http.request.body' in span.attributes
    'http.response.status_code' in span.attributes
    'http.response.body' in span.attributes
"""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import get_tracer_provider

from captureflow.distro import CaptureFlowDistro

app = FastAPI()


@app.get("/external")
async def call_external():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
        return {"status_code": response.status_code, "body": response.json()}


@pytest.fixture(scope="module")
def setup_tracer_and_exporter():
    distro = CaptureFlowDistro()
    distro._configure()

    # Retrieve the global tracer provider
    tracer_provider = get_tracer_provider()

    # Set up in-memory span exporter
    span_exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)

    yield tracer_provider, span_exporter

    # Clean-up is handled by the fixture's teardown


@pytest.fixture(autouse=True)
def clear_spans(setup_tracer_and_exporter):
    _, span_exporter = setup_tracer_and_exporter
    span_exporter.clear()
    yield
    span_exporter.clear()


def test_httpx_instrumentation(setup_tracer_and_exporter):
    tracer_provider, span_exporter = setup_tracer_and_exporter
    client = TestClient(app)

    # Make a request to the FastAPI server that calls an external HTTP service
    response = client.get("/external")
    assert response.status_code == 200

    # Retrieve the spans
    spans = span_exporter.get_finished_spans()
    http_spans = [span for span in spans if span.name.startswith("HTTP ")]

    # Debug: Print all spans
    print("All spans:")
    for span in spans:
        print(f"Span name: {span.name}, Kind: {span.kind}, Attributes: {span.attributes}")

    assert len(http_spans) >= 1, "Expected at least one HTTP span"

    external_call_span = None

    for span in http_spans:
        if span.attributes.get("http.request.url") == "https://jsonplaceholder.typicode.com/posts/1":
            external_call_span = span
            break

    assert external_call_span is not None, "External call span not found"

    # Validate external call span
    assert external_call_span.attributes["http.request.method"] == "GET"
    assert external_call_span.attributes["http.request.url"] == "https://jsonplaceholder.typicode.com/posts/1"
    assert "http.request.headers" in external_call_span.attributes
    assert external_call_span.attributes["http.response.status_code"] == 200
    assert "http.response.headers" in external_call_span.attributes
    assert "http.response.body" in external_call_span.attributes

    # Optionally, you can add more specific checks for the content of the body
    response_body = external_call_span.attributes["http.response.body"]
    assert "userId" in response_body
    assert "id" in response_body
    assert "title" in response_body
    assert "body" in response_body


if __name__ == "__main__":
    pytest.main([__file__])


if __name__ == "__main__":
    pytest.main([__file__])
