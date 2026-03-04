"""
Integration tests for Artifact (workspace) CRUD endpoints.

URL prefix (from api.py): artifacts router included with prefix /workspaces
so routes resolve to:
  GET    /workspaces/{room_id}/artifacts          - list artifacts by room
  POST   /workspaces/{room_id}/artifacts          - create artifact
  GET    /workspaces/artifacts/{artifact_id}      - get single artifact
  PUT    /workspaces/artifacts/{artifact_id}      - update artifact
  DELETE /workspaces/artifacts/{artifact_id}      - delete artifact (soft by default)

Permission model:
  - SUPER_ADMIN bypasses all room permission checks
  - The ArtifactService calls redis for GraphRAG events; this is patched out.
  - The socket_manager.broadcast is a no-op in tests (registry is cleared by conftest).

Note on artifact types (from ArtifactType enum):
  - "task"    : Kanban cards, to-do items
  - "doc"     : Rich text documents
  - "process" : Workflow state machines
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.space import Space
from app.models.room import Room


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_space_and_room(db_session: AsyncSession, owner_id) -> Room:
    """Create a Space and a Room within it; return the Room."""
    space = Space(title="Artifact Test Space", owner_id=owner_id)
    db_session.add(space)
    await db_session.flush()
    await db_session.refresh(space)

    room = Room(name="Artifact Test Room", space_id=space.id)
    db_session.add(room)
    await db_session.flush()
    await db_session.refresh(room)
    return room


# Patch target for the Redis GraphRAG event publisher inside ArtifactService
_GRAPHRAG_PATCH = "app.services.artifact_service.ArtifactService._publish_graphrag_event"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_task(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can create a 'task' type artifact in a room."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    payload = {
        "type": "task",
        "title": "Write unit tests",
        "content": {
            "status": "todo",
            "priority": "high",
            "order": 0,
        },
    }

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        response = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json=payload,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "task"
    assert data["title"] == "Write unit tests"
    assert data["content"]["status"] == "todo"
    assert data["room_id"] == str(room.id)
    assert data["created_by"] == str(mock_superuser.id)
    assert "id" in data
    assert data["version"] == 1


@pytest.mark.asyncio()
async def test_create_document(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can create a 'doc' type artifact."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    payload = {
        "type": "doc",
        "title": "Project Proposal",
        "content": {
            "delta": {"ops": [{"insert": "Hello world\n"}]},
            "html": "<p>Hello world</p>",
        },
    }

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        response = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json=payload,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "doc"
    assert data["title"] == "Project Proposal"
    assert "html" in data["content"]


@pytest.mark.asyncio()
async def test_list_artifacts_by_room(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Can list all non-deleted artifacts for a room."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "task", "title": "Task One", "content": {}},
        )
        await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "doc", "title": "Doc One", "content": {}},
        )

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    titles = [a["title"] for a in data]
    assert "Task One" in titles
    assert "Doc One" in titles


@pytest.mark.asyncio()
async def test_list_artifacts_filtered_by_type(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """The artifact_type query param filters results to only the requested type."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "task", "title": "My Task", "content": {}},
        )
        await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "doc", "title": "My Doc", "content": {}},
        )

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
        params={"artifact_type": "task"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(a["type"] == "task" for a in data)
    assert any(a["title"] == "My Task" for a in data)
    assert not any(a["title"] == "My Doc" for a in data)


@pytest.mark.asyncio()
async def test_get_artifact(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Can retrieve a specific artifact by ID."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        create_resp = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "task", "title": "Fetch Me", "content": {"status": "todo"}},
        )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["id"]

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workspaces/artifacts/{artifact_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == artifact_id
    assert data["title"] == "Fetch Me"


@pytest.mark.asyncio()
async def test_get_artifact_not_found(superuser_client: AsyncClient):
    """Requesting a non-existent artifact returns 404."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workspaces/artifacts/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_update_artifact(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Can update an artifact's title and content; version is incremented."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        create_resp = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "task", "title": "Old Title", "content": {"status": "todo"}},
        )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["id"]
    original_version = create_resp.json()["version"]  # should be 1

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        response = await superuser_client.put(
            f"{settings.API_V1_STR}/workspaces/artifacts/{artifact_id}",
            json={"title": "New Title", "content": {"status": "in_progress"}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == artifact_id
    assert data["title"] == "New Title"
    assert data["content"]["status"] == "in_progress"
    assert data["version"] == original_version + 1


@pytest.mark.asyncio()
async def test_update_artifact_version_conflict(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Update with wrong expected_version returns 409 (optimistic locking conflict)."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        create_resp = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "task", "title": "Version Test", "content": {}},
        )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["id"]

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        response = await superuser_client.put(
            f"{settings.API_V1_STR}/workspaces/artifacts/{artifact_id}",
            # Artifact is at version 1; send wrong expected_version
            json={"title": "Conflict", "expected_version": 999},
        )

    assert response.status_code == 409


@pytest.mark.asyncio()
async def test_delete_artifact(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Soft-deleting an artifact returns 204; subsequent GET returns 404."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    with patch(_GRAPHRAG_PATCH, new_callable=AsyncMock):
        create_resp = await superuser_client.post(
            f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
            json={"type": "doc", "title": "Delete Me", "content": {}},
        )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["id"]

    delete_resp = await superuser_client.delete(
        f"{settings.API_V1_STR}/workspaces/artifacts/{artifact_id}"
    )
    assert delete_resp.status_code == 204

    get_resp = await superuser_client.get(
        f"{settings.API_V1_STR}/workspaces/artifacts/{artifact_id}"
    )
    # Soft-deleted artifacts are treated as not found by the GET endpoint
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_create_artifact_invalid_type(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Creating an artifact with an unknown type returns 400."""
    room = await _create_space_and_room(db_session, mock_superuser.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/workspaces/{room.id}/artifacts",
        json={"type": "invalid_type", "title": "Bad Type", "content": {}},
    )
    assert response.status_code == 400


@pytest.mark.asyncio()
async def test_create_artifact_for_nonexistent_room(superuser_client: AsyncClient):
    """Creating an artifact for a room that doesn't exist returns 404."""
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/workspaces/00000000-0000-0000-0000-000000000099/artifacts",
        json={"type": "task", "title": "Ghost Artifact", "content": {}},
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_artifact_endpoints_require_auth(client: AsyncClient):
    """Unauthenticated requests to artifact endpoints are rejected with 401."""
    response = await client.get(
        f"{settings.API_V1_STR}/workspaces/00000000-0000-0000-0000-000000000001/artifacts"
    )
    assert response.status_code == 401
