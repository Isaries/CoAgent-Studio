"""
Integration tests for Project CRUD endpoints (/api/v1/projects).

Endpoint map (from projects.py + project_service.py):
- GET    /projects              → authenticated; returns only projects the user is a member of
                                  optional ?org_id= filter
- POST   /projects              → authenticated + must be an org member; user becomes project admin
- GET    /projects/{id}         → authenticated + must be project member (non-members get 403)
- PUT    /projects/{id}         → authenticated + project member (any role)
- DELETE /projects/{id}         → authenticated + project member; returns 204

ProjectCreate fields: name, description, organization_id
ProjectUpdate fields: name, description
ProjectRead   fields: id, name, description, organization_id, created_at
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.organization import Organization, UserOrganizationLink
from app.models.project import Project, UserProjectLink
from app.models.user import User


# ---------------------------------------------------------------------------
# DB-level helpers (flush, no commit — rolled back after each test)
# ---------------------------------------------------------------------------

async def _create_org_with_owner(
    db_session: AsyncSession,
    owner: User,
    name: str = "Test Organization",
) -> Organization:
    """Insert an Organization and its owner link directly into the test DB session."""
    org = Organization(
        name=name,
        description="A test organization",
        owner_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)

    link = UserOrganizationLink(
        user_id=owner.id, organization_id=org.id, role="owner"
    )
    db_session.add(link)
    await db_session.flush()

    return org


async def _create_project_in_db(
    db_session: AsyncSession,
    org: Organization,
    creator: User,
    name: str = "Test Project",
    description: str = "A test project",
) -> Project:
    """Insert a Project and its creator admin link directly into the test DB session."""
    project = Project(
        name=name,
        description=description,
        organization_id=org.id,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)

    link = UserProjectLink(
        user_id=creator.id, project_id=project.id, role="admin"
    )
    db_session.add(link)
    await db_session.flush()

    return project


async def _add_org_member(
    db_session: AsyncSession,
    user: User,
    org: Organization,
    role: str = "member",
) -> None:
    """Add a user as a member of an organization."""
    link = UserOrganizationLink(
        user_id=user.id, organization_id=org.id, role=role
    )
    db_session.add(link)
    await db_session.flush()


async def _add_project_member(
    db_session: AsyncSession,
    user: User,
    project: Project,
    role: str = "member",
) -> None:
    """Add a user as a member of a project."""
    link = UserProjectLink(
        user_id=user.id, project_id=project.id, role=role
    )
    db_session.add(link)
    await db_session.flush()


# ---------------------------------------------------------------------------
# POST /projects — create project
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_project_as_org_member(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """An organization member can create a project inside the org."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Dev Team Org")

    payload = {
        "name": "Agent Orchestration Engine",
        "description": "Core multi-agent workflow management system",
        "organization_id": str(org.id),
    }
    response = await teacher_client.post(
        f"{settings.API_V1_STR}/projects", json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["organization_id"] == str(org.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_create_project_without_org_membership_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A user with no org membership cannot create a project inside it (403)."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Closed Org")

    payload = {
        "name": "Sneaky Project",
        "organization_id": str(org.id),
    }
    response = await student_client.post(
        f"{settings.API_V1_STR}/projects", json=payload
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_create_project_as_org_member_non_owner(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """Any org member (not just owner) can create a project in the org."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Open Org For All")
    await _add_org_member(db_session, mock_student, org, role="member")

    payload = {
        "name": "Student-Led Research Project",
        "description": "A project created by a regular member",
        "organization_id": str(org.id),
    }
    response = await student_client.post(
        f"{settings.API_V1_STR}/projects", json=payload
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Student-Led Research Project"


@pytest.mark.asyncio()
async def test_create_project_requires_auth(
    client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Unauthenticated request to create a project must return 401."""
    org = await _create_org_with_owner(db_session, mock_teacher)
    payload = {"name": "No Auth Project", "organization_id": str(org.id)}
    response = await client.post(f"{settings.API_V1_STR}/projects", json=payload)
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /projects — list projects for current user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_list_projects_shows_membership(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """After creating a project, the creator can see it in the project list."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Listing Test Org")

    payload = {
        "name": "Visible Project",
        "organization_id": str(org.id),
    }
    await teacher_client.post(f"{settings.API_V1_STR}/projects", json=payload)

    response = await teacher_client.get(f"{settings.API_V1_STR}/projects")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert any(p["name"] == "Visible Project" for p in data)


@pytest.mark.asyncio()
async def test_list_projects_filter_by_org(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The ?org_id= query param filters projects to a specific organization."""
    org_a = await _create_org_with_owner(db_session, mock_teacher, name="Org Alpha")
    org_b = await _create_org_with_owner(db_session, mock_teacher, name="Org Beta")

    payload_a = {"name": "Alpha Project", "organization_id": str(org_a.id)}
    payload_b = {"name": "Beta Project", "organization_id": str(org_b.id)}
    await teacher_client.post(f"{settings.API_V1_STR}/projects", json=payload_a)
    await teacher_client.post(f"{settings.API_V1_STR}/projects", json=payload_b)

    response = await teacher_client.get(
        f"{settings.API_V1_STR}/projects", params={"org_id": str(org_a.id)}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    names = [p["name"] for p in data]
    assert "Alpha Project" in names
    assert "Beta Project" not in names


@pytest.mark.asyncio()
async def test_list_projects_excludes_non_member(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Projects the student is not a member of must not appear in their list."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Teachers Only Org")
    await _create_project_in_db(
        db_session, org, mock_teacher, name="Hidden From Student"
    )

    response = await student_client.get(f"{settings.API_V1_STR}/projects")
    assert response.status_code == 200, response.text
    data = response.json()
    assert not any(p["name"] == "Hidden From Student" for p in data)


@pytest.mark.asyncio()
async def test_list_projects_requires_auth(client: AsyncClient):
    """Unauthenticated request to list projects must return 401."""
    response = await client.get(f"{settings.API_V1_STR}/projects")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /projects/{project_id} — get single project
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_get_project_as_member(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A project member can fetch the project by ID."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Single Fetch Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Knowledge Graph Pipeline"
    )

    response = await teacher_client.get(
        f"{settings.API_V1_STR}/projects/{project.id}"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(project.id)
    assert data["name"] == "Knowledge Graph Pipeline"
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio()
async def test_get_project_as_non_member_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A user with no project membership receives 403 when fetching it."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Exclusive Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Private Project"
    )

    response = await student_client.get(
        f"{settings.API_V1_STR}/projects/{project.id}"
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_get_project_added_as_member(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A user added as a project member can fetch the project."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Collaborative Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Shared Analytics Platform"
    )
    await _add_project_member(db_session, mock_student, project, role="member")

    response = await student_client.get(
        f"{settings.API_V1_STR}/projects/{project.id}"
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(project.id)


# ---------------------------------------------------------------------------
# PUT /projects/{project_id} — update project
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_update_project_as_member(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A project member can update the project name and description."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Update Test Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher,
        name="Original Project Name",
        description="Original description",
    )

    update_payload = {
        "name": "Refactored Project Name",
        "description": "Updated description reflecting new scope",
    }
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/projects/{project.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Refactored Project Name"
    assert data["description"] == "Updated description reflecting new scope"


@pytest.mark.asyncio()
async def test_update_project_as_non_member_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A non-member cannot update a project (403)."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Guarded Update Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Locked Project"
    )

    response = await student_client.put(
        f"{settings.API_V1_STR}/projects/{project.id}",
        json={"name": "Tampered Name"},
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id} — delete project
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_delete_project_as_member(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A project member can delete the project; response is 204 No Content."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Delete Test Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Project To Delete"
    )

    response = await teacher_client.delete(
        f"{settings.API_V1_STR}/projects/{project.id}"
    )
    assert response.status_code == 204, response.text


@pytest.mark.asyncio()
async def test_delete_project_as_non_member_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A non-member cannot delete a project (403)."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Protected Delete Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Non-Deletable By Student"
    )

    response = await student_client.delete(
        f"{settings.API_V1_STR}/projects/{project.id}"
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_delete_project_requires_auth(
    client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Unauthenticated request to delete a project must return 401."""
    org = await _create_org_with_owner(db_session, mock_teacher, name="Auth Guard Org")
    project = await _create_project_in_db(
        db_session, org, mock_teacher, name="Auth-Gated Delete Project"
    )

    response = await client.delete(f"{settings.API_V1_STR}/projects/{project.id}")
    assert response.status_code == 401, response.text
