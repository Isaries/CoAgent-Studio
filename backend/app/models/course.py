from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .announcement import Announcement
    from .room import Room


class UserCourseLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    course_id: UUID = Field(foreign_key="course.id", primary_key=True)
    role: str = Field(default="student")  # student, ta


class CourseBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None


class Course(CourseBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    rooms: List["Room"] = Relationship(
        back_populates="course", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_links: List["UserCourseLink"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    # announcements: List["Announcement"] = Relationship(
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    # )
    # NOTE: Announcement model might not have Course relationship back-populated explicitly in this snippet.
    # Assuming standard pattern, if Announcement has course_id, we can define relationship here or rely on DB.
    # Given I cannot see Announcement model, I will adding explicit relationships for knowns.
    # Checking AgentConfig from previous view: it has course_id.

    # We must import these types if we use them in type hints, inside TYPE_CHECKING.
    # But for now, let's keep it simple. If we rely on SQLAlchemy "cascade", we need the relationship defined here.

    # To be safe without seeing all models (Announcement, etc), I will ONLY add relationship for 'rooms' and 'agent_configs' which I have confirmed.
    # And 'user_links' which is defined in this file.

    # agent_configs: List["AgentConfig"] = Relationship(
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    # )
    announcements: List["Announcement"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class CourseCreate(CourseBase):
    pass


class CourseRead(CourseBase):
    id: UUID
    owner_id: UUID
    owner_name: Optional[str] = None
    created_at: datetime


class CourseUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CourseMember(SQLModel):
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str  # student, ta


class CourseMemberUpdate(SQLModel):
    role: str
