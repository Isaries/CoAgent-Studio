
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_tool_service import _handle_manage_artifact
from app.models.artifact import Artifact
from sqlmodel import select

# Mock data
mock_user_id = uuid.uuid4()

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_agent_append_concurrency_lost_update(db_session: AsyncSession):
    """
    Test ISOLATION of Concurrency/Lost Update bug.
    Demonstrates that current implementation overwrites concurrent changes.
    """
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()

    # Setup Check: Create User/Course/Room (Standard setup)
    from app.models.user import User
    from app.models.course import Course
    from app.models.room import Room
    
    user = User(id=mock_user_id, email="test@example.com", full_name="Test User")
    db_session.add(user)
    await db_session.flush()
    
    course = Course(title="Test Course", description="Desc", owner_id=mock_user_id)
    db_session.add(course)
    await db_session.flush()
    
    room = Room(name="Test Room", description="Desc", course_id=course.id)
    db_session.add(room)
    await db_session.flush()
    
    # 1. Create Doc (Version 1)
    doc_content = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}]}
    
    # Create artifact manually
    from app.services.artifact_service import ArtifactService
    from app.models.artifact import ArtifactCreate, ArtifactUpdate
    
    # 1. Create Doc (Version 1)
    doc_content_v1 = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Original V1"}]}]}
    
    # Use real service logic for setup
    service = ArtifactService(db_session)
    artifact_v1 = await service.create_artifact(
        room.id, 
        ArtifactCreate(type="doc", title="Doc", content=doc_content_v1), 
        created_by=mock_user_id
    )
    doc_id = str(artifact_v1.id)
    assert artifact_v1.version == 1
    
    # Snapshot V1 object (detached) for mocking
    # Ideally deepcopy it or use fields
    from copy import deepcopy
    stale_artifact = deepcopy(artifact_v1)
    
    # 2. Simulate User Update (Version 2)
    # User adds a paragraph "User Update"
    doc_content_v2 = {
        "type": "doc", 
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Original V1"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "User Update"}]}
        ]
    }
    
    # We update artifact via service to bump version
    artifact_v2 = await service.update_artifact(
        artifact_v1.id,
        ArtifactUpdate(content=doc_content_v2),
        modified_by=mock_user_id
    )
    assert artifact_v2.version == 2
    assert len(artifact_v2.content["content"]) == 2
    
    # 3. Simulate Agent Append (Race Condition)
    # Agent *thinks* it sees V1 (stale read)
    # We strip the session from stale_artifact to avoid "attached to session" errors if any
    # But effectively we mock get_artifact to return this stale object
    
    append_content = {"type": "paragraph", "content": [{"type": "text", "text": "Agent Append"}]}

    with patch("app.services.artifact_service.ArtifactService.get_artifact", new_callable=AsyncMock) as mock_get:
        # First call returns stale (v1). 
        # Second call returns fresh (v2) which allows the retry to succeed.
        mock_get.side_effect = [stale_artifact, artifact_v2, artifact_v2, artifact_v2]
        
        # Agent calls append
        await _handle_manage_artifact(
            session=db_session,
            room_id=room.id,
            user_id=mock_user_id,
            action="append",
            artifact_id=doc_id,
            content=append_content
        )
        
    # 4. Verify Result
    # Agent's update calls update_artifact. 
    # Since agent assumed V1, it appended "Agent Append" to "Original V1".
    # Result: "Original V1", "Agent Append".
    # "User Update" is LOST.
    
    # Fetch final state from DB (mocked session, so we check what was flushed/committed or use service get)
    # Since we mocked get_artifact, we can't use service.get_artifact unless we unpatch.
    # But we are out of with block now.
    
    # Re-fetch deeply
    # Actually, verify via refreshing the object if it's still attached?
    # Or query fresh.
    query = select(Artifact).where(Artifact.id == artifact_v1.id)
    result = await db_session.exec(query)
    final_artifact = result.first()
    
    print(f"Final Content: {final_artifact.content}")
    
    # Assertion of BUG
    # We expect determining that "User Update" is MISSING.
    content_texts = [p["content"][0]["text"] for p in final_artifact.content["content"]]
    
    assert "Original V1" in content_texts
    assert "Agent Append" in content_texts
    
    # FAIL IF BUG EXISTS: "User Update" is missing.
    if "User Update" not in content_texts:
        pytest.fail("Concurrency bug detected! User update lost.")
    else:
        print("\n[SUCCESS] User update preserved!")

