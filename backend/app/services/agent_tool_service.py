from typing import Any, List
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.llm_service import ToolCall
from app.models.agent_config import AgentConfig, AgentType

UPDATE_TRIGGER_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "update_trigger",
        "description": "Update the trigger configuration for an agent. Use this when the current conversation pace is too slow (needs stimulation) or too fast (needs cooling down).",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "enum": ["teacher", "student"],
                    "description": "The agent to update.",
                },
                "trigger_type": {
                    "type": "string",
                    "enum": ["message_count", "time_interval", "silence"],
                    "description": "The type of trigger to set.",
                },
                "value": {
                    "type": "number",
                    "description": "The value for the trigger (e.g. number of messages or seconds).",
                },
            },
            "required": ["target_agent", "trigger_type", "value"],
        },
    },
}


async def handle_tool_calls(session: AsyncSession, course_id: UUID, tool_calls: List[ToolCall]):
    """
    Handle tool calls executed by the Agent.
    """
    for tool in tool_calls:
        if tool.name == "update_trigger":
            args = tool.arguments
            await _update_agent_trigger(
                session,
                course_id,
                str(args.get("target_agent", "")),
                str(args.get("trigger_type", "")),
                float(args.get("value", 0.0)),
            )


async def _update_agent_trigger(
    session: AsyncSession, course_id: UUID, target_role: str, type_: str, value: float
):
    print(f"[Agent Tool] Updating trigger for {target_role}: {type_}={value}")

    # Map role string to AgentType
    if target_role == "teacher":
        agent_type = AgentType.TEACHER
    elif target_role == "student":
        agent_type = AgentType.STUDENT
    else:
        return

    # Find config
    query: Any = (
        select(AgentConfig)
        .where(AgentConfig.course_id == course_id)
        .where(AgentConfig.type == agent_type)
        .order_by(col(AgentConfig.updated_at).desc())
        .limit(1)
    )
    result = await session.exec(query)
    config = result.first()

    if config:
        # Validate Bounds (Safety Rails)
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            print(f"[Agent Tool] Invalid value received: {value}")
            return

        safe_value = max(10, min(val_float, 3600))  # 10s ~ 1hr

        # Update
        new_trigger = {"type": type_, "value": safe_value}
        config.trigger_config = new_trigger
        session.add(config)
        await session.commit()
