import redis
from src.config import REDIS_URL


def get_redis_connection():
    return redis.Redis.from_url(REDIS_URL)
