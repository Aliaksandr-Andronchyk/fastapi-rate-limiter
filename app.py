"""Демо-приложение FastAPI с подключённым rate limiter."""
import os

from fastapi import FastAPI

from ratelimiter.backends import InMemoryBackend, RedisBackend
from ratelimiter.middleware import RateLimitMiddleware

app = FastAPI()

redis_url = os.getenv("REDIS_URL")
if redis_url:
    import redis.asyncio as redis

    backend = RedisBackend(redis.from_url(redis_url))
else:
    backend = InMemoryBackend()

app.add_middleware(
    RateLimitMiddleware,
    backend=backend,
    limit=int(os.getenv("RATE_LIMIT", "5")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "10")),
)


@app.get("/ping")
async def ping():
    return {"pong": True}
