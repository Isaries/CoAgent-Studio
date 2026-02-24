"""
Trigger Policy API Endpoints.

CRUD for ``TriggerPolicy`` – the event-driven rules that determine
when a specific Workflow should be activated.
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_session
from app.models.trigger import (
    TriggerPolicy,
    TriggerPolicyCreate,
    TriggerPolicyRead,
    TriggerPolicyUpdate,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get(
    "/triggers",
    response_model=List[TriggerPolicyRead],
    summary="List all trigger policies",
)
async def list_triggers(
    session: AsyncSession = Depends(get_session),
):
    stmt = select(TriggerPolicy).order_by(TriggerPolicy.created_at.desc())
    result = await session.exec(stmt)
    return result.all()


@router.get(
    "/triggers/{trigger_id}",
    response_model=TriggerPolicyRead,
    summary="Get a trigger policy by ID",
)
async def get_trigger(
    trigger_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    trigger = await session.get(TriggerPolicy, trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return trigger


@router.post(
    "/triggers",
    response_model=TriggerPolicyRead,
    summary="Create a new trigger policy",
)
async def create_trigger(
    payload: TriggerPolicyCreate,
    session: AsyncSession = Depends(get_session),
):
    trigger = TriggerPolicy(
        name=payload.name,
        event_type=payload.event_type,
        conditions=payload.conditions,
        target_workflow_id=payload.target_workflow_id,
        scope_session_id=payload.scope_session_id,
        is_active=payload.is_active,
    )
    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)
    logger.info("trigger_created", trigger_id=str(trigger.id))
    return trigger


@router.put(
    "/triggers/{trigger_id}",
    response_model=TriggerPolicyRead,
    summary="Update an existing trigger policy",
)
async def update_trigger(
    trigger_id: UUID,
    payload: TriggerPolicyUpdate,
    session: AsyncSession = Depends(get_session),
):
    trigger = await session.get(TriggerPolicy, trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    for field in ["name", "event_type", "conditions", "target_workflow_id", "scope_session_id", "is_active"]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(trigger, field, val)

    from datetime import datetime
    trigger.updated_at = datetime.utcnow()

    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)
    logger.info("trigger_updated", trigger_id=str(trigger.id))
    return trigger


@router.delete(
    "/triggers/{trigger_id}",
    summary="Delete a trigger policy",
)
async def delete_trigger(
    trigger_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    trigger = await session.get(TriggerPolicy, trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    await session.delete(trigger)
    await session.commit()
    return {"ok": True}
