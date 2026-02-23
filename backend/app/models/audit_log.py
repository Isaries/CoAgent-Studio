from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """
    Enterprise audit trail for all Agent/Key/Link configuration changes.

    Records who changed what, when, and stores both old and new values
    for full traceability.
    """

    __tablename__ = "audit_log"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    # What was changed
    entity_type: str = Field(index=True)  # "api_key", "agent", "room_agent_link", "agent_room_state"
    entity_id: str = Field(index=True)  # UUID string of the modified entity

    # What action was performed
    action: str  # "update_schedule", "update_trigger", "toggle_active",
    # "sync_to_course", "agent_self_modify", "reset_state"

    # Who performed it
    actor_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    actor_type: str = Field(default="user")  # "user", "agent", "system"

    # Change details
    old_value: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )
    new_value: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Extra context
    extra_metadata: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
