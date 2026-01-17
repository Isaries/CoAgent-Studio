from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.cache import cache
from app.core.scheduler_utils import is_agent_scheduled_now
from app.models.agent_config import AgentConfig, AgentType
from app.models.message import Message


class AgentConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_configs(
        self, course_id: UUID
    ) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
        """
        Get active Teacher and Student configs for a course, utilizing 60s cache.
        """
        # Try Cache
        cache_key = f"configs:course:{course_id}"
        cached_data = await cache.get_json(cache_key)

        t_conf = None
        s_conf = None

        if cached_data:
            # Reconstruct from dict
            t_conf = AgentConfig(**cached_data["teacher"]) if cached_data.get("teacher") else None
            s_conf = AgentConfig(**cached_data["student"]) if cached_data.get("student") else None
        else:
            # DB Query
            query = (
                select(AgentConfig)
                .where(AgentConfig.course_id == course_id)
                .order_by(AgentConfig.updated_at.desc())
            )
            result = await self.session.exec(query)
            configs = result.all()

            teacher_config = next(
                (c for c in configs if c.type == AgentType.TEACHER and c.is_active), None
            )
            if not teacher_config:
                teacher_config = next((c for c in configs if c.type == AgentType.TEACHER), None)

            student_config = next(
                (c for c in configs if c.type == AgentType.STUDENT and c.is_active), None
            )
            if not student_config:
                student_config = next((c for c in configs if c.type == AgentType.STUDENT), None)

            # Set Cache (TTL 60s)
            to_cache = {
                "teacher": teacher_config.model_dump() if teacher_config else None,
                "student": student_config.model_dump() if student_config else None,
            }
            await cache.set_json(cache_key, to_cache, ttl=60)

            t_conf = teacher_config
            s_conf = student_config

        # Check schedules (Always run this, time changes)
        if t_conf and not is_agent_scheduled_now(t_conf):
            t_conf = None
        if s_conf and not is_agent_scheduled_now(s_conf):
            s_conf = None

        return t_conf, s_conf

    async def get_time_context(self, room_id: UUID) -> Tuple[float, float, float]:
        """
        Get silence duration and time since last agent messages. Cached for 5s.
        """
        # Cache Context for short duration (e.g. 5s)
        cache_key = f"context:room:{room_id}"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached["silence"], cached["t_since"], cached["s_since"]

        # Last User Message (for Silence)
        last_msg_query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = (await self.session.exec(last_msg_query)).first()

        silence_duration = 999999.0
        if last_msg and last_msg.created_at:
            try:
                silence_duration = (datetime.utcnow() - last_msg.created_at).total_seconds()
            except Exception:
                # Fallback for TZ mixup
                silence_duration = (
                    datetime.utcnow() - last_msg.created_at.replace(tzinfo=None)
                ).total_seconds()

        # Last Teacher
        t_last = (
            await self.session.exec(
                select(Message)
                .where(Message.room_id == room_id, Message.agent_type == AgentType.TEACHER)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).first()
        t_since = (datetime.utcnow() - t_last.created_at).total_seconds() if t_last else 999999.0

        # Last Student
        s_last = (
            await self.session.exec(
                select(Message)
                .where(Message.room_id == room_id, Message.agent_type == AgentType.STUDENT)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).first()
        s_since = (datetime.utcnow() - s_last.created_at).total_seconds() if s_last else 999999.0

        # Store in Cache
        await cache.set_json(
            cache_key, {"silence": silence_duration, "t_since": t_since, "s_since": s_since}, ttl=5
        )

        return silence_duration, t_since, s_since

    async def get_message_count_gap(self, room_id: UUID) -> int:
        """Count user messages since the last Agent message."""
        query = (
            select(Message)
            .where(Message.room_id == room_id)
            .where(Message.agent_type.isnot(None))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        result = await self.session.exec(query)
        last_agent_msg = result.first()

        count_query = (
            select(col(Message.id))
            .where(Message.room_id == room_id)
            .where(Message.agent_type.is_(None))
        )
        if last_agent_msg:
            count_query = count_query.where(Message.created_at > last_agent_msg.created_at)

        results = await self.session.exec(count_query)
        return len(results.all())

    async def get_history(self, room_id: UUID, limit: int = 10) -> list[Message]:
        hist_query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        hist_result = await self.session.exec(hist_query)
        return list(reversed(hist_result.all()))
