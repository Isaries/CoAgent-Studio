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

    msg = await service.save_user_message(room_id, user, content)

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

    # Mock exec result
    # We need to ensure that iterating over result yields (msg, user) tuples
    mock_rows = [(mock_msg, mock_user)]

    # Mock object that is awaitable and iterable
    # session.exec returns a Result object which is iterable

    mock_result_obj = Mock()
    mock_result_obj.__iter__ = Mock(return_value=iter(mock_rows))

    session.exec.return_value = mock_result_obj

    messages = await service.get_room_messages(room_id)

    assert len(messages) == 1
    assert messages[0]["content"] == "Hi"
    assert messages[0]["sender"] == "Sender"
