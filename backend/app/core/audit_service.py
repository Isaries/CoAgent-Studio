"""
Audit service for logging all configuration changes.

Provides a simple interface to record who changed what, when,
with old and new values for full traceability.
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.audit_log import AuditLog

logger = structlog.get_logger()


async def log_change(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: Optional[UUID] = None,
    actor_type: str = "user",
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Record a configuration change in the audit log.

    Args:
        entity_type: "api_key", "agent", "room_agent_link", "agent_room_state"
        entity_id: UUID string of the modified entity
        action: "update_schedule", "update_trigger", "toggle_active",
                "sync_to_course", "agent_self_modify", "reset_state"
        actor_id: UUID of the user who made the change (None if system/agent)
        actor_type: "user", "agent", "system"
        old_value: Previous state (JSONB)
        new_value: New state (JSONB)
        metadata: Extra context (e.g., room_id, agent_name)
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        old_value=old_value,
        new_value=new_value,
        extra_metadata=metadata,
    )
    session.add(entry)

    logger.info(
        "audit_log",
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_type=actor_type,
    )

    return entry
