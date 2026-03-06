"""
Integration tests for Room CRUD endpoints (/api/v1/rooms).

Permission model (from rooms.py + room_service.py + permission_service.py):
- POST   /rooms/           → any authenticated user; service checks permission_service.check("create", space)
                             (space owner, admin, super_admin, TA can create rooms)
- GET    /rooms/?space_id= → any authenticated user
- GET    /rooms/{id}       → any authenticated user
- PUT    /rooms/{id}       → any authenticated user; service checks permission_service.check("update", room)
                             (space owner, admin, super_admin, TA can update)
- DELETE /rooms/{id}       → any authenticated user; service checks permission_service.check("delete", room)
                             (space owner, admin, super_admin, TA can delete)

Students enrolled in a space can READ rooms but not create/update/delete.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.room import Room
from app.models.space import Space, UserSpaceLink
from app.models.user import User

# ---------------------------------------------------------------------------
# DB-level helpers (flush, no commit — rolled back after each test)
# ---------------------------------------------------------------------------


async def _create_space_in_db(
    db_session: AsyncSession,
    owner: User,
    title: str = "Test Space",
) -> Space:
    """Insert a Space row directly into the test DB session."""
    space = Space(
        title=title,
        description="A test space",
        preset="custom",
        owner_id=owner.id,
    )
    db_session.add(space)
    await db_session.flush()
    await db_session.refresh(space)
    return space


async def _create_room_in_db(
    db_session: AsyncSession,
    space: Space,
    name: str = "Test Room",
    description: str = "A test room",
) -> Room:
    """Insert a Room row directly into the test DB session."""
    room = Room(
        name=name,
        description=description,
        space_id=space.id,
    )
    db_session.add(room)
    await db_session.flush()
    await db_session.refresh(room)
    return room


async def _enroll_user(
    db_session: AsyncSession,
    user_id,
    space_id,
    role: str = "participant",
) -> None:
    """Create a UserSpaceLink to grant a user access to a space."""
    link = UserSpaceLink(user_id=user_id, space_id=space_id, role=role)
    db_session.add(link)
    await db_session.flush()


# ---------------------------------------------------------------------------
# POST /rooms/ — create room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_room_as_space_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner (teacher) can create a room inside their space."""
    space = await _create_space_in_db(db_session, mock_teacher, title="ML Bootcamp")
    # Teacher must also have a space_owner link so permission_service passes
    await _enroll_user(db_session, mock_teacher.id, space.id, role="space_owner")

    payload = {
        "name": "Week 1: Linear Regression",
        "description": "Introduction to supervised learning",
        "space_id": str(space.id),
        "is_ai_active": True,
        "ai_mode": "teacher_only",
    }
    response = await teacher_client.post(f"{settings.API_V1_STR}/rooms/", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["space_id"] == str(space.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_create_room_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can create a room in any space."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Superadmin Test Space")

    payload = {
        "name": "Admin Room",
        "description": "Created by superadmin",
        "space_id": str(space.id),
    }
    response = await superuser_client.post(f"{settings.API_V1_STR}/rooms/", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Admin Room"
    assert data["space_id"] == str(space.id)


@pytest.mark.asyncio()
async def test_create_room_space_not_found(teacher_client: AsyncClient):
    """Creating a room with a non-existent space_id returns 404."""
    payload = {
        "name": "Orphan Room",
        "space_id": "00000000-0000-0000-0000-000000000000",
    }
    response = await teacher_client.post(f"{settings.API_V1_STR}/rooms/", json=payload)
    assert response.status_code == 404, response.text


@pytest.mark.asyncio()
async def test_create_room_as_student_without_space_access_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """A student not enrolled in a space cannot create a room in it (403)."""
    space = await _create_space_in_db(db_session, mock_teacher, title="Restricted Space")

    payload = {
        "name": "Illegal Room",
        "space_id": str(space.id),
    }
    response = await student_client.post(f"{settings.API_V1_STR}/rooms/", json=payload)
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_create_room_requires_auth(
    client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """An unauthenticated request to create a room must return 401."""
    space = await _create_space_in_db(db_session, mock_teacher)
    payload = {"name": "No Auth Room", "space_id": str(space.id)}
    response = await client.post(f"{settings.API_V1_STR}/rooms/", json=payload)
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /rooms/?space_id= — list rooms by space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_list_rooms_by_space(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Listing rooms for a space returns only rooms belonging to that space."""
    space = await _create_space_in_db(db_session, mock_teacher, title="NLP Course")
    await _create_room_in_db(db_session, space, name="Tokenisation Workshop")
    await _create_room_in_db(db_session, space, name="Attention Mechanisms")

    # Create another space to verify isolation
    other_space = await _create_space_in_db(db_session, mock_teacher, title="Unrelated Space")
    await _create_room_in_db(db_session, other_space, name="Should Not Appear")

    response = await teacher_client.get(
        f"{settings.API_V1_STR}/rooms/", params={"space_id": str(space.id)}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    names = [r["name"] for r in data]
    assert "Tokenisation Workshop" in names
    assert "Attention Mechanisms" in names
    assert "Should Not Appear" not in names


@pytest.mark.asyncio()
async def test_list_rooms_requires_auth(
    client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """An unauthenticated request to list rooms must return 401."""
    space = await _create_space_in_db(db_session, mock_teacher)
    response = await client.get(f"{settings.API_V1_STR}/rooms/", params={"space_id": str(space.id)})
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /rooms/{room_id} — get single room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_room(teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User):
    """Any authenticated user can fetch a room by ID."""
    space = await _create_space_in_db(db_session, mock_teacher)
    room = await _create_room_in_db(
        db_session, space, name="Computer Vision Lab", description="Object detection exercises"
    )

    response = await teacher_client.get(f"{settings.API_V1_STR}/rooms/{room.id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(room.id)
    assert data["name"] == "Computer Vision Lab"
    assert data["space_id"] == str(space.id)


@pytest.mark.asyncio()
async def test_get_room_not_found(teacher_client: AsyncClient):
    """Fetching a non-existent room UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await teacher_client.get(f"{settings.API_V1_STR}/rooms/{fake_id}")
    assert response.status_code == 404, response.text


@pytest.mark.asyncio()
async def test_get_room_requires_auth(
    client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """An unauthenticated request to get a room must return 401."""
    space = await _create_space_in_db(db_session, mock_teacher)
    room = await _create_room_in_db(db_session, space, name="Auth-Gated Room")
    response = await client.get(f"{settings.API_V1_STR}/rooms/{room.id}")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# PUT /rooms/{room_id} — update room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_room_as_teacher(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner (teacher) can update room name and AI settings."""
    space = await _create_space_in_db(db_session, mock_teacher, title="RL Research Space")
    # Enroll teacher as space_owner so permission check passes
    await _enroll_user(db_session, mock_teacher.id, space.id, role="space_owner")
    room = await _create_room_in_db(db_session, space, name="Policy Gradient Room")

    update_payload = {
        "name": "Policy Gradient & Actor-Critic",
        "description": "Deep dive into RL algorithms",
        "is_ai_active": False,
        "ai_mode": "off",
    }
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/rooms/{room.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Policy Gradient & Actor-Critic"
    assert data["is_ai_active"] is False
    assert data["ai_mode"] == "off"


@pytest.mark.asyncio()
async def test_update_room_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can update any room."""
    space = await _create_space_in_db(db_session, mock_teacher)
    room = await _create_room_in_db(db_session, space, name="Original Room Name")

    response = await superuser_client.put(
        f"{settings.API_V1_STR}/rooms/{room.id}",
        json={"name": "Admin Renamed Room"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Admin Renamed Room"


@pytest.mark.asyncio()
async def test_update_room_as_student_without_ta_role_forbidden(
    student_client: AsyncClient, db_session: AsyncSession, mock_teacher: User, mock_student: User
):
    """A student (not TA) enrolled in a space cannot update rooms (403)."""
    space = await _create_space_in_db(db_session, mock_teacher)
    await _enroll_user(db_session, mock_student.id, space.id, role="student")
    room = await _create_room_in_db(db_session, space, name="Student Can't Edit This")

    response = await student_client.put(
        f"{settings.API_V1_STR}/rooms/{room.id}",
        json={"name": "Hijacked Name"},
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# DELETE /rooms/{room_id} — delete room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_delete_room_as_space_owner(
    teacher_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """The space owner can delete a room; response is 204 No Content."""
    space = await _create_space_in_db(db_session, mock_teacher)
    await _enroll_user(db_session, mock_teacher.id, space.id, role="space_owner")
    room = await _create_room_in_db(db_session, space, name="Room To Delete")

    response = await teacher_client.delete(f"{settings.API_V1_STR}/rooms/{room.id}")
    assert response.status_code == 204, response.text


@pytest.mark.asyncio()
async def test_delete_room_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession, mock_teacher: User
):
    """Super admin can delete any room."""
    space = await _create_space_in_db(db_session, mock_teacher)
    room = await _create_room_in_db(db_session, space, name="Admin Deletes This Room")

    response = await superuser_client.delete(f"{settings.API_V1_STR}/rooms/{room.id}")
    assert response.status_code == 204, response.text


@pytest.mark.asyncio()
async def test_delete_room_not_found(superuser_client: AsyncClient):
    """Deleting a non-existent room UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000002"
    response = await superuser_client.delete(f"{settings.API_V1_STR}/rooms/{fake_id}")
    assert response.status_code == 404, response.text
