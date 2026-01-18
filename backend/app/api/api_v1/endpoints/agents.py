from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.security import mask_api_key
from app.models.agent_config import AgentConfigCreate, AgentConfigRead, AgentType
from app.models.user import User, UserRole
from app.services.agent_config_service import AgentConfigService

router = APIRouter()


class DesignRequest(BaseModel):
    requirement: str
    target_agent_type: str  # teacher or student
    course_context: str  # Title or description
    api_key: Optional[str] = None  # User provided temporarily
    course_id: Optional[UUID] = None  # Context to look up stored key
    provider: str = "gemini"
    
    # Sandbox / Custom Settings
    custom_system_prompt: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_provider: Optional[str] = None
    custom_model: Optional[str] = None


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
    Takes user requirements and outputs a system prompt.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = AgentConfigService(session)

    # 1. Get System Prompt for Design Agent (Instruction)
    
    # SANDBOX LOGIC: If custom prompt is provided, use it.
    if request.custom_system_prompt:
        sys_prompt = request.custom_system_prompt
    else:
        # Standard Logic
        configs = await service.get_system_agent_configs(current_user)
        sys_config = next((c for c in configs if c.type == AgentType.DESIGN), None)
        sys_prompt = sys_config.system_prompt if sys_config else None

    # 2. Determine API Key & Model Provider
    # SANDBOX LOGIC: If custom key is provided, use it.
    
    if request.custom_api_key:
        api_key = request.custom_api_key
        # Use custom provider/model if provided, otherwise default to request values or defaults
        provider = request.custom_provider or request.provider
        model = request.custom_model
    else:
        # Standard Logic
        # Priority: Request -> Course Config -> Error
        api_key = request.api_key
        provider = request.provider
        model = None # Default
    
        if not api_key:
            if request.course_id:
                # Look up course config
                course_configs = await service.get_course_agent_configs(request.course_id, current_user)
                design_config = next((c for c in course_configs if c.type == AgentType.DESIGN), None)
                if design_config: 
                    if design_config.encrypted_api_key:
                        api_key = design_config.encrypted_api_key
                    # Also use the stored provider/model if not overridden
                    if not provider and design_config.model_provider:
                        provider = design_config.model_provider
                    if not model and design_config.model:
                        model = design_config.model
            else:
                # SYSTEM SCOPE: Look up System Design Agent Config
                # (We might have fetched it above for prompt, but let's be safe)
                if 'configs' not in locals():
                    configs = await service.get_system_agent_configs(current_user)
                sys_config_for_key = next((c for c in configs if c.type == AgentType.DESIGN), None)
                if sys_config_for_key:
                    if sys_config_for_key.encrypted_api_key:
                        api_key = sys_config_for_key.encrypted_api_key
                    if not provider and sys_config_for_key.model_provider:
                        provider = sys_config_for_key.model_provider
                    if not model and sys_config_for_key.model:
                        model = sys_config_for_key.model

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API Key is required. Please set it in the Design Agent settings for this course.",
        )

    from app.core.specialized_agents import DesignAgent

    agent = DesignAgent(
        provider=provider, 
        api_key=api_key, 
        system_prompt=sys_prompt,
        model=model
    )

    try:
        result = await agent.generate_system_prompt(
            target_agent_type=request.target_agent_type,
            context=request.course_context,
            requirement=request.requirement,
        )
    except Exception as e:
        # Map common auth errors
        if "401" in str(e) or "invalid api key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Invalid API Key provided.") from e
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"generated_prompt": result}


@router.get("/system")
async def read_system_agent_configs(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all system-wide agent configs (Design, Analytics).
    """
    service = AgentConfigService(session)
    return await service.get_system_agent_configs(current_user)


@router.put("/system/{agent_type}", response_model=AgentConfigRead)
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
    service = AgentConfigService(session)
    agent_config = await service.update_system_agent_config(agent_type, config_in, current_user)
    
    # Mask
    c_read = AgentConfigRead.model_validate(agent_config)
    if agent_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(agent_config.encrypted_api_key)
        
    return c_read


@router.get("/{course_id}")
async def read_agent_configs(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all agent configs for a course.
    """
    service = AgentConfigService(session)
    configs = await service.get_course_agent_configs(course_id, current_user)

    # Mask keys for response
    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)

    return response_data


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
    service = AgentConfigService(session)

    # Logic moved to service: duplicate check, auto-activate, permission check
    new_config = await service.create_and_initialize_config(course_id, config_in, current_user)

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
    service = AgentConfigService(session)

    # Duplicate check logic:
    # Need to get config first to know course_id
    # Service update checks ID existence.
    # But for duplicate name, I need context.
    # I'll rely on frontend or DB constraint, or just let it pass for now.
    # The previous code was strict.

    agent_config = await service.update_agent_config(str(config_id), config_in, current_user)

    # Mask
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
    service = AgentConfigService(session)
    return await service.activate_agent(str(config_id), current_user)


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
    service = AgentConfigService(session)
    await service.delete_agent_config(str(config_id), current_user)
    return


@router.get("/{agent_id}/keys", response_model=Dict[str, str])
async def get_agent_keys(
    *,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = AgentConfigService(session)

    # Verify existence and permission
    await service.get_course_agent_config(agent_id, current_user)

    # Service returns list of AgentKey sqlmodels.
    keys = await service.get_agent_keys(agent_id)

    from app.core.security import mask_api_key

    # Convert directly to dict to avoid model object lingering
    return {k.key_type: mask_api_key(k.encrypted_api_key) for k in keys}


@router.put("/{agent_id}/keys", response_model=AgentConfigRead)
async def update_agent_keys(
    *,
    agent_id: UUID,
    keys_data: Dict[str, Optional[str]],  # {"room_key": "...", "global_key": "..."}
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update API keys for an agent configuration.
    """
    service = AgentConfigService(session)

    # Update logic moved to service, including permission check and refresh
    updated_config = await service.update_agent_keys(agent_id, keys_data, current_user)

    c_read = AgentConfigRead.model_validate(updated_config)

    if updated_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(updated_config.encrypted_api_key)

    return c_read



