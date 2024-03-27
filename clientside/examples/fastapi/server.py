import os

from fastapi import FastAPI, HTTPException

from captureflow.tracer import Tracer

# This will make tracer dump logs locally
os.environ["CAPTUREFLOW_DEV_SERVER"] = "true"

tracer = Tracer(
    repo_url="https://github.com/DummyUser/DummyRepo",
    server_base_url="http://127.0.0.1:1337",
)

app = FastAPI()


def calculate_avg(sample_array):
    filtered_array = [num for num in sample_array if num % 2 == 0]
    if filtered_array:
        return sum(filtered_array) / len(filtered_array)
    else:
        return 0


@app.get("/calculate_avg/")
@tracer.trace_endpoint
def calculate_average(query: str):
    try:
        sample_array = [int(x) for x in query.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Query must be a comma-separated list of numbers."
        )
    res = calculate_avg(sample_array)
    return {"message": "Calculated average of even numbers", "average": res}


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
