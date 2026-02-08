"""
Tests for ArtifactService - Phase 1 Verification.

Tests cover:
- CRUD operations
- Optimistic locking
- Soft delete
"""

import pytest
from uuid import uuid4

from app.models.artifact import (
    Artifact,
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactType,
)
from app.models.user import User
from app.services.artifact_service import ArtifactService


@pytest.fixture
def mock_artifact_data():
    """Factory for test artifact data."""
    def _create(artifact_type: str = "task", title: str = "Test Task"):
        return ArtifactCreate(
            type=artifact_type,
            title=title,
            content={"status": "todo", "priority": "high"},
        )
    return _create


class TestArtifactService:
    """Test suite for ArtifactService."""
    
    @pytest.mark.asyncio
    async def test_create_artifact(self, db_session, mock_superuser: User, mock_artifact_data):
        """Test creating a new artifact."""
        # Arrange
        from app.models.room import Room
        from app.models.course import Course
        
        room_id = uuid4()
        
        # Create prerequisite room with valid user FK
        course = Course(id=uuid4(), title="Test Course", owner_id=mock_superuser.id)
        db_session.add(course)
        await db_session.flush()
        
        room = Room(id=room_id, name="Test Room", course_id=course.id)
        db_session.add(room)
        await db_session.flush()
        
        service = ArtifactService(db_session)
        data = mock_artifact_data()
        
        # Act
        artifact = await service.create_artifact(room_id, data, created_by=mock_superuser.id)
        
        # Assert
        assert artifact is not None
        assert artifact.id is not None
        assert artifact.type == "task"
        assert artifact.title == "Test Task"
        assert artifact.version == 1
        assert artifact.room_id == room_id

    @pytest.mark.asyncio
    async def test_list_artifacts_by_type(self, db_session, mock_superuser: User):
        """Test filtering artifacts by type."""
        # Arrange
        from app.models.room import Room
        from app.models.course import Course
        
        room_id = uuid4()
        
        course = Course(id=uuid4(), title="Test Course", owner_id=mock_superuser.id)
        db_session.add(course)
        await db_session.flush()
        
        room = Room(id=room_id, name="Test Room", course_id=course.id)
        db_session.add(room)
        await db_session.flush()
        
        service = ArtifactService(db_session)
        
        # Create artifacts of different types
        await service.create_artifact(room_id, ArtifactCreate(type="task", title="Task 1", content={}), mock_superuser.id)
        await service.create_artifact(room_id, ArtifactCreate(type="doc", title="Doc 1", content={}), mock_superuser.id)
        await service.create_artifact(room_id, ArtifactCreate(type="task", title="Task 2", content={}), mock_superuser.id)
        
        # Act
        tasks = await service.list_artifacts(room_id, artifact_type="task")
        docs = await service.list_artifacts(room_id, artifact_type="doc")
        
        # Assert
        assert len(tasks) == 2
        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_update_artifact_version_increment(self, db_session, mock_superuser: User, mock_artifact_data):
        """Test that update increments version."""
        # Arrange
        from app.models.room import Room
        from app.models.course import Course
        
        room_id = uuid4()
        
        course = Course(id=uuid4(), title="Test Course", owner_id=mock_superuser.id)
        db_session.add(course)
        await db_session.flush()
        
        room = Room(id=room_id, name="Test Room", course_id=course.id)
        db_session.add(room)
        await db_session.flush()
        
        service = ArtifactService(db_session)
        artifact = await service.create_artifact(room_id, mock_artifact_data(), mock_superuser.id)
        original_version = artifact.version
        
        # Act
        updated = await service.update_artifact(
            artifact.id,
            ArtifactUpdate(title="Updated Title"),
            modified_by=mock_superuser.id
        )
        
        # Assert
        assert updated is not None
        assert updated.version == original_version + 1
        assert updated.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_artifact_optimistic_locking_conflict(self, db_session, mock_superuser: User, mock_artifact_data):
        """Test that stale version update is rejected."""
        # Arrange
        from app.models.room import Room
        from app.models.course import Course
        
        room_id = uuid4()
        
        course = Course(id=uuid4(), title="Test Course", owner_id=mock_superuser.id)
        db_session.add(course)
        await db_session.flush()
        
        room = Room(id=room_id, name="Test Room", course_id=course.id)
        db_session.add(room)
        await db_session.flush()
        
        service = ArtifactService(db_session)
        artifact = await service.create_artifact(room_id, mock_artifact_data(), mock_superuser.id)
        
        # First update succeeds
        await service.update_artifact(
            artifact.id, 
            ArtifactUpdate(title="First Update"),
            modified_by=mock_superuser.id
        )
        
        # Act - attempt stale update with old version
        result = await service.update_artifact(
            artifact.id,
            ArtifactUpdate(title="Stale Update", expected_version=1),  # Wrong version
            modified_by=mock_superuser.id
        )
        
        # Assert
        assert result is None  # Conflict detected

    @pytest.mark.asyncio
    async def test_soft_delete_artifact(self, db_session, mock_superuser: User, mock_artifact_data):
        """Test soft delete excludes from listing."""
        # Arrange
        from app.models.room import Room
        from app.models.course import Course
        
        room_id = uuid4()
        
        course = Course(id=uuid4(), title="Test Course", owner_id=mock_superuser.id)
        db_session.add(course)
        await db_session.flush()
        
        room = Room(id=room_id, name="Test Room", course_id=course.id)
        db_session.add(room)
        await db_session.flush()
        
        service = ArtifactService(db_session)
        artifact = await service.create_artifact(room_id, mock_artifact_data(), mock_superuser.id)
        
        # Act
        await service.delete_artifact(artifact.id, deleted_by=mock_superuser.id)
        
        # Assert
        visible_artifacts = await service.list_artifacts(room_id)
        all_artifacts = await service.list_artifacts(room_id, include_deleted=True)
        
        assert len(visible_artifacts) == 0
        assert len(all_artifacts) == 1
