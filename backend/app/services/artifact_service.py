"""
Artifact Service - CRUD operations for workspace artifacts.

Supports:
- Create/Read/Update/Delete operations
- Optimistic locking via version field
- Soft delete for data recovery
"""

from typing import List, Optional
from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.artifact import Artifact, ArtifactCreate, ArtifactUpdate, ArtifactType

logger = structlog.get_logger()


class ArtifactService:
    """Service for managing workspace artifacts."""
    
    def __init__(self, session: AsyncSession, socket_manager=None):
        self.session = session
        self.socket_manager = socket_manager
    
    async def list_artifacts(
        self,
        room_id: UUID,
        artifact_type: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[Artifact]:
        """
        List all artifacts in a workspace/room.
        
        Args:
            room_id: The workspace (room) ID
            artifact_type: Optional filter by type (TASK, DOC, PROCESS)
            include_deleted: Whether to include soft-deleted artifacts
        """
        query = select(Artifact).where(Artifact.room_id == room_id)
        
        if artifact_type:
            query = query.where(Artifact.type == artifact_type)
        
        if not include_deleted:
            query = query.where(Artifact.is_deleted == False)
        
        query = query.order_by(Artifact.created_at.desc())
        
        result = await self.session.exec(query)
        return list(result.all())
    
    async def get_artifact(self, artifact_id: UUID) -> Optional[Artifact]:
        """Get a single artifact by ID."""
        return await self.session.get(Artifact, artifact_id)
    
    async def create_artifact(
        self,
        room_id: UUID,
        data: ArtifactCreate,
        created_by: UUID,
    ) -> Artifact:
        """
        Create a new artifact in a workspace.
        """
        artifact = Artifact(
            room_id=room_id,
            type=data.type,
            title=data.title,
            content=data.content,
            parent_artifact_id=data.parent_artifact_id,
            created_by=created_by,
            last_modified_by=created_by,
        )
        
        self.session.add(artifact)
        await self.session.commit()
        await self.session.refresh(artifact)
        
        logger.info(
            "artifact_created",
            artifact_id=str(artifact.id),
            room_id=str(room_id),
            type=data.type,
        )

        if self.socket_manager:
            await self._broadcast_update(room_id, artifact)
        
        return artifact
    
    async def update_artifact(
        self,
        artifact_id: UUID,
        data: ArtifactUpdate,
        modified_by: UUID,
    ) -> Optional[Artifact]:
        """
        Update an artifact with optimistic locking.
        """
        artifact = await self.session.get(Artifact, artifact_id)
        if not artifact:
            return None
        
        # Optimistic locking check
        if data.expected_version is not None:
            if artifact.version != data.expected_version:
                logger.warning(
                    "artifact_version_conflict",
                    artifact_id=str(artifact_id),
                    expected=data.expected_version,
                    actual=artifact.version,
                )
                return None  # Client should refresh and retry
        
        # Apply updates
        if data.title is not None:
            artifact.title = data.title
        
        if data.content is not None:
            # Merge content if needed, or replace
            artifact.content = data.content
        
        # Increment version
        artifact.version += 1
        artifact.last_modified_by = modified_by
        
        from datetime import datetime
        artifact.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(artifact)
        
        logger.info(
            "artifact_updated",
            artifact_id=str(artifact_id),
            new_version=artifact.version,
        )

        if self.socket_manager:
            await self._broadcast_update(artifact.room_id, artifact)
        
        return artifact
    
    async def delete_artifact(
        self,
        artifact_id: UUID,
        deleted_by: UUID,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete an artifact (soft delete by default).
        """
        artifact = await self.session.get(Artifact, artifact_id)
        if not artifact:
            return False
        
        room_id = artifact.room_id

        if hard_delete:
            await self.session.delete(artifact)
        else:
            artifact.is_deleted = True
            artifact.last_modified_by = deleted_by
        
        await self.session.commit()
        
        logger.info(
            "artifact_deleted",
            artifact_id=str(artifact_id),
            hard_delete=hard_delete,
        )

        if self.socket_manager:
            await self._broadcast_delete(room_id, artifact_id)
        
        return True

    async def _broadcast_update(self, room_id: UUID, artifact: Artifact):
        """Helper to broadcast artifact updates."""
        try:
            # Convert to dict manually or use Pydantic model dump if available
            # We want to send the full artifact state
            payload = {
                "type": "artifact_update",
                "artifact": artifact.model_dump(mode='json'),
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.socket_manager.broadcast(payload, str(room_id))
        except Exception as e:
            logger.error("artifact_broadcast_failed", error=str(e))

    async def _broadcast_delete(self, room_id: UUID, artifact_id: UUID):
        """Helper to broadcast artifact deletion."""
        try:
            payload = {
                "type": "artifact_delete",
                "artifact_id": str(artifact_id),
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.socket_manager.broadcast(payload, str(room_id))
        except Exception as e:
            logger.error("artifact_broadcast_failed", error=str(e))

