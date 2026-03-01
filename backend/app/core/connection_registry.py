from typing import Dict, List

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionRegistry:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(
            "websocket_connect",
            room_id=room_id,
            total_connections=len(self.active_connections[room_id]),
        )

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
                logger.info(
                    "websocket_disconnect",
                    room_id=room_id,
                    remaining_connections=len(self.active_connections[room_id]),
                )
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_to_room(self, message: str, room_id: str) -> None:
        """
        Send message to local connected websockets in the room.
        """
        if room_id not in self.active_connections:
            return

        dead_connections: list[WebSocket] = []
        # Iterate over a copy to allow safe mutation
        for connection in list(self.active_connections.get(room_id, [])):
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn, room_id)
