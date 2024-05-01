import pytest
from fastapi import HTTPException
from asgiref.sync import async_to_sync
from unittest.mock import patch

from clientside.examples.fastapi import server

# Test data
transaction = server.Transaction(user_id='user123', company_id='company456', amount=100.0)
expected_output = {"user_id": "user123", "company_id": "company456", "amount": 100.0, "score": 0.2}

def test_score_transaction_success():
    """Test the score_transaction function with a successful transaction"""

    with patch('clientside.examples.fastapi.utilz.calculate_score', return_value=0.2), \
         patch('clientside.examples.fastapi.utilz.add_transaction'):
        
        result = async_to_sync(server.score_transaction)(transaction)

        assert result == expected_output

def test_score_transaction_failure():
    """Test the score_transaction function where transaction addition fails"""
    
    with patch('clientside.examples.fastapi.utilz.calculate_score', return_value=0.2), \
         patch('clientside.examples.fastapi.utilz.add_transaction', side_effect=Exception("Test Exception")):
        
        with pytest.raises(HTTPException):
            async_to_sync(server.score_transaction)(transaction)
