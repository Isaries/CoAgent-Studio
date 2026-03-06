from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .space import Space

# Default tab configuration for new rooms
DEFAULT_ENABLED_TABS = {
    "chat": True,
    "board": False,
    "docs": True,
    "process": True,
    "graph": False,
}


class RoomBase(SQLModel):
    name: str
    description: Optional[str] = None
    is_ai_active: bool = Field(default=True)  # Teacher/Student toggle
    is_analytics_active: bool = Field(default=False)  # Analytics toggle

    ai_frequency: float = Field(default=0.5)  # 0.0 to 1.0
    ai_mode: str = Field(default="teacher_only")  # off, teacher_only, both

    # Workflow engine version: "v2_graph" (LangGraph)
    workflow_engine_version: str = Field(default="v2_graph")

    # GraphRAG settings (kept for backward compat; new KB system via room_kb_id)
    graphrag_enabled: bool = Field(default=False)
    graphrag_extraction_model: str = Field(default="gpt-4o-mini")
    graphrag_summarization_model: str = Field(default="gpt-4o-mini")


class UserRoomLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", primary_key=True)
    role: str = Field(default="participant")


class RoomAgentLink(SQLModel, table=True):
    room_id: UUID = Field(foreign_key="room.id", primary_key=True)
    agent_id: UUID = Field(foreign_key="agentconfig.id", primary_key=True)

    # Per-room availability controls (overrides AgentConfig level)
    is_active: bool = Field(default=True)
    schedule_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    trigger_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))

    # Audit trail
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    )
    updated_by: Optional[UUID] = Field(default=None, foreign_key="user.id")


class Room(RoomBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    space_id: UUID = Field(foreign_key="space.id")
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    )

    # Decoupled workflow binding: which Workflow powers this Room's AI
    attached_workflow_id: Optional[UUID] = Field(default=None, foreign_key="workflow.id")

    # Dynamic tab configuration
    enabled_tabs: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))

    # Knowledge Base reference
    room_kb_id: Optional[UUID] = Field(default=None, foreign_key="knowledge_base.id")

    space: "Space" = Relationship(back_populates="rooms")

    # Backward compat property
    @property
    def course_id(self) -> UUID:
        return self.space_id


class RoomCreate(RoomBase):
    space_id: UUID


class RoomRead(RoomBase):
    id: UUID
    space_id: UUID
    created_at: datetime
    attached_workflow_id: Optional[UUID] = None
    enabled_tabs: Optional[Dict[str, Any]] = None
    room_kb_id: Optional[UUID] = None


class RoomUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_ai_active: Optional[bool] = None
    is_analytics_active: Optional[bool] = None
    ai_frequency: Optional[float] = None
    ai_mode: Optional[str] = None
    workflow_engine_version: Optional[str] = None
    attached_workflow_id: Optional[UUID] = None
    graphrag_enabled: Optional[bool] = None
    graphrag_extraction_model: Optional[str] = None
    graphrag_summarization_model: Optional[str] = None
    enabled_tabs: Optional[Dict[str, Any]] = None
    room_kb_id: Optional[UUID] = None
