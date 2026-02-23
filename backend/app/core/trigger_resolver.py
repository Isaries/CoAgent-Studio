"""
Trigger resolver: merges trigger_config from AgentConfig, RoomAgentLink,
and runtime overrides (AgentRoomState) into a single effective config.
"""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.agent_config import AgentConfig
from app.models.agent_room_state import AgentRoomState
from app.models.room import RoomAgentLink


_DEFAULTS: Dict[str, Any] = {
    "logic": "or",
    "trigger": {
        "enabled_conditions": [],
        "message_count": None,
        "time_interval_mins": None,
        "user_silent_mins": None,
        "context_strategy": {"type": "last_n", "n": 10},
    },
    "close": {
        "strategy": "none",
        "monologue_limit": None,
        "timeout_mins": None,
    },
    "self_modification": {
        "duration_hours": 0,
        "bounds": None,
    },
    "state_reset": {
        "enabled": False,
        "interval_days": 1,
        "reset_time": "00:00",
    },
}


def resolve_effective_trigger(
    agent_config: AgentConfig,
    link: Optional[RoomAgentLink] = None,
    state: Optional[AgentRoomState] = None,
) -> Dict[str, Any]:
    """
    Resolve the effective trigger_config using priority:
      active_overrides (if not expired) > RoomAgentLink > AgentConfig > defaults

    Returns a fully-populated trigger config dict.
    """
    # Start with defaults
    merged = deepcopy(_DEFAULTS)

    # Layer 1: AgentConfig
    base = agent_config.trigger_config
    if base:
        merged = _deep_merge(merged, base)

    # Layer 2: RoomAgentLink overrides
    if link and link.trigger_config:
        merged = _deep_merge(merged, link.trigger_config)

    # Layer 3: Runtime overrides (temporary, check expiry)
    if state and state.active_overrides:
        if _is_override_valid(state):
            merged = _deep_merge(merged, state.active_overrides)
        # else: expired → ignore

    return merged


def _is_override_valid(state: AgentRoomState) -> bool:
    """Check if the runtime override is still valid (not expired)."""
    if state.overrides_expires_at is None:
        return True  # Permanent override (duration_hours == -1)
    now = datetime.now(timezone.utc)
    expires = state.overrides_expires_at
    # Handle naive datetimes
    if expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)
    return expires > now


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Recursively merge `override` into `base`.
    override values take precedence; None values in override do NOT overwrite.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if value is None:
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result
