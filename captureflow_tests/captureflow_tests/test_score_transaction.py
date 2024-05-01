# --- Start of the Pytest Script ---
import pytest
import utilz
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, ANY
from clientside.examples.fastapi.server import app, Transaction

# Fixture for the TestClient to use with your FastAPI app
@pytest.fixture
def client():
    """Provides a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client

# Fixture for dynamic test payloads
@pytest.fixture
def test_transaction():
    """Dynamically generates test transaction data."""
    return Transaction(user_id="user123", company_id="company456", amount=100.0)

# Fixture to handle database setup and mocking
@pytest.fixture
def mock_db():
    with patch('sqlite3.connect') as mock_connect:
        # Create a cursor object from a connection object
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        yield mock_cursor

# Test function for endpoints that involve database interactions
def test_score_transaction(client, test_transaction, mock_db):
    mock_db.fetchall.return_value = [(20.0,), (40.0,), (60.0,), (80.0,), (100.0,)]

    response = client.post("/score_transaction/", json=test_transaction.dict())

    assert response.status_code == 200
    assert response.json() == {
        "user_id": test_transaction.user_id,
        "company_id": test_transaction.company_id,
        "amount": test_transaction.amount,
        "score": test_transaction.amount / sum([20.0, 40.0, 60.0, 80.0, 100.0])
    }

    # Verifying the database interactions
    mock_db.execute.assert_any_call(
        """
        SELECT amount FROM transactions
        WHERE company_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (test_transaction.company_id,)
    )
    mock_db.execute.assert_any_call(
        """
        INSERT INTO transactions (user_id, company_id, amount, score)
        VALUES (?, ?, ?, ?)
        """,
        (test_transaction.user_id, test_transaction.company_id, test_transaction.amount, ANY),
    )
# --- End of the Pytest Script ---
