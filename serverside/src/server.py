from typing import Any, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from src.utils.integrations.redis_integration import get_redis_connection
from src.utils.orchestration import Orchestrator

app = FastAPI()
redis = get_redis_connection()


# Just a couple structures defining what "trace" data looks like
class ExecutionTraceItem(BaseModel):
    id: str
    timestamp: str
    event: str
    function: str
    caller_id: Optional[str]
    file: str
    line: int
    source_line: str
    tag: str
    arguments: Optional[Any] = None
    return_value: Optional[Any] = None


class TraceData(BaseModel):
    invocation_id: str
    timestamp: str
    endpoint: str
    input: dict
    execution_trace: List[ExecutionTraceItem]
    output: dict = None
    call_stack: list = []
    log_filename: Optional[str] = None


# Store new trace
@app.post("/api/v1/traces")
async def store_trace_log(trace_data: TraceData, repo_url: str = Query(..., alias="repository-url")):
    trace_data_json = trace_data.json()

    # Updated to use the query parameter for repo_url
    trace_log_key = f"{repo_url}:{trace_data.invocation_id}"

    redis.set(trace_log_key, trace_data_json)
    return {"message": "Trace log saved successfully"}


# Generate MR for a given repo
@app.post("/api/v1/merge-requests")
async def generate_mr(repo_url: str = Query(..., alias="repository-url")):
    # Initializer and method call remain unchanged
    orchestrator = Orchestrator(redis_client=redis, repo_url=repo_url)
    orchestrator.run()
    return {"message": "MR generation process started successfully"}
