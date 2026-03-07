from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.message import Message
from app.models.user import User
from app.services.chat_service import ChatService


@pytest.mark.asyncio()
async def test_save_user_message():
    session = AsyncMock()
    service = ChatService(session)

    room_id = str(uuid4())
    user = User(id=uuid4())
    content = "Hello Chat Service"

    # Mock add/commit/refresh
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # Patch cache.redis so save_user_message can publish the GraphRAG event
    mock_redis = AsyncMock()
    with patch("app.core.cache.cache") as mock_cache:
        mock_cache.redis = mock_redis
        msg = await service.save_user_message(room_id, user.id, content)

    assert msg.content == content
    assert str(msg.room_id) == room_id
    assert msg.sender_id == user.id

    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


@pytest.mark.asyncio()
async def test_save_user_message_publishes_graphrag_event():
    """save_user_message must publish to graphrag:events via the shared redis client."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = ChatService(session)
    room_id = str(uuid4())
    user_id = uuid4()

    mock_redis = AsyncMock()
    with patch("app.core.cache.cache") as mock_cache:
        mock_cache.redis = mock_redis
        msg = await service.save_user_message(room_id, user_id, "test content")

    mock_redis.xadd.assert_awaited_once()
    call_args = mock_redis.xadd.call_args
    stream_name = call_args.args[0]
    payload = call_args.args[1]
    assert stream_name == "graphrag:events"
    assert payload["type"] == "message"
    assert payload["room_id"] == room_id
    assert payload["msg_id"] == str(msg.id)


@pytest.mark.asyncio()
async def test_save_user_message_skips_graphrag_event_when_redis_unavailable():
    """If cache.redis is None, graphrag event is silently skipped — no exception raised."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = ChatService(session)

    with patch("app.core.cache.cache") as mock_cache:
        mock_cache.redis = None  # Redis not connected
        msg = await service.save_user_message(str(uuid4()), uuid4(), "no redis content")

    # Message should still be saved successfully
    assert msg.content == "no redis content"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio()
async def test_save_user_message_does_not_create_new_redis_connection():
    """save_user_message must NOT call aioredis.from_url — it reuses cache.redis."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = ChatService(session)

    with patch("app.core.cache.cache") as mock_cache:
        mock_cache.redis = AsyncMock()
        with patch("redis.asyncio.from_url") as mock_from_url:
            await service.save_user_message(str(uuid4()), uuid4(), "content")
            mock_from_url.assert_not_called()


@pytest.mark.asyncio()
async def test_get_room_messages():
    session = AsyncMock()
    service = ChatService(session)
    room_id = uuid4()

    # Mock result
    mock_msg = Message(id=uuid4(), content="Hi", room_id=room_id, sender_id=uuid4())
    mock_user = User(id=mock_msg.sender_id, full_name="Sender")

    # Mock the repo method directly
    mock_rows = [(mock_msg, mock_user)]
    service.message_repo.get_room_history_with_users = AsyncMock(return_value=mock_rows)

    messages = await service.get_room_messages(room_id)

    assert len(messages) == 1
    assert messages[0]["content"] == "Hi"
    assert messages[0]["sender"] == "Sender"
