"""
Unit tests for app.services.room_service.RoomService.

Patches space_repo, room_repo, and permission_service at their import
locations inside the room_service module so no real DB or Redis is needed.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.agent_config import AgentConfig
from app.models.room import Room, RoomCreate, RoomUpdate
from app.models.space import Space
from app.models.user import User, UserRole
from app.services.room_service import RoomService


def _make_user(**kwargs) -> User:
    defaults = dict(id=uuid4(), email="user@example.com", role=UserRole.TEACHER, is_active=True)
    defaults.update(kwargs)
    return User(**defaults)


def _make_space(owner: User, **kwargs) -> Space:
    defaults = dict(id=uuid4(), title="Space", owner_id=owner.id)
    defaults.update(kwargs)
    return Space(**defaults)


def _make_room(space: Space, **kwargs) -> Room:
    defaults = dict(id=uuid4(), name="Room", space_id=space.id)
    defaults.update(kwargs)
    return Room(**defaults)


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# create_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_room_success():
    user = _make_user()
    space = _make_space(user)
    room_in = RoomCreate(name="New Room", space_id=space.id)
    created_room = _make_room(space)
    session = _make_session()

    with (
        patch("app.services.room_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.room_service.room_repo.create",
            new=AsyncMock(return_value=created_room),
        ),
    ):
        svc = RoomService(session)
        result = await svc.create_room(room_in, user)

    assert result is created_room


@pytest.mark.asyncio()
async def test_create_room_space_not_found_raises_404():
    user = _make_user()
    room_in = RoomCreate(name="Room", space_id=uuid4())
    session = _make_session()

    with patch("app.services.room_service.space_repo.get", new=AsyncMock(return_value=None)):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_room(room_in, user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_create_room_permission_denied_raises_403():
    user = _make_user()
    space = _make_space(user)
    room_in = RoomCreate(name="Room", space_id=space.id)
    session = _make_session()

    with (
        patch("app.services.room_service.space_repo.get", new=AsyncMock(return_value=space)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=False),
        ),
    ):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_room(room_in, user)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# get_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_room_by_id_found():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    session = _make_session()

    with patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)):
        svc = RoomService(session)
        result = await svc.get_room(room.id)

    assert result is room


@pytest.mark.asyncio()
async def test_get_room_by_id_not_found_raises_404():
    session = _make_session()

    with patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=None)):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.get_room(uuid4())

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_rooms_by_space
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_list_rooms_by_space_returns_list():
    user = _make_user()
    space = _make_space(user)
    rooms = [_make_room(space), _make_room(space)]
    session = _make_session()

    with patch(
        "app.services.room_service.room_repo.get_multi_by_space",
        new=AsyncMock(return_value=rooms),
    ):
        svc = RoomService(session)
        result = await svc.get_rooms_by_space(space.id)

    assert result == rooms
    assert len(result) == 2


@pytest.mark.asyncio()
async def test_list_rooms_by_space_empty():
    user = _make_user()
    space = _make_space(user)
    session = _make_session()

    with patch(
        "app.services.room_service.room_repo.get_multi_by_space",
        new=AsyncMock(return_value=[]),
    ):
        svc = RoomService(session)
        result = await svc.get_rooms_by_space(space.id)

    assert result == []


# ---------------------------------------------------------------------------
# update_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_room_success():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    updated_room = _make_room(space, name="Updated")
    session = _make_session()

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.room_service.room_repo.update",
            new=AsyncMock(return_value=updated_room),
        ),
    ):
        svc = RoomService(session)
        result = await svc.update_room(room.id, RoomUpdate(name="Updated"), user)

    assert result is updated_room


@pytest.mark.asyncio()
async def test_update_room_permission_denied_raises_403():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    session = _make_session()

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=False),
        ),
    ):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_room(room.id, RoomUpdate(name="Hack"), user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio()
async def test_update_room_not_found_raises_404():
    user = _make_user()
    session = _make_session()

    with patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=None)):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_room(uuid4(), RoomUpdate(name="X"), user)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_delete_room_success():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    session = _make_session()
    mock_cascade = AsyncMock()

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
        patch("app.services.room_service.room_repo.cascade_delete_room", new=mock_cascade),
    ):
        svc = RoomService(session)
        await svc.delete_room(room.id, user)

    mock_cascade.assert_awaited_once()


@pytest.mark.asyncio()
async def test_delete_room_not_found_raises_404():
    user = _make_user()
    session = _make_session()

    with patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=None)):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_room(uuid4(), user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_delete_room_permission_denied_raises_403():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    session = _make_session()

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=False),
        ),
    ):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_room(room.id, user)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# assign_agent (add_agent_to_room)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_assign_agent_to_room_success():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    agent_id = uuid4()
    agent = AgentConfig(id=agent_id, name="My Agent", agent_type="std", space_id=space.id)
    session = _make_session()
    session.get.return_value = agent

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.room_service.room_repo.get_agent_link",
            new=AsyncMock(return_value=None),
        ),
        patch("app.services.room_service.room_repo.create_agent_link", new=AsyncMock()),
    ):
        svc = RoomService(session)
        result = await svc.assign_agent(room.id, agent_id, user)

    assert "assigned" in result.lower()


@pytest.mark.asyncio()
async def test_assign_agent_already_assigned_returns_message():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    agent_id = uuid4()
    agent = AgentConfig(id=agent_id, name="Agent", agent_type="std", space_id=space.id)
    existing_link = Mock()
    session = _make_session()
    session.get.return_value = agent

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.room_service.room_repo.get_agent_link",
            new=AsyncMock(return_value=existing_link),
        ),
    ):
        svc = RoomService(session)
        result = await svc.assign_agent(room.id, agent_id, user)

    assert "already" in result.lower()


@pytest.mark.asyncio()
async def test_assign_agent_not_found_raises_404():
    user = _make_user()
    space = _make_space(user)
    room = _make_room(space)
    agent_id = uuid4()
    session = _make_session()
    session.get.return_value = None  # agent not found

    with (
        patch("app.services.room_service.room_repo.get", new=AsyncMock(return_value=room)),
        patch(
            "app.services.room_service.permission_service.check",
            new=AsyncMock(return_value=True),
        ),
    ):
        svc = RoomService(session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.assign_agent(room.id, agent_id, user)

    assert exc_info.value.status_code == 404
