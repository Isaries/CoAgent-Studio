from unittest.mock import AsyncMock, patch
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

    # Mock get (for fetching user by ID)
    mock_session.get.return_value = mock_user

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    # 2. Test
    client = TestClient(app)
    room_id = str(uuid4())

    # We patch process_agents to avoid async background logic logic
    with patch(
        "app.api.api_v1.endpoints.chat.process_agents", new_callable=AsyncMock
    ) as mock_process:
        # Correct URL: /api/v1/chat/ws/...
        with client.websocket_connect(f"/api/v1/chat/ws/{room_id}?token={token}") as websocket:
            # Send text
            websocket.send_text("Hello World")

            # Receive broadcast (format: name|timestamp|content)
            data = websocket.receive_text()
            parts = data.split("|")

            # Verify structure
            assert len(parts) >= 3
            assert parts[-1] == "Hello World"

            # Verify agent trigger
            assert mock_process.called

    # Cleanup
    app.dependency_overrides.clear()
