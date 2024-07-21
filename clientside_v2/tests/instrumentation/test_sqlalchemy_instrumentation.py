import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import get_tracer_provider
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from captureflow.distro import CaptureFlowDistro

# SQLAlchemy setup
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


def setup_database(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture(scope="function")
def engine():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb")
    engine = create_engine(DATABASE_URL)
    setup_database(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def app(engine):
    app = FastAPI()
    Session = sessionmaker(bind=engine)

    @app.get("/")
    async def read_root():
        with Session() as session:
            new_user = User(name="Test User")
            session.add(new_user)
            session.commit()
            user = session.query(User).filter_by(name="Test User").first()
        return {"message": "Hello World", "user_id": user.id if user else None}

    return app


@pytest.fixture(scope="function")
def client(app):
    return TestClient(app)


def test_sqlalchemy_instrumentation(engine, client, span_exporter):
    # Make a request to the FastAPI server
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["user_id"] is not None

    # Retrieve the spans
    spans = span_exporter.get_finished_spans()
    sql_spans = [span for span in spans if span.attributes.get("db.system") == "sqlalchemy"]

    # Filter out bootstrap-related spans
    relevant_sql_spans = [
        span for span in sql_spans if not span.attributes.get("db.statement", "").startswith("SELECT pg_catalog")
    ]

    assert len(relevant_sql_spans) >= 2, "Expected at least two relevant SQLAlchemy spans"

    insert_span = next((span for span in relevant_sql_spans if span.name.startswith("SQLAlchemy: INSERT")), None)
    select_span = next((span for span in relevant_sql_spans if span.name.startswith("SQLAlchemy: SELECT")), None)

    assert insert_span is not None, "INSERT span not found"
    assert select_span is not None, "SELECT span not found"

    # Validate INSERT span
    assert insert_span.attributes["db.system"] == "sqlalchemy"
    assert "INSERT INTO users" in insert_span.attributes["db.statement"]
    assert "db.parameters" in insert_span.attributes
    assert "db.row_count" in insert_span.attributes

    # Validate SELECT span
    assert select_span.attributes["db.system"] == "sqlalchemy"
    assert "SELECT" in select_span.attributes["db.statement"]
    assert "FROM users" in select_span.attributes["db.statement"]
    assert "db.parameters" in select_span.attributes
    assert "db.result_columns" in select_span.attributes
    assert "db.row_count" in select_span.attributes

    print("All spans:", spans)
    print("Relevant SQL spans:", relevant_sql_spans)
    print("INSERT span:", insert_span.to_json())
    print("SELECT span:", select_span.to_json())
