import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch
from server import app, Transaction, score_transaction
from samples import utilities as utilz

client = TestClient(app)

# This is a mock Transaction
transaction_data = {
    "user_id": "user123", 
    "company_id": "company456",
    "amount": 100.0, 
}

class TestScoreTransaction:
    
    @patch('server.utilz.calculate_score')
    @patch('server.utilz.add_transaction')
    def test_score_transaction_success(self, mock_add_transaction, mock_calculate_score): 
        """
        Testing the success case where the transaction details are processed without errors
        """
        mock_calculate_score.return_value = 0.2
        response = client.post('/score_transaction/', json=transaction_data)
        assert response.status_code == 200
        assert response.json() == {
            "user_id": transaction_data['user_id'], 
            "company_id": transaction_data['company_id'], 
            "amount": transaction_data['amount'], 
            "score": 0.2
        }
        mock_calculate_score.assert_called_once_with(transaction_data['user_id'], transaction_data['company_id'], transaction_data['amount']) 
        mock_add_transaction.assert_called_once_with(transaction_data['user_id'], transaction_data['company_id'], transaction_data['amount'], 0.2) 

    @patch('server.utilz.calculate_score')
    @patch('server.utilz.add_transaction')
    def test_score_transaction_failed_add_transaction(self, mock_add_transaction, mock_calculate_score):
        """
        Test the failure case where add_transaction method throws an error, thus raising an HTTPException
        """
        mock_calculate_score.return_value = 0.2
        mock_add_transaction.side_effect = Exception('Some error')
        with pytest.raises(HTTPException) as execinfo:
            response = client.post('/score_transaction/', json=transaction_data)
        assert execinfo.value.status_code == 500
        assert str(execinfo.value.detail) == 'Some error'