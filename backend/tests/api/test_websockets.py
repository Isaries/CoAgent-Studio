from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_session
from app.main import app
from app.models.user import User


@pytest.mark.asyncio()
async def test_websocket_connect():
    """
    Test WebSocket connection using TestClient.
    We use a REAL token (generated) and Mock the DB Session's .get() method
    to return a user when looking up the token's subject.

    Since the WebSocket endpoint now uses `get_session_context()` (an async context
    manager) rather than `Depends(get_session)`, we monkey-patch it directly.
    """
    # 0. Prepare User and Token
    user_id = uuid4()
    mock_user = User(id=user_id, email="ws_test@example.com", username="wstester", is_active=True)
    from app.core import security

    token = security.create_access_token(subject=user_id)

    # 1. Setup Mock Session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    def mock_add(obj):
        obj.id = uuid4()

    mock_session.add = mock_add

    # Mock get (for fetching user by ID and Room)
    mock_session.get.return_value = mock_user

    # 2. Patch get_session_context to return our mock session
    @asynccontextmanager
    async def mock_get_session_context():
        yield mock_session

    import app.api.api_v1.endpoints.chat as chat_module
    original_get_session_context = chat_module.get_session_context
    chat_module.get_session_context = mock_get_session_context

    # Mock ARQ Pool
    mock_arq_pool = AsyncMock()
    app.state.arq_pool = mock_arq_pool

    # 3. Test
    client = TestClient(app)
    room_id = str(uuid4())

    # Correct URL: /api/v1/chat/ws/...
    try:
        with client.websocket_connect(f"/api/v1/chat/ws/{room_id}?token={token}") as websocket:
            # Send text
            websocket.send_text("Hello World")

            # Receive broadcast (JSON)
            data = websocket.receive_text()
            import json

            msg_obj = json.loads(data)

            # Verify structure
            assert msg_obj["type"] == "message"
            assert msg_obj["content"] == "Hello World"
            assert "sender" in msg_obj
            assert "timestamp" in msg_obj

            # Verify agent trigger (ARQ job enqueued)
            assert mock_arq_pool.enqueue_job.called
            args = mock_arq_pool.enqueue_job.call_args
            assert args[0][0] == "run_agent_cycle_task"
            assert args[0][1] == room_id
    finally:
        # Cleanup
        chat_module.get_session_context = original_get_session_context
        app.dependency_overrides.clear()
