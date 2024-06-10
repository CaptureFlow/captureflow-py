from fastapi import FastAPI
import requests
import httpx

app = FastAPI()

def external_call():
    response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
    return response.json()

async def external_call_httpx():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/2")
    return response.json()

async def external_post_call_httpx():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://jsonplaceholder.typicode.com/posts",
            json={"title": "foo", "body": "bar", "userId": 1}
        )
    return response.json()

@app.get("/")
async def read_root():
    data = external_call()
    data_post_httpx = await external_post_call_httpx()
    data_get_httpx = await external_call_httpx()
    return {
        "message": "Hello World", 
        "data": data,
    }


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
