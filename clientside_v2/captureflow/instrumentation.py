import functools

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import SpanKind

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
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.fastapi import Span as FastAPISpan

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


def _instrument_httpx(tracer_provider=None):
    import httpx

    tracer = trace.get_tracer(__name__, tracer_provider=tracer_provider)

    def _capture_request(request: httpx.Request, span: trace.Span):
        span.set_attribute("http.lol", 1)
        span.set_attribute("http.request.method", request.method)
        span.set_attribute("http.request.url", str(request.url))
        span.set_attribute("http.request.headers", str(dict(request.headers)))
        if request.content:
            span.set_attribute("http.request.body", request.content.decode("utf-8", errors="replace"))

    def _capture_response(response: httpx.Response, span: trace.Span):
        span.set_attribute("http.response.body", response.text)
        span.set_attribute("http.response.status_code", response.status_code)
        span.set_attribute("http.response.headers", str(dict(response.headers)))

    def instrumented_send(self, request: httpx.Request, **kwargs) -> httpx.Response:
        with tracer.start_as_current_span(
            f"HTTP {request.method}",
            kind=SpanKind.CLIENT,
        ) as span:
            _capture_request(request, span)
            response = self._original_send(request, **kwargs)
            _capture_response(response, span)
            return response

    async def async_instrumented_send(self, request: httpx.Request, **kwargs) -> httpx.Response:
        with tracer.start_as_current_span(
            f"HTTP {request.method}",
            kind=SpanKind.CLIENT,
        ) as span:
            _capture_request(request, span)
            response = await self._original_send(request, **kwargs)
            _capture_response(response, span)
            return response

    original_client = httpx.Client
    original_async_client = httpx.AsyncClient

    class InstrumentedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._original_send = super().send
            self.send = functools.partial(instrumented_send, self)

    class InstrumentedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._original_send = super().send
            self.send = functools.partial(async_instrumented_send, self)

    httpx.Client = InstrumentedClient
    httpx.AsyncClient = InstrumentedAsyncClient

    return original_client, original_async_client


def _instrument_flask(tracer_provider: TracerProvider):
    try:
        from flask import Flask, g, request
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.trace import Span, SpanKind

        def before_request():
            tracer = trace.get_tracer(__name__)
            span = tracer.start_span(f"HTTP {request.method} {request.path}", kind=SpanKind.SERVER)
            g.span = span

            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.url)
            span.set_attribute("http.request.headers", str(dict(request.headers)))

            if request.data:
                span.set_attribute("http.request.body", _decode_body(request.data))

        def after_request(response):
            span: Span = getattr(g, "span", None)
            if span and span.is_recording():
                span.set_attribute("http.response.headers", str(dict(response.headers)))
                if response.data:
                    span.set_attribute("http.response.body", _decode_body(response.data))
                span.set_attribute("http.status_code", response.status_code)
                span.end()

            return response

        FlaskInstrumentor().instrument(tracer_provider=tracer_provider)

        original_wsgi_app = Flask.wsgi_app

        def wrapped_wsgi_app(app, environ, start_response):
            app.before_request(before_request)
            app.after_request(after_request)
            return original_wsgi_app(app, environ, start_response)

        Flask.wsgi_app = wrapped_wsgi_app

    except ImportError as e:
        print(f"Flask instrumentation failed: {e}")


def _instrument_sqlalchemy(tracer_provider: TracerProvider):
    try:
        import sqlalchemy
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(tracer_provider=tracer_provider)

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Start a new span for SQL execution
            span = tracer_provider.get_tracer(__name__).start_span(name="SQL Execute")
            if span.is_recording():
                span.set_attribute("db.statement", statement)
                span.set_attribute("db.parameters", str(parameters))
            context._span = span

        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
            # End the span after execution
            span = getattr(context, "_span", None)
            if span:
                # TODO: how to decode cursor and keep it usable?
                span.end()

        sqlalchemy.event.listen(sqlalchemy.engine.Engine, "before_cursor_execute", before_cursor_execute)
        sqlalchemy.event.listen(sqlalchemy.engine.Engine, "after_cursor_execute", after_cursor_execute)
    except ImportError as e:
        pass


def _instrument_dbapi(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.dbapi import DatabaseApiIntegration

        pass
    except ImportError as e:
        pass


def _instrument_sqlite3(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

        pass
    except ImportError as e:
        pass


def _instrument_redis(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        def request_hook(span, instance, args, kwargs):
            if span.is_recording():
                span.set_attribute("redis.command", args[0])
                if len(args) > 1:
                    span.set_attribute("redis.command.args", str(args[1:]))

        def response_hook(span, instance, response):
            if span.is_recording():
                span.set_attribute("redis.response", str(response))

        RedisInstrumentor().instrument(
            tracer_provider=tracer_provider,
            request_hook=request_hook,
            response_hook=response_hook,
        )
    except ImportError as e:
        pass


def _instrument_openai(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor

        pass
    except ImportError as e:
        pass


def apply_instrumentation(tracer_provider: TracerProvider):
    # Web Frameworks
    _instrument_fastapi(tracer_provider)
    _instrument_flask(tracer_provider)

    # Generic HTTP request libraries
    _instrument_requests(tracer_provider)
    _instrument_httpx(tracer_provider)

    # Database interactions
    _instrument_dbapi(tracer_provider)
    _instrument_sqlalchemy(tracer_provider)
    _instrument_sqlite3(tracer_provider)
    _instrument_redis(tracer_provider)

    # Other
    _instrument_openai(tracer_provider)
