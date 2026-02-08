
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_tool_service import _handle_manage_artifact
from app.models.artifact import ArtifactType, Artifact
from sqlmodel import select

# Mock data
mock_user_id = uuid.uuid4()
mock_superuser = type('User', (), {'id': mock_user_id, 'is_superuser': True})

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_agent_append_doc(db_session: AsyncSession):
    """Test appending to a Doc artifact via agent tool."""
    
    # Mock commit early
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()

    # Create User
    from app.models.user import User
    user = User(id=mock_user_id, email="test@example.com", full_name="Test User")
    db_session.add(user)
    await db_session.flush()

    # Create Course
    from app.models.course import Course
    course = Course(title="Test Course", description="Test Course Desc", owner_id=mock_user_id)
    db_session.add(course)
    await db_session.flush()
    await db_session.refresh(course)
    course_id = course.id

    # Create Room
    from app.models.room import Room
    room = Room(
        name="Test Room Append", 
        description="Test Desc", 
        course_id=course_id
    )
    db_session.add(room)
    await db_session.flush()
    await db_session.refresh(room)
    room_id = room.id
    
    # 1. Create Doc
    doc_content = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Original text"}]}
        ]
    }
    
    # Create artifact manually or via tool (let's use tool for consistency)
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=mock_user_id,
        action="create",
        artifact_type="doc",
        title="Agent Doc Append",
        content=doc_content
    )
    await db_session.flush() # Ensure ID
    
    # Get ID
    query = select(Artifact).where(Artifact.room_id == room_id).where(Artifact.title == "Agent Doc Append")
    result = await db_session.exec(query)
    artifact = result.first()
    assert artifact is not None
    doc_id = str(artifact.id)
    
    # 2. Append Content
    append_content = {
        "type": "paragraph", 
        "content": [{"type": "text", "text": " Appended text"}]
    }
    
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=mock_user_id,
        action="append",
        artifact_id=doc_id,
        content=append_content
    )
    await db_session.flush()
    
    # 3. Verify
    await db_session.refresh(artifact)
    assert artifact.version == 2
    content = artifact.content
    assert len(content["content"]) == 2
    assert content["content"][0]["content"][0]["text"] == "Original text"
    assert content["content"][1]["content"][0]["text"] == " Appended text"


@pytest.mark.asyncio
async def test_agent_add_step_process(db_session: AsyncSession):
    """Test adding step to Process artifact via agent tool."""
    
    # Mock commit early
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()

    # Create User
    from app.models.user import User
    # Use a different ID or reuse mock_user_id (reuse is fine logic-wise but strict tests might prefer fresh)
    # Let's reuse mock_user_id but check if it exists or use merge? 
    # Actually, the sessions are separate per test function? No, db_session fixture usually rolls back.
    # But if it persist, we might hit unique constraint on ID.
    # Let's just try to add it. If it fails, I'll use merge.
    # Wait, simple: just create it.
    user = User(id=mock_user_id, email="test2@example.com", full_name="Test User 2")
    db_session.add(user)
    await db_session.flush()

    # Create Course
    from app.models.course import Course
    course = Course(title="Test Course Step", description="Test Course Desc", owner_id=mock_user_id)
    db_session.add(course)
    await db_session.flush()
    await db_session.refresh(course)
    course_id = course.id

    # Create Room
    from app.models.room import Room
    room = Room(
        name="Test Room Step", 
        description="Test Desc", 
        course_id=course_id
    )
    db_session.add(room)
    await db_session.flush()
    await db_session.refresh(room)
    room_id = room.id
    
    # 1. Create Process
    process_content = {
        "nodes": [
            {"id": "1", "type": "input", "data": {"label": "Start"}, "position": {"x": 0, "y": 0}}
        ],
        "edges": []
    }
    
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=mock_user_id,
        action="create",
        artifact_type="process",
        title="Agent Process Step",
        content=process_content
    )
    await db_session.flush()
    
    # Get ID
    query = select(Artifact).where(Artifact.room_id == room_id).where(Artifact.title == "Agent Process Step")
    result = await db_session.exec(query)
    artifact = result.first()
    assert artifact is not None
    proc_id = str(artifact.id)
    
    # 2. Add Step
    step_content = {
        "nodes": [
            {"id": "2", "type": "default", "data": {"label": "Step 2"}, "position": {"x": 100, "y": 0}}
        ],
        "edges": [
            {"id": "e1-2", "source": "1", "target": "2"}
        ]
    }
    
    await _handle_manage_artifact(
        session=db_session,
        room_id=room_id,
        user_id=mock_user_id,
        action="add_step",
        artifact_id=proc_id,
        content=step_content
    )
    await db_session.flush()
    
    # 3. Verify
    await db_session.refresh(artifact)
    assert artifact.version == 2
    
    # Check Nodes
    nodes = artifact.content["nodes"]
    assert len(nodes) == 2
    assert nodes[1]["id"] == "2"
    
    # Check Edges
    edges = artifact.content["edges"]
    assert len(edges) == 1
    assert edges[0]["source"] == "1"
    assert edges[0]["target"] == "2"
