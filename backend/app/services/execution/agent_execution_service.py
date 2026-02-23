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
from app.services.orchestration.agent_orchestrator import AgentOrchestrator

logger = structlog.get_logger()



def _apply_state_reset_if_needed(state: AgentRoomState, effective_trigger: dict) -> bool:
    """Checks state_reset config and resets counters if the interval has passed."""
    reset_config = effective_trigger.get("state_reset", {})
    if not reset_config.get("enabled"):
        return False

    interval_days = reset_config.get("interval_days", 1)
    reset_time_str = reset_config.get("reset_time", "00:00")
    
    try:
        reset_hour, reset_minute = map(int, reset_time_str.split(':'))
    except Exception:
        return False

    overrides = state.active_overrides or {}
    last_reset_str = overrides.get("_last_reset_at")
    now = datetime.utcnow()

    if last_reset_str:
        try:
            last_reset = datetime.fromisoformat(last_reset_str)
        except Exception:
            last_reset = datetime.min
    else:
        # First time checking, initialize to yesterday to trigger immediately
        last_reset = now - timedelta(days=interval_days)

    next_reset_date = last_reset.date() + timedelta(days=interval_days)
    next_reset = datetime(
        next_reset_date.year, next_reset_date.month, next_reset_date.day, 
        reset_hour, reset_minute
    )

    if now >= next_reset:
        state.message_count_since_last_reply = 0
        state.monologue_count = 0
        state.is_sleeping = False
        if not state.active_overrides:
            state.active_overrides = {}
        state.active_overrides["_last_reset_at"] = now.isoformat()
        return True

    return False


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

async def get_message_count_gap(room_id: UUID, session: AsyncSession) -> int:
    repo = AgentConfigRepository(session)
    return await repo.get_message_count_gap(room_id)


async def _get_active_configs(
    session: AsyncSession, room_id: UUID
) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
    repo = AgentConfigRepository(session)
    return await repo.get_active_configs(room_id)


async def _get_history(
    session: AsyncSession,
    room_id: UUID,
    teacher_config: Optional[AgentConfig],
    student_config: Optional[AgentConfig],
) -> List[Message]:
    repo = AgentConfigRepository(session)
    limit = max(
        teacher_config.context_window if teacher_config else 10,
        student_config.context_window if student_config else 10,
    )
    return await repo.get_history(room_id, limit)


# Helper to publish to Redis instead of direct socket manager
async def publish_message(redis, room_id: str, message: str):
    await redis.publish(f"room_{room_id}", message)


async def publish_a2a_trace(redis, room_id: str, event_type: str, details: str):
    """
    Publish A2A trace event to WebSocket for frontend debugging/visualization.
    
    Sends JSON matching SocketMessage format so frontend can parse it.
    Frontend detects A2A traces by checking if content starts with "[A2A]".
    """
    import json
    payload = json.dumps({
        "type": "a2a_trace",
        "sender": f"[A2A {event_type}]",
        "content": f"[A2A]|{event_type}|{details}",  # Frontend parses this
        "timestamp": "",
        "room_id": room_id,
        "metadata": {"is_a2a": True, "event_type": event_type}
    })
    await redis.publish(f"room_{room_id}", payload)


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

        teacher_config, student_config = await _get_active_configs(session, room.id)
        history = await _get_history(session, UUID(room_id), teacher_config, student_config)

        # Resolve keys
        configs_to_resolve = []
        if teacher_config: configs_to_resolve.append(teacher_config)
        if student_config: configs_to_resolve.append(student_config)
        keys_map = await _resolve_agent_keys(session, configs_to_resolve)

        if trigger_role == "teacher" and teacher_config:
            t_keys = keys_map.get(teacher_config.id)
            agent = AgentFactory.create_agent(teacher_config, api_keys=t_keys)
            if not agent:
                return
            t_agent = cast(TeacherAgent, agent)
            response = await t_agent.generate_reply(history, tools=[UPDATE_TRIGGER_TOOL_DEF])

            if isinstance(response, str):
                await _save_and_broadcast(
                    session, redis, response, room_id, AgentType.TEACHER, "[Teacher AI]"
                )
            elif isinstance(response, list):
                logger.info(
                    "agent_tool_use", role="teacher", tool_count=len(response), room_id=str(room.id)
                )
                await handle_tool_calls(session, room.id, response)

        elif trigger_role == "student" and student_config:
            # Student Logic
            s_keys = keys_map.get(student_config.id)
            s_agent_core = AgentFactory.create_agent(student_config, api_keys=s_keys)
            if s_agent_core:
                s_agent = cast(StudentAgent, s_agent_core)
                proposal = await s_agent.generate_proposal(history)

                # Teacher Eval (if teacher exists)
                if teacher_config:
                    # Resolve teacher keys again (already in map)
                    t_keys = keys_map.get(teacher_config.id)
                    t_agent_core = AgentFactory.create_agent(teacher_config, api_keys=t_keys)
                    
                    # Ensure teacher has SOME key (legacy or new)
                    if t_agent_core:
                        t_agent_eval = cast(TeacherAgent, t_agent_core)
                        context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
                        logger.info(
                            "agent_decision",
                            role="teacher",
                            action="evaluate_proposal",
                            proposal_preview=proposal[:50],
                        )
                        if await t_agent_eval.evaluate_student_proposal(proposal, context_str):
                            logger.info(
                                "agent_decision", role="teacher", action="proposal_approved"
                            )
                            await _save_and_broadcast(
                                session, redis, proposal, room_id, AgentType.STUDENT, "[Student AI]"
                            )
                    else:
                        logger.info("agent_decision", role="teacher", action="proposal_denied")


async def process_agents_logic(
    room_id: str, session: AsyncSession, redis, last_message: Message
) -> None:
    """
    Trigger Agent logic with AgentRoomState lifecycle management.
    """
    room = await session.get(Room, UUID(room_id))  # type: ignore[func-returns-value]
    if not room or room.ai_mode == "off":
        return

    teacher_config, student_config = await _get_active_configs(session, room.id)

    # Resolve Keys
    active_configs = []
    if teacher_config: active_configs.append(teacher_config)
    if student_config: active_configs.append(student_config)

    if not active_configs:
        return

    keys_map = await _resolve_agent_keys(session, active_configs)
    repo = AgentConfigRepository(session)

    # --- AgentRoomState: update on user message ---
    is_user_message = last_message.agent_type is None
    states = {}
    links = {}
    for config in active_configs:
        state = await repo.get_or_create_state(UUID(room_id), config.id)
        link = await repo.get_room_agent_link(UUID(room_id), config.id)
        states[config.id] = state
        links[config.id] = link

        if is_user_message:
            state.is_sleeping = False
            state.monologue_count = 0
            state.message_count_since_last_reply += 1
            state.last_user_message_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()
            session.add(state)

    await session.flush()

    msg_gap = await get_message_count_gap(UUID(room_id), session)

    # Identify Roles
    teacher_config = next((c for c in active_configs if c.type == AgentType.TEACHER), None)
    student_config = next((c for c in active_configs if c.type == AgentType.STUDENT), None)

    # Resolve context window from effective trigger
    max_window = 10
    for config in active_configs:
        state = states.get(config.id)
        effective = resolve_effective_trigger(
            config, links.get(config.id), state
        )
        if state and _apply_state_reset_if_needed(state, effective):
            state.version += 1
            session.add(state)
            
        ctx = effective.get("trigger", {}).get("context_strategy", {})
        if ctx.get("type") == "all":
            max_window = max(max_window, 9999)
        else:
            max_window = max(max_window, ctx.get("n", config.context_window))

    hist_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(max_window)
    )
    hist_result = await session.exec(hist_query)
    history = list(reversed(hist_result.all()))

    # Initialize Agents Map
    agents = AgentFactory.create_agents_map(teacher_config, student_config, keys_map=keys_map)

    # Build config map with state/link for orchestrator
    config_map = {}
    state_map = {}
    link_map = {}
    if teacher_config:
        config_map[AgentType.TEACHER] = teacher_config
        state_map[AgentType.TEACHER] = states.get(teacher_config.id)
        link_map[AgentType.TEACHER] = links.get(teacher_config.id)
    if student_config:
        config_map[AgentType.STUDENT] = student_config
        state_map[AgentType.STUDENT] = states.get(student_config.id)
        link_map[AgentType.STUDENT] = links.get(student_config.id)

    # Orchestration Logic — pass state and link
    decision = await AgentOrchestrator.decide_turn(
        room, agents, config_map, history, msg_gap,
        state_map=state_map, link_map=link_map,
    )

    if not decision:
        return

    # Execute Decision
    role = decision["role"]
    action = decision["action"]
    agent = decision["agent"]
    config = decision.get("config")
    state = states.get(config.id) if config else None
    link = links.get(config.id) if config else None

    if role == AgentType.TEACHER and action == "reply":
        executed = await _execute_teacher_turn(
            session, redis, room, agent, teacher_config, True, history, room_id,
            agent_config_id=teacher_config.id if teacher_config else None,
        )
        if executed and state:
            await _post_agent_speak(session, state, config, link)

    elif role == AgentType.STUDENT and action == "propose":
        await _execute_student_turn(
            session, redis, room, agent, student_config, True,
            agents.get(AgentType.TEACHER), history, room_id,
        )
        s_state = states.get(student_config.id) if student_config else None
        if s_state and student_config:
            await _post_agent_speak(session, s_state, student_config, links.get(student_config.id))

    # Notify External Agents
    await _notify_external_agents(session, redis, room, history, room_id)


async def _post_agent_speak(
    session: AsyncSession, state: AgentRoomState, config: AgentConfig,
    link: Optional[RoomAgentLink] = None,
) -> None:
    """
    After an agent speaks: update counters and check close conditions.
    """
    state.monologue_count += 1
    state.message_count_since_last_reply = 0
    state.last_agent_message_at = datetime.utcnow()
    state.updated_at = datetime.utcnow()

    # Check close conditions
    effective = resolve_effective_trigger(config, link, state)
    close = effective.get("close", {})
    strategy = close.get("strategy", "none")

    if strategy == "agent_monologue":
        limit = close.get("monologue_limit", 3)
        if limit and state.monologue_count >= limit:
            state.is_sleeping = True
            logger.info("agent_sleeping", agent_id=str(config.id), reason="monologue_limit")

    elif strategy == "user_timeout":
        # This is checked in time triggers, not here
        pass

    state.version += 1
    session.add(state)
    await session.flush()


async def _execute_teacher_turn(
    session, redis, room, teacher_agent, teacher_config, should_run, history, room_id,
    agent_config_id=None,
) -> bool:
    can_teacher = room.ai_mode in ["teacher_only", "both"]
    if can_teacher and teacher_agent and should_run:
        logger.info(
            "agent_decision", role="teacher", action="reply_start", room_id=str(room.id)
        )

        t_agent = cast(TeacherAgent, teacher_agent)
        response = await t_agent.generate_reply(history, tools=[UPDATE_TRIGGER_TOOL_DEF, MANAGE_ARTIFACT_TOOL_DEF])

        if isinstance(response, list):  # List[ToolCall]
            logger.info(
                "agent_tool_use", role="teacher", tool_count=len(response), room_id=str(room.id)
            )
            tool_results = await handle_tool_calls(
                session, room.id, response, agent_config_id=agent_config_id
            )

            if tool_results:
                results_str = "\n".join(tool_results)
                await _save_and_broadcast(
                    session, redis, f"Tool Output:\n{results_str}", room_id, AgentType.TEACHER, "[System]"
                )

            return True

        elif isinstance(response, str):
            await _save_and_broadcast(
                session, redis, response, room_id, AgentType.TEACHER, "[Teacher AI]"
            )
            return True

    return False


async def _execute_student_turn(
    session,
    redis,
    room,
    student_agent,
    student_config,
    should_run,
    teacher_agent,
    history,
    room_id,
):
    """
    Execute student turn using A2A Protocol via A2AOrchestrator.
    
    Flow:
    1. Student generates proposal
    2. Orchestrator handles Student -> Teacher evaluation
    3. If approved, save and broadcast the message
    """
    # Import here to avoid circular imports
    from app.services.a2a_orchestrator import A2AOrchestrator
    from app.core.a2a import A2AMessageStore
    
    can_student = room.ai_mode == "both"
    if can_student and student_agent and teacher_agent and should_run:
            logger.info(
                "agent_decision", role="student", action="propose_start", room_id=str(room.id)
            )
            s_agent = cast(StudentAgent, student_agent)
            t_agent = cast(TeacherAgent, teacher_agent)
            
            # Generate proposal
            proposal = await s_agent.generate_proposal(history)
            context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])

            # === A2A Protocol Flow via Orchestrator ===
            orchestrator = A2AOrchestrator()
            store = A2AMessageStore(session)
            orchestrator.register_agents(t_agent, s_agent, store)

            # A2A Trace: Student proposing
            await publish_a2a_trace(
                redis, room_id, "PROPOSAL", f"Student drafted: {(proposal or '')[:80]}..."
            )

            # A2A Trace: Sending to teacher
            await publish_a2a_trace(
                redis, room_id, "EVAL_REQUEST", "Student → Teacher: Requesting evaluation"
            )

            # Request evaluation from Teacher
            eval_result = await orchestrator.request_evaluation(proposal, context_str, room_id)

            if orchestrator.is_approved(eval_result):
                logger.info("agent_decision", role="teacher", action="proposal_approved")
                
                # A2A Trace: Approved
                await publish_a2a_trace(
                    redis, room_id, "APPROVED", "Teacher approved student's proposal ✓"
                )
                
                # Complete protocol flow
                await orchestrator.process_approval(eval_result)
                
                # Save and broadcast the approved message
                await _save_and_broadcast(
                    session, redis, proposal, room_id, AgentType.STUDENT, "[Student AI]"
                )
            else:
                logger.info("agent_decision", role="teacher", action="proposal_denied")
                
                # A2A Trace: Denied
                await publish_a2a_trace(
                    redis, room_id, "DENIED", "Teacher rejected student's proposal ✗"
                )


async def _notify_external_agents(
    session: AsyncSession,
    redis,
    room: Room,
    history: List[Message],
    room_id: str,
) -> None:
    """
    Notify external agents of new messages and process their responses.
    
    External agents receive the latest message via their webhook URL
    and can respond with their own messages to be broadcast.
    """
    repo = AgentConfigRepository(session)
    external_configs = await repo.get_external_configs(room.id)
    
    if not external_configs:
        return
    
    # Import adapter
    from app.core.a2a.external_adapter import ExternalAgentAdapter
    from app.core.a2a.models import A2AMessage, MessageType
    
    # Get the latest message to send to external agents
    if not history:
        return
    
    last_msg = history[-1]
    
    for ext_config in external_configs:
        try:
            adapter = ExternalAgentAdapter(ext_config)
            
            # Create A2A message from the latest chat message
            a2a_msg = A2AMessage(
                type=MessageType.USER_MESSAGE,
                sender_id=last_msg.sender_id or "user",
                recipient_id=str(ext_config.id),
                content=last_msg.content,
                metadata={
                    "room_id": room_id,
                    "agent_name": last_msg.sender if hasattr(last_msg, 'sender') else None,
                    "history_length": len(history),
                },
            )
            
            # Send to external agent and get response
            response = await adapter.receive_message(a2a_msg)
            
            if response and response.content:
                # Broadcast response to room
                import json
                payload = json.dumps({
                    "type": "a2a_external_message",
                    "agent_id": str(ext_config.id),
                    "agent_name": ext_config.name,
                    "agent_type": ext_config.type,
                    "content": response.content,
                    "message_id": str(response.id),
                    "timestamp": response.created_at.isoformat(),
                })
                await publish_message(redis, room_id, payload)
                
                logger.info(
                    "external_agent_responded",
                    agent_id=str(ext_config.id),
                    agent_name=ext_config.name,
                    room_id=room_id,
                )
                
        except Exception as e:
            logger.warning(
                "external_agent_notify_failed",
                agent_id=str(ext_config.id),
                error=str(e),
            )


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
    Fast check for time-based triggers using new trigger config structure.
    Supports time_interval_mins and user_silent_mins with OR/AND logic.
    Also checks user_timeout close condition.
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

        # Skip sleeping agents
        if state.is_sleeping:
            # But check user_timeout close condition — if user has been silent
            # and agent is sleeping, nothing changes. If user spoke, sleep is
            # already cleared in process_agents_logic.
            continue

        effective = resolve_effective_trigger(config, link, state)
        if _apply_state_reset_if_needed(state, effective):
            state.version += 1
            session.add(state)
            await session.flush()
            
        trigger = effective.get("trigger", {})
        logic = effective.get("logic", "or")
        enabled = trigger.get("enabled_conditions", [])
        close = effective.get("close", {})

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

        # Also check message_count if it's an AND-logic scenario
        if logic == "and" and "message_count" in enabled:
            mc = trigger.get("message_count")
            if mc:
                time_results.append(state.message_count_since_last_reply >= mc)

        should_fire = False
        if time_results:
            if logic == "and":
                should_fire = all(time_results)
            else:
                should_fire = any(time_results)

        # Check user_timeout close condition
        if close.get("strategy") == "user_timeout":
            timeout = close.get("timeout_mins")
            if timeout and state.last_agent_message_at:
                since_agent = (datetime.utcnow() - state.last_agent_message_at).total_seconds()
                if since_agent >= (timeout * 60) and silence_duration >= (timeout * 60):
                    state.is_sleeping = True
                    state.updated_at = datetime.utcnow()
                    state.version += 1
                    session.add(state)
                    await session.flush()
                    logger.info("agent_sleeping", agent_id=str(config.id), reason="user_timeout")
                    continue

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
