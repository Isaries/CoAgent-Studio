from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .agent_key import AgentKey


class AgentType(str, Enum):
    """Legacy enum for backward compatibility. Use type string directly for new agents."""
    TEACHER = "teacher"
    STUDENT = "student"
    DESIGN = "design"
    ANALYTICS = "analytics"


class AgentCategory(str, Enum):
    """
    Agent category determines base behavior and UI treatment.
    Extensible via database metadata for future categories.
    """
    INSTRUCTOR = "instructor"     # Guides/supervises (e.g., Teacher)
    PARTICIPANT = "participant"   # Contributes to discussion (e.g., Student)
    UTILITY = "utility"           # Background tasks (e.g., Analytics, Design)
    EXTERNAL = "external"         # External A2A agents via webhook


class AgentConfigBase(SQLModel):
    course_id: Optional[UUID] = Field(default=None, foreign_key="course.id", index=True)
    type: str = Field(index=True)  # teacher, student, etc.
    name: str = Field(default="Default Profile")
    model_provider: str = Field(default="gemini")  # gemini, openai
    system_prompt: str

    # My Agent (Master-Instance) fields
    parent_config_id: Optional[UUID] = Field(default=None, foreign_key="agentconfig.id", index=True)
    is_template: bool = Field(default=False)  # True = Global/My Agent template

    # Multi-Agent & External Integration fields
    category: str = Field(default="instructor")  # instructor, participant, utility, external
    is_external: bool = Field(default=False)  # True = External A2A agent
    external_config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    capabilities: Optional[List[str]] = Field(default=[], sa_column=Column(JSONB))

    # User API Key Chain (Multi-Key Support)
    # List of UserAPIKey.id references
    user_key_ids: Optional[List[UUID]] = Field(default=[], sa_column=Column(JSONB))

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

    versions: List["AgentConfigVersion"] = Relationship(
        back_populates="agent_config", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class AgentConfigVersion(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    config_id: UUID = Field(foreign_key="agentconfig.id", index=True)
    
    version_label: str = Field(default="v1")
    system_prompt: str
    model_provider: str
    model: Optional[str] = None
    
    # Snapshot of settings at that time
    settings: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    agent_config: "AgentConfig" = Relationship(back_populates="versions")


class AgentConfigCreate(AgentConfigBase):
    api_key: Optional[str] = None  # Input only
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    trigger_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    context_window: int = 10
    user_key_ids: Optional[List[UUID]] = [] # Explicitly add to create schema


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

    # My Agent fields
    parent_config_id: Optional[UUID] = None
    is_template: bool = False

    # Multi-Agent & External fields
    category: str = "instructor"
    is_external: bool = False
    external_config: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = []

    created_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None

    masked_api_key: Optional[str] = None  # Calculated field for UI
    user_key_ids: Optional[List[UUID]] = []
    # encrypted_api_key is explicitly excluded from this model to prevent leak
