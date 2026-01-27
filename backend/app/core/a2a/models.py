"""
A2A Protocol Message Models.

This module defines the standardized message types used for Agent-to-Agent communication.
Based on A2A Protocol specifications (https://a2a-protocol.org).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class MessageType(str, Enum):
    """
    Enumeration of A2A message types.
    
    - USER_MESSAGE: Message from a human user
    - PROPOSAL: Agent proposes content (e.g., Student drafts a response)
    - EVALUATION_REQUEST: Agent requests evaluation from another (e.g., Student asks Teacher)
    - EVALUATION_RESULT: Agent returns evaluation result (approve/reject)
    - BROADCAST: Final message to be sent to the room
    - SYSTEM: System-level messages (joins, leaves, errors)
    """
    USER_MESSAGE = "user_message"
    PROPOSAL = "proposal"
    EVALUATION_REQUEST = "evaluation_request"
    EVALUATION_RESULT = "evaluation_result"
    BROADCAST = "broadcast"
    SYSTEM = "system"


@dataclass
class A2AMessage:
    """
    Standardized message envelope for Agent-to-Agent communication.
    
    Attributes:
        id: Unique identifier for this message
        type: The type of message (from MessageType enum)
        sender_id: Identifier of the sender ("teacher", "student", "user:uuid", "system")
        recipient_id: Identifier of the recipient ("teacher", "student", "broadcast", "all")
        correlation_id: Links related messages in a conversation thread
        content: The payload of the message (text, dict, etc.)
        metadata: Additional context (room_id, history, etc.)
        created_at: Timestamp of message creation
    """
    type: MessageType = MessageType.USER_MESSAGE
    sender_id: str = ""
    recipient_id: str = "broadcast"
    content: Any = ""
    id: UUID = field(default_factory=uuid4)
    correlation_id: Optional[UUID] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def reply(
        self,
        type: MessageType,
        content: Any,
        sender_id: str,
        recipient_id: Optional[str] = None,
    ) -> "A2AMessage":
        """
        Create a reply message linked to this message via correlation_id.
        """
        return A2AMessage(
            type=type,
            sender_id=sender_id,
            recipient_id=recipient_id or self.sender_id,
            content=content,
            correlation_id=self.id,
            metadata=self.metadata.copy(),
        )
