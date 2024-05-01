# start of pytest file

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from clientside.examples.fastapi.server import app, Transaction, utilz
from starlette.exceptions import HTTPException

# client fixture for tests
@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

# test payload fixture for tests
@pytest.fixture
def test_payload():
    return Transaction(user_id="user_id", company_id="company_id", amount=100.0)

# test score fixture for tests
@pytest.fixture
def test_score():
    return 0.2

# test function to test endpoint "/score_transaction"
def test_score_transaction(client, test_payload, test_score):
    with patch("utilz.calculate_score") as mock_calculate_score, \
         patch("utilz.add_transaction") as mock_add_transaction:
        mock_calculate_score.return_value = test_score

        response = client.post("/score_transaction/", json=test_payload.dict())

        mock_calculate_score.assert_called_once_with(
            test_payload.user_id, test_payload.company_id, test_payload.amount)
        mock_add_transaction.assert_called_once_with(
            test_payload.user_id, test_payload.company_id, test_payload.amount, test_score)

        assert response.status_code == 200
        assert response.json() == {
            "user_id": test_payload.user_id,
            "company_id": test_payload.company_id,
            "amount": test_payload.amount,
            "score": test_score,
        }

# test function to test endpoint "/score_transaction" with error
def test_score_transaction_error(client, test_payload, test_score):
    with patch("utilz.calculate_score") as mock_calculate_score, \
         patch("utilz.add_transaction") as mock_add_transaction:
        mock_calculate_score.return_value = test_score
        mock_add_transaction.side_effect = Exception("test")

        with pytest.raises(HTTPException):
            _ = client.post("/score_transaction/", json=test_payload.dict())

# End of pytest file
