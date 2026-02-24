"""
Trigger Dispatcher Service.

Provides the ``TriggerDispatcher`` class for evaluating ``TriggerPolicy``
records and initiating workflow executions, plus ARQ worker task functions.
"""

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.trigger import TriggerPolicy
from app.models.room import Room
from app.services.execution.agent_execution_service import execute_workflow

logger = structlog.get_logger()


class TriggerDispatcher:
    """
    Central dispatcher for evaluating TriggerPolicies and initiating WorkflowRuns.

    Supports two modes:
    - **Event-Driven**: Called synchronously when an event occurs (e.g. user_message).
    - **Time-Driven**: Called periodically by an ARQ cron job for timer/silence policies.
    """

    def __init__(self, session: AsyncSession, redis=None):
        self.session = session
        self.redis = redis

    async def resolve_matching_workflows(
        self, event_type: str, session_id: str, payload: dict
    ) -> List[UUID]:
        """
        Find all TriggerPolicies matching the given event and return their
        ``target_workflow_id``s.  Falls back to Room.attached_workflow_id
        for backward compatibility if no explicit policies exist.
        """
        stmt = select(TriggerPolicy).where(
            TriggerPolicy.event_type == event_type,
            TriggerPolicy.is_active == True,  # noqa: E712
        )
        result = await self.session.exec(stmt)
        policies = result.all()

        matched_workflow_ids: List[UUID] = []

        if not policies:
            # Legacy fallback: Room.attached_workflow_id
            if event_type == "user_message":
                try:
                    r_uuid = UUID(session_id)
                    room = await self.session.get(Room, r_uuid)
                    if room and room.attached_workflow_id:
                        logger.info("legacy_workflow_trigger_fallback", room_id=session_id)
                        matched_workflow_ids.append(room.attached_workflow_id)
                except (ValueError, AttributeError):
                    pass
            return matched_workflow_ids

        for policy in policies:
            # Scope check
            if policy.scope_session_id and policy.scope_session_id != session_id:
                continue

            # Condition evaluation
            if not self._evaluate_conditions(policy.conditions, payload):
                continue

            # Debounce lock
            if await self._is_locked(policy.id, session_id):
                logger.debug("trigger_debounced", trigger_id=str(policy.id), session_id=session_id)
                continue

            logger.info("trigger_matched", trigger_id=str(policy.id), workflow_id=str(policy.target_workflow_id))
            matched_workflow_ids.append(policy.target_workflow_id)

        return matched_workflow_ids

    async def evaluate_time_triggers(self, arq_pool=None) -> None:
        """
        Evaluate Time/State-Driven policies (timer, cron, silence).
        Called by the ARQ cron job every minute.
        """
        logger.info("evaluate_time_triggers_started")

        stmt = select(TriggerPolicy).where(
            TriggerPolicy.event_type.in_(["timer", "cron", "silence"]),
            TriggerPolicy.is_active == True,  # noqa: E712
        )
        result = await self.session.exec(stmt)
        policies = result.all()

        if not policies:
            return

        now = time.time()

        for policy in policies:
            session_id = policy.scope_session_id

            if policy.event_type == "silence":
                sessions_to_check = (
                    [session_id] if session_id
                    else await self._get_all_active_sessions()
                )

                threshold_mins = policy.conditions.get("threshold_mins", 5)
                lock_secs = max(int(threshold_mins * 60) // 2, 30)

                for sid in sessions_to_check:
                    if not sid:
                        continue
                    last_activity = await self._get_last_activity(sid)
                    if last_activity is None:
                        continue

                    silent_mins = (now - last_activity) / 60.0
                    if silent_mins >= threshold_mins:
                        if not await self._is_locked(policy.id, sid, lock_time=lock_secs):
                            logger.info("silence_trigger_fired", session_id=sid, duration=round(silent_mins, 1))
                            if arq_pool:
                                await arq_pool.enqueue_job(
                                    "run_workflow_task",
                                    str(policy.target_workflow_id),
                                    sid,
                                    {"type": "silence", "silent_mins": round(silent_mins, 1)},
                                )
                            else:
                                await execute_workflow(
                                    self.session, self.redis,
                                    policy.target_workflow_id, sid,
                                    {"type": "silence", "silent_mins": round(silent_mins, 1)},
                                )

            elif policy.event_type in ("timer", "cron"):
                interval_mins = policy.conditions.get("interval_mins")
                if not interval_mins:
                    continue

                sid = session_id or "global"
                lock_secs = max(int(interval_mins * 60) - 5, 30)

                if not await self._is_locked(policy.id, sid, lock_time=lock_secs):
                    logger.info("timer_trigger_fired", trigger_id=str(policy.id))
                    if arq_pool:
                        await arq_pool.enqueue_job(
                            "run_workflow_task",
                            str(policy.target_workflow_id),
                            sid,
                            {"type": "timer"},
                        )
                    else:
                        await execute_workflow(
                            self.session, self.redis,
                            policy.target_workflow_id, sid,
                            {"type": "timer"},
                        )

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _evaluate_conditions(self, conditions: dict, payload: dict) -> bool:
        """Simple condition matching (extensible for future use)."""
        keyword = conditions.get("keyword")
        if keyword and "content" in payload:
            if keyword.lower() not in payload["content"].lower():
                return False
        return True

    async def _is_locked(self, policy_id: UUID, session_id: str, lock_time: int = 10) -> bool:
        """Redis SETNX-based debounce lock."""
        if not self.redis:
            return False

        key = f"trigger_lock:{policy_id}:{session_id}"
        acquired = await self.redis.setnx(key, "locked")
        if acquired:
            await self.redis.expire(key, lock_time)
            return False  # Lock was free → NOT locked
        return True  # Lock already held → IS locked

    async def _get_last_activity(self, session_id: str) -> Optional[float]:
        if not self.redis:
            return None
        val = await self.redis.get(f"room_activity:{session_id}")
        if val:
            return float(val if isinstance(val, (str, int, float)) else val.decode("utf-8"))
        return None

    async def _get_all_active_sessions(self) -> List[str]:
        """Scan Redis for all rooms with recent activity."""
        if not self.redis:
            return []
        keys = await self.redis.keys("room_activity:*")
        sessions = []
        for k in keys:
            key_str = k.decode("utf-8") if isinstance(k, bytes) else k
            sid = key_str.split(":", 1)[-1]
            if sid:
                sessions.append(sid)
        return sessions


# ===================================================================
# ARQ Worker Tasks
# ===================================================================

async def dispatch_event_task(ctx: dict, event_type: str, session_id: str, payload: dict) -> None:
    """
    ARQ task: evaluate event-driven trigger policies and execute matched
    workflows directly (no re-enqueueing needed since we're already in the worker).
    """
    session_factory = ctx.get("session_factory")
    if not session_factory:
        logger.error("dispatch_event_task: no session_factory in ctx")
        return

    async with session_factory() as session:
        redis = ctx.get("redis")
        dispatcher = TriggerDispatcher(session, redis)

        matched_workflow_ids = await dispatcher.resolve_matching_workflows(
            event_type, session_id, payload
        )

        for wf_id in matched_workflow_ids:
            logger.info("trigger_executing_workflow", workflow_id=str(wf_id), session_id=session_id)
            try:
                await execute_workflow(session, redis, wf_id, session_id, payload)
            except Exception as e:
                logger.error("trigger_workflow_execution_failed", workflow_id=str(wf_id), error=str(e))


async def run_workflow_task(ctx: dict, workflow_id: str, session_id: str, payload: dict) -> None:
    """ARQ task: execute a single workflow by ID."""
    session_factory = ctx.get("session_factory")
    if not session_factory:
        logger.error("run_workflow_task: no session_factory in ctx")
        return

    async with session_factory() as session:
        redis = ctx.get("redis")
        try:
            await execute_workflow(session, redis, UUID(workflow_id), session_id, payload)
        except Exception as e:
            logger.error("run_workflow_task_failed", workflow_id=workflow_id, error=str(e))


async def evaluate_time_triggers_cron(ctx: dict) -> None:
    """ARQ cron task (every minute): evaluate timer/silence trigger policies."""
    session_factory = ctx.get("session_factory")
    if not session_factory:
        return

    async with session_factory() as session:
        redis = ctx.get("redis")

        # Create a temporary ARQ pool for enqueueing follow-up jobs
        from arq import create_pool
        from arq.connections import RedisSettings
        from app.core.config import settings

        try:
            arq_pool = await create_pool(
                RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            )
        except Exception as e:
            logger.error("evaluate_time_triggers_cron: failed to create arq pool", error=str(e))
            # Fall back to direct execution (no pool)
            dispatcher = TriggerDispatcher(session, redis)
            await dispatcher.evaluate_time_triggers(arq_pool=None)
            return

        try:
            dispatcher = TriggerDispatcher(session, redis)
            await dispatcher.evaluate_time_triggers(arq_pool=arq_pool)
        finally:
            await arq_pool.close()
