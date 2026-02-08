"""
Tests for External Agent Integration.

Covers:
- ExternalAgentAdapter functionality
- Webhook endpoint
- AgentFactory external agent support
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient

from app.core.a2a.external_adapter import (
    ExternalAgentAdapter,
    AuthType,
    CircuitBreakerState,
    OAuthToken,
)
from app.core.a2a.models import A2AMessage, MessageType
from app.factories.agent_factory import AgentFactory
from app.models.agent_config import AgentConfig


# ============================================================================
# CircuitBreakerState Tests
# ============================================================================


class TestCircuitBreakerState:
    """Tests for the Circuit Breaker pattern implementation."""

    def test_initial_state_closed(self):
        """Circuit breaker should start in closed state."""
        cb = CircuitBreakerState()
        assert cb.is_open is False
        assert cb.failures == 0

    def test_opens_after_threshold_failures(self):
        """Circuit should open after reaching failure threshold."""
        cb = CircuitBreakerState()
        threshold = 3
        
        cb.record_failure()
        assert cb.should_open(threshold) is False
        
        cb.record_failure()
        assert cb.should_open(threshold) is False
        
        cb.record_failure()
        assert cb.should_open(threshold) is True

    def test_resets_on_success(self):
        """Should reset failure count on success."""
        cb = CircuitBreakerState()
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failures == 2
        
        cb.record_success()
        assert cb.failures == 0
        assert cb.is_open is False

    def test_should_attempt_after_recovery_timeout(self):
        """Should allow attempts after recovery timeout."""
        cb = CircuitBreakerState()
        cb.is_open = True
        cb.last_failure = datetime.utcnow() - timedelta(seconds=120)
        
        # With 60 second recovery, should allow attempt after 120 seconds
        assert cb.should_attempt(recovery_timeout=60) is True

    def test_should_not_attempt_during_cooldown(self):
        """Should not allow attempts during cooldown period."""
        cb = CircuitBreakerState()
        cb.is_open = True
        cb.last_failure = datetime.utcnow()
        
        # With 60 second recovery, should not allow immediate attempt
        assert cb.should_attempt(recovery_timeout=60) is False


# ============================================================================
# OAuthToken Tests
# ============================================================================


class TestOAuthToken:
    """Tests for OAuth token management."""

    def test_token_not_expired(self):
        """Token should not be expired before expiration time."""
        token = OAuthToken(
            access_token="test_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        # is_expired is a property, not a method
        assert token.is_expired is False

    def test_token_expired(self):
        """Token should be expired after expiration time."""
        token = OAuthToken(
            access_token="test_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert token.is_expired is True


# ============================================================================
# AgentFactory External Agent Tests
# ============================================================================


class TestAgentFactoryExternalAgent:
    """Tests for AgentFactory external agent support."""

    def test_creates_external_adapter_for_external_config(self):
        """Factory should create ExternalAgentAdapter for external agents."""
        config = AgentConfig(
            id=uuid4(),
            type="external_gpt",
            name="External GPT Agent",
            system_prompt="You are a helpful assistant.",
            model_provider="external",
            model="gpt-4",
            course_id=None,
            is_external=True,
            external_config={
                "webhook_url": "https://external-agent.example.com/webhook",
                "auth_type": "bearer",
                "auth_token": "secret_token",
            },
            created_by=uuid4(),
            updated_at=datetime.utcnow(),
        )
        
        agent = AgentFactory.create_agent(config)
        
        assert agent is not None
        assert isinstance(agent, ExternalAgentAdapter)
        assert agent.agent_id == config.id

    def test_external_agent_no_api_key_required(self):
        """External agents should not require API keys."""
        config = AgentConfig(
            id=uuid4(),
            type="external_claude",
            name="External Claude",
            system_prompt="You are Claude.",
            model_provider="external",
            model="claude-3",
            course_id=None,
            is_external=True,
            external_config={
                "webhook_url": "https://claude.example.com/a2a",
                "auth_type": "none",
            },
            # No encrypted_api_key
            created_by=uuid4(),
            updated_at=datetime.utcnow(),
        )
        
        agent = AgentFactory.create_agent(config)
        
        assert agent is not None
        assert isinstance(agent, ExternalAgentAdapter)

    def test_internal_agent_without_key_returns_none(self):
        """Internal agents without API keys should return None."""
        config = AgentConfig(
            id=uuid4(),
            type="teacher",
            name="Teacher Agent",
            system_prompt="You are a teacher.",
            model_provider="gemini",
            model="gemini-2.0-pro",
            course_id=None,
            is_external=False,
            # No API keys
            created_by=uuid4(),
            updated_at=datetime.utcnow(),
        )
        
        agent = AgentFactory.create_agent(config)
        
        assert agent is None


# ============================================================================
# ExternalAgentAdapter Tests
# ============================================================================


class TestExternalAgentAdapter:
    """Tests for ExternalAgentAdapter functionality."""

    @pytest.fixture
    def external_config(self):
        """Create a test external agent config."""
        return AgentConfig(
            id=uuid4(),
            type="external_test",
            name="Test External Agent",
            system_prompt="Test prompt",
            model_provider="external",
            model="test-model",
            course_id=None,
            is_external=True,
            external_config={
                "webhook_url": "https://test-agent.example.com/webhook",
                "auth_type": "bearer",
                "auth_token": "test_bearer_token",
            },
            created_by=uuid4(),
            updated_at=datetime.utcnow(),
        )

    def test_adapter_initialization(self, external_config):
        """Adapter should initialize correctly from config."""
        adapter = ExternalAgentAdapter(external_config)
        
        assert adapter.agent_id == external_config.id
        assert adapter._webhook_url == "https://test-agent.example.com/webhook"
        assert adapter._auth_type == AuthType.BEARER
        assert adapter._auth_token == "test_bearer_token"

    @pytest.mark.anyio
    async def test_bearer_auth_headers(self, external_config):
        """Bearer auth should generate correct Authorization header."""
        adapter = ExternalAgentAdapter(external_config)
        headers = await adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_bearer_token"

    @pytest.mark.anyio
    async def test_no_auth_headers(self, external_config):
        """No auth type should return empty headers."""
        external_config.external_config["auth_type"] = "none"
        adapter = ExternalAgentAdapter(external_config)
        headers = await adapter._get_auth_headers()
        
        assert headers == {}

    def test_message_serialization(self, external_config):
        """Messages should be correctly serialized for external API."""
        adapter = ExternalAgentAdapter(external_config)
        
        msg = A2AMessage(
            type=MessageType.USER_MESSAGE,
            sender_id="user_123",
            recipient_id=str(external_config.id),
            content="Hello external agent!",
            metadata={"room_id": "room_abc"},
        )
        
        payload = adapter._serialize_message(msg)
        
        assert payload["sender_id"] == "user_123"
        assert payload["recipient_id"] == str(external_config.id)
        assert payload["type"] == "user_message"
        assert payload["content"] == "Hello external agent!"

    def test_fallback_response_creation(self, external_config):
        """Should create proper fallback message."""
        adapter = ExternalAgentAdapter(external_config)
        
        msg = A2AMessage(
            type=MessageType.USER_MESSAGE,
            sender_id="user",
            recipient_id="agent",
            content="Test",
        )
        
        fallback = adapter._create_fallback_response(msg)
        
        assert fallback.type == MessageType.SYSTEM
        assert fallback.sender_id == "system"
        assert fallback.correlation_id == msg.id
        assert fallback.metadata.get("fallback") is True


# ============================================================================
# Webhook Endpoint Tests
# ============================================================================


@pytest.mark.anyio
class TestWebhookEndpoint:
    """Tests for the A2A webhook endpoint."""

    async def test_health_check(self, client: AsyncClient):
        """Health check endpoint should return ok status."""
        response = await client.get("/api/v1/a2a/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    async def test_webhook_requires_agent_id_header(self, client: AsyncClient):
        """Webhook should require X-Agent-ID header."""
        response = await client.post(
            "/api/v1/a2a/webhook",
            json={
                "sender_id": "external_agent",
                "content": "Hello from external",
            },
        )
        
        assert response.status_code == 400
        assert "X-Agent-ID" in response.json()["detail"]

    async def test_webhook_rejects_invalid_agent_id(self, client: AsyncClient):
        """Webhook should reject invalid agent UUID format."""
        response = await client.post(
            "/api/v1/a2a/webhook",
            headers={"X-Agent-ID": "not-a-uuid"},
            json={
                "sender_id": "external_agent",
                "content": "Hello",
            },
        )
        
        assert response.status_code == 400
        assert "Invalid X-Agent-ID" in response.json()["detail"]

    async def test_webhook_rejects_unknown_agent(self, client: AsyncClient):
        """Webhook should reject messages from unregistered agents."""
        response = await client.post(
            "/api/v1/a2a/webhook",
            headers={"X-Agent-ID": str(uuid4())},
            json={
                "sender_id": "external_agent",
                "content": "Hello",
            },
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_webhook_validates_callback_token(
        self, client: AsyncClient, db_session, mock_teacher
    ):
        """Webhook should validate callback token when configured."""
        # Create external agent in DB
        agent_id = uuid4()
        config = AgentConfig(
            id=agent_id,
            type="external_test",
            name="Test External",
            system_prompt="Test",
            model_provider="external",
            model="test",
            course_id=None,
            is_external=True,
            external_config={
                "webhook_url": "https://example.com/webhook",
                "auth_type": "none",
                "callback_token": "secret_callback_token",
            },
            created_by=mock_teacher.id,
            updated_at=datetime.utcnow(),
        )
        db_session.add(config)
        await db_session.flush()
        
        # Wrong token should fail
        response = await client.post(
            "/api/v1/a2a/webhook",
            headers={
                "X-Agent-ID": str(agent_id),
                "X-Agent-Token": "wrong_token",
            },
            json={
                "sender_id": "external",
                "content": "Hello",
            },
        )
        
        assert response.status_code == 401

    async def test_webhook_accepts_valid_message(
        self, client: AsyncClient, db_session, mock_teacher
    ):
        """Webhook should accept valid messages from registered agents."""
        # Create external agent in DB
        agent_id = uuid4()
        config = AgentConfig(
            id=agent_id,
            type="external_test",
            name="Test External",
            system_prompt="Test",
            model_provider="external",
            model="test",
            course_id=None,
            is_external=True,
            external_config={
                "webhook_url": "https://example.com/webhook",
                "auth_type": "none",
            },
            created_by=mock_teacher.id,
            updated_at=datetime.utcnow(),
        )
        db_session.add(config)
        await db_session.flush()
        
        # Mock socket manager and store
        with patch("app.api.api_v1.endpoints.a2a_webhook.manager") as mock_manager, \
             patch("app.api.api_v1.endpoints.a2a_webhook.A2AMessageStore") as mock_store:
            mock_manager.broadcast = AsyncMock()
            mock_store_instance = MagicMock()
            mock_store_instance.save = AsyncMock()
            mock_store.return_value = mock_store_instance
            
            response = await client.post(
                "/api/v1/a2a/webhook",
                headers={"X-Agent-ID": str(agent_id)},
                json={
                    "sender_id": "external_agent",
                    "recipient_id": "broadcast",
                    "content": "Hello from external agent!",
                    "metadata": {"room_id": "test_room"},
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] is not None

    async def test_webhook_p2p_dispatch(
        self, client: AsyncClient, db_session, mock_teacher
    ):
        """Webhook should dispatch point-to-point messages to target agent."""
        # 1. Create Sender Agent
        sender_id = uuid4()
        sender_config = AgentConfig(
            id=sender_id,
            type="external_sender",
            name="Sender Agent",
            system_prompt="Sender",
            model_provider="external",
            model="sender",
            course_id=None,
            is_external=True,
            external_config={"webhook_url": "http://sender.com", "auth_type": "none"},
            created_by=mock_teacher.id,
        )
        db_session.add(sender_config)
        
        # 2. Create Recipient Agent
        recipient_id = uuid4()
        recipient_config = AgentConfig(
            id=recipient_id,
            type="external_recipient",
            name="Recipient Agent",
            system_prompt="Recipient",
            model_provider="external",
            model="recipient",
            course_id=None,
            is_external=True,
            external_config={"webhook_url": "http://recipient.com", "auth_type": "none"},
            created_by=mock_teacher.id,
        )
        db_session.add(recipient_config)
        await db_session.flush()
        
        # 3. Mock dependencies
        with patch("app.api.api_v1.endpoints.a2a_webhook.manager") as mock_manager, \
             patch("app.api.api_v1.endpoints.a2a_webhook.A2AMessageStore") as mock_store, \
             patch("app.core.a2a.external_adapter.ExternalAgentAdapter.receive_message", new_callable=AsyncMock) as mock_receive:
            
            mock_manager.broadcast = AsyncMock()
            mock_store_instance = MagicMock()
            mock_store_instance.save = AsyncMock()
            mock_store.return_value = mock_store_instance
            
            # Setup mock response from recipient
            mock_response = A2AMessage(
                content="Ack P2P",
                sender_id=str(recipient_id),
                recipient_id=str(sender_id),
                type=MessageType.EVALUATION_RESULT
            )
            mock_receive.return_value = mock_response
            
            # 4. Send P2P Message
            response = await client.post(
                "/api/v1/a2a/webhook",
                headers={"X-Agent-ID": str(sender_id)},
                json={
                    "sender_id": "sender_agent",
                    "recipient_id": str(recipient_id),  # Target UUID
                    "content": "Secret message",
                    "metadata": {"room_id": "test_room"},
                },
            )
            
            # 5. Verify Dispatch
            assert response.status_code == 200
            assert response.json()["dispatched"] is True
            
            # Verify receive_message called with correct arg
            assert mock_receive.called
            call_args = mock_receive.call_args[0][0]
            assert isinstance(call_args, A2AMessage)
            assert call_args.recipient_id == str(recipient_id)
            assert call_args.content == "Secret message"
            
            # Verify response broadcast to room
            assert mock_manager.broadcast.called
            broadcast_args = mock_manager.broadcast.call_args[0]
            payload = broadcast_args[0]
            assert payload["type"] == "a2a_external_message"
            assert payload["content"] == "Ack P2P"
            assert payload["agent_id"] == str(recipient_id)
