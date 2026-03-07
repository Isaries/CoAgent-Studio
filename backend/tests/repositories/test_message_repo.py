"""
Unit tests for app.repositories.message_repo.MessageRepository.

Covers:
- get_room_history_with_users: default limit is 500
- get_room_history_with_users: custom limit is respected
- get_room_history_with_users: results are returned in ascending order (oldest first)
- create: message is persisted with correct fields
"""

from unittest.mock import AsyncMock, Mock, call, patch
from uuid import uuid4

import pytest

from app.repositories.message_repo import MessageRepository


def _make_repo():
    session = AsyncMock()
    return MessageRepository(session), session


# ---------------------------------------------------------------------------
# get_room_history_with_users — hard limit (Bug 1 fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_get_room_history_with_users_applies_default_limit():
    """
    The query must apply .limit(500) by default.
    We verify this by inspecting the compiled query string.
    """
    repo, session = _make_repo()
    room_id = uuid4()

    mock_result = Mock()
    mock_result.all.return_value = []
    session.exec = AsyncMock(return_value=mock_result)

    captured = {}

    async def capture_exec(query):
        captured["query"] = query
        return mock_result

    session.exec = capture_exec

    await repo.get_room_history_with_users(room_id)

    assert "query" in captured
    from sqlalchemy.dialects import postgresql
    compiled = captured["query"].compile(dialect=postgresql.dialect())
    sql_str = str(compiled)
    # LIMIT appears as a bind param in PostgreSQL dialect
    assert "LIMIT" in sql_str.upper()
    assert compiled.params.get("param_1") == 500


@pytest.mark.asyncio()
async def test_get_room_history_with_users_custom_limit():
    """A custom limit parameter must be reflected in the SQL query."""
    repo, session = _make_repo()
    room_id = uuid4()

    mock_result = Mock()
    mock_result.all.return_value = []
    captured = {}

    async def capture_exec(query):
        captured["query"] = query
        return mock_result

    session.exec = capture_exec

    await repo.get_room_history_with_users(room_id, limit=100)

    from sqlalchemy.dialects import postgresql
    compiled = captured["query"].compile(dialect=postgresql.dialect())
    assert compiled.params.get("param_1") == 100


@pytest.mark.asyncio()
async def test_get_room_history_with_users_returns_ascending_order():
    """
    The repository fetches DESC then reverses, so the returned rows must be
    in ascending (oldest-first) order.
    """
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.models.message import Message
    from app.models.user import User

    repo, session = _make_repo()
    room_id = uuid4()

    older = Message(id=uuid4(), content="first", room_id=room_id, sender_id=uuid4(),
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = Message(id=uuid4(), content="second", room_id=room_id, sender_id=uuid4(),
                    created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))

    # DB returns DESC order (newest first) — repo must reverse to asc
    mock_result = Mock()
    mock_result.all.return_value = [(newer, None), (older, None)]
    session.exec = AsyncMock(return_value=mock_result)

    rows = await repo.get_room_history_with_users(room_id)

    assert rows[0][0].content == "first"
    assert rows[1][0].content == "second"


# ---------------------------------------------------------------------------
# create — basic persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_message_sets_fields_correctly():
    repo, session = _make_repo()

    room_id = uuid4()
    sender_id = uuid4()
    content = "Test message content"

    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    msg = await repo.create(content, room_id, sender_id)

    assert msg.content == content
    assert msg.room_id == room_id
    assert msg.sender_id == sender_id
    session.add.assert_called_once_with(msg)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(msg)
