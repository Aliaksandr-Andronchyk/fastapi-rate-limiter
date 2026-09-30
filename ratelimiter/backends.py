"""Хранилища для лимитера: фиксированное окно, in-memory и Redis."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LimitResult:
    allowed: bool
    remaining: int
    reset_after: float


class RateLimitBackend(ABC):
    @abstractmethod
    async def hit(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        """Зарегистрировать запрос и вернуть, разрешён ли он."""


class InMemoryBackend(RateLimitBackend):
    """Простое окно в памяти процесса – для тестов и одного воркера."""

    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float, int]] = {}

    async def hit(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        now = time.monotonic()
        count, window_start, _ = self._counters.get(key, (0, now, window_seconds))

        if now - window_start >= window_seconds:
            count, window_start = 0, now

        count += 1
        self._counters[key] = (count, window_start, window_seconds)
        self._evict_expired(now)

        reset_after = window_seconds - (now - window_start)
        return LimitResult(
            allowed=count <= limit,
            remaining=max(0, limit - count),
            reset_after=max(0.0, reset_after),
        )

    def _evict_expired(self, now: float) -> None:
        expired = [
            k for k, (_, window_start, window_seconds) in self._counters.items()
            if now - window_start >= window_seconds
        ]
        for k in expired:
            del self._counters[k]


class RedisBackend(RateLimitBackend):
    """Фиксированное окно на Redis: INCR + EXPIRE, атомарно через Lua."""

    _SCRIPT = """
    local current = redis.call("INCR", KEYS[1])
    if current == 1 then
        redis.call("EXPIRE", KEYS[1], ARGV[1])
    end
    local ttl = redis.call("TTL", KEYS[1])
    return {current, ttl}
    """

    def __init__(self, redis_client) -> None:
        self._redis = redis_client
        self._script = None

    async def hit(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        if self._script is None:
            self._script = self._redis.register_script(self._SCRIPT)

        count, ttl = await self._script(keys=[f"ratelimit:{key}"], args=[window_seconds])
        count, ttl = int(count), int(ttl)

        return LimitResult(
            allowed=count <= limit,
            remaining=max(0, limit - count),
            reset_after=float(ttl if ttl >= 0 else window_seconds),
        )
