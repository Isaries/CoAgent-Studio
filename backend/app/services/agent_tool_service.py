from typing import Any, List
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.llm_service import ToolCall
from app.models.agent_config import AgentConfig, AgentType
from app.models.room import RoomAgentLink

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


async def handle_tool_calls(session: AsyncSession, room_id: UUID, tool_calls: List[ToolCall], user_id: UUID = None) -> List[str]:
    """
    Handle tool calls executed by the Agent.
    Returns a list of result strings to be fed back to the agent or logged.
    """
    results = []
    for tool in tool_calls:
        if tool.name == "update_trigger":
            args = tool.arguments
            await _update_agent_trigger(
                session,
                room_id,
                str(args.get("target_agent", "")),
                str(args.get("trigger_type", "")),
                float(args.get("value", 0.0)),
            )
            results.append(f"Updated trigger for {args.get('target_agent')}")
            
        elif tool.name == "manage_artifact" and room_id:
            args = tool.arguments
            result = await _handle_manage_artifact(
                session,
                room_id,
                user_id or UUID("00000000-0000-0000-0000-000000000000"),  # System user fallback
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
    session: AsyncSession, room_id: UUID, target_role: str, type_: str, value: float
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
        .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
        .where(RoomAgentLink.room_id == room_id)
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

