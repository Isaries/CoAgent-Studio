from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AgentRoomState(SQLModel, table=True):
    """
    Runtime state for an Agent within a specific Room.

    Tracks counters, sleep status, and temporary trigger overrides.
    Uses Optimistic Locking via `version` field to prevent race conditions
    when multiple ARQ workers modify the same state concurrently.
    """

    __tablename__ = "agent_room_state"
    __table_args__ = (UniqueConstraint("room_id", "agent_id", name="uq_room_agent"),)

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", index=True)
    agent_id: UUID = Field(foreign_key="agentconfig.id", index=True)

    # --- Sleep / Close State ---
    is_sleeping: bool = Field(default=False)

    # --- Counters ---
    message_count_since_last_reply: int = Field(default=0)
    monologue_count: int = Field(default=0)
    last_agent_message_at: Optional[datetime] = None
    last_user_message_at: Optional[datetime] = None

    # --- Agent Self-Modification Overrides ---
    active_overrides: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )
    overrides_expires_at: Optional[datetime] = None

    # --- Optimistic Locking ---
    version: int = Field(default=0)

    updated_at: datetime = Field(default_factory=datetime.utcnow)
