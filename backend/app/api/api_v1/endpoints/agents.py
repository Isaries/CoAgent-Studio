from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any, List
from uuid import UUID
from app.api import deps
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.agent_config import AgentConfig, AgentConfigCreate, AgentConfigRead, AgentType
from app.core.agent_core import AgentCore
from pydantic import BaseModel

router = APIRouter()

# ... (DesignRequest class) ...

@router.get("/{course_id}", response_model=List[AgentConfigRead])
async def read_agent_configs(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all agent configs for a course.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    query = select(AgentConfig).where(AgentConfig.course_id == course_id)
    result = await session.exec(query)
    return result.all()

@router.put("/{course_id}/{agent_type}", response_model=AgentConfigRead)
async def update_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    agent_type: str,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update or Create Agent Config for a specific type in a course.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if exists
    query = select(AgentConfig).where(AgentConfig.course_id == course_id, AgentConfig.type == agent_type)
    result = await session.exec(query)
    agent_config = result.first()
    
    if agent_config:
        # Update
        agent_config.system_prompt = config_in.system_prompt
        agent_config.model_provider = config_in.model_provider
        if config_in.api_key:
            agent_config.encrypted_api_key = config_in.api_key 
        if config_in.settings:
            agent_config.settings = config_in.settings
        
        session.add(agent_config)
        await session.commit()
        await session.refresh(agent_config)
        return agent_config
    else:
        # Create
        new_config = AgentConfig(
            course_id=course_id,
            type=agent_type,
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            encrypted_api_key=config_in.api_key,
            settings=config_in.settings
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config

class DesignRequest(BaseModel):
    requirement: str
    target_agent_type: str # teacher or student
    course_context: str # Title or description
    api_key: str # User provided temporarily or from stored setting
    provider: str = "gemini"

class DesignResponse(BaseModel):
    generated_prompt: str



@router.post("/generate", response_model=DesignResponse)
async def generate_agent_prompt(
    *,
    request: DesignRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Design Agent endpoint.
    Takes user requirements and outputs a system prompt for Teacher/Student.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]:
         raise HTTPException(status_code=403, detail="Not enough permissions")

    # Construct meta-prompt
    from app.core.specialized_agents import DesignAgent
    
    # We use the user's API Key (or system default if we had one) to run the Design Agent
    # For now, we trust the key passed in request
    agent = DesignAgent(provider=request.provider, api_key=request.api_key)
    
    result = await agent.generate_system_prompt(
        target_agent_type=request.target_agent_type,
        context=request.course_context,
        requirement=request.requirement
    )
    
    return {"generated_prompt": result}
