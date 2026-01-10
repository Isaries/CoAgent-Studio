from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .agent_config import AgentConfig


class AgentKey(SQLModel, table=True):
    __tablename__ = "agent_key"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    agent_config_id: UUID = Field(foreign_key="agentconfig.id", index=True)
    key_type: str = Field(index=True)  # room_key, global_key, backup_key
    encrypted_api_key: str
    description: Optional[str] = None

    # Relationship
    agent_config: "AgentConfig" = Relationship(back_populates="keys")
