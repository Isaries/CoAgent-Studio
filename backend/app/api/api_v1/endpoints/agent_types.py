"""
Agent Types API Endpoints.

Provides CRUD operations for agent type metadata.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, require_role
from app.core.db import get_session
from app.models.user import User, UserRole
from app.models.agent_type_metadata import (
    AgentTypeMetadata,
    AgentTypeMetadataCreate,
    AgentTypeMetadataRead,
)
from app.services.agent_registry import AgentRegistry

router = APIRouter(prefix="/agent-types", tags=["Agent Types"])



@router.get("", response_model=List[AgentTypeMetadataRead])
async def list_agent_types(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_system: bool = Query(True, description="Include system types"),
    session=Depends(get_session),
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])),
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
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])),
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
        raise HTTPException(status_code=400, detail=str(e))


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
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{type_name}/schema", response_model=dict)
async def get_agent_type_schema(
    type_name: str,
    session=Depends(get_session),
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN])),
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
