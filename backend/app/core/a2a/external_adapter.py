"""
External Agent Adapter.

Bridges internal A2A messaging with external agents via HTTP webhooks.
Supports Bearer Token and OAuth2 authentication with resilience patterns.
"""

import asyncio
import httpx
import structlog
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.a2a.models import A2AMessage, MessageType
from app.models.agent_config import AgentConfig

logger = structlog.get_logger()


class AuthType(str, Enum):
    """Authentication types for external agents."""
    NONE = "none"
    BEARER = "bearer"
    OAUTH2 = "oauth2"


@dataclass
class CircuitBreakerState:
    """Tracks circuit breaker state per external agent."""
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = datetime.utcnow()
    
    def record_success(self):
        self.failures = 0
        self.is_open = False
    
    def should_open(self, threshold: int = 5) -> bool:
        return self.failures >= threshold
    
    def should_attempt(self, recovery_timeout: int = 60) -> bool:
        if not self.is_open:
            return True
        if self.last_failure is None:
            return True
        # Half-open: try again after recovery_timeout seconds
        return datetime.utcnow() > self.last_failure + timedelta(seconds=recovery_timeout)


@dataclass
class OAuthToken:
    """OAuth2 token cache."""
    access_token: str
    expires_at: datetime
    refresh_token: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at - timedelta(seconds=30)


class ExternalAgentAdapter:
    """
    Adapter for external A2A agents accessed via HTTP webhooks.
    
    Features:
    - Bearer Token and OAuth2 authentication
    - Circuit Breaker pattern for fault tolerance
    - Exponential backoff retry
    - Fallback to default message on failure
    
    Example external_config:
    {
        "webhook_url": "https://external-agent.com/api/a2a",
        "auth_type": "oauth2",
        "auth_token": "bearer-token-if-simple",
        "oauth_config": {
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "xxx",
            "client_secret": "yyy",
            "scope": "agent:read agent:write"
        },
        "timeout_ms": 30000,
        "fallback_message": "External agent is temporarily unavailable."
    }
    """
    
    def __init__(
        self,
        config: AgentConfig,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_recovery: int = 60,
    ):
        if not config.is_external or not config.external_config:
            raise ValueError("Config must be for an external agent")
        
        self._config = config
        self._external_config = config.external_config
        
        # Parse configuration
        self._webhook_url = self._external_config.get("webhook_url")
        self._auth_type = AuthType(self._external_config.get("auth_type", "none"))
        self._auth_token = self._external_config.get("auth_token")
        self._oauth_config = self._external_config.get("oauth_config", {})
        self._timeout_ms = self._external_config.get("timeout_ms", 30000)
        self._fallback_message = self._external_config.get(
            "fallback_message",
            "⚠️ External agent is temporarily unavailable. Please try again later."
        )
        
        # Resilience
        self._circuit_breaker = CircuitBreakerState()
        self._cb_threshold = circuit_breaker_threshold
        self._cb_recovery = circuit_breaker_recovery
        
        # OAuth token cache
        self._oauth_token: Optional[OAuthToken] = None
        
        if not self._webhook_url:
            raise ValueError("External agent config must include webhook_url")
    
    @property
    def agent_id(self) -> UUID:
        return self._config.id
    
    @property
    def agent_type(self) -> str:
        return self._config.type
    
    async def receive_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """
        Forward A2A message to external agent and return response.
        
        Implements circuit breaker and retry patterns.
        """
        # Circuit breaker check
        if self._circuit_breaker.is_open:
            if not self._circuit_breaker.should_attempt(self._cb_recovery):
                logger.warning(
                    "external_agent_circuit_open",
                    agent_id=str(self.agent_id),
                    agent_type=self.agent_type,
                )
                return self._create_fallback_response(msg)
        
        try:
            response = await self._send_with_retry(msg)
            self._circuit_breaker.record_success()
            return response
        except Exception as e:
            logger.error(
                "external_agent_failed",
                agent_id=str(self.agent_id),
                error=str(e),
            )
            self._circuit_breaker.record_failure()
            
            if self._circuit_breaker.should_open(self._cb_threshold):
                self._circuit_breaker.is_open = True
                logger.warning(
                    "external_agent_circuit_opened",
                    agent_id=str(self.agent_id),
                )
            
            return self._create_fallback_response(msg)
    
    async def _send_with_retry(
        self,
        msg: A2AMessage,
        max_retries: int = 3,
    ) -> Optional[A2AMessage]:
        """Send message with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await self._send_message(msg)
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    # Client error, don't retry
                    raise
                last_exception = e
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
            
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 0.5  # 1.5s, 2.5s, 4.5s
                logger.info(
                    "external_agent_retry",
                    agent_id=str(self.agent_id),
                    attempt=attempt + 1,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)
        
        raise last_exception or Exception("Max retries exceeded")
    
    async def _send_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """Send a single message to the external agent."""
        headers = await self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        
        payload = self._serialize_message(msg)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._webhook_url,
                json=payload,
                headers=headers,
                timeout=self._timeout_ms / 1000.0,
            )
            response.raise_for_status()
            
            data = response.json()
            return self._deserialize_response(data, msg)
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        if self._auth_type == AuthType.NONE:
            return {}
        
        if self._auth_type == AuthType.BEARER:
            return {"Authorization": f"Bearer {self._auth_token}"}
        
        if self._auth_type == AuthType.OAUTH2:
            token = await self._get_oauth_token()
            return {"Authorization": f"Bearer {token}"}
        
        return {}
    
    async def _get_oauth_token(self) -> str:
        """Get or refresh OAuth2 token."""
        if self._oauth_token and not self._oauth_token.is_expired:
            return self._oauth_token.access_token
        
        token_url = self._oauth_config.get("token_url")
        client_id = self._oauth_config.get("client_id")
        client_secret = self._oauth_config.get("client_secret")
        scope = self._oauth_config.get("scope", "")
        
        if not all([token_url, client_id, client_secret]):
            raise ValueError("Incomplete OAuth2 configuration")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
        
        expires_in = data.get("expires_in", 3600)
        self._oauth_token = OAuthToken(
            access_token=data["access_token"],
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            refresh_token=data.get("refresh_token"),
        )
        
        logger.info(
            "oauth_token_acquired",
            agent_id=str(self.agent_id),
            expires_in=expires_in,
        )
        
        return self._oauth_token.access_token
    
    def _serialize_message(self, msg: A2AMessage) -> Dict[str, Any]:
        """Serialize A2AMessage for external API."""
        return {
            "id": str(msg.id),
            "type": msg.type.value,
            "sender_id": msg.sender_id,
            "recipient_id": msg.recipient_id,
            "content": msg.content if isinstance(msg.content, (str, dict)) else str(msg.content),
            "correlation_id": str(msg.correlation_id) if msg.correlation_id else None,
            "metadata": msg.metadata,
            "created_at": msg.created_at.isoformat(),
        }
    
    def _deserialize_response(
        self,
        data: Dict[str, Any],
        original_msg: A2AMessage,
    ) -> Optional[A2AMessage]:
        """Deserialize response from external agent."""
        if not data:
            return None
        
        return A2AMessage(
            type=MessageType(data.get("type", "broadcast")),
            sender_id=data.get("sender_id", str(self.agent_id)),
            recipient_id=data.get("recipient_id", original_msg.sender_id),
            content=data.get("content", ""),
            correlation_id=original_msg.id,
            metadata=data.get("metadata", {}),
        )
    
    def _create_fallback_response(self, original_msg: A2AMessage) -> A2AMessage:
        """Create fallback message when external agent is unavailable."""
        return A2AMessage(
            type=MessageType.SYSTEM,
            sender_id="system",
            recipient_id=original_msg.sender_id,
            content=self._fallback_message,
            correlation_id=original_msg.id,
            metadata={"fallback": True, "original_recipient": str(self.agent_id)},
        )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to external agent."""
        try:
            headers = await self._get_auth_headers()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._webhook_url,
                    headers=headers,
                    timeout=10.0,
                )
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
