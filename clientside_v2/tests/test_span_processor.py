"""
This test verifies that custom SpanProcessor implemented in CaptureFlow client library
is capable of enriching all spans with python execution context, namely:
    'code.filepath' in span.attributes
    'code.lineno' in span.attributes
    'code.function' in span.attributes
"""

import os

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import get_tracer, get_tracer_provider, set_tracer_provider

from captureflow.distro import CaptureFlowDistro


@pytest.fixture(scope="module")
def setup_tracer_and_exporter():
    # Initialize CaptureFlowDistro
    distro = CaptureFlowDistro()
    distro._configure()

    # Retrieve the global tracer provider
    tracer_provider = get_tracer_provider()

    # Set up in-memory span exporter
    span_exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)

    yield tracer_provider, span_exporter

    # Reset the global tracer provider to avoid conflicts with other tests
    set_tracer_provider(None)


@pytest.fixture(autouse=True)
def clear_spans(setup_tracer_and_exporter):
    _, span_exporter = setup_tracer_and_exporter
    span_exporter.clear()
    yield
    span_exporter.clear()


def relative_path(filepath):
    return os.path.relpath(filepath, start=os.getcwd())


def test_span_processor_adds_frame_info(setup_tracer_and_exporter):
    tracer_provider, span_exporter = setup_tracer_and_exporter
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("test_span") as span:
        pass

    spans = span_exporter.get_finished_spans()

    assert len(spans) == 1
    span = spans[0]

    assert "code.filepath" in span.attributes
    assert "code.lineno" in span.attributes
    assert "code.function" in span.attributes

    expected_filepath = relative_path(__file__)

    assert span.attributes["code.filepath"] == expected_filepath
    assert span.attributes["code.function"] == "test_span_processor_adds_frame_info"
    assert isinstance(span.attributes["code.lineno"], int)


def test_span_processor_in_different_function(setup_tracer_and_exporter):
    tracer_provider, span_exporter = setup_tracer_and_exporter
    tracer = get_tracer(__name__)

    def inner_function():
        with tracer.start_as_current_span("inner_span") as span:
            return span

    span = inner_function()

    spans = span_exporter.get_finished_spans()

    assert len(spans) == 1
    span = spans[0]

    assert "code.filepath" in span.attributes
    assert "code.lineno" in span.attributes
    assert "code.function" in span.attributes

    expected_filepath = relative_path(__file__)

    assert span.attributes["code.filepath"] == expected_filepath
    assert span.attributes["code.function"] == "inner_function"
    assert isinstance(span.attributes["code.lineno"], int)


if __name__ == "__main__":
    pytest.main([__file__])
