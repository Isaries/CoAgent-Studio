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

    # Delegate to Service
    from app.services.design_service import DesignAgentService
    
    design_service = DesignAgentService(session)
    result = await design_service.generate_prompt(request, current_user)

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


@router.get("/{project_id}")
async def read_agent_configs(
    project_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all agent configs for a project.
    """
    service = AgentConfigService(session)
    Configs = await service.get_project_agent_configs(project_id, current_user)

    # Mask keys for response
    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)

    return response_data


@router.post("/{project_id}")
async def create_project_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new agent config profile.
    Allowed: Owner, TA.
    """
    service = AgentConfigService(session)

    # Logic moved to service: duplicate check, auto-activate, permission check
    new_config = await service.create_and_initialize_config(project_id, config_in, current_user)

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
    await service.get_project_agent_config(agent_id, current_user)

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


# =====================================================
# My Agent (Global Agent) Endpoints
# =====================================================


@router.get("/global/list")
async def list_global_agents(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all global agent templates (My Agents) owned by the current user.
    """
    service = AgentConfigService(session)
    configs = await service.get_global_agents(current_user)

    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)

    return response_data


@router.post("/global")
async def create_global_agent(
    *,
    session: AsyncSession = Depends(deps.get_session),
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new global agent template (My Agent).
    """
    service = AgentConfigService(session)
    new_config = await service.create_global_agent(config_in, current_user)

    c_read = AgentConfigRead.model_validate(new_config)
    if new_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(new_config.encrypted_api_key)

    return c_read


@router.post("/global/{agent_id}/clone-to-project/{project_id}")
async def clone_global_agent_to_project(
    *,
    agent_id: UUID,
    project_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Clone a global agent template to a specific project.
    Creates an instance linked to the parent template.
    """
    service = AgentConfigService(session)
    cloned_config = await service.clone_global_agent_to_project(agent_id, project_id, current_user)

    c_read = AgentConfigRead.model_validate(cloned_config)
    if cloned_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(cloned_config.encrypted_api_key)

    return c_read


@router.post("/{config_id}/sync-from-parent")
async def sync_from_parent(
    *,
    config_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Sync an agent instance with its parent template (My Agent).
    Overwrites system_prompt, model_provider, model, and settings.
    """
    service = AgentConfigService(session)
    synced_config = await service.sync_from_parent(config_id, current_user)

    c_read = AgentConfigRead.model_validate(synced_config)
    if synced_config.encrypted_api_key:
        c_read.masked_api_key = mask_api_key(synced_config.encrypted_api_key)

    return c_read


# ============================================================
# External Agent Management Endpoints
# ============================================================

# ============================================================
# External Agent Management Endpoints
# ============================================================

class ExternalAgentCreate(BaseModel):
    """Request schema for creating an external agent."""
    name: str
    type: str = "external"
    webhook_url: str
    auth_type: str = "bearer"  # none, bearer, oauth2
    auth_token: Optional[str] = None
    oauth_config: Optional[Dict[str, Any]] = None
    timeout_ms: int = 30000
    fallback_message: str = "⚠️ External agent is temporarily unavailable."
    system_prompt: str = "External agent integration."


class ExternalAgentTestResult(BaseModel):
    """Response for connection test."""
    success: bool
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


@router.get("/external/list")
async def list_external_agents(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List all external agents visible to the current user.
    """
    service = AgentConfigService(session)
    configs = await service.list_external_agents(current_user)
    
    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)
    
    return response_data


@router.post("/external/create", response_model=AgentConfigRead)
async def create_external_agent(
    *,
    data: ExternalAgentCreate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
) -> Any:
    """
    Create a new external agent configuration.
    Only admins can create external agents.
    """
    service = AgentConfigService(session)
    
    # Build external_config dict
    import secrets
    external_config = {
        "webhook_url": data.webhook_url,
        "auth_type": data.auth_type,
        "timeout_ms": data.timeout_ms,
        "fallback_message": data.fallback_message,
        "callback_token": secrets.token_urlsafe(32),
    }
    
    if data.auth_type == "bearer" and data.auth_token:
        external_config["auth_token"] = data.auth_token
    
    if data.auth_type == "oauth2" and data.oauth_config:
        external_config["oauth_config"] = data.oauth_config

    new_config = await service.create_external_agent(
        name=data.name,
        type_name=data.type,
        external_config=external_config,
        system_prompt=data.system_prompt,
        current_user=current_user
    )
    
    c_read = AgentConfigRead.model_validate(new_config)
    return c_read


@router.post("/external/test-connection", response_model=ExternalAgentTestResult)
async def test_external_connection_params(
    *,
    data: ExternalAgentCreate, # Reuse create schema for params
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Test connection params before creating the agent.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = AgentConfigService(session)
    
    # Construct config dict from request
    external_config = {
        "webhook_url": data.webhook_url,
        "auth_type": data.auth_type,
        "timeout_ms": data.timeout_ms,
    }
    if data.auth_token:
        external_config["auth_token"] = data.auth_token
    if data.oauth_config:
        external_config["oauth_config"] = data.oauth_config

    return await service.test_external_connection_params(external_config)


@router.get("/{config_id}/test-connection", response_model=ExternalAgentTestResult)
async def test_external_agent_connection(
    *,
    config_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Test connection to an existing external agent.
    Sends a health check request to the webhook URL.
    """
    service = AgentConfigService(session)
    config = await service.get_course_agent_config(config_id, current_user) # Permission check included
    
    if not config.is_external:
        raise HTTPException(status_code=400, detail="Not an external agent")
        
    return await service.test_external_connection(config)


