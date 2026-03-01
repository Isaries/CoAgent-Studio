"""
A2A Distributed Dispatcher using Redis Streams.

Enables cross-process and cross-machine Agent communication via Redis Streams.
Each agent runs as an independent consumer, reading from its own message stream.

Key Concepts:
- Each agent has a dedicated stream: `a2a:{agent_id}`
- Consumer groups enable multiple workers per agent
- Pending entries list (PEL) ensures message delivery
- Supports both fire-and-forget and request-response patterns
"""

import asyncio
import json
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis

from .models import A2AMessage, MessageType

logger = structlog.get_logger()

# Type aliases
MessageHandler = Callable[[A2AMessage], Awaitable[Optional[A2AMessage]]]


@dataclass
class DistributedDispatcherConfig:
    """Configuration for the distributed dispatcher."""
    stream_prefix: str = "a2a"
    consumer_group: str = "a2a_workers"
    block_ms: int = 5000  # How long to block waiting for messages
    max_retries: int = 3  # Retries for failed message processing
    claim_min_idle_ms: int = 60000  # Claim messages idle for 60s
    response_timeout_ms: int = 30000  # Timeout for request-response


class DistributedDispatcher:
    """
    Redis Streams-based distributed message dispatcher for A2A protocol.
    
    Unlike the in-memory dispatcher, this enables:
    - Cross-process communication (different Python processes)
    - Cross-machine communication (different servers)
    - Horizontal scaling (multiple workers per agent)
    - Message persistence and replay
    - Exactly-once processing semantics
    
    Architecture:
    
        ┌─────────────┐         ┌─────────────────────┐
        │ Agent A     │         │     Redis Server    │
        │ (Process 1) │◄───────►│ ┌─────────────────┐ │
        └─────────────┘         │ │ stream:a2a:agentA│ │
                                │ └─────────────────┘ │
        ┌─────────────┐         │ ┌─────────────────┐ │
        │ Agent B     │◄───────►│ │ stream:a2a:agentB│ │
        │ (Process 2) │         │ └─────────────────┘ │
        └─────────────┘         │ ┌─────────────────┐ │
                                │ │ stream:responses │ │
        ┌─────────────┐         │ └─────────────────┘ │
        │ Agent C     │◄───────►│                     │
        │ (Process 3) │         └─────────────────────┘
        └─────────────┘
    
    Example:
        dispatcher = DistributedDispatcher(redis_url="redis://localhost:6379")
        await dispatcher.connect()
        
        # Register handler for this agent
        await dispatcher.register("teacher", teacher_handler)
        
        # Start consuming (runs forever)
        await dispatcher.start_consuming("teacher")
        
        # Or dispatch a message
        await dispatcher.dispatch(message)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: Optional[DistributedDispatcherConfig] = None,
    ):
        self._redis_url = redis_url
        self._config = config or DistributedDispatcherConfig()
        self._redis: Optional[redis.Redis] = None
        self._handlers: Dict[str, MessageHandler] = {}
        self._consumer_id: str = f"consumer_{uuid4().hex[:8]}"
        self._running: bool = False
        self._pending_responses: Dict[str, asyncio.Future] = {}
    
    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = redis.from_url(self._redis_url, decode_responses=True)
        await self._redis.ping()
        logger.info("distributed_dispatcher_connected", redis_url=self._redis_url)
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._running = False
        if self._redis:
            await self._redis.close()
            self._redis = None
        logger.info("distributed_dispatcher_disconnected")
    
    def _get_stream_name(self, agent_id: str) -> str:
        """Get the stream name for an agent."""
        return f"{self._config.stream_prefix}:{agent_id}"
    
    def _get_response_stream(self) -> str:
        """Get the response stream name."""
        return f"{self._config.stream_prefix}:responses"

    def _get_dlq_stream(self, agent_id: str) -> str:
        """Get the dead-letter queue stream name for an agent."""
        return f"{self._config.stream_prefix}:dlq:{agent_id}"
    
    async def _ensure_consumer_group(self, stream_name: str) -> None:
        """Create consumer group if it doesn't exist."""
        try:
            await self._redis.xgroup_create(
                stream_name,
                self._config.consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info("consumer_group_created", stream=stream_name)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            # Group already exists, which is fine
    
    def register(self, agent_id: str, handler: MessageHandler) -> None:
        """
        Register a message handler for an agent.
        
        Args:
            agent_id: The agent identifier (e.g., "teacher", "student")
            handler: Async function that processes messages and returns optional response
        """
        self._handlers[agent_id] = handler
        logger.info("distributed_handler_registered", agent_id=agent_id)
    
    def unregister(self, agent_id: str) -> None:
        """Remove an agent handler."""
        if agent_id in self._handlers:
            del self._handlers[agent_id]
            logger.info("distributed_handler_unregistered", agent_id=agent_id)
    
    async def dispatch(
        self,
        msg: A2AMessage,
        wait_response: bool = False,
        timeout_ms: Optional[int] = None,
    ) -> Optional[A2AMessage]:
        """
        Dispatch a message to an agent's stream.
        
        Args:
            msg: The A2AMessage to dispatch
            wait_response: If True, wait for a response message
            timeout_ms: Custom timeout for response (default: config.response_timeout_ms)
            
        Returns:
            Response message if wait_response=True, else None
        """
        if not self._redis:
            raise RuntimeError("Dispatcher not connected")
        
        stream_name = self._get_stream_name(msg.recipient_id)
        payload = self._serialize(msg)
        
        # Add message to recipient's stream
        entry_id = await self._redis.xadd(stream_name, {"data": payload})
        
        logger.info(
            "distributed_message_dispatched",
            message_id=str(msg.id),
            recipient=msg.recipient_id,
            stream=stream_name,
            entry_id=entry_id,
        )
        
        if not wait_response:
            return None
        
        # Wait for response on response stream
        return await self._wait_for_response(
            msg.id,
            timeout_ms or self._config.response_timeout_ms,
        )
    
    async def _wait_for_response(
        self,
        correlation_id: UUID,
        timeout_ms: int,
    ) -> Optional[A2AMessage]:
        """Wait for a response message with matching correlation_id."""
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[str(correlation_id)] = future
        
        try:
            return await asyncio.wait_for(
                future,
                timeout=timeout_ms / 1000.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "response_timeout",
                correlation_id=str(correlation_id),
                timeout_ms=timeout_ms,
            )
            return None
        finally:
            self._pending_responses.pop(str(correlation_id), None)
    
    async def _publish_response(self, msg: A2AMessage) -> None:
        """Publish a response message."""
        if not self._redis:
            return
        
        stream_name = self._get_response_stream()
        payload = self._serialize(msg)
        
        await self._redis.xadd(
            stream_name,
            {"data": payload},
            maxlen=10000,  # Keep last 10k responses
        )
        
        # Also check local pending responses
        correlation_key = str(msg.correlation_id) if msg.correlation_id else None
        if correlation_key and correlation_key in self._pending_responses:
            self._pending_responses[correlation_key].set_result(msg)
    
    async def start_consuming(
        self,
        agent_id: str,
        stop_on_error: bool = False,
    ) -> None:
        """
        Start consuming messages for an agent.
        
        This runs in an infinite loop until stop() is called or an error occurs.
        
        Args:
            agent_id: The agent to consume messages for
            stop_on_error: If True, stop on first processing error
        """
        handler = self._handlers.get(agent_id)
        if not handler:
            raise ValueError(f"No handler registered for agent: {agent_id}")
        
        if not self._redis:
            raise RuntimeError("Dispatcher not connected")
        
        stream_name = self._get_stream_name(agent_id)
        await self._ensure_consumer_group(stream_name)
        
        self._running = True
        logger.info(
            "distributed_consumer_started",
            agent_id=agent_id,
            stream=stream_name,
            consumer_id=self._consumer_id,
        )
        
        # First, process any pending messages (from previous crashes)
        await self._process_pending(agent_id, stream_name, handler)
        
        # Start background autoclaim task
        autoclaim_task = asyncio.create_task(
            self._autoclaim_loop(agent_id, stream_name, handler)
        )
        
        # Then consume new messages
        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    self._config.consumer_group,
                    self._consumer_id,
                    {stream_name: ">"},
                    count=10,
                    block=self._config.block_ms,
                )
                
                if not messages:
                    continue
                
                for stream, entries in messages:
                    for entry_id, data in entries:
                        await self._process_entry(
                            agent_id,
                            stream_name,
                            entry_id,
                            data,
                            handler,
                        )
                
            except asyncio.CancelledError:
                logger.info("consumer_cancelled", agent_id=agent_id)
                break
            except Exception as e:
                logger.error(
                    "consumer_error",
                    agent_id=agent_id,
                    error=str(e),
                )
                if stop_on_error:
                    raise
                await asyncio.sleep(1)  # Brief pause before retry
        
        # Stop autoclaim task
        autoclaim_task.cancel()
        try:
            await autoclaim_task
        except asyncio.CancelledError:
            pass
            
        logger.info("distributed_consumer_stopped", agent_id=agent_id)
    
    async def _autoclaim_loop(
        self,
        agent_id: str,
        stream_name: str,
        handler: MessageHandler,
    ) -> None:
        """Background loop to claim pending messages from dead consumers."""
        while self._running:
            try:
                # Sleep first to avoid hammering Redis
                await asyncio.sleep(self._config.claim_min_idle_ms / 1000.0)
                
                # claim_min_idle_ms is used as the idle time threshold
                # 0-0 means start from the beginning
                # count=10 items at a time
                result = await self._redis.xautoclaim(
                    stream_name,
                    self._config.consumer_group,
                    self._consumer_id,
                    self._config.claim_min_idle_ms,
                    start_id="0-0",
                    count=10,
                )
                
                # xautoclaim returns: (start_id, messages, deleted_ids)
                # In newer redis-py: [start_id, messages, deleted_ids]
                messages = result[1]
                
                if messages:
                    logger.info(
                        "messages_autoclaimed",
                        agent_id=agent_id,
                        count=len(messages),
                    )
                    
                    for entry_id, data in messages:
                        if data:
                            await self._process_entry(
                                agent_id,
                                stream_name,
                                entry_id,
                                data,
                                handler,
                            )
                        else:
                            # Ack empty entries
                            await self._redis.xack(stream_name, self._config.consumer_group, entry_id)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "autoclaim_error",
                    agent_id=agent_id,
                    error=str(e),
                )
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_pending(
        self,
        agent_id: str,
        stream_name: str,
        handler: MessageHandler,
    ) -> None:
        """Process messages that were claimed but not acknowledged."""
        try:
            # Read pending messages for this consumer
            pending = await self._redis.xreadgroup(
                self._config.consumer_group,
                self._consumer_id,
                {stream_name: "0"},  # Read from beginning of PEL
                count=100,
            )
            
            if not pending:
                return
            
            for stream, entries in pending:
                for entry_id, data in entries:
                    if data:  # Might be None if already processed
                        await self._process_entry(
                            agent_id,
                            stream_name,
                            entry_id,
                            data,
                            handler,
                        )
                    else:
                        # Acknowledge empty entries
                        await self._redis.xack(stream_name, self._config.consumer_group, entry_id)
            
            logger.info(
                "pending_messages_processed",
                agent_id=agent_id,
                count=sum(len(entries) for _, entries in pending),
            )
        except Exception as e:
            logger.error("pending_processing_error", agent_id=agent_id, error=str(e))
    
    async def _get_delivery_count(
        self,
        stream_name: str,
        entry_id: str,
    ) -> int:
        """Get the number of times a message has been delivered (from Redis PEL)."""
        try:
            pending = await self._redis.xpending_range(
                stream_name,
                self._config.consumer_group,
                min=entry_id,
                max=entry_id,
                count=1,
            )
            if pending:
                # Each entry is a dict with 'times_delivered' (or index-based tuple)
                entry = pending[0]
                if isinstance(entry, dict):
                    return entry.get("times_delivered", 1)
                # redis-py returns a list of dicts with 'times_delivered'
                return 1
        except Exception as e:
            logger.warning(
                "delivery_count_lookup_failed",
                stream=stream_name,
                entry_id=entry_id,
                error=str(e),
            )
        return 1

    async def _move_to_dlq(
        self,
        agent_id: str,
        stream_name: str,
        entry_id: str,
        data: Dict[str, str],
        error: str,
    ) -> None:
        """Move a message to the dead-letter queue and ACK the original."""
        dlq_stream = self._get_dlq_stream(agent_id)

        await self._redis.xadd(dlq_stream, {
            "data": data.get("data", "{}"),
            "original_stream": stream_name,
            "original_entry_id": entry_id,
            "error": error,
            "moved_at": datetime.utcnow().isoformat(),
        })

        # ACK the original so it leaves the PEL
        await self._redis.xack(stream_name, self._config.consumer_group, entry_id)

        logger.warning(
            "message_moved_to_dlq",
            agent_id=agent_id,
            entry_id=entry_id,
            dlq_stream=dlq_stream,
            error=error,
        )

    async def _process_entry(
        self,
        agent_id: str,
        stream_name: str,
        entry_id: str,
        data: Dict[str, str],
        handler: MessageHandler,
    ) -> None:
        """Process a single stream entry."""
        try:
            msg = self._deserialize(data.get("data", "{}"))

            logger.debug(
                "processing_message",
                agent_id=agent_id,
                message_id=str(msg.id),
                entry_id=entry_id,
            )

            # Call handler
            response = await handler(msg)

            # Acknowledge successful processing
            await self._redis.xack(stream_name, self._config.consumer_group, entry_id)

            # Publish response if any
            if response:
                await self._publish_response(response)

            logger.info(
                "message_processed",
                agent_id=agent_id,
                message_id=str(msg.id),
                has_response=response is not None,
            )

        except Exception as e:
            logger.error(
                "message_processing_error",
                agent_id=agent_id,
                entry_id=entry_id,
                error=str(e),
            )
            # Check delivery count — move to DLQ if max retries exceeded
            delivery_count = await self._get_delivery_count(stream_name, entry_id)
            if delivery_count >= self._config.max_retries:
                await self._move_to_dlq(agent_id, stream_name, entry_id, data, str(e))
            # Otherwise leave unacknowledged for retry

    async def get_dlq_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about an agent's dead-letter queue stream."""
        if not self._redis:
            return {}

        dlq_stream = self._get_dlq_stream(agent_id)
        try:
            info = await self._redis.xinfo_stream(dlq_stream)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except redis.ResponseError:
            return {"length": 0, "exists": False}

    async def reprocess_dlq(
        self,
        agent_id: str,
        count: int = 10,
    ) -> int:
        """
        Move messages from the DLQ back to the agent's main stream for retry.

        Returns the number of messages requeued.
        """
        if not self._redis:
            return 0

        dlq_stream = self._get_dlq_stream(agent_id)
        main_stream = self._get_stream_name(agent_id)

        # Read oldest entries from DLQ
        entries = await self._redis.xrange(dlq_stream, count=count)
        requeued = 0
        for entry_id, fields in entries:
            payload = fields.get("data")
            if payload:
                await self._redis.xadd(main_stream, {"data": payload})
                await self._redis.xdel(dlq_stream, entry_id)
                requeued += 1

        if requeued:
            logger.info(
                "dlq_messages_reprocessed",
                agent_id=agent_id,
                count=requeued,
            )
        return requeued

    def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False
    
    def _serialize(self, msg: A2AMessage) -> str:
        """Serialize A2AMessage to JSON string."""
        return json.dumps({
            "id": str(msg.id),
            "type": msg.type.value,
            "sender_id": str(msg.sender_id),
            "recipient_id": str(msg.recipient_id),
            "content": self._serialize_content(msg.content),
            "correlation_id": str(msg.correlation_id) if msg.correlation_id else None,
            "metadata": msg.metadata,
            "created_at": msg.created_at.isoformat(),
        })
    
    def _serialize_content(self, content: Any) -> Any:
        """Serialize message content, handling Pydantic models."""
        if hasattr(content, "model_dump"):
            return content.model_dump()
        return content
    
    def _deserialize(self, data: str) -> A2AMessage:
        """Deserialize JSON string to A2AMessage."""
        d = json.loads(data)
        return A2AMessage(
            id=UUID(d["id"]) if d.get("id") else uuid4(),
            type=MessageType(d["type"]),
            sender_id=d["sender_id"],
            recipient_id=d["recipient_id"],
            content=d.get("content", ""),
            correlation_id=UUID(d["correlation_id"]) if d.get("correlation_id") else None,
            metadata=d.get("metadata", {}),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.utcnow(),
        )
    
    # === Utility Methods ===
    
    async def get_stream_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about an agent's stream."""
        if not self._redis:
            return {}
        
        stream_name = self._get_stream_name(agent_id)
        
        try:
            info = await self._redis.xinfo_stream(stream_name)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except redis.ResponseError:
            return {"length": 0, "exists": False}
    
    async def get_pending_count(self, agent_id: str) -> int:
        """Get count of pending messages for an agent."""
        if not self._redis:
            return 0
        
        stream_name = self._get_stream_name(agent_id)
        
        try:
            pending = await self._redis.xpending(stream_name, self._config.consumer_group)
            return pending.get("pending", 0) if pending else 0
        except redis.ResponseError:
            return 0
    
    async def cleanup_old_messages(
        self,
        agent_id: str,
        max_age_seconds: int = 86400,  # 24 hours
    ) -> int:
        """Remove messages older than max_age from stream."""
        if not self._redis:
            return 0
        
        stream_name = self._get_stream_name(agent_id)
        cutoff = int((datetime.utcnow().timestamp() - max_age_seconds) * 1000)
        
        # XTRIM with MINID removes entries older than the given ID
        deleted = await self._redis.xtrim(
            stream_name,
            minid=f"{cutoff}-0",
        )
        
        logger.info(
            "stream_cleaned",
            agent_id=agent_id,
            deleted_count=deleted,
        )
        
        return deleted


# === Factory Functions ===

async def create_distributed_dispatcher(
    redis_url: str = "redis://localhost:6379",
    **config_kwargs,
) -> DistributedDispatcher:
    """
    Create and connect a distributed dispatcher.
    
    Usage:
        dispatcher = await create_distributed_dispatcher("redis://localhost:6379")
        dispatcher.register("teacher", teacher_handler)
        await dispatcher.start_consuming("teacher")
    """
    config = DistributedDispatcherConfig(**config_kwargs)
    dispatcher = DistributedDispatcher(redis_url=redis_url, config=config)
    await dispatcher.connect()
    return dispatcher
