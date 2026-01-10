from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .agent_key import AgentKey


class AgentType(str):
    TEACHER = "teacher"
    STUDENT = "student"
    DESIGN = "design"
    ANALYTICS = "analytics"


class AgentConfigBase(SQLModel):
    course_id: Optional[UUID] = Field(default=None, foreign_key="course.id", index=True)
    type: str = Field(index=True)  # teacher, student, etc.
    name: str = Field(default="Default Profile")
    model_provider: str = Field(default="gemini")  # gemini, openai
    system_prompt: str

    # We don't store raw api key in base.
    # API Key will be stored in a separate encrypted field or column in table.

    # Model Version (e.g. gemini-1.5-pro, gpt-4o)
    model: Optional[str] = Field(default=None)


class AgentConfig(AgentConfigBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    encrypted_api_key: Optional[str] = None
    settings: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))

    # Advanced Trigger & Schedule Configs
    trigger_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    schedule_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    context_window: int = Field(default=10)

    is_active: bool = Field(default=False)
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def has_api_key(self) -> bool:
        return bool(self.encrypted_api_key)

    keys: List["AgentKey"] = Relationship(
        back_populates="agent_config", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )  # Auto-delete keys when config is deleted


class AgentConfigCreate(AgentConfigBase):
    api_key: Optional[str] = None  # Input only
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    trigger_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    context_window: int = 10


class AgentConfigRead(SQLModel):
    id: UUID
    course_id: Optional[UUID] = None
    type: str
    name: Optional[str] = "Default Profile"
    model_provider: str = "gemini"
    model: Optional[str] = None
    system_prompt: Optional[str] = ""
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)

    trigger_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    context_window: int = 10

    is_active: Optional[bool] = False

    created_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None

    masked_api_key: Optional[str] = None  # Calculated field for UI
    # encrypted_api_key is explicitly excluded from this model to prevent leak
