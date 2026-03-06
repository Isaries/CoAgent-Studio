"""
Unit tests for app.services.trigger_service.TriggerDispatcher.

Covers:
- _evaluate_conditions: pure sync method, zero mocking needed
- resolve_matching_workflows: DB session mocked via AsyncMock
- _is_locked: Redis mocked via AsyncMock
- evaluate_time_triggers: lightly tested via condition helpers
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models.trigger import TriggerPolicy
from app.services.trigger_service import TriggerDispatcher


def _make_policy(**kwargs) -> TriggerPolicy:
    defaults = {
        "id": uuid4(),
        "name": "Test Trigger",
        "event_type": "user_message",
        "conditions": {},
        "target_workflow_id": uuid4(),
        "scope_session_id": None,
        "is_active": True,
    }
    defaults.update(kwargs)
    return TriggerPolicy(**defaults)


def _make_session(policies=None) -> AsyncMock:
    """Return a session mock whose exec().all() returns the given policy list."""
    session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = policies if policies is not None else []
    session.exec.return_value = mock_result
    session.get = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# _evaluate_conditions — pure unit, no DB or Redis
# ---------------------------------------------------------------------------


def test_evaluate_conditions_empty_conditions_always_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert dispatcher._evaluate_conditions({}, {"content": "anything"}) is True


def test_evaluate_conditions_empty_conditions_empty_payload():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert dispatcher._evaluate_conditions({}, {}) is True


def test_evaluate_conditions_keyword_match_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert dispatcher._evaluate_conditions({"keyword": "hello"}, {"content": "Hello World"}) is True


def test_evaluate_conditions_keyword_match_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert (
        dispatcher._evaluate_conditions({"keyword": "goodbye"}, {"content": "Hello World"}) is False
    )


def test_evaluate_conditions_keyword_case_insensitive():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert dispatcher._evaluate_conditions({"keyword": "HELLO"}, {"content": "hello world"}) is True


def test_evaluate_conditions_keyword_no_content_field_true():
    """If the payload has no 'content' key the keyword check is skipped (returns True)."""
    dispatcher = TriggerDispatcher(session=AsyncMock())
    assert dispatcher._evaluate_conditions({"keyword": "hello"}, {"role": "admin"}) is True


def test_evaluate_conditions_pattern_match_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"pattern": r"\d{3}-\d{4}"}
    assert dispatcher._evaluate_conditions(cond, {"content": "Call 123-4567 now"}) is True


def test_evaluate_conditions_pattern_match_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"pattern": r"\d{10}"}
    assert dispatcher._evaluate_conditions(cond, {"content": "no numbers here"}) is False


def test_evaluate_conditions_pattern_case_insensitive():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"pattern": r"URGENT"}
    assert dispatcher._evaluate_conditions(cond, {"content": "this is urgent!"}) is True


def test_evaluate_conditions_field_check_eq_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "role", "operator": "eq", "value": "admin"}]}
    assert dispatcher._evaluate_conditions(cond, {"role": "admin"}) is True


def test_evaluate_conditions_field_check_eq_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "role", "operator": "eq", "value": "admin"}]}
    assert dispatcher._evaluate_conditions(cond, {"role": "student"}) is False


def test_evaluate_conditions_field_check_neq_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "status", "operator": "neq", "value": "banned"}]}
    assert dispatcher._evaluate_conditions(cond, {"status": "active"}) is True


def test_evaluate_conditions_field_check_neq_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "status", "operator": "neq", "value": "banned"}]}
    assert dispatcher._evaluate_conditions(cond, {"status": "banned"}) is False


def test_evaluate_conditions_field_check_contains_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "tags", "operator": "contains", "value": "urgent"}]}
    assert dispatcher._evaluate_conditions(cond, {"tags": "urgent,important"}) is True


def test_evaluate_conditions_field_check_contains_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "tags", "operator": "contains", "value": "critical"}]}
    assert dispatcher._evaluate_conditions(cond, {"tags": "normal,low"}) is False


def test_evaluate_conditions_field_check_gt_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "score", "operator": "gt", "value": 50}]}
    assert dispatcher._evaluate_conditions(cond, {"score": 75}) is True


def test_evaluate_conditions_field_check_gt_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "score", "operator": "gt", "value": 50}]}
    assert dispatcher._evaluate_conditions(cond, {"score": 30}) is False


def test_evaluate_conditions_field_check_lt_true():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "score", "operator": "lt", "value": 100}]}
    assert dispatcher._evaluate_conditions(cond, {"score": 75}) is True


def test_evaluate_conditions_field_check_lt_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "score", "operator": "lt", "value": 10}]}
    assert dispatcher._evaluate_conditions(cond, {"score": 75}) is False


def test_evaluate_conditions_missing_field_returns_false():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {"field_checks": [{"field": "nonexistent", "operator": "eq", "value": "x"}]}
    assert dispatcher._evaluate_conditions(cond, {}) is False


def test_evaluate_conditions_multiple_field_checks_all_pass():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {
        "field_checks": [
            {"field": "role", "operator": "eq", "value": "admin"},
            {"field": "score", "operator": "gt", "value": 50},
        ]
    }
    assert dispatcher._evaluate_conditions(cond, {"role": "admin", "score": 99}) is True


def test_evaluate_conditions_multiple_field_checks_one_fails():
    dispatcher = TriggerDispatcher(session=AsyncMock())
    cond = {
        "field_checks": [
            {"field": "role", "operator": "eq", "value": "admin"},
            {"field": "score", "operator": "gt", "value": 50},
        ]
    }
    assert dispatcher._evaluate_conditions(cond, {"role": "admin", "score": 10}) is False


# ---------------------------------------------------------------------------
# resolve_matching_workflows — no policies (legacy fallback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_no_policies_no_room_returns_empty():
    """No policies and no room — result is an empty list."""
    session = _make_session(policies=[])
    dispatcher = TriggerDispatcher(session=session)
    result = await dispatcher.resolve_matching_workflows("user_message", str(uuid4()), {})
    assert result == []


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_no_policies_with_attached_workflow_fires():
    """Legacy fallback: room.attached_workflow_id is returned when no policies exist."""
    from app.models.room import Room

    workflow_id = uuid4()
    room_id = uuid4()
    room = Room(id=room_id, name="R", space_id=uuid4(), attached_workflow_id=workflow_id)

    session = _make_session(policies=[])
    session.get.return_value = room

    dispatcher = TriggerDispatcher(session=session)
    result = await dispatcher.resolve_matching_workflows("user_message", str(room_id), {})

    assert workflow_id in result


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_no_policies_room_no_workflow_returns_empty():
    """Legacy fallback: room exists but has no attached workflow — still empty."""
    from app.models.room import Room

    room_id = uuid4()
    room = Room(id=room_id, name="R", space_id=uuid4(), attached_workflow_id=None)

    session = _make_session(policies=[])
    session.get.return_value = room

    dispatcher = TriggerDispatcher(session=session)
    result = await dispatcher.resolve_matching_workflows("user_message", str(room_id), {})

    assert result == []


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_webhook_no_policies_returns_empty():
    """Webhook events have no legacy fallback."""
    session = _make_session(policies=[])
    dispatcher = TriggerDispatcher(session=session)
    result = await dispatcher.resolve_matching_workflows("webhook", "session-1", {})
    assert result == []


# ---------------------------------------------------------------------------
# resolve_matching_workflows — with active policies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_condition_matched_fires():
    """Policy with a matching keyword condition is included in results."""
    policy = _make_policy(conditions={"keyword": "help"})
    session = _make_session(policies=[policy])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows(
        "user_message", "session-1", {"content": "I need help"}
    )

    assert policy.target_workflow_id in result


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_condition_not_matched_skipped():
    """Policy whose keyword condition fails is excluded."""
    policy = _make_policy(conditions={"keyword": "goodbye"})
    session = _make_session(policies=[policy])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows(
        "user_message", "session-1", {"content": "Hello there"}
    )

    assert result == []


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_scope_session_mismatch_skipped():
    """Policy scoped to a different session_id is skipped."""
    policy = _make_policy(scope_session_id="room-abc", conditions={})
    session = _make_session(policies=[policy])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows(
        "user_message", "room-xyz", {"content": "Hello"}
    )

    assert result == []


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_scope_session_match_fires():
    """Policy scoped to the same session_id fires when conditions match."""
    policy = _make_policy(scope_session_id="room-abc", conditions={})
    session = _make_session(policies=[policy])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows(
        "user_message", "room-abc", {"content": "Hello"}
    )

    assert policy.target_workflow_id in result


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_global_scope_matches_any_session():
    """Policy with scope_session_id=None applies to all sessions."""
    policy = _make_policy(scope_session_id=None, conditions={})
    session = _make_session(policies=[policy])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows("user_message", "any-room-id", {})

    assert policy.target_workflow_id in result


@pytest.mark.asyncio()
async def test_resolve_matching_workflows_multiple_policies_partial_match():
    """Only policies with matching conditions are included."""
    policy_match = _make_policy(conditions={"keyword": "hello"})
    policy_no_match = _make_policy(conditions={"keyword": "goodbye"})
    session = _make_session(policies=[policy_match, policy_no_match])

    dispatcher = TriggerDispatcher(session=session, redis=None)
    result = await dispatcher.resolve_matching_workflows(
        "user_message", "session-1", {"content": "hello world"}
    )

    assert policy_match.target_workflow_id in result
    assert policy_no_match.target_workflow_id not in result


# ---------------------------------------------------------------------------
# _is_locked — Redis mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_is_locked_no_redis_always_false():
    """Without Redis configured, _is_locked always returns False."""
    dispatcher = TriggerDispatcher(session=AsyncMock(), redis=None)
    result = await dispatcher._is_locked(uuid4(), "session-1")
    assert result is False


@pytest.mark.asyncio()
async def test_is_locked_setnx_acquired_lock_is_free():
    """setnx returns 1 (lock was free) — _is_locked returns False (not locked), sets expiry."""
    redis = AsyncMock()
    redis.setnx = AsyncMock(return_value=1)
    redis.expire = AsyncMock()

    dispatcher = TriggerDispatcher(session=AsyncMock(), redis=redis)
    result = await dispatcher._is_locked(uuid4(), "session-1")

    assert result is False
    redis.expire.assert_awaited_once()


@pytest.mark.asyncio()
async def test_is_locked_setnx_not_acquired_lock_held():
    """setnx returns 0 (lock already held) — _is_locked returns True."""
    redis = AsyncMock()
    redis.setnx = AsyncMock(return_value=0)

    dispatcher = TriggerDispatcher(session=AsyncMock(), redis=redis)
    result = await dispatcher._is_locked(uuid4(), "session-1")

    assert result is True


@pytest.mark.asyncio()
async def test_is_locked_key_format_includes_policy_and_session():
    """The Redis key must encode both policy_id and session_id."""
    redis = AsyncMock()
    redis.setnx = AsyncMock(return_value=1)
    redis.expire = AsyncMock()

    policy_id = uuid4()
    session_id = "room-xyz"

    dispatcher = TriggerDispatcher(session=AsyncMock(), redis=redis)
    await dispatcher._is_locked(policy_id, session_id)

    call_args = redis.setnx.call_args
    key_used = call_args.args[0] if call_args.args else call_args[0][0]
    assert str(policy_id) in key_used
    assert session_id in key_used


# ---------------------------------------------------------------------------
# TriggerPolicy model — toggle active state
# ---------------------------------------------------------------------------


def test_trigger_policy_toggle_active_to_inactive():
    policy = _make_policy(is_active=True)
    policy.is_active = False
    assert policy.is_active is False


def test_trigger_policy_toggle_inactive_to_active():
    policy = _make_policy(is_active=False)
    policy.is_active = True
    assert policy.is_active is True


def test_trigger_policy_default_is_active():
    policy = TriggerPolicy(
        name="Default",
        event_type="user_message",
        conditions={},
        target_workflow_id=uuid4(),
    )
    assert policy.is_active is True
