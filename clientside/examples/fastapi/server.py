import os

from fastapi import FastAPI, HTTPException
from utilz import calculate_avg

from captureflow.tracer import Tracer

# This will make tracer dump logs locally
os.environ["CAPTUREFLOW_DEV_SERVER"] = "true"

tracer = Tracer(
    repo_url="https://github.com/CaptureFlow/captureflow-py",
    server_base_url="http://127.0.0.1:8000",
)

app = FastAPI()


@app.get("/calculate_avg/")
@tracer.trace_endpoint
def calculate_average():
    # sample_array = [] # That would produce an exception
    sample_array = []
    return {"message": "Calculated average of even numbers", "average": calculate_avg(sample_array)}


@app.get("/search/{x}")
@tracer.trace_endpoint
def search(x: int):
    # A logical mistake: attempting to search with an integer key in a dictionary with string keys
    data_to_search = {"1": "one", "2": "two", "3": "three"}

    # This will lead to a TypeError, as dictionaries expect their keys to be accessed with the correct type
    result = data_to_search[x]
    return {"found": True, "value": result}


@app.get("/search_better/{x}")
@tracer.trace_endpoint
def search_handled(x: int):
    # A logical mistake: attempting to search with an integer key in a dictionary with string keys
    data_to_search = {"1": "one", "2": "two", "3": "three"}

    # This will lead to a TypeError, as dictionaries expect their keys to be accessed with the correct type
    try:
        result = data_to_search[x]
    except Exception as e:
        return {"found": False}

    return {"found": True, "value": result}
