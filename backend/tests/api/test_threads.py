"""
Integration tests for AgentThread CRUD endpoints.

URL prefix (from api.py): /api/v1/threads

Routes tested:
  POST   /threads/                       - create thread
  GET    /threads/                       - list threads (current user's)
  GET    /threads/{thread_id}            - get thread with ownership check
  GET    /threads/{thread_id}/messages   - get thread messages
  DELETE /threads/{thread_id}            - delete thread (owner only)

Permission model:
  - All endpoints require authentication.
  - ThreadService.get_thread enforces thread.user_id == current_user.id.
  - create_thread verifies the referenced AgentConfig exists in DB.

Prerequisites for thread creation:
  - A valid Project must exist (AgentThread.project_id FK).
  - A valid AgentConfig must exist (AgentThread.agent_id FK).
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.agent_config import AgentConfig
from app.models.organization import Organization
from app.models.project import Project

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_project(db_session: AsyncSession, owner_id) -> Project:
    """Create an Organization + Project and return the Project."""
    org = Organization(name="Thread Test Org", owner_id=owner_id)
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)

    project = Project(name="Thread Test Project", organization_id=org.id)
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_agent_config(db_session: AsyncSession, project_id, created_by) -> AgentConfig:
    """Seed an AgentConfig for the given project and return it."""
    agent = AgentConfig(
        project_id=project_id,
        type="teacher",
        name="Test Teacher Agent",
        model_provider="gemini",
        system_prompt="You are a helpful teacher.",
        created_by=created_by,
    )
    db_session.add(agent)
    await db_session.flush()
    await db_session.refresh(agent)
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_thread(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Authenticated user can create a thread linked to an agent and project."""
    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    payload = {
        "project_id": str(project.id),
        "agent_id": str(agent.id),
        "name": "My First Thread",
        "metadata_json": "{}",
    }

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/threads/",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My First Thread"
    assert data["project_id"] == str(project.id)
    assert data["agent_id"] == str(agent.id)
    assert data["user_id"] == str(mock_superuser.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_list_threads(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Listing threads returns only threads owned by the current user."""
    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    # Create two threads
    for name in ["Thread Alpha", "Thread Beta"]:
        create_resp = await superuser_client.post(
            f"{settings.API_V1_STR}/threads/",
            json={"project_id": str(project.id), "agent_id": str(agent.id), "name": name},
        )
        assert create_resp.status_code == 200

    response = await superuser_client.get(f"{settings.API_V1_STR}/threads/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [t["name"] for t in data]
    assert "Thread Alpha" in names
    assert "Thread Beta" in names


@pytest.mark.asyncio()
async def test_get_thread(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Owner can retrieve their thread by ID."""
    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/threads/",
        json={
            "project_id": str(project.id),
            "agent_id": str(agent.id),
            "name": "Fetch Thread",
        },
    )
    assert create_resp.status_code == 200
    thread_id = create_resp.json()["id"]

    response = await superuser_client.get(f"{settings.API_V1_STR}/threads/{thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == thread_id
    assert data["name"] == "Fetch Thread"


@pytest.mark.asyncio()
async def test_get_thread_not_found(superuser_client: AsyncClient):
    """Requesting a thread that does not exist returns 404."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/threads/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_get_thread_messages_empty(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """A freshly created thread has no messages."""
    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/threads/",
        json={"project_id": str(project.id), "agent_id": str(agent.id), "name": "Empty Thread"},
    )
    assert create_resp.status_code == 200
    thread_id = create_resp.json()["id"]

    response = await superuser_client.get(f"{settings.API_V1_STR}/threads/{thread_id}/messages")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio()
async def test_delete_thread(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Thread owner can delete their thread; subsequent GET returns 404."""
    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/threads/",
        json={"project_id": str(project.id), "agent_id": str(agent.id), "name": "Delete Thread"},
    )
    assert create_resp.status_code == 200
    thread_id = create_resp.json()["id"]

    delete_resp = await superuser_client.delete(f"{settings.API_V1_STR}/threads/{thread_id}")
    assert delete_resp.status_code == 204

    get_resp = await superuser_client.get(f"{settings.API_V1_STR}/threads/{thread_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_thread_requires_auth(client: AsyncClient):
    """Unauthenticated requests to thread endpoints are rejected with 401."""
    response = await client.get(f"{settings.API_V1_STR}/threads/")
    assert response.status_code == 401


@pytest.mark.asyncio()
async def test_another_user_cannot_read_thread(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
    mock_student,
):
    """A user who does not own the thread gets 403 when attempting to read it."""
    from app.api import deps
    from app.main import app

    project = await _create_project(db_session, mock_superuser.id)
    agent = await _create_agent_config(db_session, project.id, mock_superuser.id)

    # Superuser creates the thread
    async def superuser_override():
        return mock_superuser

    app.dependency_overrides[deps.get_current_user] = superuser_override
    try:
        create_resp = await client.post(
            f"{settings.API_V1_STR}/threads/",
            json={
                "project_id": str(project.id),
                "agent_id": str(agent.id),
                "name": "Private Thread",
            },
        )
        assert create_resp.status_code == 200
        thread_id = create_resp.json()["id"]
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)

    # Student tries to read the thread
    async def student_override():
        return mock_student

    app.dependency_overrides[deps.get_current_user] = student_override
    try:
        response = await client.get(f"{settings.API_V1_STR}/threads/{thread_id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)


@pytest.mark.asyncio()
async def test_create_thread_with_nonexistent_agent(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Creating a thread with an agent_id that doesn't exist returns 404."""
    project = await _create_project(db_session, mock_superuser.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/threads/",
        json={
            "project_id": str(project.id),
            "agent_id": "00000000-0000-0000-0000-000000000099",
            "name": "Orphan Thread",
        },
    )
    assert response.status_code == 404
