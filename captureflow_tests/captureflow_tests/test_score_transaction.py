from unittest.mock import  MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from clientside.examples.fastapi.server import app, Transaction


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_cursor():
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = mock_connect.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [(10,), (20,), (30,), (40,), (50,)]
        yield mock_cursor


"""Test case for `score_transaction`"""
def test_score_transaction(client, mock_cursor):
    transaction = Transaction(user_id="user123", company_id="company456", amount=100.0)

    # Mock db call in utilz.calculate_score
    mock_cursor.execute.assert_called_with(
            """
            SELECT amount FROM transactions
            WHERE company_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
            """,
            (transaction.company_id,),
        )

    response = client.post("/score_transaction/", json=transaction.dict())

    assert response.status_code == 200
    assert response.json() == {"user_id": "user123", "company_id": "company456", "amount": 100.0, "score": 100/sum([10., 20., 30., 40., 50.])}

