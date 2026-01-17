from datetime import datetime
from typing import Any, Dict

from zoneinfo import ZoneInfo

from app.core.config import settings
from app.models.agent_config import AgentConfig


def is_agent_scheduled_now(config: AgentConfig) -> bool:
    """Check if agent is allowed to run at this current time (UTC+8)."""
    if not config.schedule_config:
        return True  # Default to always active if no schedule

    schedule = config.schedule_config
    if not isinstance(schedule, dict):
        return True  # Malformed

    # 1. Check Specific Rules (Priority: Override)
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)
    current_date_str = now.strftime("%Y-%m-%d")
    current_time = now.time()

    # Check specifics
    if _check_specific_rules(schedule, current_date_str, current_time):
        return True

    # Check if specific rules exist for today but failed (implicit block)
    specific_rules = schedule.get("specific", [])
    if isinstance(specific_rules, list):
        if any(r.get("date") == current_date_str for r in specific_rules):
            return False

    # 2. Check General Pattern (Fallback)
    return _check_general_schedule(schedule, current_date_str, current_time, now.weekday())


def _check_specific_rules(schedule: Dict, date_str: str, current_time: Any) -> bool:
    specific_rules = schedule.get("specific", [])
    if not isinstance(specific_rules, list):
        return False

    todays_specifics = [r for r in specific_rules if r.get("date") == date_str]
    for rule in todays_specifics:
        try:
            start = datetime.strptime(rule["start"], "%H:%M").time()
            end = datetime.strptime(rule["end"], "%H:%M").time()
            if start <= current_time <= end:
                return True
        except Exception:
            continue
    return False


def _check_general_schedule(schedule: Dict, date_str: str, current_time: Any, weekday: int) -> bool:
    general = schedule.get("general", {})
    if not general:
        if "mode" in schedule and "general" not in schedule:
            general = schedule
        else:
            return True

    mode = general.get("mode", "none")
    if mode == "none":
        return True

    if not _check_date_range(mode, general, date_str):
        return False

    return _check_time_rules(mode, general, current_time, weekday)


def _check_date_range(mode: str, general: Dict, date_str: str) -> bool:
    if mode in ["range_daily", "range_weekly"]:
        s_date = general.get("start_date")
        e_date = general.get("end_date")
        if s_date and e_date:
            if not (s_date <= date_str <= e_date):
                return False
    return True


def _check_time_rules(mode: str, general: Dict, current_time: Any, weekday: int) -> bool:
    g_rules = general.get("rules", [])
    if not g_rules:
        return False

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
