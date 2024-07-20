import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import get_tracer_provider

from captureflow.distro import CaptureFlowDistro


@pytest.fixture(scope="session")
def span_exporter():
    distro = CaptureFlowDistro()
    distro._configure()

    # Retrieve the global tracer provider
    tracer_provider = get_tracer_provider()

    # Set up in-memory span exporter
    span_exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)

    return span_exporter


@pytest.fixture(autouse=True)
def clear_exporter(span_exporter):
    span_exporter.clear()
