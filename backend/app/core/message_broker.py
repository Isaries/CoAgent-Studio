import asyncio
from typing import Awaitable, Callable

import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RedisMessageBroker:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.callback: Callable[[str, str], Awaitable[None]] = None
        self.task = None

    async def connect(self, redis_url: str, callback: Callable[[str, str], Awaitable[None]]):
        self.redis_client = redis.from_url(redis_url)
        self.pubsub = self.redis_client.pubsub()
        self.callback = callback
        self.task = asyncio.create_task(self._listener_loop())

    async def publish(self, room_id: str, message: str):
        if self.redis_client:
            await self.redis_client.publish(f"room_{room_id}", message)

    async def _listener_loop(self):
        if not self.pubsub:
            return

        await self.pubsub.psubscribe("room_*")
        logger.info("redis_broker_listener_started")

        async for message in self.pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"].decode("utf-8")  # e.g. room_123
                data = message["data"].decode("utf-8")
                room_id = channel.replace("room_", "")

                if self.callback:
                    await self.callback(data, room_id)
