from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from server import app, Transaction  # adapt your import according to the location of your scripts.

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_payload():
    return {"user_id": "user123", "company_id": "company456", "amount": 100.0}

@pytest.fixture
def mock_db():
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        yield mock_cursor


def test_score_transaction(client, test_payload, mock_db):
    mock_db.fetchall.return_value = [(50,), (60,), (70,), (80,), (90,)]   # mock previous transaction amounts of the company

    response = client.post("/score_transaction/", json=test_payload)

    assert response.status_code == 200
    assert response.json() == {
        "user_id": test_payload["user_id"],
        "company_id": test_payload["company_id"],
        "amount": test_payload["amount"],
        "score": test_payload["amount"] / sum([50, 60, 70, 80, 90]),  # same score calculation
    }

    mock_db.execute.assert_called_with(
        """
        SELECT amount FROM transactions
        WHERE company_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (test_payload["company_id"],),
    )

    mock_db.execute.assert_called_with(
        """
        INSERT INTO transactions (user_id, company_id, amount, score)
        VALUES (?, ?, ?, ?)
        """,
        (test_payload["user_id"], test_payload["company_id"], test_payload["amount"],
         test_payload["amount"] / sum([50, 60, 70, 80, 90])),
    )
