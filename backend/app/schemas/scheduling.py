"""
Pydantic validation schemas for Schedule Config and Trigger Config.

These models are used at the API input layer to validate JSON payloads
before they are stored in JSONB columns.
"""

from typing import Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


# ============================================================
# Schedule Config Schemas
# ============================================================

class ScheduleRuleSchema(BaseModel):
    """A single scheduling rule."""

    type: Literal["everyday", "specific_date", "day_of_week"]
    date: Optional[str] = Field(
        None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD, required for specific_date"
    )
    days: Optional[List[int]] = Field(
        None, description="1=Monday..7=Sunday, required for day_of_week"
    )
    time_range: Optional[List[str]] = Field(
        None, description='["HH:MM","HH:MM"] or null for all-day'
    )

    @field_validator("days")
    @classmethod
    def validate_days(cls, v):
        if v is not None:
            for d in v:
                if d < 1 or d > 7:
                    raise ValueError(f"Day must be 1-7, got {d}")
        return v

    @field_validator("time_range")
    @classmethod
    def validate_time_range(cls, v):
        if v is not None:
            if len(v) != 2:
                raise ValueError("time_range must have exactly 2 elements [start, end]")
            # Basic HH:MM format check
            import re
            pattern = re.compile(r"^\d{2}:\d{2}$")
            for t in v:
                if not pattern.match(t):
                    raise ValueError(f"Invalid time format: {t}, expected HH:MM")
        return v


class ScheduleConfigSchema(BaseModel):
    """
    Unified schedule configuration for API Key / Agent / RoomAgentLink.
    Supports whitelist (only allow) and blacklist (block) modes.
    """

    mode: Literal["whitelist", "blacklist"]
    rules: List[ScheduleRuleSchema] = []


# ============================================================
# Trigger Config Schemas
# ============================================================

class ContextStrategySchema(BaseModel):
    """How much conversation history the agent should read."""

    type: Literal["last_n", "all"] = "last_n"
    n: int = Field(default=10, ge=1, le=10000)


class TriggerBoundsSchema(BaseModel):
    """Bounds for a single trigger parameter when agent self-modifies."""

    min: Optional[float] = Field(None, ge=0)
    max: Optional[float] = Field(None, ge=0)


class TriggerRuleSchema(BaseModel):
    """Trigger conditions — which conditions are active and their values."""

    enabled_conditions: List[str] = Field(
        default=[],
        description="Which conditions to evaluate: message_count, time_interval_mins, user_silent_mins",
    )
    message_count: Optional[int] = Field(None, ge=1, le=10000)
    time_interval_mins: Optional[float] = Field(None, ge=0.5, le=1440)
    user_silent_mins: Optional[float] = Field(None, ge=0.5, le=1440)
    context_strategy: ContextStrategySchema = Field(default_factory=ContextStrategySchema)

    @field_validator("enabled_conditions")
    @classmethod
    def validate_conditions(cls, v):
        allowed = {"message_count", "time_interval_mins", "user_silent_mins"}
        for c in v:
            if c not in allowed:
                raise ValueError(f"Unknown condition: {c}. Allowed: {allowed}")
        return v


class CloseRuleSchema(BaseModel):
    """Agent close/sleep conditions."""

    strategy: Literal["none", "agent_monologue", "user_timeout"] = "none"
    monologue_limit: Optional[int] = Field(None, ge=1, le=100)
    timeout_mins: Optional[float] = Field(None, ge=1, le=1440)


class SelfModificationSchema(BaseModel):
    """Controls whether and how the agent can modify its own triggers."""

    duration_hours: float = Field(
        default=0, ge=-1, le=720,
        description="0=disabled, >0=temp override (hours), -1=permanent"
    )
    bounds: Optional[Dict[str, TriggerBoundsSchema]] = Field(
        default=None,
        description="Per-condition min/max bounds for self-modification",
    )


class StateResetSchema(BaseModel):
    """Configurable auto-reset for AgentRoomState counters."""

    enabled: bool = False
    interval_days: int = Field(default=1, ge=1, le=365)
    reset_time: str = Field(
        default="00:00",
        pattern=r"^\d{2}:\d{2}$",
        description="HH:MM in server timezone",
    )


class TriggerConfigSchema(BaseModel):
    """
    Complete trigger configuration for Agent / RoomAgentLink.
    Includes trigger rules, close rules, self-modification settings,
    and state reset scheduling.
    """

    logic: Literal["or", "and"] = "or"
    trigger: TriggerRuleSchema = Field(default_factory=TriggerRuleSchema)
    close: CloseRuleSchema = Field(default_factory=CloseRuleSchema)
    self_modification: SelfModificationSchema = Field(default_factory=SelfModificationSchema)
    state_reset: StateResetSchema = Field(default_factory=StateResetSchema)
