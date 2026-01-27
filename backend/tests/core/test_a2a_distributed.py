"""
Tests for A2A P3: Distributed Messaging.

These tests verify the distributed dispatcher and hybrid dispatcher,
including Redis Streams integration and fallback behavior.

Note: Some tests require a running Redis instance and are marked with
@pytest.mark.redis to allow skipping when Redis is unavailable.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.a2a import (
    # Core
    A2AMessage,
    MessageType,
    # P3: Distributed
    DistributedDispatcher,
    DistributedDispatcherConfig,
    HybridDispatcher,
    DispatchMode,
)


# ============================================================
# Mock Redis for unit testing without actual Redis
# ============================================================

class MockRedis:
    """Mock Redis client for testing without actual Redis."""
    
    def __init__(self):
        self.streams = {}
        self.groups = {}
    
    async def ping(self):
        return True
    
    async def close(self):
        pass
    
    async def xadd(self, stream, fields, maxlen=None):
        if stream not in self.streams:
            self.streams[stream] = []
        entry_id = f"{len(self.streams[stream])}-0"
        self.streams[stream].append((entry_id, fields))
        return entry_id
    
    async def xgroup_create(self, stream, group, id="0", mkstream=False):
        if mkstream and stream not in self.streams:
            self.streams[stream] = []
        key = f"{stream}:{group}"
        if key in self.groups:
            from redis import ResponseError
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        self.groups[key] = {"pending": []}
    
    async def xreadgroup(self, group, consumer, streams_dict, count=None, block=None):
        results = []
        for stream_name, start_id in streams_dict.items():
            if stream_name in self.streams:
                if start_id == ">":  # New messages only
                    entries = self.streams[stream_name][-count:] if count else self.streams[stream_name]
                    if entries:
                        results.append((stream_name, entries))
                        self.streams[stream_name] = []  # Clear after read
        return results
    
    async def xack(self, stream, group, entry_id):
        return 1
    
    async def xpending(self, stream, group):
        return {"pending": 0}
    
    async def xinfo_stream(self, stream):
        if stream in self.streams:
            return {
                "length": len(self.streams[stream]),
                "first-entry": self.streams[stream][0] if self.streams[stream] else None,
                "last-entry": self.streams[stream][-1] if self.streams[stream] else None,
                "groups": len([k for k in self.groups if k.startswith(stream)]),
            }
        from redis import ResponseError
        raise ResponseError("no such stream")
    
    async def xtrim(self, stream, minid=None):
        return 0
    
    async def xautoclaim(self, stream, group, consumer, min_idle_time, start_id="0-0", count=100):
        # Mock empty claim
        return (start_id, [], [])


# ============================================================
# DistributedDispatcher Tests
# ============================================================

class TestDistributedDispatcherConfig:
    """Tests for configuration dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DistributedDispatcherConfig()
        assert config.stream_prefix == "a2a"
        assert config.consumer_group == "a2a_workers"
        assert config.block_ms == 5000
        assert config.max_retries == 3
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = DistributedDispatcherConfig(
            stream_prefix="custom",
            block_ms=10000,
        )
        assert config.stream_prefix == "custom"
        assert config.block_ms == 10000


class TestDistributedDispatcher:
    """Tests for distributed dispatcher (mocked Redis)."""
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connection lifecycle."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            
            dispatcher = DistributedDispatcher(redis_url="redis://mock:6379")
            await dispatcher.connect()
            
            assert dispatcher._redis is not None
            
            await dispatcher.disconnect()
            assert dispatcher._redis is None
    
    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test handler registration."""
        dispatcher = DistributedDispatcher()
        
        async def handler(msg):
            return None
        
        dispatcher.register("test_agent", handler)
        assert "test_agent" in dispatcher._handlers
        
        dispatcher.unregister("test_agent")
        assert "test_agent" not in dispatcher._handlers
    
    @pytest.mark.asyncio
    async def test_dispatch_message(self):
        """Test dispatching a message."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            
            dispatcher = DistributedDispatcher()
            await dispatcher.connect()
            
            msg = A2AMessage(
                type=MessageType.PROPOSAL,
                sender_id="student",
                recipient_id="teacher",
                content="Test proposal",
            )
            
            await dispatcher.dispatch(msg)
            
            # Check message was added to stream
            stream_name = "a2a:teacher"
            assert stream_name in mock_client.streams
            assert len(mock_client.streams[stream_name]) == 1
    
    @pytest.mark.asyncio
    async def test_serialize_deserialize(self):
        """Test message serialization roundtrip."""
        dispatcher = DistributedDispatcher()
        
        original = A2AMessage(
            type=MessageType.EVALUATION_REQUEST,
            sender_id="student",
            recipient_id="teacher",
            content={"proposal": "Hello", "context": "Test"},
            metadata={"room_id": "123"},
        )
        
        serialized = dispatcher._serialize(original)
        deserialized = dispatcher._deserialize(serialized)
        
        assert deserialized.type == original.type
        assert deserialized.sender_id == original.sender_id
        assert deserialized.recipient_id == original.recipient_id
        assert deserialized.content == original.content
        assert deserialized.metadata == original.metadata
    
    @pytest.mark.asyncio
    async def test_get_stream_name(self):
        """Test stream name generation."""
        dispatcher = DistributedDispatcher()
        assert dispatcher._get_stream_name("teacher") == "a2a:teacher"
        
        custom_config = DistributedDispatcherConfig(stream_prefix="custom")
        dispatcher2 = DistributedDispatcher(config=custom_config)
        assert dispatcher2._get_stream_name("teacher") == "custom:teacher"


# ============================================================
# HybridDispatcher Tests
# ============================================================

class TestHybridDispatcher:
    """Tests for hybrid dispatcher."""
    
    @pytest.mark.asyncio
    async def test_local_mode(self):
        """Test local mode initialization."""
        dispatcher = HybridDispatcher(mode=DispatchMode.LOCAL)
        await dispatcher.connect()
        
        assert dispatcher.mode == DispatchMode.LOCAL
        assert dispatcher.is_distributed is False
        assert dispatcher._local is not None
        assert dispatcher._distributed is None
        
        await dispatcher.disconnect()
    
    @pytest.mark.asyncio
    async def test_local_mode_dispatch(self):
        """Test dispatching in local mode."""
        dispatcher = HybridDispatcher(mode=DispatchMode.LOCAL)
        await dispatcher.connect()
        
        # Register handler
        received = []
        async def handler(msg):
            received.append(msg)
            return A2AMessage(
                type=MessageType.EVALUATION_RESULT,
                sender_id="teacher",
                recipient_id="student",
                content={"approved": True, "proposal": msg.content},
            )
        
        dispatcher.register("teacher", handler)
        
        # Dispatch
        msg = A2AMessage(
            type=MessageType.EVALUATION_REQUEST,
            sender_id="student",
            recipient_id="teacher",
            content="Test",
        )
        
        response = await dispatcher.dispatch(msg)
        
        assert len(received) == 1
        assert response is not None
        assert response.content["approved"] is True
        
        await dispatcher.disconnect()
    
    @pytest.mark.asyncio
    async def test_auto_mode_fallback(self):
        """Test AUTO mode falls back to local when Redis unavailable."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            # Make Redis connection fail
            mock_redis_module.from_url.side_effect = Exception("Connection refused")
            
            dispatcher = HybridDispatcher(mode=DispatchMode.AUTO)
            await dispatcher.connect()
            
            # Should fall back to local
            assert dispatcher.mode == DispatchMode.LOCAL
            assert dispatcher._local is not None
            assert dispatcher._distributed is None
            
            await dispatcher.disconnect()
    
    @pytest.mark.asyncio
    async def test_distributed_mode_with_mock(self):
        """Test distributed mode with mocked Redis."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            
            dispatcher = HybridDispatcher(mode=DispatchMode.DISTRIBUTED)
            await dispatcher.connect()
            
            assert dispatcher.mode == DispatchMode.DISTRIBUTED
            assert dispatcher.is_distributed is True
            assert dispatcher._distributed is not None
            
            await dispatcher.disconnect()
    
    @pytest.mark.asyncio
    async def test_middleware_local_only(self):
        """Test middleware only works in local mode."""
        local_dispatcher = HybridDispatcher(mode=DispatchMode.LOCAL)
        await local_dispatcher.connect()
        
        middleware_calls = []
        async def test_middleware(msg):
            middleware_calls.append(msg)
        
        local_dispatcher.add_middleware(test_middleware)
        
        # Register handler
        async def handler(msg):
            return None
        local_dispatcher.register("test", handler)
        
        # Dispatch
        msg = A2AMessage(
            type=MessageType.SYSTEM,
            sender_id="system",
            recipient_id="test",
            content="Hello",
        )
        await local_dispatcher.dispatch(msg)
        
        assert len(middleware_calls) == 1
        
        await local_dispatcher.disconnect()


class TestDispatchMode:
    """Tests for dispatch mode enum."""
    
    def test_enum_values(self):
        """Test enum has expected values."""
        assert DispatchMode.LOCAL.value == "local"
        assert DispatchMode.DISTRIBUTED.value == "distributed"
        assert DispatchMode.AUTO.value == "auto"


# ============================================================
# Integration Tests (require Redis)
# ============================================================

@pytest.mark.redis
class TestDistributedIntegration:
    """
    Integration tests that require a running Redis instance.
    
    Run with: pytest -m redis tests/core/test_a2a_distributed.py
    Skip with: pytest -m "not redis" tests/
    """
    
    @pytest.fixture
    async def redis_dispatcher(self):
        """Create a dispatcher connected to real Redis."""
        dispatcher = DistributedDispatcher(redis_url="redis://localhost:6379")
        try:
            await dispatcher.connect()
            yield dispatcher
        except Exception:
            pytest.skip("Redis not available")
        finally:
            await dispatcher.disconnect()
    
    @pytest.mark.asyncio
    async def test_real_dispatch(self, redis_dispatcher):
        """Test dispatching to real Redis."""
        msg = A2AMessage(
            type=MessageType.PROPOSAL,
            sender_id="test_student",
            recipient_id="test_teacher",
            content="Integration test message",
        )
        
        await redis_dispatcher.dispatch(msg)
        
        # Verify stream info
        info = await redis_dispatcher.get_stream_info("test_teacher")
        assert info.get("length", 0) >= 1
