# tracer.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from functools import wraps
import json

# Configure OpenTelemetry
def configure_tracer():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # Configure Jaeger Exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name='localhost',  # Change to your Jaeger agent host
        agent_port=6831               # Change to your Jaeger agent port
    )
    provider.add_span_processor(SimpleSpanProcessor(jaeger_exporter))

    # Instrument libraries
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    PymongoInstrumentor().instrument()

# Decorator to trace function calls
def trace_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(func.__name__) as span:
            span.set_attribute("args", json.dumps(args, default=str))
            span.set_attribute("kwargs", json.dumps(kwargs, default=str))
            try:
                result = func(*args, **kwargs)
                span.set_attribute("result", json.dumps(result, default=str))
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("error", True)
                raise
    return wrapper

# Configure the tracer when the module is imported
configure_tracer()
