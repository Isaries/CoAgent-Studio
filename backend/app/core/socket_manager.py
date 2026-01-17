from typing import Dict, Union

import structlog
from fastapi import WebSocket

from app.core.connection_registry import ConnectionRegistry
from app.core.message_broker import RedisMessageBroker

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self.registry = ConnectionRegistry()
        self.broker = RedisMessageBroker()

    async def connect_redis(self, redis_url: str):
        # Bind Broker to Registry's send_to_room
        await self.broker.connect(redis_url, self.registry.send_to_room)

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        await self.registry.connect(websocket, room_id)

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        self.registry.disconnect(websocket, room_id)

    async def broadcast(self, message: Union[str, Dict], room_id: str) -> None:
        """
        Send message to Redis Pub/Sub, which calls back to Registry via listener.
        Supports sending JSON (dict) or raw string.
        """
        if isinstance(message, dict):
            import json

            message = json.dumps(message)

        # Publish to Redis
        if self.broker.redis_client:
            await self.broker.publish(room_id, message)
        else:
            # Fallback
            await self.registry.send_to_room(message, room_id)

    # For compatibility/monitor access
    @property
    def active_connections(self):
        return self.registry.active_connections


manager = ConnectionManager()
