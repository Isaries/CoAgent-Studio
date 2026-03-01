"""
Artifact API Endpoints - Workspace artifact CRUD operations.

Provides REST API for managing artifacts within workspaces (rooms).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.core.socket_manager import manager
from app.models.artifact import ArtifactCreate, ArtifactRead, ArtifactUpdate, ArtifactType
from app.models.user import User, UserRole
from app.models.room import Room
from app.services.artifact_service import ArtifactService

router = APIRouter()


@router.get("/{room_id}/artifacts", response_model=List[ArtifactRead])
async def list_artifacts(
    room_id: UUID,
    artifact_type: Optional[str] = Query(None, description="Filter by type: task, doc, process"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all artifacts in a workspace.
    
    Optionally filter by artifact type.
    """
    # Verify room exists and user has access
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # TODO: Check user permission to access this room
    
    service = ArtifactService(session, socket_manager=manager)
    artifacts = await service.list_artifacts(room_id, artifact_type=artifact_type)
    
    return artifacts


@router.post("/{room_id}/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    room_id: UUID,
    data: ArtifactCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new artifact in a workspace.
    
    Artifact types:
    - task: Kanban cards, to-do items
    - doc: Rich text documents
    - process: Workflow state machines
    """
    # Verify room exists
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Validate artifact type
    valid_types = [t.value for t in ArtifactType]
    if data.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact type. Must be one of: {valid_types}"
        )
    
    service = ArtifactService(session, socket_manager=manager)
    artifact = await service.create_artifact(room_id, data, created_by=current_user.id)
    
    return artifact


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
async def get_artifact(
    artifact_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single artifact by ID."""
    service = ArtifactService(session, socket_manager=manager)
    artifact = await service.get_artifact(artifact_id)
    
    if not artifact or artifact.is_deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return artifact


@router.put("/artifacts/{artifact_id}", response_model=ArtifactRead)
async def update_artifact(
    artifact_id: UUID,
    data: ArtifactUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update an artifact.
    
    Supports optimistic locking via expected_version field.
    If provided, update will fail if current version doesn't match.
    """
    service = ArtifactService(session, socket_manager=manager)
    
    # Check exists
    existing = await service.get_artifact(artifact_id)
    if not existing or existing.is_deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    artifact = await service.update_artifact(artifact_id, data, modified_by=current_user.id)
    
    if artifact is None:
        # Version conflict
        raise HTTPException(
            status_code=409,
            detail="Version conflict. Please refresh and retry."
        )
    
    return artifact


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    hard_delete: bool = Query(False, description="Permanently delete (admin only)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an artifact (soft delete by default).
    
    Use hard_delete=true for permanent removal (requires admin privileges).
    """
    service = ArtifactService(session, socket_manager=manager)
    
    # Check exists
    existing = await service.get_artifact(artifact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Hard delete requires admin privileges
    if hard_delete and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can permanently delete artifacts")

    success = await service.delete_artifact(artifact_id, deleted_by=current_user.id, hard_delete=hard_delete)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete artifact")
    
    return None
