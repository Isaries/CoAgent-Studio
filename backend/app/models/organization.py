from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class UserOrganizationLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    organization_id: UUID = Field(foreign_key="organization.id", primary_key=True)
    role: str = Field(default="member")  # owner, admin, member


class OrganizationBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None


class Organization(OrganizationBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    projects: List["Project"] = Relationship(
        back_populates="organization", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_links: List["UserOrganizationLink"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    id: UUID
    owner_id: UUID
    created_at: datetime


class OrganizationUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
