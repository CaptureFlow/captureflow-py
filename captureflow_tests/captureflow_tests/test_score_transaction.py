import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from your_application import app  # Modify as needed to import your app

class Transaction(BaseModel):
    user_id: str
    company_id: str
    amount: float

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_transaction():
    return Transaction(user_id='user123', company_id='company456', amount=100.0)

@pytest.fixture
def mock_utilz(module_mocker):
    module_mocker.patch('your_application.server.utilz.calculate_score', return_value=0.2)
    module_mocker.patch('your_application.server.utilz.init_db')
    add_transaction_mock = module_mocker.patch('your_application.server.utilz.add_transaction')
    return add_transaction_mock

def test_score_transaction(client, test_transaction, mock_utilz):
    response = client.post("/score_transaction/", json=test_transaction.dict())
    
    assert response.status_code == 200
    assert response.json() == {
        "user_id": test_transaction.user_id,
        "company_id": test_transaction.company_id,
        "amount": test_transaction.amount,
        "score": 0.2,
    }

    mock_utilz.assert_called_once_with(
        test_transaction.user_id, 
        test_transaction.company_id,
        test_transaction.amount,
        0.2
    )
