from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, cast
from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.agents.std_agents import StudentAgent, TeacherAgent
from app.core.a2a import A2ADispatcher, A2AMessage, MessageType, AgentId
from app.core.trigger_resolver import resolve_effective_trigger
from app.factories.agent_factory import AgentFactory
from app.models.agent_config import AgentConfig, AgentType
from app.models.agent_room_state import AgentRoomState
from app.models.message import Message
from app.models.room import Room, RoomAgentLink
from app.repositories.agent_repo import AgentConfigRepository

from app.services.agent_tool_service import UPDATE_TRIGGER_TOOL_DEF, MANAGE_ARTIFACT_TOOL_DEF, handle_tool_calls

logger = structlog.get_logger()




# Helper to resolve keys
async def _resolve_agent_keys(
    session: AsyncSession, configs: List[AgentConfig]
) -> Dict[UUID, List[str]]:
    """
    Resolve decrypted API keys for a list of configs.
    Returns Map: ConfigID -> List[DecryptedKey]
    """
    from app.services.user_key_service import UserKeyService
    service = UserKeyService(session)
    keys_map = {}
    
    for config in configs:
        if not config:
            continue
        
        # If user_key_ids present, fetch them
        if config.user_key_ids:
            if not config.created_by:
                continue

            decrypted_keys = []
            for key_id in config.user_key_ids:
                try:
                    k = await service.get_decrypted_key(key_id, config.created_by)
                    if k:
                        decrypted_keys.append(k)
                except Exception as e:
                    logger.warning(f"Failed to resolve key {key_id}: {e}")
            
            if decrypted_keys:
                keys_map[config.id] = decrypted_keys
                
    return keys_map


async def _get_active_configs(
    session: AsyncSession, room_id: UUID
) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
    repo = AgentConfigRepository(session)
    return await repo.get_active_configs(room_id)



# Helper to publish to Redis instead of direct socket manager
async def publish_message(redis, room_id: str, message: str):
    await redis.publish(f"room_{room_id}", message)


async def publish_a2a_trace(
    redis, room_id: str, event_type: str, details: str,
    *, node_id: str = None, run_id: str = None,
):
    """
    Publish A2A trace event to WebSocket for frontend debugging/visualization.

    Supports two formats:
    - v1 (legacy): ``a2a_trace`` type with ``[A2A]|EVENT|details`` content.
    - v2 (workflow): ``workflow_trace`` type with ``node_id`` and ``run_id``
      for the frontend canvas to highlight active nodes.
    """
    import json
    from datetime import datetime

    ts = datetime.utcnow().isoformat() + "Z"

    # v1 legacy format (backward compat)
    payload_v1 = json.dumps({
        "type": "a2a_trace",
        "sender": f"[A2A {event_type}]",
        "content": f"[A2A]|{event_type}|{details}",
        "timestamp": ts,
        "room_id": room_id,
        "metadata": {"is_a2a": True, "event_type": event_type},
    })
    await redis.publish(f"room_{room_id}", payload_v1)

    # v2 workflow trace format (for canvas live-tracing)
    if node_id or run_id:
        payload_v2 = json.dumps({
            "type": "workflow_trace",
            "run_id": run_id or "",
            "room_id": room_id,
            "event_type": event_type,
            "node_id": node_id or "",
            "sub_status": details,
            "timestamp": ts,
        })
        await redis.publish(f"room_{room_id}", payload_v2)


async def run_agent_cycle_task(ctx, room_id: str, user_msg_id: str) -> None:
    """
    ARQ Task to run agent cycle.
    """
    session_factory = ctx.get("session_factory")
    if not session_factory:
        logger.error("worker_error", error="no_session_factory")
        return

    logger.info("agent_task_start", room_id=room_id)

    async with session_factory() as session:
        # Re-fetch message to ensure it exists and get fresh state
        user_msg = await session.get(Message, UUID(user_msg_id))
        if not user_msg:
            logger.warning("agent_task_skipped", reason="message_not_found", msg_id=user_msg_id)
            return

        # We also need a redis client for publishing results
        # ARQ ctx has a redis pool? Yes ctx['redis']
        redis = ctx["redis"]

        await process_agents_logic(room_id, session, redis, user_msg)


async def run_agent_time_task(ctx, room_id: str, trigger_role: str) -> None:  # noqa: C901
    """
    ARQ Task to run agent time-based trigger.
    trigger_role: "teacher" or "student"
    """
    session_factory = ctx.get("session_factory")
    if not session_factory:
        return

    logger.info("agent_time_task_start", room_id=room_id, role=trigger_role)
    async with session_factory() as session:
        redis = ctx["redis"]
        room = await session.get(Room, UUID(room_id))
        if not room:
            return

        # ── v2 Graph Engine Time Trigger ─────────────────────────────────
        logger.info("run_agent_time_task_dispatch", room_id=room_id)
        from app.models.message import Message
        # Create a mock message representing the timer event
        timer_msg = Message(
            room_id=room.id,
            content="[System Timer Event]",
            sender_id=None,
        )
        await _execute_v2_graph_workflow(session, redis, room, room_id, timer_msg)
        return


async def _execute_v2_graph_workflow(
    session: AsyncSession,
    redis,
    room,
    room_id: str,
    last_message: Message,
) -> None:
    """
    Execute the v2 LangGraph-based workflow engine for a room.

    Loads the RoomWorkflow graph_data, compiles it into a LangGraph,
    resolves all agent instances, and runs the graph.
    """
    from app.core.a2a.compiler import WorkflowCompiler
    from app.models.workflow import RoomWorkflow, WorkflowRun, WorkflowStatus
    from app.repositories.agent_repo import AgentConfigRepository
    from app.factories.agent_factory import AgentFactory

    # 1. Load workflow topology
    stmt = select(RoomWorkflow).where(RoomWorkflow.room_id == room.id)
    result = await session.exec(stmt)
    workflow = result.first()

    if not workflow or not workflow.is_active:
        logger.warning("v2_workflow_not_found", room_id=room_id)
        return

    # 2. Resolve all agent configs linked to this room
    repo = AgentConfigRepository(session)
    all_configs = await repo.get_all_active_configs(room.id)
    if not all_configs:
        return

    keys_map = await _resolve_agent_keys(session, all_configs)

    # 3. Build agent registry: agent_config.id -> AgentCore instance
    agent_registry = {}
    for config in all_configs:
        agent_keys = keys_map.get(config.id)
        agent = AgentFactory.create_agent(config, api_keys=agent_keys)
        if agent:
            agent_registry[str(config.id)] = agent

    # 4. Create a WorkflowRun record
    run = WorkflowRun(
        room_id=UUID(room_id),
        workflow_id=workflow.id,
        trigger_message_id=last_message.id if hasattr(last_message, 'id') else None,
        status=WorkflowStatus.RUNNING.value,
    )
    session.add(run)
    await session.flush()

    # 5. Compile and execute the graph
    compiler = WorkflowCompiler()

    # Action registry: broadcast action saves and publishes messages
    async def broadcast_action(state: dict) -> None:
        proposal = state.get("current_proposal", "")
        if proposal:
            await _save_and_broadcast(
                session, redis, proposal, room_id,
                AgentType.TEACHER, "[AI Agent]"
            )

    try:
        compiled_graph = compiler.compile(
            graph_data=workflow.graph_data,
            agent_registry=agent_registry,
            action_registry={"broadcast": broadcast_action},
        )

        # Build initial state from the triggering message
        initial_state = {
            "messages": [{
                "type": "user_message",
                "sender_id": str(last_message.sender_id) if hasattr(last_message, 'sender_id') else "user",
                "content": last_message.content or "",
            }],
            "current_proposal": None,
            "evaluation_result": None,
            "shared_memory": {"room_id": room_id},
            "_cycle_count": 0,
            "_active_node_id": None,
        }

        # Publish trace: workflow started
        await publish_a2a_trace(redis, room_id, "WORKFLOW_START", f"Workflow '{workflow.name}' triggered")

        result = await compiled_graph.ainvoke(initial_state)

        # Update run status
        run.status = WorkflowStatus.COMPLETED.value
        from datetime import datetime as dt
        run.completed_at = dt.utcnow()
        session.add(run)
        await session.commit()

        await publish_a2a_trace(redis, room_id, "WORKFLOW_END", "Workflow completed ✓")
        logger.info("v2_workflow_completed", room_id=room_id, run_id=str(run.id))

    except Exception as e:
        run.status = WorkflowStatus.FAILED.value
        run.error_message = str(e)[:500]
        session.add(run)
        await session.commit()

        await publish_a2a_trace(redis, room_id, "WORKFLOW_ERROR", f"Workflow failed: {str(e)[:80]}")
        logger.error("v2_workflow_failed", room_id=room_id, error=str(e))


async def process_agents_logic(
    room_id: str, session: AsyncSession, redis, last_message: Message
) -> None:
    """
    Trigger Agent logic.
    Executes LangGraph-based dynamic workflow engine.
    """
    room = await session.get(Room, UUID(room_id))  # type: ignore[func-returns-value]
    if not room or room.ai_mode == "off":
        return

    logger.info("process_agents_logic_v2_graph", room_id=room_id)
    await _execute_v2_graph_workflow(session, redis, room, room_id, last_message)





async def _save_and_broadcast(session, redis, content, room_id, agent_type, prefix) -> None:
    msg = Message(content=content, room_id=UUID(room_id), agent_type=agent_type)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    timestamp = msg.created_at.isoformat() + "Z"

    # Broadcast via Redis Pub/Sub as JSON matching SocketMessage
    import json
    payload = json.dumps({
        "type": "message",
        "sender": prefix,  # e.g. "[Student AI]"
        "content": content,
        "timestamp": timestamp,
        "room_id": str(room_id),
        "metadata": {
            "is_ai": True, 
            "agent_type": agent_type.value if hasattr(agent_type, "value") else str(agent_type)
        }
    })
    await publish_message(redis, room_id, payload)


async def check_and_process_time_triggers(room_id: str, session: AsyncSession, arq_pool) -> None:
    """
    Fast check for time-based triggers.
    Supports time_interval_mins and user_silent_mins with OR/AND logic.
    """
    room = await session.get(Room, UUID(room_id))  # type: ignore[func-returns-value]
    if not room or room.ai_mode == "off":
        return

    teacher_config, student_config = await _get_active_configs(session, room.id)
    if not teacher_config and not student_config:
        return

    repo = AgentConfigRepository(session)
    silence_duration, t_since, s_since = await repo.get_time_context(UUID(room_id))

    teacher_action = False
    student_action = False

    for config, since in [(teacher_config, t_since), (student_config, s_since)]:
        if not config:
            continue

        state = await repo.get_or_create_state(UUID(room_id), config.id)
        link = await repo.get_room_agent_link(UUID(room_id), config.id)

        effective = resolve_effective_trigger(config, link, state)
            
        trigger = effective.get("trigger", {})
        logic = effective.get("logic", "or")
        enabled = trigger.get("enabled_conditions", [])

        # Check time-based trigger conditions
        time_results = []

        if "time_interval_mins" in enabled:
            interval = trigger.get("time_interval_mins")
            if interval and since >= (interval * 60):
                time_results.append(True)
            else:
                time_results.append(False)

        if "user_silent_mins" in enabled:
            threshold = trigger.get("user_silent_mins")
            if threshold and silence_duration >= (threshold * 60):
                time_results.append(True)
            else:
                time_results.append(False)

        should_fire = False
        if time_results:
            if logic == "and":
                should_fire = all(time_results)
            else:
                should_fire = any(time_results)

        if should_fire:
            if config.type == AgentType.TEACHER:
                teacher_action = True
            else:
                student_action = True

    if not teacher_action and not student_action:
        return

    if arq_pool:
        if teacher_action:
            await arq_pool.enqueue_job("run_agent_time_task", room_id, "teacher")
        elif student_action:
            await arq_pool.enqueue_job("run_agent_time_task", room_id, "student")
    else:
        logger.warning("time_trigger_skipped", reason="no_arq_pool")


async def _get_time_context(session: AsyncSession, room_id: UUID) -> Tuple[float, float, float]:
    repo = AgentConfigRepository(session)
    return await repo.get_time_context(room_id)
