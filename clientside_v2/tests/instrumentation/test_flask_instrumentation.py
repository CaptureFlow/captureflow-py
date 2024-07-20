"""
This test verifies that Flask request spans include request and response details:
    'http.request.method' in span.attributes
    'http.request.url' in span.attributes
    'http.request.body' in span.attributes
    'http.response.status_code' in span.attributes
    'http.response.body' in span.attributes
"""

import pytest
import requests
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/external", methods=["GET"])
def call_external():
    response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
    return jsonify({"status_code": response.status_code, "body": response.json()})


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_flask_instrumentation(span_exporter, client):
    # Make a request to the Flask server that calls an external HTTP service
    response = client.get("/external")
    assert response.status_code == 200

    # Retrieve the spans
    spans = span_exporter.get_finished_spans()
    flask_spans = [span for span in spans if span.name.startswith("HTTP GET /external")]

    # Debug: Print all spans
    print("All spans:")
    for span in spans:
        print(f"Span name: {span.name}, Kind: {span.kind}, Attributes: {span.attributes}")

    assert len(flask_spans) == 1, "Expected at least one Flask span"

    flask_span = flask_spans[0]

    # Validate Flask span
    assert flask_span.attributes["http.method"] == "GET"
    assert flask_span.attributes["http.url"].endswith("/external")
    assert "http.request.headers" in flask_span.attributes
    assert flask_span.attributes["http.status_code"] == 200
    assert "http.response.headers" in flask_span.attributes
    assert "http.response.body" in flask_span.attributes

    response_body = flask_span.attributes["http.response.body"]
    assert "status_code" in response_body
    assert "body" in response_body


if __name__ == "__main__":
    pytest.main([__file__])
