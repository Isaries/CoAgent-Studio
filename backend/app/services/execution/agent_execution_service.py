from typing import List, Optional, Tuple, cast
from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.specialized_agents import StudentAgent, TeacherAgent
from app.core.a2a import A2ADispatcher, A2AMessage, MessageType, AgentId
from app.factories.agent_factory import AgentFactory
from app.models.agent_config import AgentConfig, AgentType
from app.models.message import Message
from app.models.room import Room
from app.repositories.agent_repo import AgentConfigRepository

# AgentToolService requires session, ensure imports are clean
from app.services.agent_tool_service import UPDATE_TRIGGER_TOOL_DEF, handle_tool_calls
from app.services.orchestration.agent_orchestrator import AgentOrchestrator

logger = structlog.get_logger()


async def get_message_count_gap(room_id: UUID, session: AsyncSession) -> int:
    repo = AgentConfigRepository(session)
    return await repo.get_message_count_gap(room_id)


async def _get_active_configs(
    session: AsyncSession, course_id: UUID
) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
    repo = AgentConfigRepository(session)
    return await repo.get_active_configs(course_id)


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

        teacher_config, student_config = await _get_active_configs(session, room.course_id)
        history = await _get_history(session, UUID(room_id), teacher_config, student_config)

        if trigger_role == "teacher" and teacher_config:
            agent = AgentFactory.create_agent(teacher_config)
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
                await handle_tool_calls(session, room.course_id, response)

        elif trigger_role == "student" and student_config:
            # Student Logic
            s_agent_core = AgentFactory.create_agent(student_config)
            if s_agent_core:
                s_agent = cast(StudentAgent, s_agent_core)
                proposal = await s_agent.generate_proposal(history)

                # Teacher Eval (if teacher exists)
                if teacher_config and teacher_config.has_api_key:
                    t_agent_core = AgentFactory.create_agent(teacher_config)
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
    Trigger Agent logic.
    """
    room = await session.get(Room, UUID(room_id))  # type: ignore[func-returns-value]
    if not room or room.ai_mode == "off":
        return

    teacher_config, student_config = await _get_active_configs(session, room.course_id)

    # Refactor: Support generic list of configs
    # We still need to distinguish roles for some specific "Interaction" logic (like student proposing to teacher).
    # But for "Triggering" and "Replying", we can be more generic.

    # Let's keep the _get_active_configs structure for now but iterate over them?
    # Actually, let's fetch ALL active configs.

    # We use repo at line 242 to get configs.
    # Logic below (querying all configs again) is redundant.
    # Removing redundant query logic.
    # query = (
    #     select(AgentConfig)
    #     .where(AgentConfig.course_id == room.course_id)
    #     .where(AgentConfig.is_active == True)
    # )
    # result = await session.exec(query)
    # all_configs = result.all()

    # Filter by schedule
    # Repo check already filters active, but we double check schedule here?
    # Actually Repo.get_active_configs returns specific teacher/student configs.
    # The logic below was previously querying ALL configs then filtering.
    # Now we have t_conf, s_conf from logic at line 242.
    # We can simplify active_configs construction:
    active_configs = []
    if teacher_config:
        active_configs.append(teacher_config)
    if student_config:
        active_configs.append(student_config)

    if not active_configs:
        return

    msg_gap = await get_message_count_gap(UUID(room_id), session)

    # We need to reconstruct the "teacher" and "student" for specific orchestration logic
    # (Student proposes -> Teacher evaluates).
    # This specific orchestration is "Role Based" interaction.
    # Future agents might just be "Independent Responders".

    # Identify Roles
    teacher_config = next((c for c in active_configs if c.type == AgentType.TEACHER), None)
    student_config = next((c for c in active_configs if c.type == AgentType.STUDENT), None)

    # Load history once
    # We need a unified context window? Or max of all?
    max_window = max((c.context_window for c in active_configs), default=10)

    hist_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(max_window)
    )
    hist_result = await session.exec(hist_query)
    history = list(reversed(hist_result.all()))

    # Initialize Agents Map
    agents = AgentFactory.create_agents_map(teacher_config, student_config)

    # Orchestration Logic
    # -------------------
    # Use Orchestrator to decide next action
    decision = await AgentOrchestrator.decide_turn(
        room,
        agents,
        {AgentType.TEACHER: teacher_config, AgentType.STUDENT: student_config},
        history,
        msg_gap,
    )

    if not decision:
        return

    # Execute Decision
    role = decision["role"]
    action = decision["action"]
    agent = decision["agent"]

    if role == AgentType.TEACHER and action == "reply":
        should_run = True  # Decided by Orchestrator
        if await _execute_teacher_turn(
            session, redis, room, agent, teacher_config, should_run, history, room_id
        ):
            return

    elif role == AgentType.STUDENT and action == "propose":
        should_run = True  # Decided by Orchestrator
        await _execute_student_turn(
            session,
            redis,
            room,
            agent,
            student_config,
            should_run,
            agents.get(AgentType.TEACHER),  # Need teacher instance
            history,
            room_id,
        )


async def _execute_teacher_turn(
    session, redis, room, teacher_agent, teacher_config, should_run, history, room_id
) -> bool:
    can_teacher = room.ai_mode in ["teacher_only", "both"]
    if can_teacher and teacher_agent and should_run:
        force_reply = teacher_config.trigger_config is not None
        if force_reply or teacher_agent.should_reply(history, room.ai_frequency):
            logger.info(
                "agent_decision", role="teacher", action="reply_start", room_id=str(room.id)
            )

            # Pass tools to teacher agent
            # TeacherAgent.generate_reply now accepts tools
            t_agent = cast(TeacherAgent, teacher_agent)
            response = await t_agent.generate_reply(history, tools=[UPDATE_TRIGGER_TOOL_DEF])

            if isinstance(response, list):  # List[ToolCall]
                logger.info(
                    "agent_tool_use", role="teacher", tool_count=len(response), room_id=str(room.id)
                )
                await handle_tool_calls(session, room.course_id, response)
                return True  # Teacher used a tool, treat as a turn taken

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
        force_reply = student_config.trigger_config is not None
        if force_reply or student_agent.should_reply(history, room.ai_frequency):
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
    Fast check. If trigger needed, enqueue job.
    """
    room = await session.get(Room, UUID(room_id))  # type: ignore[func-returns-value]
    if not room or room.ai_mode == "off":
        return

    teacher_config, student_config = await _get_active_configs(session, room.course_id)
    if not teacher_config and not student_config:
        return

    # Time Context
    silence_duration, t_since, s_since = await _get_time_context(session, UUID(room_id))

    # Check Triggers
    teacher_action = _check_time_trigger(teacher_config, t_since, silence_duration)
    student_action = False
    if student_config and not teacher_action:
        student_action = _check_time_trigger(student_config, s_since, silence_duration)

    if not teacher_action and not student_action:
        return

    # Action Needed -> Enqueue
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


def _check_time_trigger(config: AgentConfig, since: float, silence: float) -> bool:
    if not config:
        return False
    conf = config.trigger_config or {}
    if conf.get("type") == "time_interval":
        interval = float(conf.get("value", 60))
        return since >= interval
    elif conf.get("type") == "silence":
        threshold = float(conf.get("value", 60))
        return silence >= threshold
    return False
