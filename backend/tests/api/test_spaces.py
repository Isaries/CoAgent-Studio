"""
Integration tests for Space CRUD endpoints (/api/v1/spaces).

Permission model (from spaces.py + space_service.py + permission_service.py):
- POST   /spaces/       → require_role([ADMIN, TEACHER])
- GET    /spaces/       → any authenticated user; admin sees all, others see owned/enrolled
- GET    /spaces/{id}   → authenticated + permission_service.check("read")
                          (owner, admin, super_admin, enrolled TA/student can read)
- PUT    /spaces/{id}   → require_role([ADMIN, TEACHER]); service also checks owner or admin
- DELETE /spaces/{id}   → require_role([ADMIN, TEACHER]); service also checks owner or admin
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.space import Space, UserSpaceLink
from app.models.user import User

# ---------------------------------------------------------------------------
# DB-level helpers (flush, no commit — rolled back after each test)
# ---------------------------------------------------------------------------


async def _create_space_in_db(
    db_session: AsyncSession,
    owner: User,
    title: str = "Test Space",
    description: str = "A space created directly in the DB",
    preset: str = "custom",
) -> Space:
    """Insert a Space row directly into the test DB session."""
    space = Space(
        title=title,
        description=description,
        preset=preset,
        owner_id=owner.id,
    )
    db_session.add(space)
    await db_session.flush()
    await db_session.refresh(space)
    return space


async def _enroll_user(
    db_session: AsyncSession,
    user_id,
    space_id,
    role: str = "participant",
) -> None:
    """Create a UserSpaceLink so a user has access to a space."""
    link = UserSpaceLink(user_id=user_id, space_id=space_id, role=role)
    db_session.add(link)
    await db_session.flush()


# ---------------------------------------------------------------------------
# POST /spaces/ — create space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_space_as_teacher(teacher_client: AsyncClient):
    """A teacher can create a new space and receives a full SpaceRead response."""
    payload = {
        "title": "Introduction to Machine Learning",
        "description": "Hands-on ML course for beginners",
        "preset": "colearn",
    }
    response = await teacher_client.post(f"{settings.API_V1_STR}/spaces/", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["preset"] == payload["preset"]
    assert "id" in data
    assert "owner_id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_create_space_as_student_forbidden(student_client: AsyncClient):
    """A student cannot create a space — blocked at the require_role guard (403)."""
    payload = {
        "title": "Unauthorised Student Space",
        "description": "This should be rejected",
    }
    response = await student_client.post(f"{settings.API_V1_STR}/spaces/", json=payload)
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_create_space_requires_auth(client: AsyncClient):
    """An unauthenticated request to create a space must return 401."""
    payload = {"title": "No Auth Space"}
    response = await client.post(f"{settings.API_V1_STR}/spaces/", json=payload)
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /spaces/ — list spaces
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_list_spaces_as_teacher(teacher_client: AsyncClient):
    """After creating a space, the teacher sees it in the list response."""
    payload = {
        "title": "Data Science Fundamentals",
        "description": "Advanced analytics techniques",
    }
    create_res = await teacher_client.post(f"{settings.API_V1_STR}/spaces/", json=payload)
    assert create_res.status_code == 200

    response = await teacher_client.get(f"{settings.API_V1_STR}/spaces/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert any(s["title"] == "Data Science Fundamentals" for s in data)


@pytest.mark.asyncio()
async def test_list_spaces_as_superadmin(
    superuser_client: AsyncClient, teacher_client: AsyncClient
):
    """Super admin can list all spaces, including those created by other users."""
    # Teacher creates a space that the superadmin didn't create
    payload = {"title": "Space For Superadmin Listing Test"}
    await teacher_client.post(f"{settings.API_V1_STR}/spaces/", json=payload)

    response = await superuser_client.get(f"{settings.API_V1_STR}/spaces/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert any(s["title"] == "Space For Superadmin Listing Test" for s in data)


@pytest.mark.asyncio()
async def test_list_spaces_requires_auth(client: AsyncClient):
    """An unauthenticated request to list spaces must return 401."""
    response = await client.get(f"{settings.API_V1_STR}/spaces/")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /spaces/{space_id} — read single space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_space_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner can fetch a space by its ID."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Cognitive Science 101")

    response = await teacher_client.get(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(space.id)
    assert data["title"] == "Cognitive Science 101"
    assert data["owner_id"] == str(mock_teacher.id)


@pytest.mark.asyncio()
async def test_get_space_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can fetch any space by ID regardless of ownership."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Private Teacher Space")

    response = await superuser_client.get(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(space.id)


@pytest.mark.asyncio()
async def test_get_space_not_found(teacher_client: AsyncClient):
    """Requesting a space with a non-existent UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await teacher_client.get(f"{settings.API_V1_STR}/spaces/{fake_id}")
    assert response.status_code == 404, response.text


@pytest.mark.asyncio()
async def test_get_space_as_unenrolled_student_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A student who is not enrolled in a space must receive 403."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Restricted Space")
    response = await student_client.get(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_get_space_as_enrolled_student(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher: User,
    mock_student: User,
):
    """A student enrolled in a space can read it."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Open Enrollment Space")
    await _enroll_user(db_session, mock_student.id, space.id, role="student")

    response = await student_client.get(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(space.id)


# ---------------------------------------------------------------------------
# PUT /spaces/{space_id} — update space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_space_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner (teacher) can update the title, description, and preset."""
    space = await _create_space_in_db(
        db_session, mock_teacher, title="Old Title", description="Old description"
    )

    update_payload = {
        "title": "Updated Space Title",
        "description": "Updated description with more details",
        "preset": "research",
    }
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/spaces/{space.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Space Title"
    assert data["description"] == "Updated description with more details"
    assert data["preset"] == "research"


@pytest.mark.asyncio()
async def test_update_space_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can update any space regardless of ownership."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Admin Editable Space")

    update_payload = {"title": "Renamed By Admin"}
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/spaces/{space.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Renamed By Admin"


@pytest.mark.asyncio()
async def test_update_space_as_student_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A student cannot update a space — blocked by require_role (403)."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Read-Only Space")

    response = await student_client.put(
        f"{settings.API_V1_STR}/spaces/{space.id}",
        json={"title": "Hacked Title"},
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# DELETE /spaces/{space_id} — delete space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_delete_space_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can delete any space; response contains the deleted SpaceRead."""
    space = await _create_space_in_db(
        db_session, mock_teacher, title="Space To Be Deleted By Admin"
    )

    response = await superuser_client.delete(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(space.id)
    assert data["title"] == "Space To Be Deleted By Admin"


@pytest.mark.asyncio()
async def test_delete_space_as_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner (teacher) can delete their own space."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Owner Deletes This Space")

    response = await teacher_client.delete(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 200, response.text


@pytest.mark.asyncio()
async def test_delete_space_as_student_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A student cannot delete a space — blocked by require_role (403)."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Protected Space")

    response = await student_client.delete(f"{settings.API_V1_STR}/spaces/{space.id}")
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_delete_space_not_found(superuser_client: AsyncClient):
    """Deleting a space with a non-existent UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    response = await superuser_client.delete(f"{settings.API_V1_STR}/spaces/{fake_id}")
    assert response.status_code == 404, response.text
