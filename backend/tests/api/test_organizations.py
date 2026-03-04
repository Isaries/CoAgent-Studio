"""
Integration tests for Organization CRUD endpoints (/api/v1/organizations).

Endpoint map (from organizations.py + organization_service.py):
- GET    /organizations         → authenticated; returns only orgs the user is a member of
- POST   /organizations         → any authenticated user (becomes owner + member link created)
- GET    /organizations/{id}    → authenticated member only (non-members get 403)
- PUT    /organizations/{id}    → authenticated; must be member AND owner (non-owner member gets 403)
- DELETE /organizations/{id}    → authenticated; must be member AND owner; returns 204

OrganizationCreate fields: name, description
OrganizationUpdate fields: name, description
OrganizationRead fields: id, name, description, owner_id, created_at
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.organization import Organization, UserOrganizationLink
from app.models.user import User


# ---------------------------------------------------------------------------
# DB-level helpers (flush, no commit — rolled back after each test)
# ---------------------------------------------------------------------------

async def _create_org_in_db(
    db_session: AsyncSession,
    owner: User,
    name: str = "Test Organization",
    description: str = "An organization created directly in the DB",
) -> Organization:
    """Insert an Organization and its owner link directly into the test DB session."""
    org = Organization(
        name=name,
        description=description,
        owner_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)

    # Create the owner membership link (mirrors what OrganizationService.create_organization does)
    link = UserOrganizationLink(
        user_id=owner.id, organization_id=org.id, role="owner"
    )
    db_session.add(link)
    await db_session.flush()

    return org


async def _add_member_to_org(
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


# ---------------------------------------------------------------------------
# POST /organizations — create organization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_organization_as_teacher(teacher_client: AsyncClient):
    """A teacher can create an organization and becomes its owner."""
    payload = {
        "name": "AI Research Lab",
        "description": "Dedicated to advancing machine learning research",
    }
    response = await teacher_client.post(
        f"{settings.API_V1_STR}/organizations", json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert "id" in data
    assert "owner_id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_create_organization_as_student(student_client: AsyncClient):
    """A student can also create an organization (no role restriction on this endpoint)."""
    payload = {
        "name": "Student Study Group",
        "description": "Peer learning collective",
    }
    response = await student_client.post(
        f"{settings.API_V1_STR}/organizations", json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == payload["name"]


@pytest.mark.asyncio()
async def test_create_organization_as_superadmin(superuser_client: AsyncClient):
    """Super admin can create an organization."""
    payload = {"name": "Platform Admin Org", "description": "Top-level admin organization"}
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/organizations", json=payload
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Platform Admin Org"


@pytest.mark.asyncio()
async def test_create_organization_requires_auth(client: AsyncClient):
    """Unauthenticated requests to create an organization must return 401."""
    payload = {"name": "No Auth Org"}
    response = await client.post(f"{settings.API_V1_STR}/organizations", json=payload)
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /organizations — list organizations for current user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_list_organizations_shows_owned(teacher_client: AsyncClient):
    """After creating an org, it appears in the teacher's organization list."""
    payload = {"name": "Visible In List Org"}
    await teacher_client.post(f"{settings.API_V1_STR}/organizations", json=payload)

    response = await teacher_client.get(f"{settings.API_V1_STR}/organizations")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert any(o["name"] == "Visible In List Org" for o in data)


@pytest.mark.asyncio()
async def test_list_organizations_shows_membership(
    teacher_client: AsyncClient,
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A user added as a member of an org can see it in their list."""
    org = await _create_org_in_db(db_session, mock_teacher, name="Shared Research Org")
    await _add_member_to_org(db_session, mock_student, org, role="member")

    response = await student_client.get(f"{settings.API_V1_STR}/organizations")
    assert response.status_code == 200, response.text
    data = response.json()
    assert any(o["name"] == "Shared Research Org" for o in data)


@pytest.mark.asyncio()
async def test_list_organizations_excludes_non_member(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """An organization the student is not a member of must not appear in their list."""
    await _create_org_in_db(db_session, mock_teacher, name="Private Teacher Org")

    response = await student_client.get(f"{settings.API_V1_STR}/organizations")
    assert response.status_code == 200, response.text
    data = response.json()
    assert not any(o["name"] == "Private Teacher Org" for o in data)


@pytest.mark.asyncio()
async def test_list_organizations_requires_auth(client: AsyncClient):
    """Unauthenticated request to list organizations must return 401."""
    response = await client.get(f"{settings.API_V1_STR}/organizations")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /organizations/{org_id} — get single organization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_get_organization_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The organization owner can retrieve it by ID."""
    org = await _create_org_in_db(
        db_session, mock_teacher, name="Quantum Computing Lab"
    )

    response = await teacher_client.get(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(org.id)
    assert data["name"] == "Quantum Computing Lab"
    assert data["owner_id"] == str(mock_teacher.id)


@pytest.mark.asyncio()
async def test_get_organization_as_member(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A user who is a member of an org can retrieve it by ID."""
    org = await _create_org_in_db(
        db_session, mock_teacher, name="Open Science Collective"
    )
    await _add_member_to_org(db_session, mock_student, org, role="member")

    response = await student_client.get(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(org.id)


@pytest.mark.asyncio()
async def test_get_organization_as_non_member_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A user who is not a member of an org receives 403 when fetching it."""
    org = await _create_org_in_db(
        db_session, mock_teacher, name="Members Only Org"
    )

    response = await student_client.get(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# PUT /organizations/{org_id} — update organization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_update_organization_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The organization owner can update name and description."""
    org = await _create_org_in_db(
        db_session, mock_teacher, name="Old Org Name", description="Old description"
    )

    update_payload = {
        "name": "Rebranded Research Institute",
        "description": "New mission statement after strategic realignment",
    }
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/organizations/{org.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Rebranded Research Institute"
    assert data["description"] == "New mission statement after strategic realignment"


@pytest.mark.asyncio()
async def test_update_organization_as_non_owner_member_forbidden(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A member who is not the owner cannot update the organization (403)."""
    org = await _create_org_in_db(db_session, mock_teacher, name="Read-Only For Members")
    await _add_member_to_org(db_session, mock_student, org, role="member")

    response = await student_client.put(
        f"{settings.API_V1_STR}/organizations/{org.id}",
        json={"name": "Attempted Override"},
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# DELETE /organizations/{org_id} — delete organization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_delete_organization_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The organization owner can delete the organization; response is 204."""
    org = await _create_org_in_db(
        db_session, mock_teacher, name="Org To Be Dissolved"
    )

    response = await teacher_client.delete(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 204, response.text


@pytest.mark.asyncio()
async def test_delete_organization_as_non_owner_member_forbidden(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A non-owner member cannot delete the organization (403)."""
    org = await _create_org_in_db(db_session, mock_teacher, name="Protected Org")
    await _add_member_to_org(db_session, mock_student, org, role="member")

    response = await student_client.delete(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_delete_organization_as_non_member_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A user with no membership in the org cannot delete it (403)."""
    org = await _create_org_in_db(db_session, mock_teacher, name="Invisible Org")

    response = await student_client.delete(
        f"{settings.API_V1_STR}/organizations/{org.id}"
    )
    assert response.status_code == 403, response.text
