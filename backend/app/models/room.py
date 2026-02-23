from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .course import Course
    from .agent_config import AgentConfig


class RoomBase(SQLModel):
    name: str
    description: Optional[str] = None
    is_ai_active: bool = Field(default=True)  # Teacher/Student toggle
    is_analytics_active: bool = Field(default=False)  # Analytics toggle

    ai_frequency: float = Field(default=0.5)  # 0.0 to 1.0
    ai_mode: str = Field(default="teacher_only")  # off, teacher_only, both


class UserRoomLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", primary_key=True)
    role: str = Field(default="student")


class RoomAgentLink(SQLModel, table=True):
    room_id: UUID = Field(foreign_key="room.id", primary_key=True)
    agent_id: UUID = Field(foreign_key="agentconfig.id", primary_key=True)

    # Per-room availability controls (overrides AgentConfig level)
    is_active: bool = Field(default=True)
    schedule_config: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )
    trigger_config: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[UUID] = Field(default=None, foreign_key="user.id")


class Room(RoomBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    course: "Course" = Relationship(back_populates="rooms")


class RoomCreate(RoomBase):
    course_id: UUID


class RoomRead(RoomBase):
    id: UUID
    course_id: UUID
    created_at: datetime


class RoomUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_ai_active: Optional[bool] = None
    is_analytics_active: Optional[bool] = None
    ai_frequency: Optional[float] = None
    ai_mode: Optional[str] = None
