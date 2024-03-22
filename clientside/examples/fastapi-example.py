from fastapi import FastAPI
from captureflow.tracer import Tracer

tracer = Tracer(mode="remote", auth_key="4c417841-77ad-4c96-9319-d4104aa4a27e")

app = FastAPI()

def calculate_avg(sample_array):
    pass

@app.get("/")
@tracer.trace_endpoint
def calculate_average():
    sample_array = [1,2,3,5,6]
    res = calculate_avg(sample_array)
    return {"Hello": "World", "average": res}

@app.get("/fetch_similar/")
@tracer.trace_endpoint
def fetch_similar_array():
    sample_array = np.array([1,2,3,5,6]) + 1
    res = calculate_avg(sample_array)
    return {"Hello": "World", "average": res}