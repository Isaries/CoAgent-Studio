from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_base"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: Optional[str] = None
    space_id: Optional[UUID] = Field(default=None, foreign_key="space.id")
    room_id: Optional[UUID] = Field(default=None, foreign_key="room.id")
    source_type: str = Field(default="conversation")  # conversation, document, merged
    build_status: str = Field(default="idle")  # idle, building, ready, error
    extraction_model: Optional[str] = None
    summarization_model: Optional[str] = None
    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)
    last_built_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KBCreate(SQLModel):
    name: str
    description: Optional[str] = None
    space_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    source_type: str = "conversation"
    extraction_model: Optional[str] = None
    summarization_model: Optional[str] = None


class KBRead(SQLModel):
    id: UUID
    name: str
    description: Optional[str] = None
    space_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    source_type: str
    build_status: str
    extraction_model: Optional[str] = None
    summarization_model: Optional[str] = None
    node_count: int
    edge_count: int
    last_built_at: Optional[datetime] = None
    created_at: datetime


class KBUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    extraction_model: Optional[str] = None
    summarization_model: Optional[str] = None
