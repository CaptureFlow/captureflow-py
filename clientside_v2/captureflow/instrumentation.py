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


def _instrument_httpx(tracer_provider: TracerProvider):
    try:
        import httpx
        from opentelemetry.instrumentation.httpx import (
            HTTPXClientInstrumentor,
            RequestInfo,
            ResponseInfo,
        )

        async def read_stream(stream):
            if stream is None:
                return None
            content = b""
            async for chunk in stream:
                content += chunk
            return content

        async def request_hook(span, request: RequestInfo):
            if span.is_recording():
                span.set_attribute("http.request.method", request.method.decode())
                span.set_attribute("http.request.url", str(request.url))
                span.set_attribute("http.request.headers", str(request.headers))
                body = await read_stream(request.stream)
                if body:
                    span.set_attribute("http.request.body", _decode_body(body))
                    new_stream = httpx.ByteStream([body])  # Reset the stream for the actual request
                    request = httpx.Request(
                        method=request.method,
                        url=request.url,
                        headers=request.headers,
                        stream=new_stream,
                        extensions=request.extensions,
                    )

        async def response_hook(span, request: RequestInfo, response: ResponseInfo):
            if span.is_recording():
                span.set_attribute("http.response.status_code", response.status_code)
                span.set_attribute("http.response.headers", str(response.headers))
                body: httpx.AsyncResponseStream = response.stream  # AsyncResponseStream
                # TODO: how to decode stream and keep it usable?

        # Do we actually need sync hooks?
        HTTPXClientInstrumentor().instrument(
            tracer_provider=tracer_provider,
            async_request_hook=request_hook,
            async_response_hook=response_hook,
        )
    except ImportError as e:
        pass


def _instrument_flask(tracer_provider: TracerProvider):
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        pass
    except ImportError as e:
        pass


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
