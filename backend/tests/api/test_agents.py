"""
Integration tests for Agent Config endpoints.

URL prefix (from api.py): /api/v1/agents
Routes tested:
  POST   /agents/{project_id}      - create agent config
  GET    /agents/{project_id}      - list agents for a project
  PUT    /agents/{config_id}       - update agent config
  DELETE /agents/{config_id}       - delete agent config
  GET    /agents/{config_id}/keys  - get agent keys (exercises get_project_agent_config)

Permission model:
  - SUPER_ADMIN bypasses all project permission checks
  - Project member with role "admin" or "owner" can create/update/delete
  - Unauthenticated requests get 401
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.organization import Organization
from app.models.project import Project, UserProjectLink

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

AGENT_PAYLOAD = {
    "type": "teacher",
    "name": "Alpha Teacher",
    "model_provider": "gemini",
    "system_prompt": "You are a helpful teacher assistant.",
    "category": "instructor",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_org_and_project(db_session: AsyncSession, owner_id) -> Project:
    """Create an Organization and a Project owned by owner_id, return the Project."""
    org = Organization(name="Agent Test Org", owner_id=owner_id)
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)

    project = Project(name="Agent Test Project", organization_id=org.id)
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_agent_config(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin creates an agent config; first of its type is auto-activated."""
    project = await _make_org_and_project(db_session, mock_superuser.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/agents/{project.id}",
        json=AGENT_PAYLOAD,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "teacher"
    assert data["name"] == "Alpha Teacher"
    assert data["model_provider"] == "gemini"
    assert data["system_prompt"] == "You are a helpful teacher assistant."
    assert "id" in data
    # First config of this type is auto-activated by the service
    assert data["is_active"] is True


@pytest.mark.asyncio()
async def test_list_agents_in_project(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can list all agent configs for a given project."""
    project = await _make_org_and_project(db_session, mock_superuser.id)

    # Seed one agent
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/agents/{project.id}",
        json=AGENT_PAYLOAD,
    )
    assert create_resp.status_code == 200

    response = await superuser_client.get(f"{settings.API_V1_STR}/agents/{project.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(a["name"] == "Alpha Teacher" for a in data)


@pytest.mark.asyncio()
async def test_get_agent_config(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """The /keys endpoint internally validates the agent exists; 200 + empty dict when no keys."""
    project = await _make_org_and_project(db_session, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/agents/{project.id}",
        json=AGENT_PAYLOAD,
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    response = await superuser_client.get(f"{settings.API_V1_STR}/agents/{agent_id}/keys")
    assert response.status_code == 200
    # No keys set yet, so returns an empty dict
    assert response.json() == {}


@pytest.mark.asyncio()
async def test_update_agent_config(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can update an existing agent config's name and system_prompt."""
    project = await _make_org_and_project(db_session, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/agents/{project.id}",
        json=AGENT_PAYLOAD,
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    updated_payload = {
        **AGENT_PAYLOAD,
        "name": "Updated Teacher",
        "system_prompt": "Updated system prompt.",
    }
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/agents/{agent_id}",
        json=updated_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Teacher"
    assert data["system_prompt"] == "Updated system prompt."
    assert data["id"] == agent_id


@pytest.mark.asyncio()
async def test_delete_agent_config(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can delete an agent config; subsequent access returns 404."""
    project = await _make_org_and_project(db_session, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/agents/{project.id}",
        json=AGENT_PAYLOAD,
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    delete_resp = await superuser_client.delete(f"{settings.API_V1_STR}/agents/{agent_id}")
    assert delete_resp.status_code == 204

    # Deleted agent's keys endpoint should now return 404
    get_resp = await superuser_client.get(f"{settings.API_V1_STR}/agents/{agent_id}/keys")
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_agent_config_requires_auth(client: AsyncClient):
    """Unauthenticated requests to agent endpoints must be rejected (401)."""
    # client has no auth override, get_current_user will raise 401
    response = await client.get(
        f"{settings.API_V1_STR}/agents/00000000-0000-0000-0000-000000000001"
    )
    assert response.status_code == 401


@pytest.mark.asyncio()
async def test_project_member_with_admin_role_can_create(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
    mock_teacher,
):
    """A project member holding role 'admin' can create agent configs."""
    from app.api import deps
    from app.main import app

    project = await _make_org_and_project(db_session, mock_superuser.id)

    # Give the teacher admin-level access to the project
    link = UserProjectLink(
        user_id=mock_teacher.id,
        project_id=project.id,
        role="admin",
    )
    db_session.add(link)
    await db_session.flush()

    async def override_user():
        return mock_teacher

    app.dependency_overrides[deps.get_current_user] = override_user
    try:
        response = await client.post(
            f"{settings.API_V1_STR}/agents/{project.id}",
            json=AGENT_PAYLOAD,
        )
        assert response.status_code == 200
        assert response.json()["type"] == "teacher"
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)


@pytest.mark.asyncio()
async def test_project_member_without_permission_cannot_create(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
    mock_student,
):
    """A project member with role 'member' (not admin/owner) gets 403 on create."""
    from app.api import deps
    from app.main import app

    project = await _make_org_and_project(db_session, mock_superuser.id)

    # Give the student plain member access
    link = UserProjectLink(
        user_id=mock_student.id,
        project_id=project.id,
        role="member",
    )
    db_session.add(link)
    await db_session.flush()

    async def override_user():
        return mock_student

    app.dependency_overrides[deps.get_current_user] = override_user
    try:
        response = await client.post(
            f"{settings.API_V1_STR}/agents/{project.id}",
            json=AGENT_PAYLOAD,
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)
