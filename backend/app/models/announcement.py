from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AnnouncementBase(SQLModel):
    title: str
    content: str
    course_id: UUID = Field(foreign_key="course.id")


class Announcement(AnnouncementBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    author_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    # course is defined in Course model (update needed there if we want back_populates)
    # author needs back_populates in User if desired, or just foreign key


class AnnouncementCreate(SQLModel):
    title: str
    content: str
    course_id: UUID


class AnnouncementRead(AnnouncementBase):
    id: UUID
    author_id: UUID
    created_at: datetime
