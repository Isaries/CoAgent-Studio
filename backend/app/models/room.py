from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel

class RoomBase(SQLModel):
    name: str
    description: Optional[str] = None
    is_ai_active: bool = Field(default=True)

    ai_frequency: float = Field(default=0.5) # 0.0 to 1.0

class UserRoomLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", primary_key=True)
    role: str = Field(default="student")

class Room(RoomBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    course: "Course" = Relationship(back_populates="rooms")

class RoomCreate(RoomBase):
    course_id: UUID

class RoomRead(RoomBase):
    id: UUID
    course_id: UUID
    created_at: datetime

class RoomUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_ai_active: Optional[bool] = None
    ai_frequency: Optional[float] = None
