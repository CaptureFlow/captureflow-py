"""Module for tracing function calls in Python applications with remote logging capability."""
import asyncio
import sys
import linecache
import uuid
import json
import requests
import inspect

from typing import Any, Dict, Callable
from functools import wraps
from datetime import datetime

STDLIB_PATH = "/lib/python"
LIBRARY_PATH = "/site-packages/"
TEMP_FOLDER = "temp/"

class Tracer:
    def __init__(self, repo_url: str, server_base_url: str = "http://127.0.0.1:8000"):
        """Initialize the tracer with the repository URL and optionally the remote logging URL."""
        self.repo_url = repo_url
        self.trace_endpoint_url = f"{server_base_url.rstrip('/')}/api/v1/traces"

    def trace_endpoint(self, func: Callable) -> Callable:
        """Decorator to trace endpoint function calls."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            invocation_id = str(uuid.uuid4())
            context = {
                "invocation_id": invocation_id,
                "timestamp": datetime.now().isoformat(),
                "endpoint": func.__qualname__,
                "input": {
                    "args": [self._serialize_variable(arg) for arg in args],
                    "kwargs": {k: self._serialize_variable(v) for k, v in kwargs.items()}
                },
                "execution_trace": [],
                "log_filename": f"{TEMP_FOLDER}{func.__name__}_trace_{invocation_id}.json"
            }

            sys.settrace(self._setup_trace(context))
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                context["output"] = {"result": self._serialize_variable(result)}
            finally:
                sys.settrace(None)
                self._send_trace_log(context)

            return result

        return wrapper
    
    def _send_trace_log(self, context: Dict[str, Any]) -> None:
        headers = {"Content-Type": "application/json"}
        # Include the repository URL as a query parameter for the trace data
        response = requests.post(self.trace_endpoint_url, params={"repository-url": self.repo_url}, json=context, headers=headers)
        if response.status_code != 200:
            print(f"Failed to send trace log, status code: {response.status_code}")

    def _write_trace_log(self, context: Dict[str, Any]) -> None:
        """Write the trace log to a file."""
        with open(context["log_filename"], "w") as log_file:
            json.dump(context, log_file, indent=4)

    def _serialize_variable(self, value: Any) -> Dict[str, Any]:
        try:
            json_value = json.dumps(value, default=str)
        except TypeError:
            json_value = str(value)
        return {
            "python_type": str(type(value)),
            "json_serialized": json_value
        }

    def _get_file_tag(self, file_path: str) -> str:
        """Determine the file tag based on the file path."""
        if STDLIB_PATH in file_path:
            return "STDLIB"
        elif LIBRARY_PATH in file_path:
            return "LIBRARY"
        return "INTERNAL"

    def _setup_trace(self, context: Dict[str, Any]) -> Callable:
        """Setup the trace function."""
        context["call_stack"] = []
        return lambda frame, event, arg: self._trace_function_calls(frame, event, arg, context)

    def _capture_arguments(self, frame) -> Dict[str, Any]:
        """
        Capture arguments passed to the function and serialize them.
        This simplified version does not distinguish between args and kwargs based on the function's signature.
        """
        args, _, _, values = inspect.getargvalues(frame)
        
        serialized_args = []
        serialized_kwargs = {}
        for arg in args:
            serialized_value = self._serialize_variable(values[arg])
            if arg == 'args' or arg.startswith('arg'):
                serialized_args.append(serialized_value)
            else:
                serialized_kwargs[arg] = serialized_value
        
        return {"args": serialized_args, "kwargs": serialized_kwargs}

    def _trace_function_calls(self, frame, event, arg, context: Dict[str, Any]) -> Callable:
        """Trace function calls and capture relevant data."""
        code = frame.f_code
        func_name, file_name, line_no = code.co_name, code.co_filename, frame.f_lineno

        tag = self._get_file_tag(file_name)
        caller_id = context["call_stack"][-1]["id"] if context["call_stack"] else None

        call_id = str(uuid.uuid4())
        trace_event = {
            "id": call_id,
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "function": func_name,
            "caller_id": caller_id,
            "file": file_name,
            "line": line_no,
            "source_line": linecache.getline(file_name, line_no).strip(),
            "tag": tag,
        }
    
        if event == "call":
            trace_event["arguments"] = self._capture_arguments(frame)
            context["call_stack"].append(trace_event)
        elif event == "return":
            if context["call_stack"]:
                context["call_stack"][-1]["return_value"] = self._serialize_variable(arg)
                context["call_stack"].pop()

        context["execution_trace"].append(trace_event)

        return lambda frame, event, arg: self._trace_function_calls(frame, event, arg, context)
