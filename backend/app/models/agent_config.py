from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class AgentType(str):
    TEACHER = "teacher"
    STUDENT = "student"
    DESIGN = "design"
    ANALYTICS = "analytics"

class AgentConfigBase(SQLModel):
    course_id: UUID = Field(foreign_key="course.id")
    type: str = Field(index=True) # teacher, student, etc.
    model_provider: str = Field(default="gemini") # gemini, openai
    system_prompt: str
    
    # We don't store raw api key in base. 
    # API Key will be stored in a separate encrypted field or column in table.
    
class AgentConfig(AgentConfigBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    encrypted_api_key: Optional[str] = None
    settings: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AgentConfigCreate(AgentConfigBase):
    api_key: Optional[str] = None # Input only
    settings: Optional[Dict[str, Any]] = {}

class AgentConfigRead(AgentConfigBase):
    id: UUID
    updated_at: datetime
    has_api_key: bool # Derived
