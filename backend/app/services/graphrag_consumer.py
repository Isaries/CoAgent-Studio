"""
GraphRAG Stream Consumer — Listens to Redis Stream for incremental graph updates.

Runs as a background asyncio task inside the ARQ worker.
When new messages or artifacts are published to `graphrag:events`,
it debounces events per room and triggers incremental entity extraction.
"""

import asyncio
import time
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

STREAM_KEY = "graphrag:events"
GROUP_NAME = "graphrag_workers"
CONSUMER_NAME = "worker_0"
DEBOUNCE_SECONDS = 10  # Wait 10s of silence per room before processing


class GraphRAGConsumer:
    """
    Redis Stream consumer that triggers incremental graph extraction.

    Uses a consumer group for reliable delivery.  Events are debounced
    per room_id so that a burst of messages only triggers one extraction.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    # ── Redis-backed pending room tracking ──────────────────────────

    async def _get_pending(self, room_id: str) -> Optional[float]:
        """Get the last event timestamp for a pending room from Redis."""
        assert self._redis is not None
        val = await self._redis.hget("graphrag:pending_rooms", room_id)
        return float(val) if val else None

    async def _set_pending(self, room_id: str) -> None:
        """Set the pending timestamp for a room in Redis."""
        assert self._redis is not None
        await self._redis.hset("graphrag:pending_rooms", room_id, str(time.time()))

    async def _remove_pending(self, room_id: str) -> None:
        """Remove a room from the pending set in Redis."""
        assert self._redis is not None
        await self._redis.hdel("graphrag:pending_rooms", room_id)

    async def _get_all_pending(self) -> Dict[str, float]:
        """Get all pending rooms and their timestamps from Redis."""
        assert self._redis is not None
        raw = await self._redis.hgetall("graphrag:pending_rooms")
        return {k: float(v) for k, v in raw.items()} if raw else {}

    async def start(self, worker_ctx: Dict[str, Any]) -> None:
        """Start the consumer loop as a background task."""
        self._redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            decode_responses=True,
        )

        # Create consumer group (ignore if already exists)
        try:
            await self._redis.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        self._running = True
        self._task = asyncio.create_task(self._consume_loop(worker_ctx))
        logger.info("graphrag_consumer_started")

    async def stop(self) -> None:
        """Stop the consumer loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
        logger.info("graphrag_consumer_stopped")

    async def _consume_loop(self, ctx: Dict[str, Any]) -> None:
        """
        Main loop: read events from Redis Stream, debounce per room,
        and trigger extraction when a room goes quiet.
        """
        assert self._redis is not None

        while self._running:
            try:
                # Read new messages (block for 2s max)
                results = await self._redis.xreadgroup(
                    GROUP_NAME,
                    CONSUMER_NAME,
                    {STREAM_KEY: ">"},
                    count=50,
                    block=2000,
                )

                now = time.time()

                if results:
                    for _stream, messages in results:
                        for msg_id, data in messages:
                            room_id = data.get("room_id", "")
                            if room_id:
                                await self._set_pending(room_id)
                                logger.debug(
                                    "graphrag_event_received",
                                    room_id=room_id,
                                    event_type=data.get("type"),
                                )
                            # ACK immediately
                            await self._redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

                # Check for rooms that have been quiet long enough
                pending = await self._get_all_pending()
                rooms_to_process = [
                    rid for rid, ts in pending.items() if now - ts >= DEBOUNCE_SECONDS
                ]

                for room_id in rooms_to_process:
                    await self._remove_pending(room_id)
                    asyncio.create_task(self._trigger_extraction(ctx, room_id))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("graphrag_consumer_error", error=str(e))
                await asyncio.sleep(5)  # Back off on errors

    async def _trigger_extraction(self, ctx: Dict[str, Any], room_id: str) -> None:
        """Trigger incremental entity extraction for a room (if GraphRAG is enabled)."""
        try:
            from app.models.room import Room
            from app.services.graphrag_service import extract_entities_task

            # ── Gate: check if GraphRAG is enabled for this room ──
            session_factory = ctx["session_factory"]
            async with session_factory() as session:
                room = await session.get(Room, room_id)
                if not room:
                    logger.warning("graphrag_room_not_found", room_id=room_id)
                    return
                if not room.graphrag_enabled:
                    logger.debug("graphrag_disabled_skip", room_id=room_id)
                    return
                extraction_model = room.graphrag_extraction_model

            logger.info("graphrag_incremental_start", room_id=room_id, model=extraction_model)
            result = await extract_entities_task(ctx, room_id, extraction_model=extraction_model)
            logger.info("graphrag_incremental_complete", room_id=room_id, result=result)
        except Exception as e:
            logger.error("graphrag_incremental_failed", room_id=room_id, error=str(e))


# Module-level singleton
graphrag_consumer = GraphRAGConsumer()
