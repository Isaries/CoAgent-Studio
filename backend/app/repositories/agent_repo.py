from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.availability_checker import check_agent_availability
from app.core.cache import cache
from app.core.scheduler_utils import is_agent_scheduled_now
from app.models.agent_config import AgentConfig, AgentType
from app.models.agent_room_state import AgentRoomState
from app.models.message import Message
from app.models.room import RoomAgentLink


class AgentConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_configs(
        self, room_id: UUID
    ) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
        """
        Get active Teacher and Student configs for a room via RoomAgentLink, utilizing 60s cache.
        """
        # Try Cache
        cache_key = f"configs:room:{room_id}"
        cached_data = await cache.get_json(cache_key)

        t_conf = None
        s_conf = None

        if cached_data:
            # Reconstruct from dict
            t_conf = AgentConfig(**cached_data["teacher"]) if cached_data.get("teacher") else None
            s_conf = AgentConfig(**cached_data["student"]) if cached_data.get("student") else None
        else:
            # DB Query
            query: Any = (
                select(AgentConfig)
                .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
                .where(RoomAgentLink.room_id == room_id)
                .order_by(col(AgentConfig.updated_at).desc())
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

        # Check three-layer availability (API Key > Agent > Room)
        if t_conf and not await check_agent_availability(self.session, t_conf, room_id):
            t_conf = None
        if s_conf and not await check_agent_availability(self.session, s_conf, room_id):
            s_conf = None

        return t_conf, s_conf

    async def get_external_configs(self, room_id: UUID) -> list[AgentConfig]:
        """
        Get all active external agent configs for a room.
        External agents can participate in multi-agent conversations.
        """
        cache_key = f"external_configs:room:{room_id}"
        cached_data = await cache.get_json(cache_key)
        
        if cached_data:
            return [AgentConfig(**c) for c in cached_data]
        
        query: Any = (
            select(AgentConfig)
            .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
            .where(
                RoomAgentLink.room_id == room_id,
                AgentConfig.is_external == True,
                AgentConfig.is_active == True,
            )
        )
        result = await self.session.exec(query)
        configs = list(result.all())
        
        # Cache for 60s
        await cache.set_json(cache_key, [c.model_dump() for c in configs], ttl=60)
        
        return configs

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
        last_msg_query: Any = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(col(Message.created_at).desc())
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
                .order_by(col(Message.created_at).desc())
                .limit(1)
            )
        ).first()
        t_since = (datetime.utcnow() - t_last.created_at).total_seconds() if t_last else 999999.0

        # Last Student
        s_last = (
            await self.session.exec(
                select(Message)
                .where(Message.room_id == room_id, Message.agent_type == AgentType.STUDENT)
                .order_by(col(Message.created_at).desc())
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
        query: Any = (
            select(Message)
            .where(Message.room_id == room_id)
            .where(col(Message.agent_type).isnot(None))
            .order_by(col(Message.created_at).desc())
            .limit(1)
        )
        result = await self.session.exec(query)
        last_agent_msg = result.first()

        count_query = (
            select(col(Message.id))
            .where(Message.room_id == room_id)
            .where(col(Message.agent_type).is_(None))
        )
        if last_agent_msg:
            count_query = count_query.where(Message.created_at > last_agent_msg.created_at)

        results = await self.session.exec(count_query)
        return len(results.all())

    async def get_history(self, room_id: UUID, limit: int = 10) -> list[Message]:
        hist_query: Any = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(col(Message.created_at).desc())
            .limit(limit)
        )
        hist_result = await self.session.exec(hist_query)
        return list(reversed(hist_result.all()))

    async def get_or_create_state(self, room_id: UUID, agent_id: UUID) -> AgentRoomState:
        """Get or create the runtime state for an agent in a room."""
        result = await self.session.exec(
            select(AgentRoomState).where(
                AgentRoomState.room_id == room_id,
                AgentRoomState.agent_id == agent_id,
            )
        )
        state = result.first()
        if not state:
            state = AgentRoomState(room_id=room_id, agent_id=agent_id)
            self.session.add(state)
            await self.session.flush()
        return state

    async def get_room_agent_link(self, room_id: UUID, agent_id: UUID) -> Optional[RoomAgentLink]:
        """Get the RoomAgentLink for a specific room+agent pair."""
        result = await self.session.exec(
            select(RoomAgentLink).where(
                RoomAgentLink.room_id == room_id,
                RoomAgentLink.agent_id == agent_id,
            )
        )
        return result.first()
