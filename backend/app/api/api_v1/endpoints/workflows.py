"""
Workflow API Endpoints.

CRUD operations for ``RoomWorkflow`` (the graph topology) and read-only
access to ``WorkflowRun`` (execution history / traces).
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_session
from app.models.workflow import (
    RoomWorkflow,
    RoomWorkflowCreate,
    RoomWorkflowRead,
    RoomWorkflowUpdate,
    WorkflowRun,
    WorkflowRunRead,
)

logger = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# RoomWorkflow CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/rooms/{room_id}/workflow",
    response_model=Optional[RoomWorkflowRead],
    summary="Get the workflow graph for a room",
)
async def get_room_workflow(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Return the active workflow topology for the given room."""
    stmt = select(RoomWorkflow).where(RoomWorkflow.room_id == room_id)
    result = await session.exec(stmt)
    workflow = result.first()
    if not workflow:
        return None
    return workflow


@router.put(
    "/rooms/{room_id}/workflow",
    response_model=RoomWorkflowRead,
    summary="Create or update the workflow graph for a room",
)
async def upsert_room_workflow(
    room_id: UUID,
    payload: RoomWorkflowUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Upsert the workflow graph.

    If a workflow already exists for this room it is updated in-place;
    otherwise a new record is created.  The ``graph_data`` field should
    contain the full nodes/edges JSON from the frontend canvas.
    """
    stmt = select(RoomWorkflow).where(RoomWorkflow.room_id == room_id)
    result = await session.exec(stmt)
    workflow = result.first()

    if workflow:
        # Update existing
        if payload.graph_data is not None:
            workflow.graph_data = payload.graph_data
        if payload.name is not None:
            workflow.name = payload.name
        if payload.is_active is not None:
            workflow.is_active = payload.is_active
        from datetime import datetime
        workflow.updated_at = datetime.utcnow()
    else:
        # Create new
        workflow = RoomWorkflow(
            room_id=room_id,
            graph_data=payload.graph_data or {"nodes": [], "edges": []},
            name=payload.name or "Default Workflow",
            is_active=payload.is_active if payload.is_active is not None else True,
        )

    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    logger.info("workflow_upserted", room_id=str(room_id), workflow_id=str(workflow.id))
    return workflow


@router.delete(
    "/rooms/{room_id}/workflow",
    summary="Delete the workflow graph for a room",
)
async def delete_room_workflow(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(RoomWorkflow).where(RoomWorkflow.room_id == room_id)
    result = await session.exec(stmt)
    workflow = result.first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await session.delete(workflow)
    await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# WorkflowRun read-only endpoints (debugging / tracing)
# ---------------------------------------------------------------------------

@router.get(
    "/rooms/{room_id}/workflow/runs",
    response_model=List[WorkflowRunRead],
    summary="List recent workflow runs for a room",
)
async def list_workflow_runs(
    room_id: UUID,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.room_id == room_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    result = await session.exec(stmt)
    return result.all()


@router.get(
    "/rooms/{room_id}/workflow/runs/{run_id}",
    response_model=WorkflowRunRead,
    summary="Get a specific workflow run with full execution log",
)
async def get_workflow_run(
    room_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(WorkflowRun, run_id)
    if not run or run.room_id != room_id:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run
