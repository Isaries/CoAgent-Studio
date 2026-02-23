"""
Three-layer availability checker.

Checks in order: API Key > Agent > RoomAgentLink.
If any layer blocks, the agent is not allowed to run.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.scheduler_utils import is_schedule_allowed_now
from app.models.agent_config import AgentConfig
from app.models.room import RoomAgentLink
from app.models.user_api_key import UserAPIKey


async def check_agent_availability(
    session: AsyncSession,
    agent_config: AgentConfig,
    room_id: UUID,
) -> bool:
    """
    Three-layer availability check: API Key > Agent > RoomAgentLink.
    Returns True only if ALL layers pass.
    """
    # --- Layer 3 (lowest priority): RoomAgentLink ---
    link = await _get_room_agent_link(session, room_id, agent_config.id)
    if link:
        if not link.is_active:
            return False
        if not is_schedule_allowed_now(link.schedule_config):
            return False

    # --- Layer 2: AgentConfig ---
    if not agent_config.is_active:
        return False
    if not is_schedule_allowed_now(agent_config.schedule_config):
        return False

    # --- Layer 1 (highest priority): UserAPIKey ---
    if agent_config.user_key_ids:
        has_valid_key = False
        for key_id in agent_config.user_key_ids:
            api_key = await session.get(UserAPIKey, key_id)
            if api_key:
                if api_key.is_active and is_schedule_allowed_now(api_key.schedule_config):
                    has_valid_key = True
                    break
        if not has_valid_key:
            return False

    return True


async def _get_room_agent_link(
    session: AsyncSession, room_id: UUID, agent_id: UUID
) -> Optional[RoomAgentLink]:
    """Fetch the RoomAgentLink for a specific room+agent pair."""
    result = await session.exec(
        select(RoomAgentLink).where(
            RoomAgentLink.room_id == room_id,
            RoomAgentLink.agent_id == agent_id,
        )
    )
    return result.first()
