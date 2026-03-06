"""
Unit tests for app.services.user_service.UserService.

Uses AsyncMock for the SQLModel AsyncSession — no real DB required.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import User, UserCreate, UserRole, UserUpdate
from app.services.user_service import UserService


def _make_user(**kwargs) -> User:
    defaults = {
        "id": uuid4(),
        "email": "user@example.com",
        "role": UserRole.GUEST,
        "is_active": True,
        "hashed_password": "$2b$12$fakehash",
    }
    defaults.update(kwargs)
    return User(**defaults)


def _make_session() -> AsyncMock:
    """Return a minimal AsyncMock that mimics AsyncSession."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_user_by_id_found():
    user = _make_user()
    session = _make_session()
    session.get.return_value = user

    svc = UserService(session)
    result = await svc.get_user(str(user.id))

    assert result is not None
    assert result.id == user.id
    session.get.assert_awaited_once_with(User, user.id)


@pytest.mark.asyncio()
async def test_get_user_by_id_not_found():
    session = _make_session()
    session.get.return_value = None

    svc = UserService(session)
    result = await svc.get_user(str(uuid4()))

    assert result is None


@pytest.mark.asyncio()
async def test_get_user_invalid_uuid_returns_none():
    session = _make_session()
    svc = UserService(session)
    result = await svc.get_user("not-a-uuid")
    assert result is None


# ---------------------------------------------------------------------------
# get_users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_users_returns_list():
    users = [_make_user(email="a@a.com"), _make_user(email="b@b.com")]
    session = _make_session()
    mock_result = Mock()
    mock_result.all.return_value = users
    session.exec.return_value = mock_result

    svc = UserService(session)
    result = await svc.get_users()

    assert result == users
    assert len(result) == 2


@pytest.mark.asyncio()
async def test_get_users_empty_list():
    session = _make_session()
    mock_result = Mock()
    mock_result.all.return_value = []
    session.exec.return_value = mock_result

    svc = UserService(session)
    result = await svc.get_users()

    assert result == []


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_user_hashes_password():
    """create_user should hash the plain password before persisting."""
    session = _make_session()
    # exec().first() returns None — no duplicate found
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result
    session.refresh = AsyncMock()

    current_user = _make_user(role=UserRole.SUPER_ADMIN)
    user_in = UserCreate(email="new@example.com", password="plain-pass", role=UserRole.GUEST)

    with patch(
        "app.services.user_service.security.get_password_hash", return_value="$2b$hashed"
    ) as mock_hash:
        svc = UserService(session)
        await svc.create_user(user_in, current_user)

    mock_hash.assert_called_once_with("plain-pass")
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio()
async def test_create_user_duplicate_raises_400():
    session = _make_session()
    existing = _make_user(email="taken@example.com")
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = existing
    session.exec.return_value = mock_exec_result

    current_user = _make_user(role=UserRole.SUPER_ADMIN)
    user_in = UserCreate(email="taken@example.com", role=UserRole.GUEST)

    svc = UserService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create_user(user_in, current_user)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio()
async def test_create_user_non_super_admin_cannot_create_admin():
    session = _make_session()
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result

    current_user = _make_user(role=UserRole.TEACHER)
    user_in = UserCreate(email="admin@example.com", role=UserRole.ADMIN)

    svc = UserService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create_user(user_in, current_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio()
async def test_create_user_without_password_skips_hashing():
    """create_user with no password should not call get_password_hash."""
    session = _make_session()
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result
    session.refresh = AsyncMock()

    current_user = _make_user(role=UserRole.SUPER_ADMIN)
    user_in = UserCreate(email="nopass@example.com", role=UserRole.GUEST)

    with patch("app.services.user_service.security.get_password_hash") as mock_hash:
        svc = UserService(session)
        await svc.create_user(user_in, current_user)

    mock_hash.assert_not_called()


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_user_updates_fields():
    target_user = _make_user(full_name="Old Name")
    session = _make_session()
    session.get.return_value = target_user
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result

    current_user = _make_user(id=uuid4(), role=UserRole.SUPER_ADMIN)
    user_in = UserUpdate(full_name="New Name")

    svc = UserService(session)
    await svc.update_user(str(target_user.id), user_in, current_user)

    assert target_user.full_name == "New Name"
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio()
async def test_update_user_not_found_raises_404():
    session = _make_session()
    session.get.return_value = None

    current_user = _make_user(role=UserRole.SUPER_ADMIN)
    user_in = UserUpdate(full_name="Anything")

    svc = UserService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update_user(str(uuid4()), user_in, current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_update_user_hashes_new_password():
    target_user = _make_user()
    session = _make_session()
    session.get.return_value = target_user
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result

    current_user = _make_user(id=uuid4(), role=UserRole.SUPER_ADMIN)
    user_in = UserUpdate(password="new-plain-password")

    with patch(
        "app.services.user_service.security.get_password_hash", return_value="$2b$new"
    ) as mock_hash:
        svc = UserService(session)
        await svc.update_user(str(target_user.id), user_in, current_user)

    mock_hash.assert_called_once_with("new-plain-password")


@pytest.mark.asyncio()
async def test_update_user_super_admin_cannot_downgrade_own_role():
    super_admin = _make_user(role=UserRole.SUPER_ADMIN)
    session = _make_session()
    session.get.return_value = super_admin
    mock_exec_result = Mock()
    mock_exec_result.first.return_value = None
    session.exec.return_value = mock_exec_result

    user_in = UserUpdate(role=UserRole.GUEST)

    svc = UserService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update_user(str(super_admin.id), user_in, super_admin)

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_delete_user_not_found_raises_404():
    session = _make_session()
    session.get.return_value = None

    current_user = _make_user(role=UserRole.SUPER_ADMIN)
    svc = UserService(session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_user(str(uuid4()), current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_delete_user_cannot_delete_self():
    user = _make_user()
    session = _make_session()
    session.get.return_value = user

    svc = UserService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_user(str(user.id), user)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio()
async def test_delete_user_non_super_cannot_delete_admin():
    admin_user = _make_user(role=UserRole.ADMIN)
    session = _make_session()
    session.get.return_value = admin_user

    current_user = _make_user(id=uuid4(), role=UserRole.TEACHER)
    svc = UserService(session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_user(str(admin_user.id), current_user)

    assert exc_info.value.status_code == 403
