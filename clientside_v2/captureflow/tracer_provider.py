# captureflow/tracer_provider.py
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from captureflow.config import CF_DEBUG, CF_OTLP_ENDPOINT

def get_tracer_provider(resource: Resource) -> TracerProvider:
    trace_provider = TracerProvider(resource=resource)
    
    # Replace with Jaeger
    otlp_exporter = OTLPSpanExporter(
        endpoint=CF_OTLP_ENDPOINT,
        insecure=True
    )
    
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    if CF_DEBUG:
        trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    
    return trace_provider
