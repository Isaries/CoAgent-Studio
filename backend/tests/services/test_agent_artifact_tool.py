
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_tool_service import _handle_manage_artifact
from app.models.artifact import ArtifactType, Artifact
from sqlmodel import select

@pytest.fixture
def mock_broadcast():
    with patch("app.core.socket_manager.manager.broadcast", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_agent_create_task_artifact(
    db_session: AsyncSession,
    mock_superuser,
    mock_broadcast
):
    """Test creating a task artifact via agent tool."""
    
    # Create Course and Room
    from app.models.course import Course
    from app.models.room import Room
    course = Course(title="Test Course", description="Test", owner_id=mock_superuser.id)
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    
    room = Room(name="Test Room", description="Test Desc", course_id=course.id, created_by=mock_superuser.id)
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    room_id = room.id
    
    user_id = mock_superuser.id
    
    # 1. Agent calls manage_artifact with 'create'
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=user_id,
        action="create",
        artifact_type="task",
        title="Agent Created Task",
        content={"status": "todo", "priority": "high"}
    )
    
    # 2. Verify artifact in DB
    query = select(Artifact).where(Artifact.room_id == room_id)
    result = await db_session.exec(query)
    artifacts = result.all()
    
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.title == "Agent Created Task"
    assert artifact.type == ArtifactType.TASK
    assert artifact.content["status"] == "todo"
    
    # 3. Verify broadcast called
    mock_broadcast.assert_called_once()
    call_args = mock_broadcast.call_args
    # call_args[0] -> (message, room_id)
    # message is dict
    message = call_args[0][0]
    target_room = call_args[0][1]
    
    assert target_room == str(room_id)
    assert message["type"] == "artifact_update"
    assert message["artifact"]["id"] == str(artifact.id)

@pytest.mark.asyncio
async def test_agent_update_artifact(
    db_session: AsyncSession,
    mock_superuser,
    mock_broadcast
):
    """Test updating an artifact via agent tool."""
    
    # Create Course and Room
    from app.models.course import Course
    from app.models.room import Room
    course = Course(title="Test Course", description="Test", owner_id=mock_superuser.id)
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    
    room = Room(name="Test Room", description="Test Desc", course_id=course.id, created_by=mock_superuser.id)
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    room_id = room.id
    
    user_id = mock_superuser.id
    
    # Setup: Create initial artifact directly
    artifact = Artifact(
        room_id=room_id,
        type=ArtifactType.TASK,
        title="Original Title",
        content={"status": "todo"},
        created_by=user_id,
        last_modified_by=user_id
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)
    
    # reset mock because create might have triggered broadcast if we used service (but we used direct DB)
    mock_broadcast.reset_mock()
    
    # 1. Agent calls manage_artifact with 'update'
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=user_id,
        action="update",
        artifact_id=str(artifact.id),
        title="Updated Title",
        content={"status": "done"}
    )
    
    await db_session.refresh(artifact)
    
    # 2. Verify update
    assert artifact.title == "Updated Title"
    assert artifact.content["status"] == "done"
    assert artifact.version == 2
    
    # 3. Verify broadcast
    mock_broadcast.assert_called_once()
    message = mock_broadcast.call_args[0][0]
    assert message["type"] == "artifact_update"
    assert message["artifact"]["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_agent_delete_artifact(
    db_session: AsyncSession,
    mock_superuser,
    mock_broadcast
):
    """Test deleting an artifact via agent tool."""
    
    # Create Course and Room
    from app.models.course import Course
    from app.models.room import Room
    course = Course(title="Test Course", description="Test", owner_id=mock_superuser.id)
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    
    room = Room(name="Test Room", description="Test Desc", course_id=course.id, created_by=mock_superuser.id)
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    room_id = room.id
    
    user_id = mock_superuser.id
    
    # Setup
    artifact = Artifact(
        room_id=room_id,
        type=ArtifactType.DOC,
        title="To Delete",
        content={"text": "foo"},
        created_by=user_id,
        last_modified_by=user_id
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)
    
    # 1. Agent calls delete
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=user_id,
        action="delete",
        artifact_id=str(artifact.id)
    )
    
    await db_session.refresh(artifact)
    
    # 2. Verify soft delete
    assert artifact.is_deleted is True
    
    # 3. Verify broadcast
    mock_broadcast.assert_called_once()
    message = mock_broadcast.call_args[0][0]
    assert message["type"] == "artifact_delete"
    assert message["artifact_id"] == str(artifact.id)
