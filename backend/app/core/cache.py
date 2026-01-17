import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CacheService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        self.redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any:
        if not self.redis:
            return None
        return await self.redis.get(key)

    async def set(self, key: str, value: Any, ttl: int = 60):
        if not self.redis:
            return
        await self.redis.set(key, value, ex=ttl)

    async def get_json(self, key: str) -> Any:
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 60):
        await self.set(key, json.dumps(value), ttl)

    def cached(self, ttl: int = 60, key_builder: Optional[Callable] = None):
        """
        Decorator for caching async functions.
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.redis:
                    return await func(*args, **kwargs)

                # Build Key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Simple default key builder (caution: might not be unique enough)
                    func_name = func.__name__
                    args_str = "-".join([str(a) for a in args])
                    cache_key = f"cache:{func_name}:{args_str}"

                # Try Cache
                cached_val = await self.get_json(cache_key)
                if cached_val is not None:
                    # logger.debug("cache_hit", key=cache_key)
                    return cached_val

                # Miss
                # logger.debug("cache_miss", key=cache_key)
                result = await func(*args, **kwargs)

                # We need to serialize result. Pydantic models need .model_dump()
                # This simplistic cache needs to handle Pydantic objects specifically if result is one.
                # For now, let's assume result is serializable or dict.

                # Save to cache
                if result is not None:
                    await self.set_json(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


cache = CacheService()
