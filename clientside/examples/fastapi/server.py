import utilz
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from captureflow.tracer import Tracer

tracer = Tracer(
    repo_url="https://github.com/CaptureFlow/captureflow-py",
    server_base_url="http://127.0.0.1:8000",
)

app = FastAPI()


class Transaction(BaseModel):
    user_id: str
    company_id: str
    amount: float


@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup."""
    utilz.init_db()


@app.post("/score_transaction/")
@tracer.trace_endpoint
async def score_transaction(transaction: Transaction):
    """
    Scores a given transaction for fraud potential based on amount similarity to the last 5 transactions for the same company_id.

    ## cURL examples:
    ```
    curl -X 'POST' 'http://127.0.0.1:1337/score_transaction/' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"user_id": "user123", "company_id": "company456", "amount": 100.0}'
    ```
    """
    score = utilz.calculate_score(transaction.user_id, transaction.company_id, transaction.amount)
    try:
        utilz.add_transaction(transaction.user_id, transaction.company_id, transaction.amount, score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "user_id": transaction.user_id,
        "company_id": transaction.company_id,
        "amount": transaction.amount,
        "score": score,
    }
