from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    GUEST = "guest"
    STUDENT = "student"
    TA = "ta"
    TEACHER = "teacher"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class UserBase(SQLModel):
    email: str = Field(index=True)
    username: Optional[str] = Field(default=None, index=True, unique=True, description="For non-email login")
    full_name: Optional[str] = Field(default=None)
    role: UserRole = Field(default=UserRole.GUEST)
    avatar_url: Optional[str] = None

class User(UserBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    hashed_password: Optional[str] = None
    google_sub: Optional[str] = Field(default=None, index=True) # Google Unique ID
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships will be added later (enrollments, messages, etc.)

class UserCreate(UserBase):
    password: Optional[str] = None
    google_sub: Optional[str] = None

class UserRead(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    username: Optional[str] = None
