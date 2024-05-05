import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from serverside.clientside.examples.fastapi.server import app

@pytest.fixture
def client():
    """Setting up the FastAPI application as a fixture."""
    client = TestClient(app)
    return client

@pytest.fixture
def mock_db():
    """Setting up mock for the sqlite3 database operations."""
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        yield mock_cursor

@pytest.fixture
def test_transaction_data():
    """Test data for posting to 'score_transaction' endpoint."""
    return {"user_id": "user123", "company_id": "company456", "amount": 100.0}

def test_score_transaction(client, mock_db, test_transaction_data):
    """Test POST request to the 'score_transaction' endpoint."""
    mock_db.fetchall.return_value = [(200.0,), (250.0,), (300.0,), (350.0,), (400.0,)]
    response = client.post("/score_transaction/", json=test_transaction_data)

    assert response.status_code == 200
    expected_score = test_transaction_data["amount"] / sum([200.0, 250.0, 300.0, 350.0, 400.0])  # Assumed calculation
    expected_response = {
        "user_id": test_transaction_data["user_id"],
        "company_id": test_transaction_data["company_id"],
        "amount": test_transaction_data["amount"],
        "score": expected_score,
    }
    assert response.json() == expected_response

    # Assert that sqlite3.connect().cursor().execute() is called with correct arguments.
    mock_db.execute.assert_called_once_with(
        """
        SELECT amount FROM transactions
        WHERE company_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (test_transaction_data["company_id"],),
    )
