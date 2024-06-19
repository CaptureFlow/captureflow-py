"""
This test verifies that custom SpanProcessor implemented in CaptureFlow client library
is capable of enriching all spans with python execution context, namely:
    'code.filepath' in span.attributes
    'code.lineno' in span.attributes
    'code.function' in span.attributes
"""
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import set_tracer_provider, get_tracer

from captureflow.span_processor import FrameInfoSpanProcessor

@pytest.fixture(scope='module')
def setup_tracer_and_exporter():
    tracer_provider = TracerProvider()
    span_exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(span_exporter)
    frame_info_processor = FrameInfoSpanProcessor()

    tracer_provider.add_span_processor(span_processor)
    tracer_provider.add_span_processor(frame_info_processor)

    set_tracer_provider(tracer_provider)
    return tracer_provider, span_exporter

@pytest.fixture(autouse=True)
def clear_spans(setup_tracer_and_exporter):
    _, span_exporter = setup_tracer_and_exporter
    span_exporter.clear()
    yield
    span_exporter.clear()

def test_span_processor_adds_frame_info(setup_tracer_and_exporter):
    tracer_provider, span_exporter = setup_tracer_and_exporter
    tracer = get_tracer(__name__)
    
    with tracer.start_as_current_span("test_span") as span:
        pass

    spans = span_exporter.get_finished_spans()

    assert len(spans) == 1
    span = spans[0]

    assert 'code.filepath' in span.attributes
    assert 'code.lineno' in span.attributes
    assert 'code.function' in span.attributes

    assert span.attributes['code.filepath'] == 'tests/test_span_processor.py'
    assert span.attributes['code.function'] == 'test_span_processor_adds_frame_info'
    assert isinstance(span.attributes['code.lineno'], int)

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

    assert 'code.filepath' in span.attributes
    assert 'code.lineno' in span.attributes
    assert 'code.function' in span.attributes

    assert span.attributes['code.filepath'] == 'tests/test_span_processor.py'
    assert span.attributes['code.function'] == 'inner_function'
    assert isinstance(span.attributes['code.lineno'], int)

if __name__ == "__main__":
    pytest.main([__file__])