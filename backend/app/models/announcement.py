from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class AnnouncementBase(SQLModel):
    title: str
    content: str
    space_id: UUID = Field(foreign_key="space.id")


class Announcement(AnnouncementBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    author_id: UUID = Field(foreign_key="user.id")
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)))

    # Backward compat property
    @property
    def course_id(self) -> UUID:
        return self.space_id


class AnnouncementCreate(SQLModel):
    title: str
    content: str
    space_id: UUID


class AnnouncementRead(AnnouncementBase):
    id: UUID
    author_id: UUID
    created_at: datetime
