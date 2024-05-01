import pytest
from fastapi import HTTPException
from server import score_transaction, Transaction, app
from unittest.mock import patch, Mock

@pytest.fixture
def transaction_instance():
    return Transaction(user_id="user123", company_id="company456", amount=100.0)

@pytest.fixture
def score():
    return 0.2

@pytest.fixture
def app_context():
    return app.test_request_context()

@patch("server.utilz.calculate_score")
@patch("server.utilz.add_transaction")
def test_score_transaction(mock_add_transaction, mock_calculate_score, transaction_instance, score, app_context):
    mock_calculate_score.return_value = score
    mock_add_transaction.return_value = None

    with app_context:
        result = score_transaction(transaction_instance)
    expected_output = {"user_id": transaction_instance.user_id, "company_id": transaction_instance.company_id, "amount": transaction_instance.amount, "score": score}

    assert result == expected_output

    mock_calculate_score.assert_called_once_with(transaction_instance.user_id, transaction_instance.company_id, transaction_instance.amount)
    mock_add_transaction.assert_called_once_with(transaction_instance.user_id, transaction_instance.company_id, transaction_instance.amount, score)

@patch("server.utilz.calculate_score")
@patch("server.utilz.add_transaction")
def test_score_transaction_with_add_transaction_error(mock_add_transaction, mock_calculate_score, transaction_instance, score, app_context):
    mock_calculate_score.return_value = score
    mock_add_transaction.side_effect = Exception("Error")

    with pytest.raises(HTTPException):
        with app_context:
            score_transaction(transaction_instance)

    mock_calculate_score.assert_called_once_with(transaction_instance.user_id, transaction_instance.company_id, transaction_instance.amount)
    mock_add_transaction.assert_called_once_with(transaction_instance.user_id, transaction_instance.company_id, transaction_instance.amount, score)