"""
A2A Message Store.

Provides persistence for A2A messages, enabling:
- Audit trail of agent communications
- Debugging and troubleshooting
- Analytics on agent interactions
"""

import structlog
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.a2a.models import A2AMessage, MessageType

logger = structlog.get_logger()


class A2AMessageRecord(SQLModel, table=True):
    """
    Database model for persisted A2A messages.
    
    This is a flattened representation of A2AMessage suitable for SQL storage.
    """
    __tablename__ = "a2a_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: str = Field(index=True)  # UUID as string
    correlation_id: Optional[str] = Field(default=None, index=True)
    type: str = Field(index=True)
    sender_id: str = Field(index=True)
    recipient_id: str
    content: str  # JSON-serialized content
    room_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def from_a2a_message(cls, msg: A2AMessage) -> "A2AMessageRecord":
        """Convert an A2AMessage to a database record."""
        import json
        try:
            content_str = json.dumps(msg.content) if not isinstance(msg.content, str) else msg.content
        except (TypeError, ValueError):
            # Fallback for non-serializable content
            content_str = str(msg.content)
        room_id = msg.metadata.get("room_id") if msg.metadata else None
        
        return cls(
            message_id=str(msg.id),
            correlation_id=str(msg.correlation_id) if msg.correlation_id else None,
            type=msg.type.value,
            sender_id=str(msg.sender_id),
            recipient_id=str(msg.recipient_id),
            content=content_str,
            room_id=room_id,
            created_at=msg.created_at,
        )


class A2AMessageStore:
    """
    Repository for storing and querying A2A messages.
    
    Example:
        store = A2AMessageStore(session)
        await store.save(message)
        history = await store.get_by_correlation_id(correlation_id)
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, msg: A2AMessage) -> A2AMessageRecord:
        """
        Persist an A2A message to the database.
        
        Args:
            msg: The A2AMessage to save
            
        Returns:
            The saved database record
        """
        record = A2AMessageRecord.from_a2a_message(msg)
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        logger.info("a2a_message_saved", message_id=record.message_id, type=record.type)
        return record
    
    async def get_by_message_id(self, message_id: UUID) -> Optional[A2AMessageRecord]:
        """Get a specific message by its ID."""
        stmt = select(A2AMessageRecord).where(
            A2AMessageRecord.message_id == str(message_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_correlation_id(self, correlation_id: UUID) -> List[A2AMessageRecord]:
        """
        Get all messages in a conversation thread.
        
        Returns messages ordered by creation time.
        """
        stmt = (
            select(A2AMessageRecord)
            .where(A2AMessageRecord.correlation_id == str(correlation_id))
            .order_by(A2AMessageRecord.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_room(
        self,
        room_id: str,
        limit: int = 100,
        message_type: Optional[MessageType] = None,
    ) -> List[A2AMessageRecord]:
        """
        Get A2A messages for a specific room.
        
        Args:
            room_id: The room identifier
            limit: Maximum number of messages to return
            message_type: Optional filter by message type
        """
        stmt = (
            select(A2AMessageRecord)
            .where(A2AMessageRecord.room_id == room_id)
        )
        if message_type:
            stmt = stmt.where(A2AMessageRecord.type == message_type.value)
        stmt = stmt.order_by(A2AMessageRecord.created_at.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
