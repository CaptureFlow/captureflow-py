import pytest
import asyncio
from fastapi import HTTPException
from unittest.mock import Mock, call
from clientside.examples.fastapi.server import score_transaction
from clientside.models import Transaction

# Replace 'your_package' with the actual package containing these modules
from your_package import utilz

@pytest.fixture
def transaction():
    return Transaction(user_id="tester", company_id="test_company", amount=100.0)

@pytest.fixture
def mock_utilz(mocker):
    mock = mocker.patch('your_package.server.utilz', autospec=True)
    mock.calculate_score.return_value = 0.8
    return mock

@pytest.mark.asyncio
async def test_score_transaction_normal_case(transaction, mock_utilz):
    score = await score_transaction(transaction)
    expected = {
        "user_id": transaction.user_id,
        "company_id": transaction.company_id,
        "amount": transaction.amount,
        "score": 0.8,
    }

    assert score == expected
    mock_utilz.calculate_score.assert_called_once_with(transaction.user_id, transaction.company_id, transaction.amount)
    mock_utilz.add_transaction.assert_called_once_with(transaction.user_id, transaction.company_id, transaction.amount, 0.8)

@pytest.mark.asyncio
async def test_score_transaction_database_error(transaction, mock_utilz):
    mock_utilz.add_transaction.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await score_transaction(transaction)

    assert exc_info.value.status_code == 500
    assert str(exc_info.value.detail) == "Database error"
```

Make sure to replace `'your_package'` with the actual package containing `utilz` module in your project. 

Here we defined two test cases: one for normal path and another for when an exception occurs while adding a transaction. 

This test relies on pytest-mock library for mocking objects, and pytest-asyncio for testing async functions. You can install these dependencies using pip:
```
pip install pytest-mock pytest-asyncio