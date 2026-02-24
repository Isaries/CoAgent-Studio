"""
Workflow API Endpoints.

Provides TWO sets of routes:
1. **Global** ``/workflows`` – CRUD for the decoupled Workflow resource.
2. **Legacy** ``/rooms/{room_id}/workflow`` – backward-compatible endpoints
   that resolve a Room's ``attached_workflow_id``.

Also exposes WorkflowRun read endpoints and a manual execution trigger.
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_session
from app.models.workflow import (
    Workflow,
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowRun,
    WorkflowRunRead,
)
from app.models.room import Room

logger = structlog.get_logger()
router = APIRouter()


# ===================================================================
# Global Workflow CRUD  (/workflows)
# ===================================================================

@router.get(
    "/workflows",
    response_model=List[WorkflowRead],
    summary="List all workflows",
)
async def list_workflows(
    session: AsyncSession = Depends(get_session),
):
    """Return all available workflow templates."""
    stmt = select(Workflow).order_by(Workflow.created_at.desc())
    result = await session.exec(stmt)
    return result.all()


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowRead,
    summary="Get a workflow by ID",
)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post(
    "/workflows",
    response_model=WorkflowRead,
    summary="Create a new workflow",
)
async def create_workflow(
    payload: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
):
    workflow = Workflow(
        name=payload.name,
        is_active=payload.is_active,
        graph_data=payload.graph_data,
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    logger.info("workflow_created", workflow_id=str(workflow.id))
    return workflow


@router.put(
    "/workflows/{workflow_id}",
    response_model=WorkflowRead,
    summary="Update an existing workflow",
)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    session: AsyncSession = Depends(get_session),
):
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.name is not None:
        workflow.name = payload.name
    if payload.graph_data is not None:
        workflow.graph_data = payload.graph_data
    if payload.is_active is not None:
        workflow.is_active = payload.is_active

    from datetime import datetime
    workflow.updated_at = datetime.utcnow()

    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    logger.info("workflow_updated", workflow_id=str(workflow.id))
    return workflow


@router.delete(
    "/workflows/{workflow_id}",
    summary="Delete a workflow",
)
async def delete_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await session.delete(workflow)
    await session.commit()
    return {"ok": True}


@router.post(
    "/workflows/{workflow_id}/execute",
    summary="Manually trigger a workflow execution",
)
async def execute_workflow_endpoint(
    workflow_id: UUID,
    payload: dict = {},
    session: AsyncSession = Depends(get_session),
):
    """
    Manually trigger a workflow.  The request body is passed as the
    ``trigger_payload`` to the execution engine.

    Example body::

        {"type": "user_message", "content": "Hello, analyze this..."}
    """
    from app.services.execution.agent_execution_service import execute_workflow
    import uuid as _uuid

    # Extract session_id without mutating the original payload
    session_id = payload.get("session_id", str(_uuid.uuid4()))
    trigger_payload = {k: v for k, v in payload.items() if k != "session_id"}

    try:
        from app.core.config import settings
        import redis.asyncio as aioredis

        redis_conn = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        )
        try:
            await execute_workflow(session, redis_conn, workflow_id, session_id, trigger_payload)
        finally:
            await redis_conn.aclose()
        return {"ok": True, "session_id": session_id}
    except Exception as e:
        logger.error("workflow_execute_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ===================================================================
# WorkflowRun endpoints (global)
# ===================================================================

@router.get(
    "/workflows/{workflow_id}/runs",
    response_model=List[WorkflowRunRead],
    summary="List recent runs for a workflow",
)
async def list_workflow_runs_global(
    workflow_id: UUID,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    result = await session.exec(stmt)
    return result.all()


@router.get(
    "/workflows/{workflow_id}/runs/{run_id}",
    response_model=WorkflowRunRead,
    summary="Get a specific workflow run",
)
async def get_workflow_run_global(
    workflow_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(WorkflowRun, run_id)
    if not run or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


# ===================================================================
# Legacy Room-scoped endpoints  (/rooms/{room_id}/workflow)
# These resolve the Room's attached_workflow_id transparently.
# ===================================================================

@router.get(
    "/rooms/{room_id}/workflow",
    response_model=Optional[WorkflowRead],
    summary="Get the workflow attached to a room (legacy)",
)
async def get_room_workflow(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Return the workflow attached to this room, if any."""
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room.attached_workflow_id:
        return None

    workflow = await session.get(Workflow, room.attached_workflow_id)
    return workflow


@router.put(
    "/rooms/{room_id}/workflow",
    response_model=WorkflowRead,
    summary="Create/update the workflow attached to a room (legacy)",
)
async def upsert_room_workflow(
    room_id: UUID,
    payload: WorkflowUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Upsert the workflow graph for a room.

    If the room already has an attached workflow, update it.
    Otherwise create a new Workflow and attach it to the room.
    """
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.attached_workflow_id:
        # Update existing
        workflow = await session.get(Workflow, room.attached_workflow_id)
        if workflow:
            if payload.graph_data is not None:
                workflow.graph_data = payload.graph_data
            if payload.name is not None:
                workflow.name = payload.name
            if payload.is_active is not None:
                workflow.is_active = payload.is_active
            from datetime import datetime
            workflow.updated_at = datetime.utcnow()
        else:
            # Workflow was deleted; re-create
            workflow = Workflow(
                graph_data=payload.graph_data or {"nodes": [], "edges": []},
                name=payload.name or "Default Workflow",
                is_active=payload.is_active if payload.is_active is not None else True,
            )
            session.add(workflow)
            await session.flush()
            room.attached_workflow_id = workflow.id
    else:
        # Create new
        workflow = Workflow(
            graph_data=payload.graph_data or {"nodes": [], "edges": []},
            name=payload.name or "Default Workflow",
            is_active=payload.is_active if payload.is_active is not None else True,
        )
        session.add(workflow)
        await session.flush()
        room.attached_workflow_id = workflow.id

    session.add(room)
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    logger.info("workflow_upserted", room_id=str(room_id), workflow_id=str(workflow.id))
    return workflow


@router.delete(
    "/rooms/{room_id}/workflow",
    summary="Detach and delete the workflow from a room (legacy)",
)
async def delete_room_workflow(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    room = await session.get(Room, room_id)
    if not room or not room.attached_workflow_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = await session.get(Workflow, room.attached_workflow_id)
    room.attached_workflow_id = None
    session.add(room)

    if workflow:
        await session.delete(workflow)

    await session.commit()
    return {"ok": True}


@router.get(
    "/rooms/{room_id}/workflow/runs",
    response_model=List[WorkflowRunRead],
    summary="List recent workflow runs for a room (legacy)",
)
async def list_workflow_runs(
    room_id: UUID,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """Lists runs where session_id matches the room_id."""
    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.session_id == str(room_id))
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    result = await session.exec(stmt)
    return result.all()


@router.get(
    "/rooms/{room_id}/workflow/runs/{run_id}",
    response_model=WorkflowRunRead,
    summary="Get a specific workflow run (legacy)",
)
async def get_workflow_run(
    room_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(WorkflowRun, run_id)
    if not run or run.session_id != str(room_id):
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run
