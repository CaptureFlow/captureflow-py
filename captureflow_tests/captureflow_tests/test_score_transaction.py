from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from clientside.examples.fastapi.server import app, Transaction


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_transaction():
    return Transaction(user_id="user123", company_id="company456", amount=100.0)


@pytest.fixture
def mock_db():
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        yield mock_cursor


def test_score_transaction(client, test_transaction, mock_db):
    # Setup database mock
    mock_db.fetchall.return_value = [(10,), (20,)]
    mock_db.execute.return_value = None

    # Make request to the FastAPI application
    response = client.post("/score_transaction/", json=test_transaction.dict())

    # Verify the response status code and contents
    assert response.status_code == 200
    expected_response = {
        "user_id": test_transaction.user_id,
        "company_id": test_transaction.company_id,
        "amount": test_transaction.amount,
        "score": test_transaction.amount / 30,  # Based on the mocked fetchall result
    }
    assert response.json() == expected_response

    # Assert the interactions with the database
    mock_db.execute.assert_any_call(
        """
        SELECT amount FROM transactions
        WHERE company_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (test_transaction.company_id,),
    )
    mock_db.execute.assert_any_call(
        """
        INSERT INTO transactions (user_id, company_id, amount, score)
        VALUES (?, ?, ?, ?)
        """,
        (test_transaction.user_id, test_transaction.company_id, test_transaction.amount, expected_response["score"]),
    )
