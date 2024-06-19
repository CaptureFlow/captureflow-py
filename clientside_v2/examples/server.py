import requests
import httpx

from fastapi import FastAPI
from contextlib import contextmanager

from sqlalchemy_init import Item, get_db

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

@contextmanager
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def perform_database_operations():
    with get_db_session() as db:
        new_item = Item(name="Test Item", description="This is a test item")
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        items = db.query(Item).all()
    return items

def perform_redis_operations():
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.set("test_key", "test_value")
    value = redis_client.get("test_key")
    return value.decode("utf-8") if value else None


@app.get("/")
async def read_root():
    # [HTTP API] Requests invocation
    data = external_call()

    # [HTTP API] Httpx invocation
    data_post_httpx = await external_post_call_httpx()
    data_get_httpx = await external_call_httpx()

    # [DB] SQLite invocation
    data_sqlite = perform_database_operations()

    # [DB] Redis invocation
    data_redis = perform_redis_operations()

    return {
        "message": "Hello World", 
        "data": data,
        "items": [{"id": item.id, "name": item.name, "description": item.description} for item in data_sqlite]
    }

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
