from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Dictionary to store connections: room_id -> List of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            # Create a copy of the list to iterate safely in case of disconnects during iteration
            # though disconnect usually happens in the read loop context.
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_text(message)
                except RuntimeError:
                    # Handle cases where connection might be closed already
                    pass

manager = ConnectionManager()
