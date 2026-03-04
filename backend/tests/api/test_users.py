"""
Integration tests for User management endpoints (/api/v1/users).

Endpoint map (from users.py + api.py):
- GET    /users/me          → any authenticated user (returns current user)
- PUT    /users/me          → any authenticated user (updates own profile)
- GET    /users/            → admin or super_admin only (permission_service "list_users")
- POST   /users/            → admin or super_admin only (permission_service "manage_users")
- PUT    /users/{user_id}   → admin or super_admin can update any user
- DELETE /users/{user_id}   → admin or super_admin only

UserUpdate fields: full_name, role, password, username
UserCreate fields: email, full_name, role, avatar_url, username, password, google_sub
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_get_current_user_as_teacher(
    teacher_client: AsyncClient, mock_teacher: User
):
    """Authenticated teacher can retrieve their own profile via /users/me."""
    response = await teacher_client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == mock_teacher.email
    assert data["role"] == UserRole.TEACHER
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio()
async def test_get_current_user_as_student(
    student_client: AsyncClient, mock_student: User
):
    """Authenticated student can retrieve their own profile via /users/me."""
    response = await student_client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == mock_student.email
    assert data["role"] == UserRole.STUDENT


@pytest.mark.asyncio()
async def test_get_current_user_requires_auth(client: AsyncClient):
    """Unauthenticated request to /users/me must return 401."""
    response = await client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# PUT /users/me — update own profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_update_current_user_full_name(
    teacher_client: AsyncClient, mock_teacher: User
):
    """A user can update their own full_name via PUT /users/me."""
    update_payload = {"full_name": "Dr. Jane Smith"}
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/users/me", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["full_name"] == "Dr. Jane Smith"
    assert data["email"] == mock_teacher.email


@pytest.mark.asyncio()
async def test_update_current_user_username(
    student_client: AsyncClient, mock_student: User
):
    """A user can update their username via PUT /users/me."""
    update_payload = {"username": "student_handle_42"}
    response = await student_client.put(
        f"{settings.API_V1_STR}/users/me", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "student_handle_42"


@pytest.mark.asyncio()
async def test_update_current_user_requires_auth(client: AsyncClient):
    """Unauthenticated request to PUT /users/me must return 401."""
    response = await client.put(
        f"{settings.API_V1_STR}/users/me", json={"full_name": "Ghost"}
    )
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# GET /users/ — list all users (admin only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_list_users_as_superadmin(superuser_client: AsyncClient):
    """Super admin can retrieve the full user list."""
    response = await superuser_client.get(f"{settings.API_V1_STR}/users/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    # At minimum the superuser fixture itself should appear
    assert len(data) >= 1


@pytest.mark.asyncio()
async def test_list_users_as_student_forbidden(student_client: AsyncClient):
    """A student cannot list users — permission_service denies non-admin (403)."""
    response = await student_client.get(f"{settings.API_V1_STR}/users/")
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_list_users_as_teacher_forbidden(teacher_client: AsyncClient):
    """A teacher cannot list all users — only admin/super_admin may (403)."""
    response = await teacher_client.get(f"{settings.API_V1_STR}/users/")
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_list_users_requires_auth(client: AsyncClient):
    """Unauthenticated request to GET /users/ must return 401."""
    response = await client.get(f"{settings.API_V1_STR}/users/")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# POST /users/ — create a new user (admin only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_user_as_superadmin(superuser_client: AsyncClient):
    """Super admin can create a new user account."""
    payload = {
        "email": "new.recruit@university.edu",
        "full_name": "Alice Recruit",
        "role": "student",
        "password": "SecurePassword123!",
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/users/", json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "student"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio()
async def test_create_user_as_teacher_forbidden(teacher_client: AsyncClient):
    """A teacher cannot create new users — only admin/super_admin may (403)."""
    payload = {
        "email": "fake.student@example.com",
        "role": "student",
        "password": "somepassword",
    }
    response = await teacher_client.post(
        f"{settings.API_V1_STR}/users/", json=payload
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_create_user_as_student_forbidden(student_client: AsyncClient):
    """A student cannot create new users (403)."""
    payload = {
        "email": "another.student@example.com",
        "role": "student",
        "password": "somepassword",
    }
    response = await student_client.post(
        f"{settings.API_V1_STR}/users/", json=payload
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# PUT /users/{user_id} — admin updates any user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_update_user_role_as_superadmin(
    superuser_client: AsyncClient, db_session: AsyncSession
):
    """Super admin can change the role of any user."""
    # Create a target user directly in the DB
    user = User(
        email="promotable.user@example.com",
        role=UserRole.STUDENT,
        is_active=True,
        hashed_password=get_password_hash("password"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    update_payload = {"role": "teacher"}
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/users/{user.id}", json=update_payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["role"] == "teacher"


@pytest.mark.asyncio()
async def test_update_user_as_student_forbidden(
    student_client: AsyncClient, db_session: AsyncSession
):
    """A student cannot update another user's profile (403)."""
    target_user = User(
        email="target.user@example.com",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(target_user)
    await db_session.flush()
    await db_session.refresh(target_user)

    response = await student_client.put(
        f"{settings.API_V1_STR}/users/{target_user.id}",
        json={"full_name": "Hacked Name"},
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio()
async def test_update_nonexistent_user_returns_404(superuser_client: AsyncClient):
    """Updating a user with a non-existent ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/users/{fake_id}",
        json={"full_name": "Ghost User"},
    )
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# GET /users/search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_search_users(
    teacher_client: AsyncClient, db_session: AsyncSession
):
    """Any authenticated user can search users by partial email or name."""
    searchable_user = User(
        email="searchable.person@example.com",
        full_name="Searchable Person",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(searchable_user)
    await db_session.flush()

    response = await teacher_client.get(
        f"{settings.API_V1_STR}/users/search", params={"q": "searchable"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert any("searchable" in u["email"] for u in data)
