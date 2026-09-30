import asyncio

from ratelimiter.backends import InMemoryBackend


def test_inmemory_backend_allows_within_limit():
    async def run():
        backend = InMemoryBackend()
        return await backend.hit("k", limit=2, window_seconds=10)

    result = asyncio.run(run())
    assert result.allowed is True
    assert result.remaining == 1


def test_inmemory_backend_blocks_over_limit():
    async def run():
        backend = InMemoryBackend()
        for _ in range(2):
            await backend.hit("k", limit=2, window_seconds=10)
        return await backend.hit("k", limit=2, window_seconds=10)

    result = asyncio.run(run())
    assert result.allowed is False
    assert result.remaining == 0


def test_inmemory_backend_separate_keys():
    async def run():
        backend = InMemoryBackend()
        a = await backend.hit("a", limit=1, window_seconds=10)
        b = await backend.hit("b", limit=1, window_seconds=10)
        return a, b

    a, b = asyncio.run(run())
    assert a.allowed is True
    assert b.allowed is True


def test_inmemory_backend_evicts_expired_keys():
    async def run():
        backend = InMemoryBackend()
        await backend.hit("old", limit=1, window_seconds=0.05)
        await asyncio.sleep(0.06)
        await backend.hit("new", limit=1, window_seconds=10)
        return backend

    backend = asyncio.run(run())
    assert "old" not in backend._counters


def test_inmemory_backend_resets_after_window():
    async def run():
        backend = InMemoryBackend()
        first = await backend.hit("k", limit=1, window_seconds=0.05)
        await asyncio.sleep(0.06)
        second = await backend.hit("k", limit=1, window_seconds=0.05)
        return first, second

    first, second = asyncio.run(run())
    assert first.allowed is True
    assert second.allowed is True
