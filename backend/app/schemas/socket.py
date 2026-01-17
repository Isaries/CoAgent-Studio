from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class SocketMessage(BaseModel):
    type: str = "message"  # message, system, error
    sender: str
    content: str
    timestamp: str  # ISO8601
    room_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
