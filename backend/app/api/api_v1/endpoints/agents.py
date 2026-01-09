from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
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

from app.core.security import encrypt_api_key, mask_api_key

router = APIRouter()

@router.get("/system")
async def read_system_agent_configs(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all system-wide agent configs (Design, Analytics).
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = select(AgentConfig).where(AgentConfig.course_id == None)
    result = await session.exec(query)
    return result.all()

@router.put("/system/{agent_type}")
async def update_system_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    agent_type: str,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update or Create System Agent Config (Design, Analytics).
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if exists
    query = select(AgentConfig).where(AgentConfig.course_id == None, AgentConfig.type == agent_type)
    result = await session.exec(query)
    agent_config = result.first()
    
    if agent_config:
        # Update
        agent_config.system_prompt = config_in.system_prompt
        agent_config.model_provider = config_in.model_provider
        agent_config.model = config_in.model
        agent_config.model = config_in.model
        if config_in.api_key is not None:
            if config_in.api_key == "":
                agent_config.encrypted_api_key = None
            else:
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
            course_id=None,
            type=agent_type,
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            model=config_in.model,
            encrypted_api_key=config_in.api_key,
            settings=config_in.settings
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config

@router.get("/{course_id}")
async def read_agent_configs(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all agent configs for a course.
    """
    try:
        print(f"DEBUG: START read_agent_configs course_id={course_id} user={current_user.id}")
        course = await session.get(Course, course_id)
        if not course:
            print("DEBUG: Course not found")
            raise HTTPException(status_code=404, detail="Course not found")
            
        # Permission Check
        print(f"DEBUG: Check perms. Owner={course.owner_id}, Current={current_user.id}, Role={current_user.role}")
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
              # Check if TA
              print("DEBUG: Checking TA link")
              from app.models.course import UserCourseLink
              link = await session.get(UserCourseLink, (current_user.id, course_id))
              if not link or link.role != "ta":
                   print("DEBUG: Not TA")
                   raise HTTPException(status_code=403, detail="Not enough permissions")
    
        print("DEBUG: Querying AgentConfig")
        query = select(AgentConfig).where(AgentConfig.course_id == course_id)
        result = await session.exec(query)
        data = result.all()
        print(f"DEBUG: FETCHED {len(data)} configs.")
        
        # Masking for Security
        response_data = []
        for config in data:
            c_read = AgentConfigRead.model_validate(config)
            if config.encrypted_api_key:
                c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
            response_data.append(c_read)
            
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"DEBUG: EXCEPTION {e}")
        raise HTTPException(status_code=500, detail=f"DEBUG ERROR: {str(e)} TYPE: {type(e)}")

@router.post("/{course_id}")
async def create_course_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new agent config profile.
    Allowed: Owner, TA.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Permission Check: Owner or TA
    is_admin_or_owner = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] or course.owner_id == current_user.id
    if not is_admin_or_owner:
         from app.models.course import UserCourseLink
         link = await session.get(UserCourseLink, (current_user.id, course_id))
         if not link or link.role != "ta":
              raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check for duplicate name
    query = select(AgentConfig).where(
        AgentConfig.course_id == course_id,
        AgentConfig.type == config_in.type,
        AgentConfig.name == config_in.name
    )
    dup = await session.exec(query)
    if dup.first():
        raise HTTPException(status_code=400, detail="A brain with this name already exists for this agent type.")

    # If this is the first config of this type for this course, make it active
    query = select(AgentConfig).where(AgentConfig.course_id == course_id, AgentConfig.type == config_in.type)
    existing = await session.exec(query)
    is_first = existing.first() is None
    
    # Encrypt API Key if provided
    encrypted_key = None
    if config_in.api_key:
        encrypted_key = encrypt_api_key(config_in.api_key)

    new_config = AgentConfig(
        course_id=course_id,
        type=config_in.type,
        name=config_in.name,
        system_prompt=config_in.system_prompt,
        model_provider=config_in.model_provider,
        model=config_in.model,
        encrypted_api_key=encrypted_key,
        settings=config_in.settings,
        is_active=is_first, # Auto-activate if first
        created_by=current_user.id
    )
    session.add(new_config)
    await session.commit()
    await session.refresh(new_config)
    
    # Return masked response
    c_read = AgentConfigRead.model_validate(new_config)
    if new_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(new_config.encrypted_api_key)
        
    return c_read

@router.put("/{config_id}")
async def update_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    config_id: UUID,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update an agent config profile.
    Allowed: Owner, or Creator (if TA).
    """
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    course = await session.get(Course, agent_config.course_id)
    
    # Permission Check
    is_admin_or_owner = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] or (course and course.owner_id == current_user.id)
    is_creator = agent_config.created_by == current_user.id
    
    if not (is_admin_or_owner or is_creator):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check for duplicate name
    if config_in.name != agent_config.name:
        query = select(AgentConfig).where(
            AgentConfig.course_id == agent_config.course_id,
            AgentConfig.type == agent_config.type,
            AgentConfig.name == config_in.name,
            AgentConfig.id != config_id
        )
        dup = await session.exec(query)
        if dup.first():
            raise HTTPException(status_code=400, detail="A brain with this name already exists.")

    agent_config.name = config_in.name
    agent_config.system_prompt = config_in.system_prompt
    agent_config.model_provider = config_in.model_provider
    agent_config.model = config_in.model
    
    agent_config.model = config_in.model
    
    if config_in.api_key is not None:
        if config_in.api_key == "":
             agent_config.encrypted_api_key = None
        else:
            # Encrypt the new key
            agent_config.encrypted_api_key = encrypt_api_key(config_in.api_key)
        
    if config_in.settings:
        agent_config.settings = config_in.settings
    
    agent_config.updated_at = datetime.utcnow()
    
    session.add(agent_config)
    await session.commit()
    await session.refresh(agent_config)
    
    # Return masked response
    c_read = AgentConfigRead.model_validate(agent_config)
    if agent_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(agent_config.encrypted_api_key)
        
    return c_read


@router.put("/{config_id}/activate")
async def activate_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    config_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Set a config as active.
    Allowed: Owner Only.
    """
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    course = await session.get(Course, agent_config.course_id)
    
    # Permission Check: Owner Only
    is_admin_or_owner = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] or (course and course.owner_id == current_user.id)
    if not is_admin_or_owner:
        raise HTTPException(status_code=403, detail="Only the course owner can activate a brain profile")

    # Deactivate others of same type efficiently
    from sqlmodel import update
    stmt = update(AgentConfig).where(
        AgentConfig.course_id == agent_config.course_id, 
        AgentConfig.type == agent_config.type
    ).values(is_active=False)
    await session.exec(stmt)
    
    # Activate current
    # We must reload or set explicitly. Since we updated all to False (including this one potentially if logic matched),
    # we set this one to True.
    agent_config.is_active = True
    session.add(agent_config)
        
    await session.commit()
    await session.refresh(agent_config)
    return agent_config

@router.delete("/{config_id}", status_code=204)
async def delete_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    config_id: UUID,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Delete a config profile.
    Allowed: Owner or Creator.
    """
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    course = await session.get(Course, agent_config.course_id)
    
    # Permission Check
    is_admin_or_owner = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] or (course and course.owner_id == current_user.id)
    is_creator = agent_config.created_by == current_user.id
    
    if not (is_admin_or_owner or is_creator):
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    await session.delete(agent_config)
    await session.commit()
    return

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
    session: AsyncSession = Depends(deps.get_session),
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
    
    # 1. Look for system-level Design Agent config
    from app.models.agent_config import AgentType
    query = select(AgentConfig).where(AgentConfig.course_id == None, AgentConfig.type == AgentType.DESIGN)
    db_result = await session.exec(query)
    sys_config = db_result.first()
    
    sys_prompt = sys_config.system_prompt if sys_config else None
    api_key = request.api_key # Priority to temporary key for generation
    if not api_key and sys_config:
        api_key = sys_config.encrypted_api_key

    agent = DesignAgent(provider=request.provider, api_key=api_key, system_prompt=sys_prompt)
    
    result = await agent.generate_system_prompt(
        target_agent_type=request.target_agent_type,
        context=request.course_context,
        requirement=request.requirement
    )
    
    return {"generated_prompt": result}
