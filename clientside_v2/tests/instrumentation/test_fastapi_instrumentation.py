import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()


@app.get("/external")
async def call_external():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
    return {"status_code": response.status_code, "body": response.json()}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_fastapi_instrumentation(span_exporter, client):
    # TODO, implement
    # The challenge: fastapi.testclient is not a real ASGI app that gets instrumented by OTel-Contrib module, so we need to spawn real FastAPI app, yet we still need to access processed spans
    # It's still testable by examples/server.py, but that's suboptimal DX
    pass


if __name__ == "__main__":
    pytest.main([__file__])
