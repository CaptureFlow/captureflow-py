import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field, parse_obj_as, validator
from src.utils.exception_patcher import ExceptionPatcher
from src.utils.integrations.redis_integration import get_redis_connection
from src.utils.test_creator import TestCoverageCreator

app = FastAPI()
redis = get_redis_connection()


class SerializedObject(BaseModel):
    python_type: str
    json_serialized: str


class Arguments(BaseModel):
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, SerializedObject] = Field(default_factory=dict)


class ExceptionInfo(BaseModel):
    type: str
    value: str
    traceback: List[str]


class BaseExecutionTraceItem(BaseModel):
    id: str
    timestamp: str
    event: str
    function: str
    caller_id: Optional[str] = None
    file: str
    line: int
    source_line: str
    tag: str


class CallExecutionTraceItem(BaseExecutionTraceItem):
    arguments: Arguments
    return_value: SerializedObject


class LineExecutionTraceItem(BaseExecutionTraceItem):
    pass


class ExceptionExecutionTraceItem(BaseExecutionTraceItem):
    exception_info: ExceptionInfo


class ReturnExecutionTraceItem(BaseExecutionTraceItem):
    return_value: SerializedObject


class TraceData(BaseModel):
    invocation_id: str
    timestamp: str
    endpoint: str
    execution_trace: List[Any]
    output: Optional[Dict[str, Any]] = None
    call_stack: List[Dict[str, Any]] = []
    log_filename: Optional[str] = None
    input: Dict[str, Any]

    @validator("execution_trace", pre=True)
    def parse_execution_trace(cls, v):
        items = []
        mapping = {
            "call": CallExecutionTraceItem,
            "line": LineExecutionTraceItem,
            "exception": ExceptionExecutionTraceItem,
            "return": ReturnExecutionTraceItem,
        }
        for item in v:
            item_type = mapping.get(item.get("event"), BaseExecutionTraceItem)
            items.append(parse_obj_as(item_type, item))
        return items


# Store new trace
@app.post("/api/v1/traces")
async def store_trace_log(trace_data: TraceData, repo_url: str = Query(..., alias="repository-url")):
    trace_data_json = trace_data.json()
    trace_log_key = f"{repo_url}:{trace_data.invocation_id}"

    redis.set(trace_log_key, trace_data_json)
    return {"message": "Trace log saved successfully"}


# Process accumulated traces and create bugfix MR if needed
@app.post("/api/v1/merge-requests/bugfix")
async def generate_bugfix_mr(repo_url: str = Query(..., alias="repository-url")):
    orchestrator = ExceptionPatcher(redis_client=redis, repo_url=repo_url)
    orchestrator.run()
    return {"message": "MR generation process started successfully"}


@app.post("/api/v1/test-coverage/create")
async def generate_test_coverage(repo_url: str = Query(..., alias="repository-url")):
    """
    Endpoint to trigger test coverage creation using the TestCoverageCreator.
    The process will look at non-standard library functions in the trace and attempt to generate tests.
    """
    test_creator = TestCoverageCreator(redis_client=redis, repo_url=repo_url)
    test_creator.run()
    return {"message": "Test coverage creation process initiated successfully"}
