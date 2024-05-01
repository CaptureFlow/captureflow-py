import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import patch
from server import app, Transaction

@pytest.fixture
def client():
    return TestClient(app)

test_transaction = Transaction(user_id="user123", company_id="company456", amount=100.0)

@patch('server.utilz.calculate_score')
@patch('server.utilz.add_transaction')
def test_score_transaction(mock_add_transaction, mock_calculate_score, client):
    
    # Set the outputs returned by the mock functions when called
    mock_calculate_score.return_value = 0.2
    mock_add_transaction.return_value = None
    
    response = client.post("/score_transaction/", json=test_transaction.dict())
    
    # Test if status code of the response is 200
    assert response.status_code == 200
    
    # Test if the response is equal to the expected output
    assert response.json() == {"user_id": test_transaction.user_id,
                               "company_id": test_transaction.company_id,
                               "amount": test_transaction.amount,
                               "score": 0.2}
@patch('server.utilz.calculate_score')
@patch('server.utilz.add_transaction')
def test_add_transaction_exception(mock_add_transaction, mock_calculate_score, client):
    
    # Set the outputs returned by the mock functions when called
    mock_calculate_score.return_value = 0.2
    mock_add_transaction.side_effect = Exception("Test Exception!")
    
    with pytest.raises(HTTPException):
        client.post("/score_transaction/", json=test_transaction.dict())