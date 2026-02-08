"""
Artifact Model - Polymorphic Resource for Multi-Modal Workspaces.

This model supports:
- TaskArtifact: Kanban cards, to-dos
- DocArtifact: Collaborative documents
- ProcessArtifact: Workflow state machines
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class ArtifactType(str, Enum):
    """Types of artifacts that can be stored in a workspace."""
    TASK = "task"           # Kanban cards, to-do items
    DOC = "doc"             # Rich text documents
    PROCESS = "process"     # Workflow state machines


class AgentCapability(str, Enum):
    """
    Fine-grained permissions for agent actions.
    Used for RBAC enforcement in artifact operations.
    """
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    ARTIFACT_READ = "artifact:read"
    ARTIFACT_WRITE = "artifact:write"
    ARTIFACT_DELETE = "artifact:delete"


class ArtifactBase(SQLModel):
    """Base fields for Artifact."""
    room_id: UUID = Field(foreign_key="room.id", index=True)
    type: str = Field(index=True)  # ArtifactType value
    title: str
    
    # Polymorphic content storage
    # Task: {"status": "todo", "assignee": "agent-1", "priority": "high", "order": 0}
    # Doc: {"delta": {...}, "html": "...", "version_vector": {...}}
    # Process: {"steps": [...], "current_step": 0, "status": "running"}
    content: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    
    # Optional parent for hierarchical artifacts (subtasks, doc sections)
    parent_artifact_id: Optional[UUID] = Field(default=None, foreign_key="artifact.id", index=True)


class Artifact(ArtifactBase, table=True):
    """
    Core artifact entity.
    
    Supports optimistic locking via `version` field.
    """
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    
    # Audit fields
    version: int = Field(default=1)
    created_by: UUID = Field(foreign_key="user.id")
    last_modified_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Soft delete support
    is_deleted: bool = Field(default=False)


# --- Pydantic Schemas ---

class ArtifactCreate(SQLModel):
    """Schema for creating a new artifact."""
    type: str  # ArtifactType value
    title: str
    content: Dict[str, Any] = {}
    parent_artifact_id: Optional[UUID] = None


class ArtifactUpdate(SQLModel):
    """Schema for updating an artifact (partial)."""
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    
    # For optimistic locking - client must send current version
    expected_version: Optional[int] = None


class ArtifactRead(SQLModel):
    """Schema for reading an artifact."""
    id: UUID
    room_id: UUID
    type: str
    title: str
    content: Dict[str, Any]
    parent_artifact_id: Optional[UUID] = None
    
    version: int
    created_by: UUID
    last_modified_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
