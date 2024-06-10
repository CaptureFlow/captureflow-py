from opentelemetry.sdk.trace import TracerProvider

# TBD: instrument all top libraries

def _decode_body(body):
    try:
        if isinstance(body, bytes):
            return body.decode("utf-8")
        return body
    except Exception as e:
        return body

def _instrument_fastapi(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.fastapi import (
            FastAPIInstrumentor,
            Span as FastAPISpan,
        )

        def client_response_hook(span: FastAPISpan, message: dict):
            if span and span.is_recording():
                if "body" in message:
                    span.set_attribute("http.response.body", _decode_body(message["body"]))

        FastAPIInstrumentor().instrument(
            client_response_hook=client_response_hook,
            tracer_provider=tracer_provider,
        )
    except ImportError as e:
        pass

def _instrument_requests(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        def request_hook(span, request_obj):
            if request_obj.headers:
                for k, v in request_obj.headers.items():
                    span.set_attribute("http.request.header.%s" % k.lower(), v)
            if request_obj.body:
                span.set_attribute("http.request.body", _decode_body(request_obj.body))

        def response_hook(span, request_obj, response):
            if response.headers:
                for k, v in response.headers.items():
                    span.set_attribute("http.response.header.%s" % k.lower(), v)
            if response.text:
                span.set_attribute("http.response.body", response.text)

        RequestsInstrumentor().instrument(
            request_hook=request_hook,
            response_hook=response_hook,
            tracer_provider=tracer_provider,
        )
    except ImportError as e:
        pass

def apply_instrumentation(tracer_provider: TracerProvider):
    _instrument_fastapi(tracer_provider)
    _instrument_requests(tracer_provider)