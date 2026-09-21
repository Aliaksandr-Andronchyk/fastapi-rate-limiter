# fastapi-rate-limiter

FastAPI middleware that rate-limits requests by API token (`Authorization` header) or
client IP, using a fixed-window counter. Ships with two interchangeable backends:
in-memory (single process, good for tests) and Redis (atomic `INCR`+`EXPIRE` via Lua,
safe across multiple workers).

## What it does

- Wraps any FastAPI/Starlette app as `RateLimitMiddleware`.
- Keys requests by `Authorization` header if present, otherwise by client IP.
- Returns `429 Too Many Requests` once the limit is hit within the window.
- Adds `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset` headers to
  every response.

## Run it

```bash
pip install -r requirements.txt
uvicorn app:app --reload
curl http://localhost:8000/ping
```

By default it uses the in-memory backend (5 requests / 10 seconds). Set `REDIS_URL` to
switch to Redis:

```bash
REDIS_URL=redis://localhost:6379/0 uvicorn app:app
```

## Run with Docker

```bash
docker compose up --build
curl http://localhost:8000/ping
```

This starts Redis and the API together, wired via `REDIS_URL`.

## Tests

```bash
pytest
```
