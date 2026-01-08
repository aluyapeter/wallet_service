import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

def get_redis():
    """
    Returns an async Redis client.
    """
    return redis.Redis(connection_pool=pool)