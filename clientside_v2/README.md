# What

OpenTelemetry-based tracer with custom instrumentations that are crucial for CaptureFlow.

# Development

- Uses Poetry, as it's easy to publish this way.

# Running

Run Jaeger-UI and trace collector via `docker-compose up`.
Run your app via `opentelemetry-instrument uvicorn server:app`

Check your `http://localhost:16686/search` for application monitoring.

# Publishing

`poetry config pypi-token.pypi <your_api_token>`
`poetry publish`