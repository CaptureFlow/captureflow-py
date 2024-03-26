import os

from fastapi import FastAPI

from captureflow.tracer import Tracer

# Actually makes tracer dump file locally
os.environ["CAPTUREFLOW_DEV_SERVER"] = "true"

tracer = Tracer(
    repo_url="https://github.com/DummyUser/DummyRepo",
    server_base_url="http://127.0.0.1:1337",
)

app = FastAPI()


def calculate_avg(sample_array):
    return sample_array


@app.get("/")
@tracer.trace_endpoint
def calculate_average():
    sample_array = [1, 2, 3, 5, 6]
    res = calculate_avg(sample_array)
    return {"Hello": "World", "average": res}


@app.get("/fetch_similar/")
@tracer.trace_endpoint
def fetch_similar_array():
    sample_array = [1, 2, 3, 4]
    res = calculate_avg(sample_array)
    return {"Hello": "World", "average": res}
