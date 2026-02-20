from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .agent_config import AgentConfig
    from .project import Project
    from .user import User


class AgentThreadBase(SQLModel):
    name: Optional[str] = Field(default="New Thread")
    metadata_json: Optional[str] = Field(default="{}")


class AgentThread(AgentThreadBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    agent_id: UUID = Field(foreign_key="agentconfig.id", index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    messages: List["ThreadMessage"] = Relationship(
        back_populates="thread",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ThreadMessage.created_at"}
    )
    
class AgentThreadCreate(AgentThreadBase):
    project_id: UUID
    agent_id: UUID


class AgentThreadRead(AgentThreadBase):
    id: UUID
    project_id: UUID
    agent_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class AgentThreadUpdate(SQLModel):
    name: Optional[str] = None
    metadata_json: Optional[str] = None


class ThreadMessageBase(SQLModel):
    role: str = Field(description="Role of the sender (user, assistant, tool, system)")
    content: str
    metadata_json: Optional[str] = Field(default=None, description="Additional data like tool calls")


class ThreadMessage(ThreadMessageBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    thread_id: UUID = Field(foreign_key="agentthread.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    thread: AgentThread = Relationship(back_populates="messages")


class ThreadMessageCreate(ThreadMessageBase):
    pass


class ThreadMessageRead(ThreadMessageBase):
    id: UUID
    thread_id: UUID
    created_at: datetime


class ThreadMessageUpdate(SQLModel):
    content: Optional[str] = None
    metadata_json: Optional[str] = None
