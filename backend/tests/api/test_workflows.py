"""
Integration tests for Workflow CRUD endpoints.

URL prefix (from api.py): workflows router included with no prefix,
so routes are defined directly as /workflows/...

Routes tested:
  POST   /workflows                          - create workflow
  GET    /workflows                          - list all workflows
  GET    /workflows/{workflow_id}            - get single workflow
  PUT    /workflows/{workflow_id}            - update workflow
  DELETE /workflows/{workflow_id}            - delete workflow
  GET    /workflows/{workflow_id}/runs       - list workflow runs
  POST   /workflows/{workflow_id}/runs/{run_id}/pause   - pause a run
  POST   /workflows/{workflow_id}/runs/{run_id}/resume  - resume a run
  POST   /workflows/{workflow_id}/execute    - manual trigger (mocked)

Auth: all endpoints require authentication via get_current_user dependency.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.workflow import Workflow, WorkflowRun, WorkflowStatus


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

WORKFLOW_PAYLOAD = {
    "name": "Test Workflow",
    "is_active": True,
    "graph_data": {
        "nodes": [
            {"id": "start-1", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
            {"id": "agent-1", "type": "agent", "config": {"agent_id": "some-agent"}, "position": {"x": 200, "y": 0}},
            {"id": "end-1", "type": "end", "config": {}, "position": {"x": 400, "y": 0}},
        ],
        "edges": [
            {"id": "e1", "source": "start-1", "target": "agent-1", "type": "forward"},
            {"id": "e2", "source": "agent-1", "target": "end-1", "type": "forward"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_workflow(superuser_client: AsyncClient):
    """Authenticated user can create a workflow."""
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # Verify graph_data round-trips correctly
    assert len(data["graph_data"]["nodes"]) == 3
    assert len(data["graph_data"]["edges"]) == 2


@pytest.mark.asyncio()
async def test_list_workflows(superuser_client: AsyncClient):
    """Listing workflows returns all created workflows."""
    # Create two workflows
    await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json={**WORKFLOW_PAYLOAD, "name": "Workflow A"},
    )
    await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json={**WORKFLOW_PAYLOAD, "name": "Workflow B"},
    )

    response = await superuser_client.get(f"{settings.API_V1_STR}/workflows")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [w["name"] for w in data]
    assert "Workflow A" in names
    assert "Workflow B" in names


@pytest.mark.asyncio()
async def test_get_workflow(superuser_client: AsyncClient):
    """Can retrieve a specific workflow by ID."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workflows/{workflow_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow_id
    assert data["name"] == "Test Workflow"


@pytest.mark.asyncio()
async def test_get_workflow_not_found(superuser_client: AsyncClient):
    """Requesting a non-existent workflow returns 404."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workflows/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_update_workflow(superuser_client: AsyncClient):
    """Can update name, graph_data, and is_active on an existing workflow."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    update_payload = {
        "name": "Updated Workflow Name",
        "is_active": False,
        "graph_data": {"nodes": [], "edges": []},
    }
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/workflows/{workflow_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow_id
    assert data["name"] == "Updated Workflow Name"
    assert data["is_active"] is False
    assert data["graph_data"] == {"nodes": [], "edges": []}


@pytest.mark.asyncio()
async def test_update_workflow_partial(superuser_client: AsyncClient):
    """Partial update: only name is changed, graph_data stays intact."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    response = await superuser_client.put(
        f"{settings.API_V1_STR}/workflows/{workflow_id}",
        json={"name": "Partially Updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partially Updated"
    # graph_data should be unchanged from original
    assert len(data["graph_data"]["nodes"]) == 3


@pytest.mark.asyncio()
async def test_delete_workflow(superuser_client: AsyncClient):
    """Deleting a workflow removes it; subsequent GET returns 404."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    delete_resp = await superuser_client.delete(
        f"{settings.API_V1_STR}/workflows/{workflow_id}"
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    get_resp = await superuser_client.get(
        f"{settings.API_V1_STR}/workflows/{workflow_id}"
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_workflow_requires_auth(client: AsyncClient):
    """Unauthenticated requests are rejected with 401."""
    response = await client.get(f"{settings.API_V1_STR}/workflows")
    assert response.status_code == 401


@pytest.mark.asyncio()
async def test_list_workflow_runs_empty(superuser_client: AsyncClient):
    """A freshly created workflow has no runs."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    workflow_id = create_resp.json()["id"]

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/workflows/{workflow_id}/runs"
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio()
async def test_pause_workflow_run(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Pausing a RUNNING workflow run transitions its status to 'paused'."""
    # Create the workflow via API
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    # Seed a WorkflowRun directly in the DB with status=running
    from uuid import UUID
    run = WorkflowRun(
        workflow_id=UUID(workflow_id),
        session_id="test-session-pause",
        trigger_payload={},
        status=WorkflowStatus.RUNNING.value,
    )
    db_session.add(run)
    await db_session.flush()
    await db_session.refresh(run)
    run_id = str(run.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows/{workflow_id}/runs/{run_id}/pause"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    assert data["run_id"] == run_id


@pytest.mark.asyncio()
async def test_resume_workflow_run(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Resuming a PAUSED workflow run transitions its status to 'running'."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    from uuid import UUID
    run = WorkflowRun(
        workflow_id=UUID(workflow_id),
        session_id="test-session-resume",
        trigger_payload={},
        status=WorkflowStatus.PAUSED.value,
    )
    db_session.add(run)
    await db_session.flush()
    await db_session.refresh(run)
    run_id = str(run.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows/{workflow_id}/runs/{run_id}/resume"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resumed"
    assert data["run_id"] == run_id


@pytest.mark.asyncio()
async def test_execute_workflow_mocked(superuser_client: AsyncClient):
    """Manual workflow execution is mocked to avoid real Redis/LangGraph calls."""
    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/workflows",
        json=WORKFLOW_PAYLOAD,
    )
    assert create_resp.status_code == 200
    workflow_id = create_resp.json()["id"]

    with patch(
        "app.services.execution.agent_execution_service.execute_workflow",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "redis.asyncio.from_url",
        return_value=AsyncMock(aclose=AsyncMock()),
    ):
        mock_exec.return_value = None
        response = await superuser_client.post(
            f"{settings.API_V1_STR}/workflows/{workflow_id}/execute",
            json={"type": "manual", "content": "Run now"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "session_id" in data
