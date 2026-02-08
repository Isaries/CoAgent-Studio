"""
Agent Type Metadata Model.

Stores metadata for dynamic agent types, enabling users to create
custom agent types without code changes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AgentTypeMetadata(SQLModel, table=True):
    """
    Metadata for agent types. Enables dynamic creation of new agent types.
    
    System types (is_system=True) are pre-defined and cannot be deleted.
    User types can be created by admins and used across the platform.
    """
    __tablename__ = "agenttypemetadata"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    
    # Type identification
    type_name: str = Field(unique=True, index=True)  # "researcher", "code_reviewer"
    display_name: str = Field(default="")  # "Research Assistant"
    description: Optional[str] = None
    
    # Category determines base behavior
    category: str = Field(default="instructor", index=True)  # instructor, participant, utility, external
    
    # UI configuration
    icon: Optional[str] = None  # Icon identifier for frontend
    color: Optional[str] = None  # Badge/accent color
    
    # Defaults for new agents of this type
    default_system_prompt: Optional[str] = None
    default_model_provider: str = Field(default="gemini")
    default_model: Optional[str] = None
    default_settings: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))
    
    # Capabilities this type typically has
    default_capabilities: Optional[List[str]] = Field(default=[], sa_column=Column(JSONB))
    
    # Ownership
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    is_system: bool = Field(default=False)  # System types cannot be deleted
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTypeMetadataRead(SQLModel):
    """Read schema for AgentTypeMetadata."""
    id: UUID
    type_name: str
    display_name: str
    description: Optional[str] = None
    category: str
    icon: Optional[str] = None
    color: Optional[str] = None
    default_system_prompt: Optional[str] = None
    default_model_provider: str = "gemini"
    default_model: Optional[str] = None
    default_settings: Optional[Dict[str, Any]] = {}
    default_capabilities: Optional[List[str]] = []
    is_system: bool = False


class AgentTypeMetadataCreate(SQLModel):
    """Create schema for AgentTypeMetadata."""
    type_name: str
    display_name: str
    description: Optional[str] = None
    category: str = "instructor"
    icon: Optional[str] = None
    color: Optional[str] = None
    default_system_prompt: Optional[str] = None
    default_model_provider: str = "gemini"
    default_model: Optional[str] = None
    default_settings: Optional[Dict[str, Any]] = {}
    default_capabilities: Optional[List[str]] = []
