import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from server import app, calculate_score, add_transaction

# Load mock data
with open('interactions/calculate_score_mock_data.json') as f:
    calculate_score_mock_data = json.load(f)
    
with open('interactions/add_transaction_mock_data.json') as f:
    add_transaction_mock_data = json.load(f)
    
# Initialize test client
client = TestClient(app)

@pytest.fixture
def mock_calculate_score(monkeypatch):
    """Fixture for mocking the calculate_score function"""
    def mock(*args, **kwargs):
        return calculate_score_mock_data.get('score')
    monkeypatch.setattr(calculate_score, 'calculate_score', mock)
    
@pytest.fixture
def mock_add_transaction(monkeypatch):
    """Fixture for mocking the add_transaction function"""
    def mock(*args, **kwargs):
        return add_transaction_mock_data.get('transaction_id')
    monkeypatch.setattr(add_transaction, 'add_transaction', mock)

def test_score_transaction(mock_calculate_score, mock_add_transaction):
    transaction = {
        "user_id": "user123",
        "company_id": "company456",
        "amount": 100.0
    }
    
    response = client.post("/score_transaction",
                           json={"transaction": transaction})

    assert response.status_code == 200

    expected_output = {
        "user_id": "user123",
        "company_id": "company456",
        "amount": 100.0,
        "score": 0.2
    }
    
    assert response.json() == expected_output
