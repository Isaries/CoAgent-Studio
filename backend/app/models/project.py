from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .agent_config import AgentConfig
    from .organization import Organization
    from .user import User


class UserProjectLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", primary_key=True)
    role: str = Field(default="member")  # admin, member, viewer


class ProjectBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None


class Project(ProjectBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organization.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    organization: "Organization" = Relationship(back_populates="projects")
    
    agent_configs: List["AgentConfig"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_links: List["UserProjectLink"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class ProjectCreate(ProjectBase):
    organization_id: UUID


class ProjectRead(ProjectBase):
    id: UUID
    organization_id: UUID
    created_at: datetime


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
