"""
Unified schedule checking utility.

Supports the new { "mode": "whitelist|blacklist", "rules": [...] } format.
Backwards-compatible with old AgentConfig.schedule_config via wrapper.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from zoneinfo import ZoneInfo

from app.core.config import settings


def is_schedule_allowed_now(schedule_config: Optional[Dict[str, Any]]) -> bool:
    """
    Universal schedule check for API Key / Agent / RoomAgentLink.
    Supports whitelist/blacklist mode with rules.
    Returns True if the current time is allowed.
    """
    if not schedule_config:
        return True  # No schedule = always allowed

    mode = schedule_config.get("mode")
    rules = schedule_config.get("rules")

    if not mode or not rules:
        # Might be old format — try legacy check
        if "specific" in schedule_config or "general" in schedule_config:
            return _legacy_check(schedule_config)
        return True

    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)
    current_time_str = now.strftime("%H:%M")
    current_date_str = now.strftime("%Y-%m-%d")
    current_weekday = now.isoweekday()  # 1=Monday, 7=Sunday

    matched = _any_rule_matches(rules, current_date_str, current_time_str, current_weekday)

    if mode == "whitelist":
        return matched  # Must match at least one rule to be allowed
    else:  # blacklist
        return not matched  # Must NOT match any rule to be allowed


def _any_rule_matches(
    rules: List[Dict], date_str: str, time_str: str, weekday: int
) -> bool:
    """Check if any rule matches the current date/time."""
    for rule in rules:
        rule_type = rule.get("type")
        time_range = rule.get("time_range")  # None means all day

        # Date match
        date_match = False
        if rule_type == "everyday":
            date_match = True
        elif rule_type == "specific_date":
            date_match = rule.get("date") == date_str
        elif rule_type == "day_of_week":
            date_match = weekday in (rule.get("days") or [])

        if not date_match:
            continue

        # Time match
        if time_range is None:
            return True  # Any time of the matched day
        if isinstance(time_range, list) and len(time_range) == 2:
            if time_range[0] <= time_str <= time_range[1]:
                return True

    return False


# ============================================================
# Legacy Compatibility
# ============================================================

def _legacy_check(schedule: Dict) -> bool:
    """Check using the old { specific: [...], general: {...} } format."""
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)
    current_date_str = now.strftime("%Y-%m-%d")
    current_time = now.time()

    # Check specific date rules first (priority)
    specific_rules = schedule.get("specific", [])
    if isinstance(specific_rules, list):
        todays_specifics = [r for r in specific_rules if r.get("date") == current_date_str]
        for rule in todays_specifics:
            try:
                start = datetime.strptime(rule["start"], "%H:%M").time()
                end = datetime.strptime(rule["end"], "%H:%M").time()
                if start <= current_time <= end:
                    return True
            except Exception:
                continue
        # If specific rules exist for today but none matched → blocked
        if todays_specifics:
            return False

    # Fallback to general schedule
    general = schedule.get("general", {})
    if not general:
        return True

    mode = general.get("mode", "none")
    if mode == "none":
        return True

    # Date range check
    if mode in ["range_daily", "range_weekly"]:
        s_date = general.get("start_date")
        e_date = general.get("end_date")
        if s_date and e_date:
            if not (s_date <= current_date_str <= e_date):
                return False

    # Time rules
    g_rules = general.get("rules", [])
    if not g_rules:
        return False

    weekday = now.weekday()  # 0=Monday in old format
    for rule in g_rules:
        try:
            start_str = rule.get("start_time")
            end_str = rule.get("end_time")
            if not start_str or not end_str:
                continue
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()

            if mode == "range_weekly":
                allowed_days = rule.get("days", [])
                if weekday not in allowed_days:
                    continue

            if start <= current_time <= end:
                return True
        except Exception:
            continue

    return False


# Backward-compatible wrapper
def is_agent_scheduled_now(config) -> bool:
    """Legacy wrapper for AgentConfig objects."""
    return is_schedule_allowed_now(getattr(config, "schedule_config", None))
