"""
Unit tests for app.services.space_service.SpaceService.

SpaceService delegates to space_repo (a module-level singleton), so tests
patch individual repo methods via unittest.mock.patch.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.space import Space, SpaceCreate, SpaceUpdate
from app.models.user import User, UserRole
from app.services.space_service import SpaceService


def _make_user(**kwargs) -> User:
    defaults = {
        "id": uuid4(),
        "email": "user@example.com",
        "role": UserRole.TEACHER,
        "is_active": True,
    }
    defaults.update(kwargs)
    return User(**defaults)


def _make_space(owner: User, **kwargs) -> Space:
    defaults = {"id": uuid4(), "title": "Test Space", "owner_id": owner.id}
    defaults.update(kwargs)
    return Space(**defaults)


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# create_space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_space_returns_space():
    owner = _make_user()
    session = _make_session()
    space = _make_space(owner)

    with (
        patch("app.services.space_service.space_repo.create", new=AsyncMock(return_value=space)),
        patch("app.services.space_service.space_repo.create_user_link", new=AsyncMock()),
    ):
        svc = SpaceService(session)
        result = await svc.create_space(SpaceCreate(title="Test Space"), owner)

    assert result is space


@pytest.mark.asyncio()
async def test_create_space_enrolls_owner_as_space_owner():
    owner = _make_user()
    session = _make_session()
    space = _make_space(owner)
    mock_create_link = AsyncMock()

    with (
        patch("app.services.space_service.space_repo.create", new=AsyncMock(return_value=space)),
        patch("app.services.space_service.space_repo.create_user_link", new=mock_create_link),
    ):
        svc = SpaceService(session)
        await svc.create_space(SpaceCreate(title="Test Space"), owner)

    mock_create_link.assert_awaited_once()
    call_kwargs = mock_create_link.call_args.kwargs
    assert call_kwargs["role"] == "space_owner"
    assert call_kwargs["user_id"] == owner.id
    assert call_kwargs["space_id"] == space.id


# ---------------------------------------------------------------------------
# get_space_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_space_by_id_found():
    owner = _make_user()
    space = _make_space(owner)
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)):
        svc = SpaceService(session)
        result = await svc.get_space_by_id(space.id)

    assert result is space


@pytest.mark.asyncio()
async def test_get_space_by_id_not_found():
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=None)):
        svc = SpaceService(session)
        result = await svc.get_space_by_id(uuid4())

    assert result is None


# ---------------------------------------------------------------------------
# get_spaces (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_spaces_admin_uses_get_multi_with_owner():
    admin = _make_user(role=UserRole.ADMIN)
    session = _make_session()
    mock_get_multi = AsyncMock(return_value=[])

    with patch("app.services.space_service.space_repo.get_multi_with_owner", new=mock_get_multi):
        svc = SpaceService(session)
        await svc.get_spaces(admin)

    mock_get_multi.assert_awaited_once()


@pytest.mark.asyncio()
async def test_get_spaces_super_admin_uses_get_multi_with_owner():
    super_admin = _make_user(role=UserRole.SUPER_ADMIN)
    session = _make_session()
    mock_get_multi = AsyncMock(return_value=[])

    with patch("app.services.space_service.space_repo.get_multi_with_owner", new=mock_get_multi):
        svc = SpaceService(session)
        await svc.get_spaces(super_admin)

    mock_get_multi.assert_awaited_once()


@pytest.mark.asyncio()
async def test_get_spaces_regular_user_uses_get_multi_by_user():
    user = _make_user(role=UserRole.TEACHER)
    session = _make_session()
    mock_get_user = AsyncMock(return_value=[])

    with patch(
        "app.services.space_service.space_repo.get_multi_by_user_with_owner",
        new=mock_get_user,
    ):
        svc = SpaceService(session)
        await svc.get_spaces(user)

    mock_get_user.assert_awaited_once()


# ---------------------------------------------------------------------------
# update_space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_space_owner_can_update():
    owner = _make_user()
    space = _make_space(owner)
    updated_space = _make_space(owner, title="Updated")
    session = _make_session()

    with (
        patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch(
            "app.services.space_service.space_repo.update",
            new=AsyncMock(return_value=updated_space),
        ),
    ):
        svc = SpaceService(session)
        result = await svc.update_space(space.id, SpaceUpdate(title="Updated"), owner)

    assert result is updated_space


@pytest.mark.asyncio()
async def test_update_space_admin_can_update_any_space():
    owner = _make_user()
    admin = _make_user(id=uuid4(), role=UserRole.ADMIN)
    space = _make_space(owner)
    updated_space = _make_space(owner, title="Admin Updated")
    session = _make_session()

    with (
        patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch(
            "app.services.space_service.space_repo.update",
            new=AsyncMock(return_value=updated_space),
        ),
    ):
        svc = SpaceService(session)
        result = await svc.update_space(space.id, SpaceUpdate(title="Admin Updated"), admin)

    assert result is updated_space


@pytest.mark.asyncio()
async def test_update_space_not_found_raises_404():
    user = _make_user()
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=None)):
        svc = SpaceService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_space(uuid4(), SpaceUpdate(title="X"), user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_update_space_non_owner_non_admin_raises_403():
    owner = _make_user()
    other_user = _make_user(id=uuid4(), role=UserRole.GUEST)
    space = _make_space(owner)
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)):
        svc = SpaceService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_space(space.id, SpaceUpdate(title="Hack"), other_user)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# delete_space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_delete_space_owner_can_delete():
    owner = _make_user()
    space = _make_space(owner)
    session = _make_session()

    with (
        patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch("app.services.space_service.space_repo.remove", new=AsyncMock(return_value=space)),
    ):
        svc = SpaceService(session)
        result = await svc.delete_space(space.id, owner)

    assert result is space


@pytest.mark.asyncio()
async def test_delete_space_not_found_raises_404():
    user = _make_user()
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=None)):
        svc = SpaceService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_space(uuid4(), user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_delete_space_non_owner_non_admin_raises_403():
    owner = _make_user()
    other_user = _make_user(id=uuid4(), role=UserRole.GUEST)
    space = _make_space(owner)
    session = _make_session()

    with patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)):
        svc = SpaceService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_space(space.id, other_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio()
async def test_delete_space_admin_can_delete_any_space():
    owner = _make_user()
    admin = _make_user(id=uuid4(), role=UserRole.ADMIN)
    space = _make_space(owner)
    session = _make_session()

    with (
        patch("app.services.space_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch("app.services.space_service.space_repo.remove", new=AsyncMock(return_value=space)),
    ):
        svc = SpaceService(session)
        result = await svc.delete_space(space.id, admin)

    assert result is space
