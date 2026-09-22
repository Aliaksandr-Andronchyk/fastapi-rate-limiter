import asyncio

from ratelimiter.backends import RedisBackend


class FakeRedis:
    """Мини-замена redis.asyncio: держит счётчики и TTL в памяти,
    исполняет тот же INCR/EXPIRE, что и Lua-скрипт бэкенда."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._ttls: dict[str, int] = {}

    def register_script(self, script: str):
        async def run(keys, args):
            key = keys[0]
            window_seconds = int(args[0])

            count = self._counters.get(key, 0) + 1
            self._counters[key] = count
            if count == 1:
                self._ttls[key] = window_seconds

            return [count, self._ttls.get(key, window_seconds)]

        return run


def test_redis_backend_allows_within_limit():
    async def run():
        backend = RedisBackend(FakeRedis())
        result = await backend.hit("k", limit=3, window_seconds=10)
        return result

    result = asyncio.run(run())
    assert result.allowed is True
    assert result.remaining == 2
    assert result.reset_after == 10.0


def test_redis_backend_blocks_over_limit():
    async def run():
        backend = RedisBackend(FakeRedis())
        for _ in range(2):
            await backend.hit("k", limit=2, window_seconds=10)
        return await backend.hit("k", limit=2, window_seconds=10)

    result = asyncio.run(run())
    assert result.allowed is False
    assert result.remaining == 0


def test_redis_backend_separate_keys():
    async def run():
        backend = RedisBackend(FakeRedis())
        blocked = await backend.hit("a", limit=1, window_seconds=10)
        allowed = await backend.hit("b", limit=1, window_seconds=10)
        return blocked, allowed

    blocked, allowed = asyncio.run(run())
    assert blocked.allowed is True
    assert allowed.allowed is True
