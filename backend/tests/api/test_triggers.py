"""
Integration tests for TriggerPolicy endpoints.

URL prefix (from api.py): triggers router included with no prefix,
so routes are defined directly as /triggers/...

Routes tested:
  GET    /triggers                   - list all trigger policies
  GET    /triggers/{trigger_id}      - get single trigger policy
  POST   /triggers                   - create trigger policy
  PUT    /triggers/{trigger_id}      - update trigger policy
  DELETE /triggers/{trigger_id}      - delete trigger policy
  (toggle enabled via PUT with is_active field)

Note: TriggerPolicy requires a valid target_workflow_id FK,
so each test that creates a trigger must first create a Workflow.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.workflow import Workflow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_workflow(
    db_session: AsyncSession, name: str = "Trigger Test Workflow"
) -> Workflow:
    """Seed a Workflow directly in the DB and return it."""
    workflow = Workflow(
        name=name,
        is_active=True,
        graph_data={"nodes": [], "edges": []},
    )
    db_session.add(workflow)
    await db_session.flush()
    await db_session.refresh(workflow)
    return workflow


def _trigger_payload(workflow_id: str) -> dict:
    return {
        "name": "On User Message",
        "event_type": "user_message",
        "conditions": {},
        "target_workflow_id": workflow_id,
        "scope_session_id": None,
        "is_active": True,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_create_trigger(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Authenticated user can create a trigger policy linked to a workflow."""
    workflow = await _create_workflow(db_session)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=_trigger_payload(str(workflow.id)),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "On User Message"
    assert data["event_type"] == "user_message"
    assert data["target_workflow_id"] == str(workflow.id)
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_list_triggers(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Listing triggers returns all created trigger policies."""
    workflow = await _create_workflow(db_session)

    await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json={**_trigger_payload(str(workflow.id)), "name": "Trigger Alpha"},
    )
    await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json={
            **_trigger_payload(str(workflow.id)),
            "name": "Trigger Beta",
            "event_type": "silence",
        },
    )

    response = await superuser_client.get(f"{settings.API_V1_STR}/triggers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [t["name"] for t in data]
    assert "Trigger Alpha" in names
    assert "Trigger Beta" in names


@pytest.mark.asyncio()
async def test_get_trigger(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Can retrieve a specific trigger policy by ID."""
    workflow = await _create_workflow(db_session)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=_trigger_payload(str(workflow.id)),
    )
    assert create_resp.status_code == 200
    trigger_id = create_resp.json()["id"]

    response = await superuser_client.get(f"{settings.API_V1_STR}/triggers/{trigger_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trigger_id
    assert data["event_type"] == "user_message"
    assert data["target_workflow_id"] == str(workflow.id)


@pytest.mark.asyncio()
async def test_get_trigger_not_found(superuser_client: AsyncClient):
    """Requesting a non-existent trigger returns 404."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/triggers/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_update_trigger(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Can update trigger name and conditions."""
    workflow = await _create_workflow(db_session)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=_trigger_payload(str(workflow.id)),
    )
    assert create_resp.status_code == 200
    trigger_id = create_resp.json()["id"]

    update_payload = {
        "name": "Updated Trigger Name",
        "conditions": {"threshold_mins": 10},
    }
    response = await superuser_client.put(
        f"{settings.API_V1_STR}/triggers/{trigger_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trigger_id
    assert data["name"] == "Updated Trigger Name"
    assert data["conditions"] == {"threshold_mins": 10}
    # Fields not in update payload should be unchanged
    assert data["event_type"] == "user_message"


@pytest.mark.asyncio()
async def test_delete_trigger(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Deleting a trigger removes it; subsequent GET returns 404."""
    workflow = await _create_workflow(db_session)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=_trigger_payload(str(workflow.id)),
    )
    assert create_resp.status_code == 200
    trigger_id = create_resp.json()["id"]

    delete_resp = await superuser_client.delete(f"{settings.API_V1_STR}/triggers/{trigger_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    get_resp = await superuser_client.get(f"{settings.API_V1_STR}/triggers/{trigger_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_trigger_toggle_enabled(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """Trigger can be disabled and re-enabled via PUT with is_active field."""
    workflow = await _create_workflow(db_session)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=_trigger_payload(str(workflow.id)),
    )
    assert create_resp.status_code == 200
    trigger_id = create_resp.json()["id"]
    assert create_resp.json()["is_active"] is True

    # Disable
    disable_resp = await superuser_client.put(
        f"{settings.API_V1_STR}/triggers/{trigger_id}",
        json={"is_active": False},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    # Re-enable
    enable_resp = await superuser_client.put(
        f"{settings.API_V1_STR}/triggers/{trigger_id}",
        json={"is_active": True},
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["is_active"] is True


@pytest.mark.asyncio()
async def test_trigger_requires_auth(client: AsyncClient):
    """Unauthenticated requests to trigger endpoints must be rejected with 401."""
    response = await client.get(f"{settings.API_V1_STR}/triggers")
    assert response.status_code == 401


@pytest.mark.asyncio()
async def test_create_trigger_with_cron_condition(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
):
    """TIMER type trigger with a cron condition is accepted and stored correctly."""
    workflow = await _create_workflow(db_session, name="Cron Workflow")

    payload = {
        "name": "Daily Summary",
        "event_type": "timer",
        "conditions": {"cron": "0 0 * * *"},
        "target_workflow_id": str(workflow.id),
        "scope_session_id": "room-abc-123",
        "is_active": True,
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/triggers",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "timer"
    assert data["conditions"] == {"cron": "0 0 * * *"}
    assert data["scope_session_id"] == "room-abc-123"
