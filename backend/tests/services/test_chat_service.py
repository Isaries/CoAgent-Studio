from unittest.mock import AsyncMock, Mock
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

    msg = await service.save_user_message(room_id, user.id, content)

    assert msg.content == content
    assert str(msg.room_id) == room_id
    assert msg.sender_id == user.id

    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


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
