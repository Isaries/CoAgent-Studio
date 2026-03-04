from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .announcement import Announcement
    from .room import Room


class UserSpaceLink(SQLModel, table=True):
    __tablename__ = "user_space_link"
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    space_id: UUID = Field(foreign_key="space.id", primary_key=True)
    role: str = Field(default="participant")  # participant, space_admin, space_owner


class SpaceBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None


class Space(SpaceBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")
    preset: str = Field(default="custom")  # colearn, support, research, custom
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)))

    # Relationships
    rooms: List["Room"] = Relationship(
        back_populates="space", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_links: List["UserSpaceLink"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    announcements: List["Announcement"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class SpaceCreate(SpaceBase):
    preset: str = "custom"


class SpaceRead(SpaceBase):
    id: UUID
    owner_id: UUID
    preset: str = "custom"
    owner_name: Optional[str] = None
    created_at: datetime


class SpaceUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    preset: Optional[str] = None


class SpaceMember(SQLModel):
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str  # participant, space_admin, space_owner


class SpaceMemberUpdate(SQLModel):
    role: str
