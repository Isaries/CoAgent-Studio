"""
Agent Types API Endpoints.

Provides CRUD operations for agent type metadata.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import SQLModel

from app.api.deps import require_role
from app.core.db import get_session
from app.models.agent_type_metadata import (
    AgentTypeMetadataCreate,
    AgentTypeMetadataRead,
)
from app.models.user import User, UserRole
from app.services.agent_registry import AgentRegistry


class AgentTypeMetadataUpdate(SQLModel):
    """Update schema for AgentTypeMetadata."""

    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    default_system_prompt: Optional[str] = None
    default_model_provider: Optional[str] = None
    default_model: Optional[str] = None
    default_settings: Optional[Dict[str, Any]] = None
    default_capabilities: Optional[List[str]] = None


router = APIRouter(prefix="/agent-types", tags=["Agent Types"])


@router.get("", response_model=List[AgentTypeMetadataRead])
async def list_agent_types(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_system: bool = Query(True, description="Include system types"),
    session=Depends(get_session),
    current_user: User = Depends(
        require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """
    List all available agent types.

    Categories: instructor, participant, utility, external
    """
    registry = AgentRegistry(session)
    return await registry.list_agent_types(category=category, include_system=include_system)


@router.get("/{type_name}", response_model=AgentTypeMetadataRead)
async def get_agent_type(
    type_name: str,
    session=Depends(get_session),
    current_user: User = Depends(
        require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """Get metadata for a specific agent type."""
    registry = AgentRegistry(session)
    type_meta = await registry.get_agent_type(type_name)

    if not type_meta:
        raise HTTPException(status_code=404, detail=f"Agent type '{type_name}' not found")

    return AgentTypeMetadataRead.model_validate(type_meta)


@router.post("", response_model=AgentTypeMetadataRead, status_code=201)
async def create_agent_type(
    data: AgentTypeMetadataCreate,
    session=Depends(get_session),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """
    Create a new custom agent type.

    Only admins can create new agent types.
    """
    registry = AgentRegistry(session)

    try:
        type_meta = await registry.create_agent_type(data, created_by=current_user.id)
        return AgentTypeMetadataRead.model_validate(type_meta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{type_name}", response_model=AgentTypeMetadataRead)
async def update_agent_type(
    type_name: str,
    data: AgentTypeMetadataUpdate,
    session=Depends(get_session),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """
    Update an existing agent type's metadata.

    Only admins can update agent types. System types can be updated
    but their type_name and is_system flag remain immutable.
    """
    registry = AgentRegistry(session)
    type_meta = await registry.get_agent_type(type_name)

    if not type_meta:
        raise HTTPException(status_code=404, detail=f"Agent type '{type_name}' not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(type_meta, field, value)

    from datetime import datetime, timezone

    type_meta.updated_at = datetime.now(timezone.utc)

    session.add(type_meta)
    await session.commit()
    await session.refresh(type_meta)

    # Invalidate cache for this type
    registry.invalidate_cache(type_name)

    return AgentTypeMetadataRead.model_validate(type_meta)


@router.delete("/{type_name}", status_code=204)
async def delete_agent_type(
    type_name: str,
    session=Depends(get_session),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """
    Delete a custom agent type.

    System types cannot be deleted.
    """
    registry = AgentRegistry(session)

    try:
        deleted = await registry.delete_agent_type(type_name)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Agent type '{type_name}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{type_name}/schema", response_model=dict)
async def get_agent_type_schema(
    type_name: str,
    session=Depends(get_session),
    current_user: User = Depends(
        require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """
    Get the configuration schema for an agent type.

    Returns defaults and available options for creating agents of this type.
    """
    registry = AgentRegistry(session)
    type_meta = await registry.get_agent_type(type_name)

    if not type_meta:
        raise HTTPException(status_code=404, detail=f"Agent type '{type_name}' not found")

    return {
        "type_name": type_meta.type_name,
        "category": type_meta.category,
        "defaults": {
            "system_prompt": type_meta.default_system_prompt,
            "model_provider": type_meta.default_model_provider,
            "model": type_meta.default_model,
            "settings": type_meta.default_settings,
            "capabilities": type_meta.default_capabilities,
        },
        "is_external": type_meta.category == "external",
    }
