from fastapi import FastAPI
import requests

app = FastAPI()

def external_call():
    response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
    return response.json()

@app.get("/")
async def read_root():
    data = external_call()
    return {"message": "Hello World", "data": data}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
