from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel

class UserCourseLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    course_id: UUID = Field(foreign_key="course.id", primary_key=True)
    role: str = Field(default="student") # student, ta

class CourseBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None

class Course(CourseBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    rooms: List["Room"] = Relationship(back_populates="course")

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
    role: str # student, ta

class CourseMemberUpdate(SQLModel):
    role: str
