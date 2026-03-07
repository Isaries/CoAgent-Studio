"""
Unit tests for app.core.cache.CacheService.

Covers:
- cached() decorator: key hashing via sha256
- cached() decorator: cache hit returns stored value (no func call)
- cached() decorator: cache miss calls func and stores result
- cached() decorator: custom key_builder is respected
- cached() decorator: skip cache when redis is None
"""

import hashlib
import json
from unittest.mock import AsyncMock, call

import pytest

from app.core.cache import CacheService


def _make_service_with_redis() -> CacheService:
    """Return a CacheService with a mocked redis client."""
    svc = CacheService()
    svc.redis = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# Key hashing behaviour (Bug 7 fix verification)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_cached_key_uses_sha256_hash():
    """Default key builder must hash args with sha256[:16], not raw concatenation."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    @svc.cached(ttl=60)
    async def my_func(a, b):
        return a + b

    await my_func("hello", "world")

    # Extract the key used in redis.set(key, value, ex=ttl)
    set_call_args = svc.redis.set.call_args
    key_used = set_call_args.args[0]

    assert key_used.startswith("cache:my_func:")
    hash_part = key_used.split(":")[-1]
    assert len(hash_part) == 16

    expected_hash = hashlib.sha256("hello-world".encode()).hexdigest()[:16]
    assert hash_part == expected_hash


@pytest.mark.asyncio()
async def test_cached_key_is_deterministic():
    """Same args must always produce the same cache key."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    @svc.cached(ttl=60)
    async def fn(x):
        return x

    await fn("stable")
    await fn("stable")

    keys = [c.args[0] for c in svc.redis.set.call_args_list]
    assert keys[0] == keys[1]


@pytest.mark.asyncio()
async def test_cached_different_args_produce_different_keys():
    """Different args must produce different cache keys."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    @svc.cached(ttl=60)
    async def fn(x):
        return x

    await fn("arg_one")
    await fn("arg_two")

    keys = [c.args[0] for c in svc.redis.set.call_args_list]
    assert keys[0] != keys[1]


@pytest.mark.asyncio()
async def test_cached_key_is_fixed_length_regardless_of_arg_length():
    """A very long arg string must still produce a short (16-char) hash suffix."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    @svc.cached(ttl=60)
    async def fn(x):
        return x

    very_long_arg = "x" * 10_000
    await fn(very_long_arg)

    key_used = svc.redis.set.call_args.args[0]
    hash_part = key_used.split(":")[-1]
    assert len(hash_part) == 16


# ---------------------------------------------------------------------------
# Cache hit / miss
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_cached_hit_does_not_call_function():
    """On a cache hit, the underlying function must NOT be called."""
    svc = _make_service_with_redis()
    cached_value = json.dumps({"val": 42})
    svc.redis.get = AsyncMock(return_value=cached_value)

    call_count = 0

    @svc.cached(ttl=60)
    async def fn():
        nonlocal call_count
        call_count += 1
        return {"val": 42}

    result = await fn()
    assert result == {"val": 42}
    assert call_count == 0


@pytest.mark.asyncio()
async def test_cached_miss_calls_function_and_stores_result():
    """On a cache miss, function is called and result is written to redis."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    call_count = 0

    @svc.cached(ttl=30)
    async def fn():
        nonlocal call_count
        call_count += 1
        return {"answer": 99}

    result = await fn()
    assert result == {"answer": 99}
    assert call_count == 1
    svc.redis.set.assert_awaited_once()
    # TTL should match
    _, _, kwargs = svc.redis.set.mock_calls[0]
    assert kwargs.get("ex") == 30 or svc.redis.set.call_args.kwargs.get("ex") == 30 or svc.redis.set.call_args.args[2] == 30


@pytest.mark.asyncio()
async def test_cached_skip_when_redis_none():
    """When redis is None, the function is always called directly."""
    svc = CacheService()
    svc.redis = None

    call_count = 0

    @svc.cached(ttl=60)
    async def fn():
        nonlocal call_count
        call_count += 1
        return "direct"

    result = await fn()
    assert result == "direct"
    assert call_count == 1


# ---------------------------------------------------------------------------
# Custom key_builder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_cached_custom_key_builder_is_used():
    """When key_builder is provided, it overrides the default hash logic."""
    svc = _make_service_with_redis()
    svc.redis.get = AsyncMock(return_value=None)
    svc.redis.set = AsyncMock()

    @svc.cached(ttl=60, key_builder=lambda x: f"custom:{x}")
    async def fn(x):
        return x

    await fn("abc")

    key_used = svc.redis.set.call_args.args[0]
    assert key_used == "custom:abc"
