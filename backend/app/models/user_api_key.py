from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class UserAPIKeyBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", index=True)
    provider: str = Field(index=True)  # openai, gemini
    alias: str = Field(index=True)  # e.g. "Personal Gemini Key"
    description: Optional[str] = None


class UserAPIKey(UserAPIKeyBase, table=True):
    __tablename__ = "user_api_key"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    encrypted_key: str

    # Scheduling & Availability Controls
    is_active: bool = Field(default=True)
    schedule_config: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="api_keys")


class UserAPIKeyCreate(UserAPIKeyBase):
    api_key: str  # Raw key input


class UserAPIKeyRead(UserAPIKeyBase):
    id: UUID
    masked_key: str
    is_active: bool = True
    schedule_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
