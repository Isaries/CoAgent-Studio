from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MessageBase(SQLModel):
    content: str
    room_id: UUID = Field(foreign_key="room.id", index=True)

class Message(MessageBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    sender_id: Optional[UUID] = Field(foreign_key="user.id", nullable=True) # Null if AI
    agent_type: Optional[str] = None # 'teacher', 'student', 'analytics' if AI
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships need to be defined in User/Room if we want ORM access

class MessageCreate(MessageBase):
    pass

class MessageRead(MessageBase):
    id: UUID
    sender_id: Optional[UUID]
    agent_type: Optional[str]
    created_at: datetime
