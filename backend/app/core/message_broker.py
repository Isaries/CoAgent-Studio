import asyncio
from typing import Awaitable, Callable, Optional

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

CHANNEL_PREFIX = "room_"


class RedisMessageBroker:
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub = None
        self.callback: Optional[Callable[[str, str], Awaitable[None]]] = None
        self.task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, redis_url: str, callback: Callable[[str, str], Awaitable[None]]):
        self.redis_client = aioredis.from_url(redis_url)
        self.pubsub = self.redis_client.pubsub()
        self.callback = callback
        self._running = True
        self.task = asyncio.create_task(self._listener_loop())

    async def disconnect(self):
        """Gracefully stop the listener and close connections."""
        self._running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

    async def publish(self, room_id: str, message: str):
        if self.redis_client:
            await self.redis_client.publish(f"{CHANNEL_PREFIX}{room_id}", message)

    async def _listener_loop(self):
        if not self.pubsub:
            return

        while self._running:
            try:
                await self.pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
                logger.info("redis_broker_listener_started")

                async for message in self.pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] == "pmessage":
                        raw_channel = message["channel"]
                        raw_data = message["data"]
                        channel = raw_channel.decode("utf-8") if isinstance(raw_channel, bytes) else raw_channel
                        data = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
                        # Extract room_id by removing the prefix
                        room_id = channel[len(CHANNEL_PREFIX):]

                        if self.callback:
                            try:
                                await self.callback(data, room_id)
                            except Exception as e:
                                logger.error("redis_broker_callback_error", error=str(e), room_id=room_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("redis_broker_listener_error", error=str(e))
                if self._running:
                    await asyncio.sleep(2)  # Brief pause before reconnect
