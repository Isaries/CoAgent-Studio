from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.agent_config import AgentConfig, AgentConfigCreate, AgentConfigRead, AgentConfigVersion
from app.models.project import Project, UserProjectLink
from app.models.user import User, UserRole
router = APIRouter()

# ... existing design endpoint ...

# CRUD for Agent Config


@router.get("/{project_id}", response_model=List[AgentConfigRead])
async def read_agent_configs(
    project_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:  # type: ignore[func-returns-value]
    """
    Get all agent configs for a project.
    """
    project = await session.get(Project, project_id)  # type: ignore[func-returns-value]
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN:
        link = await session.get(UserProjectLink, (current_user.id, project_id))
        if not link:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    query: Any = select(AgentConfig).where(AgentConfig.project_id == project_id)
    result = await session.exec(query)
    return result.all()


@router.put("/{project_id}/{agent_type}", response_model=AgentConfigRead)
async def update_agent_config(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    agent_type: str,
    config_in: AgentConfigCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:  # type: ignore[func-returns-value]
    """
    Update or Create Agent Config for a specific type in a project.
    """
    project = await session.get(Project, project_id)  # type: ignore[func-returns-value]
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN:
        link = await session.get(UserProjectLink, (current_user.id, project_id))
        if not link or link.role not in ["admin", "owner", "editor"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if exists
    query: Any = select(AgentConfig).where(
        AgentConfig.project_id == project_id, AgentConfig.type == agent_type
    )
    result = await session.exec(query)
    agent_config = result.first()

    if agent_config:
        # Update
        agent_config.system_prompt = config_in.system_prompt
        agent_config.model_provider = config_in.model_provider
        if config_in.api_key:
            agent_config.encrypted_api_key = config_in.api_key  # In real app, encrypt here!
        if config_in.settings:
            agent_config.settings = config_in.settings

        session.add(agent_config)
        await session.commit()
        await session.refresh(agent_config)
        return agent_config
    else:
        # Create
        new_config = AgentConfig(
            project_id=project_id,
            type=agent_type,
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            encrypted_api_key=config_in.api_key,  # Encrypt!
            settings=config_in.settings,
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config


# ==========================
# Versioning Endpoints
# ==========================

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class VersionCreate(SQLModel):
    version_label: str
    # Optional overrides if they want to save something different than current config
    # usually we just snapshot the current config
    
class VersionRead(SQLModel):
    id: UUID
    config_id: UUID
    version_label: str
    system_prompt: str
    model_provider: str
    model: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None


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
    admin_service = AgentConfigService(session)
    # Check permission (using service logic or direct check)
    
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    # Check permissions
    if agent_config.project_id:
        project = await session.get(Project, agent_config.project_id)
        if not project:
             raise HTTPException(status_code=404, detail="Project not found")
             
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await session.get(UserProjectLink, (current_user.id, agent_config.project_id))
            if not link or link.role not in ["admin", "owner", "editor"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        # System Agent: Only Admin
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
             raise HTTPException(status_code=403, detail="Not enough permissions")

    version = AgentConfigVersion(
        config_id=config_id,
        version_label=version_in.version_label,
        system_prompt=agent_config.system_prompt,
        model_provider=agent_config.model_provider,
        model=agent_config.model,
        settings=agent_config.settings,
        created_by=current_user.id
    )
    
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/{config_id}/versions", response_model=List[VersionRead])
async def list_config_versions(
    *,
    config_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    # Check existence
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Basic read permission check
    if agent_config.project_id:
        project = await session.get(Project, agent_config.project_id)
        if not project:
             raise HTTPException(status_code=404, detail="Project not found")
             
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await session.get(UserProjectLink, (current_user.id, agent_config.project_id))
            if not link:
                 raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        # System Agent: Admin or Teacher? Usually Admin for editing, but maybe readable?
        # Let's say Admin only for system config versions
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
             raise HTTPException(status_code=403, detail="Not enough permissions")
         
    query = select(AgentConfigVersion).where(AgentConfigVersion.config_id == config_id).order_by(AgentConfigVersion.created_at.desc())
    result = await session.exec(query)
    return result.all()


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
    agent_config = await session.get(AgentConfig, config_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    version = await session.get(AgentConfigVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    if version.config_id != config_id:
        raise HTTPException(status_code=400, detail="Version does not belong to this config")

    # Check permissions (Write)
    if agent_config.project_id:
        project = await session.get(Project, agent_config.project_id)
        if not project:
             raise HTTPException(status_code=404, detail="Project not found")
             
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await session.get(UserProjectLink, (current_user.id, agent_config.project_id))
            if not link or link.role not in ["admin", "owner", "editor"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        # System Agent
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
             raise HTTPException(status_code=403, detail="Not enough permissions")

    # Restore
    agent_config.system_prompt = version.system_prompt
    agent_config.model_provider = version.model_provider
    agent_config.model = version.model
    if version.settings:
        agent_config.settings = version.settings
        
    session.add(agent_config)
    await session.commit()
    await session.refresh(agent_config)
    
    # Mask API Key (not part of version, kept from original config)
    c_read = AgentConfigRead.model_validate(agent_config)
    if agent_config.encrypted_api_key:
        from app.core.security import mask_api_key
        c_read.masked_api_key = mask_api_key(agent_config.encrypted_api_key)
        
    return c_read
