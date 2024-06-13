from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from your_application import app


# Fixture for the TestClient to use with your FastAPI app
@pytest.fixture
def client():
    """Provides a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


# Fixture for dynamic test payloads
@pytest.fixture
def test_payload():
    """Dynamically generates test payload data."""
    return {"user_id": "example_user", "company_id": "example_company", "amount": 150.0}


# Fixture to handle database setup and mocking
@pytest.fixture
def mock_db():
    with patch("sqlite3.connect") as mock_connect:
        # Create a cursor object from a connection object
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        yield mock_cursor


# Test function for endpoints that involve database interactions
def test_endpoint_with_db_interaction(client, test_payload, mock_db):
    mock_db.fetchall.return_value = [(50,), (60,), (70,), (80,), (90,)]

    response = client.post("/test_endpoint_path/", json=test_payload)

    assert response.status_code == 200
    assert response.json() == {
        "user_id": test_payload["user_id"],
        "company_id": test_payload["company_id"],
        "amount": test_payload["amount"],
        "score": test_payload["amount"] / sum([50, 60, 70, 80, 90]),  # Example calculation
    }

    # That's how you would mock DB interactions
    mock_db.execute.assert_called_once_with(
        """
        SELECT amount FROM transactions
        WHERE company_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (test_payload["company_id"],),
    )
