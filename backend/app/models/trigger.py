"""
TriggerPolicy – Defines when and how a Workflow should be triggered.

Replaces the hard-coded time-based trigger logic previously bound to
Room/Agent configurations.  Each policy subscribes to a specific event
type and, when its conditions are met, invokes a target Workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TriggerEventType(str, Enum):
    """Canonical event types that can activate a trigger."""
    USER_MESSAGE = "user_message"       # A user sends a message
    SILENCE = "silence"                 # No activity for N minutes
    TIMER = "timer"                     # Cron / interval timer
    WEBHOOK = "webhook"                 # Incoming external HTTP call
    MANUAL = "manual"                   # Explicitly triggered by user / API


class TriggerPolicy(SQLModel, table=True):
    """
    Stores a single trigger rule that links an event condition to a Workflow.

    Example conditions JSON:
        {"threshold_mins": 5}           # for SILENCE
        {"cron": "0 0 * * *"}           # for TIMER
        {"interval_mins": 30}           # for TIMER (interval-based)
    """
    __tablename__ = "trigger_policy"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(default="Untitled Trigger")
    event_type: str = Field(default=TriggerEventType.USER_MESSAGE.value)

    conditions: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )

    target_workflow_id: UUID = Field(foreign_key="workflow.id", index=True)

    # Optional: scope the trigger to a specific session/room
    # If null, the trigger applies globally
    scope_session_id: Optional[str] = Field(default=None, index=True)

    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")


class TriggerPolicyCreate(SQLModel):
    name: str = "Untitled Trigger"
    event_type: str = TriggerEventType.USER_MESSAGE.value
    conditions: Dict[str, Any] = {}
    target_workflow_id: UUID
    scope_session_id: Optional[str] = None
    is_active: bool = True


class TriggerPolicyRead(SQLModel):
    id: UUID
    name: str
    event_type: str
    conditions: Dict[str, Any]
    target_workflow_id: UUID
    scope_session_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TriggerPolicyUpdate(SQLModel):
    name: Optional[str] = None
    event_type: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    target_workflow_id: Optional[UUID] = None
    scope_session_id: Optional[str] = None
    is_active: Optional[bool] = None
