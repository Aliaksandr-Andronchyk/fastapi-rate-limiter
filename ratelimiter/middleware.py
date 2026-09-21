"""ASGI-мидлварь: rate limiting по токену (заголовок Authorization) или IP."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .backends import RateLimitBackend


def _client_key(request: Request) -> str:
    auth = request.headers.get("authorization")
    if auth:
        return f"token:{auth}"

    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        backend: RateLimitBackend,
        limit: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._backend = backend
        self._limit = limit
        self._window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = _client_key(request)
        result = await self._backend.hit(key, self._limit, self._window_seconds)

        headers = {
            "X-RateLimit-Limit": str(self._limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_after)),
        }

        if not result.allowed:
            return JSONResponse(
                {"detail": "Too Many Requests"},
                status_code=429,
                headers=headers,
            )

        response = await call_next(request)
        for name, value in headers.items():
            response.headers[name] = value
        return response
