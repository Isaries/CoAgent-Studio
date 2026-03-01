"""
Tests for A2A P3: Distributed Messaging.

These tests verify the distributed dispatcher and hybrid dispatcher,
including Redis Streams integration and fallback behavior.

Note: Some tests require a running Redis instance and are marked with
@pytest.mark.redis to allow skipping when Redis is unavailable.
"""

import pytest
import asyncio
from typing import Dict
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
        # Track per-entry delivery counts for xpending_range mock
        self._delivery_counts: Dict[str, Dict[str, int]] = {}

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

    async def xpending_range(self, stream, group, min=None, max=None, count=1):
        """Mock xpending_range — returns delivery count from _delivery_counts."""
        key = f"{stream}:{min}" if min else None
        if key and stream in self._delivery_counts and min in self._delivery_counts[stream]:
            return [{"times_delivered": self._delivery_counts[stream][min]}]
        return [{"times_delivered": 1}]

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

    async def xrange(self, stream, min="-", max="+", count=None):
        """Mock xrange — return entries from stream."""
        if stream not in self.streams:
            return []
        entries = self.streams[stream]
        if count:
            entries = entries[:count]
        return list(entries)

    async def xdel(self, stream, *entry_ids):
        """Mock xdel — remove entries by ID."""
        if stream in self.streams:
            self.streams[stream] = [
                (eid, data) for eid, data in self.streams[stream]
                if eid not in entry_ids
            ]
        return len(entry_ids)

    def set_delivery_count(self, stream: str, entry_id: str, count: int):
        """Test helper to set the delivery count for a specific entry."""
        if stream not in self._delivery_counts:
            self._delivery_counts[stream] = {}
        self._delivery_counts[stream][entry_id] = count


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
# Dead-Letter Queue Tests
# ============================================================

class TestDeadLetterQueue:
    """Tests for dead-letter queue behaviour in DistributedDispatcher."""

    @pytest.mark.asyncio
    async def test_message_moved_to_dlq_after_max_retries(self):
        """Message exceeding max_retries is moved to the DLQ."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            mock_redis_module.ResponseError = Exception  # for xinfo_stream fallback

            config = DistributedDispatcherConfig(max_retries=3)
            dispatcher = DistributedDispatcher(config=config)
            await dispatcher.connect()

            # Dispatch a message so it exists in the stream
            msg = A2AMessage(
                type=MessageType.PROPOSAL,
                sender_id="student",
                recipient_id="teacher",
                content="will fail",
            )
            await dispatcher.dispatch(msg)

            # Set up a handler that always fails
            async def failing_handler(m):
                raise RuntimeError("permanent failure")

            stream_name = "a2a:teacher"
            entry_id = "0-0"
            data = mock_client.streams[stream_name][0][1]

            # Simulate delivery count >= max_retries
            mock_client.set_delivery_count(stream_name, entry_id, 3)

            await dispatcher._process_entry(
                "teacher", stream_name, entry_id, data, failing_handler
            )

            # Verify message was moved to DLQ
            dlq_stream = "a2a:dlq:teacher"
            assert dlq_stream in mock_client.streams
            assert len(mock_client.streams[dlq_stream]) == 1
            dlq_entry = mock_client.streams[dlq_stream][0][1]
            assert "permanent failure" in dlq_entry["error"]

    @pytest.mark.asyncio
    async def test_message_stays_for_retry_below_max(self):
        """Message below max_retries stays unacknowledged for retry."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            mock_redis_module.ResponseError = Exception

            config = DistributedDispatcherConfig(max_retries=3)
            dispatcher = DistributedDispatcher(config=config)
            await dispatcher.connect()

            msg = A2AMessage(
                type=MessageType.PROPOSAL,
                sender_id="student",
                recipient_id="teacher",
                content="will retry",
            )
            await dispatcher.dispatch(msg)

            async def failing_handler(m):
                raise RuntimeError("transient failure")

            stream_name = "a2a:teacher"
            entry_id = "0-0"
            data = mock_client.streams[stream_name][0][1]

            # delivery count below threshold
            mock_client.set_delivery_count(stream_name, entry_id, 1)

            await dispatcher._process_entry(
                "teacher", stream_name, entry_id, data, failing_handler
            )

            # DLQ should NOT exist
            dlq_stream = "a2a:dlq:teacher"
            assert dlq_stream not in mock_client.streams

    @pytest.mark.asyncio
    async def test_reprocess_dlq(self):
        """reprocess_dlq moves messages from DLQ back to main stream."""
        with patch("app.core.a2a.distributed.redis") as mock_redis_module:
            mock_client = MockRedis()
            mock_redis_module.from_url.return_value = mock_client
            mock_redis_module.ResponseError = Exception

            dispatcher = DistributedDispatcher()
            await dispatcher.connect()

            # Manually add an entry to the DLQ stream
            dlq_stream = "a2a:dlq:teacher"
            await mock_client.xadd(dlq_stream, {
                "data": '{"fake": "payload"}',
                "original_stream": "a2a:teacher",
                "original_entry_id": "0-0",
                "error": "some error",
            })

            requeued = await dispatcher.reprocess_dlq("teacher", count=10)
            assert requeued == 1

            # Main stream should have the message
            main_stream = "a2a:teacher"
            assert main_stream in mock_client.streams
            assert len(mock_client.streams[main_stream]) == 1

            # DLQ should be empty
            assert len(mock_client.streams[dlq_stream]) == 0

    @pytest.mark.asyncio
    async def test_get_dlq_stream_name(self):
        """DLQ stream name follows expected convention."""
        dispatcher = DistributedDispatcher()
        assert dispatcher._get_dlq_stream("teacher") == "a2a:dlq:teacher"

        custom = DistributedDispatcherConfig(stream_prefix="custom")
        dispatcher2 = DistributedDispatcher(config=custom)
        assert dispatcher2._get_dlq_stream("teacher") == "custom:dlq:teacher"


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
