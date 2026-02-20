from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.agent_config import AgentConfigCreate, AgentConfigRead, VersionCreate, VersionRead
from app.models.user import User
from app.services.agent_config_service import AgentConfigService

router = APIRouter()


@router.get("/{project_id}", response_model=List[AgentConfigRead])
async def read_agent_configs(
    project_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all agent configs for a project.
    """
    service = AgentConfigService(session)
    return await service.get_project_agent_configs(project_id, current_user)


@router.put("/{project_id}/{agent_type}", response_model=AgentConfigRead)
async def update_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    agent_type: str,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update or Create Agent Config for a specific type in a project.
    """
    service = AgentConfigService(session)
    return await service.upsert_project_agent_config_by_type(
        project_id, agent_type, config_in, current_user
    )


# ==========================
# Versioning Endpoints
# ==========================


@router.post("/{config_id}/versions", response_model=VersionRead)
async def create_config_version(
    *,
    config_id: UUID,
    version_in: VersionCreate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Save current config state as a new version.
    """
    service = AgentConfigService(session)
    return await service.create_version(config_id, version_in.version_label, current_user)


@router.get("/{config_id}/versions", response_model=List[VersionRead])
async def list_config_versions(
    *,
    config_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List history versions of the config.
    """
    service = AgentConfigService(session)
    return await service.list_versions(config_id, current_user)


@router.post("/{config_id}/versions/{version_id}/restore", response_model=AgentConfigRead)
async def restore_config_version(
    *,
    config_id: UUID,
    version_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Restore a specific version to be the active config.
    """
    service = AgentConfigService(session)
    agent_config = await service.restore_version(config_id, version_id, current_user)
    
    # Mask API Key (not part of version, kept from original config)
    from app.models.agent_config import AgentConfigRead
    c_read = AgentConfigRead.model_validate(agent_config)
    if agent_config.encrypted_api_key:
        from app.core.security import mask_api_key
        c_read.masked_api_key = mask_api_key(agent_config.encrypted_api_key)
        
    return c_read
