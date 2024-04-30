import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch
import examples.fastapi.server as server
from examples.fastapi.models import Transaction

def test_utils_calculate_score():
    """
    Mock the utilz.calculate_score function here just to validate interactions with the function.
    You might want to implement a separate test suite to target the calculate_score function directly.
    """
    with patch('examples.fastapi.utilz.calculate_score', return_value=0.8) as mocked_func:
        example_transaction = Transaction(user_id="test123", company_id="company456", amount=100.0)
        server.score_transaction(example_transaction)
        mocked_func.assert_called_once_with("test123", "company456", 100.0)

def test_utils_add_transaction_exc():
    """
    Test for exception when utilz.add_transaction() encounters an error.
    """
    with patch('examples.fastapi.utilz.calculate_score', return_value=0.8), \
            patch('examples.fastapi.utilz.add_transaction', side_effect=Exception('Testing Exceptions')):
        example_transaction = Transaction(user_id="test123", company_id="company456", amount=100.0)
        with pytest.raises(HTTPException) as excinfo:
            server.score_transaction(example_transaction)
        assert str(excinfo.value) == '500: Testing Exceptions'
        
def test_score_transaction():
    """
    Test for successful run of score_transaction() function.
    """
    with patch('examples.fastapi.utilz.calculate_score', return_value=0.8) as mocked_func, \
            patch('examples.fastapi.utilz.add_transaction') as mocked_transac:
        example_transaction = Transaction(user_id="test123", company_id="company456", amount=100.0)
        result = server.score_transaction(example_transaction)
        assert result == {
            "user_id": "test123",
            "company_id": "company456",
            "amount": 100.0,
            "score": 0.8,
        }
        mocked_func.assert_called_once_with("test123", "company456", 100.0)
        mocked_transac.assert_called_once_with("test123", "company456", 100.0, 0.8)