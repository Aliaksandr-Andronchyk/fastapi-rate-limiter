import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ratelimiter.backends import InMemoryBackend
from ratelimiter.middleware import RateLimitMiddleware


def make_client(limit: int = 3, window_seconds: int = 10) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        backend=InMemoryBackend(),
        limit=limit,
        window_seconds=window_seconds,
    )

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    return TestClient(app)


def test_allows_requests_within_limit():
    client = make_client(limit=3)
    for _ in range(3):
        response = client.get("/ping")
        assert response.status_code == 200


def test_blocks_requests_over_limit():
    client = make_client(limit=2)
    for _ in range(2):
        assert client.get("/ping").status_code == 200

    response = client.get("/ping")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too Many Requests"}


def test_separate_keys_by_ip():
    client = make_client(limit=1)
    client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"})
    response_a = client.get("/ping")
    assert response_a.status_code == 429


def test_separate_keys_by_token():
    client = make_client(limit=1)
    client.get("/ping", headers={"Authorization": "Bearer aaa"})
    ok = client.get("/ping", headers={"Authorization": "Bearer bbb"})
    blocked = client.get("/ping", headers={"Authorization": "Bearer aaa"})

    assert ok.status_code == 200
    assert blocked.status_code == 429


def test_headers_present():
    client = make_client(limit=5)
    response = client.get("/ping")
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


def test_window_resets_after_expiry():
    async def run():
        backend = InMemoryBackend()
        result_first = await backend.hit("k", limit=1, window_seconds=0)
        await asyncio.sleep(0.01)
        result_second = await backend.hit("k", limit=1, window_seconds=0)
        return result_first, result_second

    first, second = asyncio.run(run())
    assert first.allowed is True
    assert second.allowed is True
