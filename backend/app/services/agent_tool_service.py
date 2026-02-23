from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.audit_service import log_change
from app.core.llm_service import ToolCall
from app.core.trigger_resolver import resolve_effective_trigger
from app.models.agent_config import AgentConfig, AgentType
from app.models.agent_room_state import AgentRoomState
from app.models.room import RoomAgentLink

UPDATE_TRIGGER_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "update_trigger",
        "description": (
            "Adjust how often you speak. Set one or more trigger parameters. "
            "Only the fields you provide will be changed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_count": {
                    "type": "integer",
                    "description": "Trigger every N user messages.",
                },
                "time_interval_mins": {
                    "type": "number",
                    "description": "Trigger every N minutes.",
                },
                "user_silent_mins": {
                    "type": "number",
                    "description": "Trigger after N minutes of user silence.",
                },
            },
            "required": [],
        },
    },
}

MANAGE_ARTIFACT_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "manage_artifact",
        "description": "Create, update, or delete artifacts (tasks, documents, processes) in the workspace. Use this to help users organize information beyond chat.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "delete", "append", "add_step"],
                    "description": "The action to perform on the artifact.",
                },
                "artifact_type": {
                    "type": "string",
                    "enum": ["task", "doc", "process"],
                    "description": "The type of artifact. Required for 'create' action.",
                },
                "artifact_id": {
                    "type": "string",
                    "description": "The UUID of the artifact. Required for 'update' and 'delete' actions.",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the artifact. Required for 'create', optional for 'update'.",
                },
                "content": {
                    "type": "object",
                    "description": """Content payload.
                    - For 'task': {"status": "todo"|"in_progress"|"done", "priority": "low"|"medium"|"high"}
                    - For 'doc' (Tiptap JSON): {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "..."}]}]}
                    - For 'process' (Vue Flow): {"nodes": [{"id": "1", "type": "input", "data": {"label": "Start"}, "position": {"x": 0, "y": 0}}], "edges": [{"id": "e1-2", "source": "1", "target": "2"}]}
                    """,
                },
            },
            "required": ["action"],
        },
    },
}


async def handle_tool_calls(
    session: AsyncSession,
    room_id: UUID,
    tool_calls: List[ToolCall],
    user_id: UUID = None,
    agent_config_id: UUID = None,
) -> List[str]:
    """
    Handle tool calls executed by the Agent.
    Returns a list of result strings to be fed back to the agent or logged.
    """
    results = []
    for tool in tool_calls:
        if tool.name == "update_trigger":
            args = tool.arguments
            if agent_config_id:
                result = await _update_agent_trigger(
                    session,
                    room_id,
                    agent_config_id,
                    args,
                )
                results.append(result)
            else:
                results.append("Error: agent_config_id required for update_trigger")

        elif tool.name == "manage_artifact" and room_id:
            args = tool.arguments
            result = await _handle_manage_artifact(
                session,
                room_id,
                user_id or UUID("00000000-0000-0000-0000-000000000000"),
                str(args.get("action", "")),
                args.get("artifact_type"),
                args.get("artifact_id"),
                args.get("title"),
                args.get("content"),
            )
            if result:
                results.append(result)

    return results


async def _handle_manage_artifact(
    session: AsyncSession,
    room_id: UUID,
    user_id: UUID,
    action: str,
    artifact_type: str = None,
    artifact_id: str = None,
    title: str = None,
    content: dict = None,
) -> str:
    """Handle artifact management tool calls from agents."""
    from app.services.artifact_service import ArtifactService
    from app.models.artifact import ArtifactCreate, ArtifactUpdate
    from app.core.socket_manager import manager
    
    service = ArtifactService(session, socket_manager=manager)
    
    if action == "create":
        if not artifact_type or not title:
            return "Error: manage_artifact create requires artifact_type and title"
        
        data = ArtifactCreate(
            type=artifact_type,
            title=title,
            content=content or {},
        )
        artifact = await service.create_artifact(room_id, data, created_by=user_id)
        return f"Created artifact: {artifact.id} ({artifact_type}: {title})"
    
    elif action == "update":
        if not artifact_id:
            return "Error: manage_artifact update requires artifact_id"
        
        data = ArtifactUpdate(
            title=title,
            content=content,
        )
        artifact = await service.update_artifact(UUID(artifact_id), data, modified_by=user_id)
        if artifact:
            return f"Updated artifact: {artifact_id}"
        else:
            return f"Failed to update artifact: {artifact_id}"
    
    elif action == "delete":
        if not artifact_id:
            return "Error: manage_artifact delete requires artifact_id"
        
        success = await service.delete_artifact(UUID(artifact_id), deleted_by=user_id)
        return f"Deleted artifact: {artifact_id} (success={success})"

    elif action == "append":
        # Specific to Docs (Tiptap)
        if not artifact_id or not content:
            return "Error: manage_artifact append requires artifact_id and content"
            
        # Retry loop for Optimistic Locking
        max_retries = 3
        for attempt in range(max_retries):
            artifact = await service.get_artifact(UUID(artifact_id))
            if not artifact:
                return f"Error: Artifact not found: {artifact_id}"
                
            # Merge Tiptap JSON
            current_content = artifact.content or {"type": "doc", "content": []}
            current_version = artifact.version
            new_items = []
            
            if isinstance(content, dict):
                if content.get("type") == "doc":
                    new_items = content.get("content", [])
                else:
                    new_items = [content]
            elif isinstance(content, list):
                new_items = content
                
            # Append
            import copy
            updated_content_dict = copy.deepcopy(current_content)
            if "content" not in updated_content_dict:
                updated_content_dict["content"] = []
            updated_content_dict["content"].extend(new_items)
            
            # Save
            updated_artifact = await service.update_artifact(
                UUID(artifact_id), 
                ArtifactUpdate(content=updated_content_dict, expected_version=current_version), 
                modified_by=user_id
            )
            
            if updated_artifact:
                return f"Appended to artifact: {artifact_id} (v{updated_artifact.version})"
            else:
                # Conflict occurred
                print(f"[Agent Tool] Version conflict for {artifact_id}, retrying ({attempt + 1}/{max_retries})...")
                continue
        
        return f"Error: Failed to append to artifact {artifact_id} after {max_retries} retries due to concurrent updates."

    elif action == "add_step":
        # Specific to Processes (Vue Flow)
        if not artifact_id or not content:
            return "Error: manage_artifact add_step requires artifact_id and content"

        # Retry loop
        max_retries = 3
        for attempt in range(max_retries):
            artifact = await service.get_artifact(UUID(artifact_id))
            if not artifact:
                return f"Error: Artifact not found: {artifact_id}"
                
            # Merge Vue Flow JSON
            current_content = artifact.content or {"nodes": [], "edges": []}
            current_version = artifact.version
            
            # Deepcopy to be safe
            import copy
            updated_content_dict = copy.deepcopy(current_content)
            
            current_nodes = updated_content_dict.get("nodes", [])
            current_edges = updated_content_dict.get("edges", [])
            
            new_nodes = content.get("nodes", [])
            new_edges = content.get("edges", [])
            
            # ID Collision Check
            existing_ids = set(n.get("id") for n in current_nodes if n.get("id"))
            for node in new_nodes:
                if node.get("id") in existing_ids:
                    return f"Error: Node ID conflict. Node ID '{node.get('id')}' already exists in artifact {artifact_id}."
            
            updated_final = {
                "nodes": current_nodes + new_nodes,
                "edges": current_edges + new_edges
            }
            
            # Save
            updated_artifact = await service.update_artifact(
                UUID(artifact_id), 
                ArtifactUpdate(content=updated_final, expected_version=current_version), 
                modified_by=user_id
            )
            
            if updated_artifact:
                return f"Added steps to artifact: {artifact_id} (v{updated_artifact.version})"
            else:
                 print(f"[Agent Tool] Version conflict for {artifact_id}, retrying ({attempt + 1}/{max_retries})...")
                 continue
                 
        return f"Error: Failed to add steps to artifact {artifact_id} after {max_retries} retries."
        
    return "Error: Unknown action"


async def _update_agent_trigger(
    session: AsyncSession,
    room_id: UUID,
    agent_config_id: UUID,
    new_params: Dict[str, Any],
) -> str:
    """
    Write trigger overrides to AgentRoomState (temporary) or
    RoomAgentLink/AgentConfig (permanent), respecting self_modification settings.
    """
    import structlog
    logger = structlog.get_logger()
    logger.info("agent_self_modify", room_id=str(room_id), params=new_params)

    # 1. Resolve current effective config
    config = await session.get(AgentConfig, agent_config_id)
    if not config:
        return "Error: Agent config not found"

    link_result = await session.exec(
        select(RoomAgentLink).where(
            RoomAgentLink.room_id == room_id,
            RoomAgentLink.agent_id == agent_config_id,
        )
    )
    link = link_result.first()

    effective = resolve_effective_trigger(config, link, None)
    self_mod = effective.get("self_modification", {})
    duration_hours = self_mod.get("duration_hours", 0)

    if duration_hours == 0:
        return "Self-modification is not allowed for this agent."

    # 2. Validate bounds
    bounds = self_mod.get("bounds") or {}
    validated_trigger = {}

    for key in ["message_count", "time_interval_mins", "user_silent_mins"]:
        if key in new_params and new_params[key] is not None:
            val = float(new_params[key])
            key_bounds = bounds.get(key, {})
            lower = key_bounds.get("min", 1)
            upper = key_bounds.get("max", 1000)
            val = max(lower, min(val, upper))
            if key == "message_count":
                val = int(val)
            validated_trigger[key] = val

    if not validated_trigger:
        return "No valid parameters to update."

    override_payload = {"trigger": validated_trigger}
    old_trigger = effective.get("trigger", {})

    # 3. Write
    if duration_hours == -1:
        # Permanent: write to RoomAgentLink (preferred) or AgentConfig
        target = link if link else config
        existing = (target.trigger_config or {}).copy()
        existing_trigger = existing.get("trigger", {})
        existing_trigger.update(validated_trigger)
        existing["trigger"] = existing_trigger
        target.trigger_config = existing
        session.add(target)

        entity_type = "room_agent_link" if link else "agent"
        entity_id = f"{room_id}:{agent_config_id}" if link else str(agent_config_id)
    else:
        # Temporary: write to AgentRoomState
        state_result = await session.exec(
            select(AgentRoomState).where(
                AgentRoomState.room_id == room_id,
                AgentRoomState.agent_id == agent_config_id,
            )
        )
        state = state_result.first()
        if not state:
            state = AgentRoomState(room_id=room_id, agent_id=agent_config_id)

        state.active_overrides = override_payload
        state.overrides_expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        state.updated_at = datetime.utcnow()
        session.add(state)

        entity_type = "agent_room_state"
        entity_id = f"{room_id}:{agent_config_id}"

    # 4. Audit log
    await log_change(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        action="agent_self_modify",
        actor_type="agent",
        old_value={"trigger": old_trigger},
        new_value=override_payload,
        metadata={"room_id": str(room_id), "duration_hours": duration_hours},
    )

    await session.commit()
    return f"Trigger updated: {validated_trigger}"

