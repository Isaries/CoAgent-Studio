from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.scheduler_utils import is_agent_scheduled_now
from app.core.socket_manager import ConnectionManager
from app.core.specialized_agents import StudentAgent, TeacherAgent
from app.models.agent_config import AgentConfig, AgentType
from app.models.message import Message
from app.models.room import Room
from app.services.agent_tool_service import UPDATE_TRIGGER_TOOL_DEF, handle_tool_calls


async def get_message_count_gap(room_id: UUID, session: AsyncSession) -> int:
    """Count user messages since the last Agent message."""
    query = (
        select(Message)
        .where(Message.room_id == room_id)
        .where(Message.agent_type.isnot(None))
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    result = await session.exec(query)
    last_agent_msg = result.first()

    count_query = (
        select(col(Message.id))
        .where(Message.room_id == room_id)
        .where(Message.agent_type.is_(None))
    )
    if last_agent_msg:
        count_query = count_query.where(Message.created_at > last_agent_msg.created_at)

    results = await session.exec(count_query)
    return len(results.all())


async def _get_active_configs(
    session: AsyncSession, course_id: UUID
) -> Tuple[Optional[AgentConfig], Optional[AgentConfig]]:
    query = (
        select(AgentConfig)
        .where(AgentConfig.course_id == course_id)
        .order_by(AgentConfig.updated_at.desc())
    )
    result = await session.exec(query)
    configs = result.all()

    teacher_config = next((c for c in configs if c.type == AgentType.TEACHER and c.is_active), None)
    if not teacher_config:
        teacher_config = next((c for c in configs if c.type == AgentType.TEACHER), None)

    student_config = next((c for c in configs if c.type == AgentType.STUDENT and c.is_active), None)
    if not student_config:
        student_config = next((c for c in configs if c.type == AgentType.STUDENT), None)

    # Check schedules
    if teacher_config and not is_agent_scheduled_now(teacher_config):
        teacher_config = None
    if student_config and not is_agent_scheduled_now(student_config):
        student_config = None

    return teacher_config, student_config


async def _should_run_by_message_count(config: AgentConfig, msg_gap: int) -> bool:
    if not config:
        return False
    trigger = config.trigger_config or {}
    if trigger.get("type") == "message_count":
        return msg_gap >= trigger.get("value", 10)
    elif not trigger:
        return True  # Default behavior if no trigger config
    return False


async def _get_history(
    session: AsyncSession,
    room_id: UUID,
    teacher_config: Optional[AgentConfig],
    student_config: Optional[AgentConfig],
) -> List[Message]:
    limit = max(
        teacher_config.context_window if teacher_config else 10,
        student_config.context_window if student_config else 10,
    )
    hist_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    hist_result = await session.exec(hist_query)
    return list(reversed(hist_result.all()))


async def process_agents(
    room_id: str, session: AsyncSession, manager: ConnectionManager, last_message: Message
):
    """
    Trigger Agent logic.
    """
    room = await session.get(Room, UUID(room_id))
    if not room or room.ai_mode == "off":
        return

    teacher_config, student_config = await _get_active_configs(session, room.course_id)

    # Refactor: Support generic list of configs
    # We still need to distinguish roles for some specific "Interaction" logic (like student proposing to teacher).
    # But for "Triggering" and "Replying", we can be more generic.

    # Let's keep the _get_active_configs structure for now but iterate over them?
    # Actually, let's fetch ALL active configs.

    query = (
        select(AgentConfig)
        .where(AgentConfig.course_id == room.course_id)
        .where(AgentConfig.is_active == True)
    )
    result = await session.exec(query)
    all_configs = result.all()

    # Filter by schedule
    active_configs = []
    for c in all_configs:
        if is_agent_scheduled_now(c):
            active_configs.append(c)

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
    agents = {}
    for config in active_configs:
        if config.encrypted_api_key:
            # Polymorphic Agent Creation could be here
            if config.type == AgentType.TEACHER:
                agents[config.type] = TeacherAgent(
                    provider=config.model_provider,
                    api_key=config.encrypted_api_key,
                    system_prompt=config.system_prompt,
                    model=config.model,
                )
            elif config.type == AgentType.STUDENT:
                agents[config.type] = StudentAgent(
                    provider=config.model_provider,
                    api_key=config.encrypted_api_key,
                    system_prompt=config.system_prompt,
                    model=config.model,
                )
            # Add other types here

    # Orchestration Logic

    # 1. Independent Triggers (e.g. Teacher deciding to speak, or generic agent)
    # Currently Teacher logic covers "Reply directly"

    teacher_agent = agents.get(AgentType.TEACHER)
    if teacher_agent and teacher_config:
        should_run = await _should_run_by_message_count(teacher_config, msg_gap)
        if await _execute_teacher_turn(
            session, manager, room, teacher_agent, teacher_config, should_run, history, room_id
        ):
            return  # Teacher spoke, end turn

    # 2. Dependent Triggers (Student proposes)
    student_agent = agents.get(AgentType.STUDENT)
    if student_agent and student_config and teacher_agent:
        # Student needs Teacher to exist to evaluate
        should_run = await _should_run_by_message_count(student_config, msg_gap)
        await _execute_student_turn(
            session,
            manager,
            room,
            student_agent,
            student_config,
            should_run,
            teacher_agent,
            history,
            room_id,
        )


async def _execute_teacher_turn(
    session, manager, room, teacher_agent, teacher_config, should_run, history, room_id
) -> bool:
    can_teacher = room.ai_mode in ["teacher_only", "both"]
    if can_teacher and teacher_agent and should_run:
        force_reply = teacher_config.trigger_config is not None
        if force_reply or teacher_agent.should_reply(history, room.ai_frequency):
            print("[Agent] Teacher deciding to reply...")

            # Pass tools to teacher agent
            # TeacherAgent.generate_reply now accepts tools
            response = await teacher_agent.generate_reply(history, tools=[UPDATE_TRIGGER_TOOL_DEF])

            if isinstance(response, list):  # List[ToolCall]
                print(f"[Agent] Teacher triggered {len(response)} tools.")
                await handle_tool_calls(session, room.course_id, response)
                return True  # Teacher used a tool, treat as a turn taken

            elif isinstance(response, str):
                await _save_and_broadcast(
                    session, manager, response, room_id, AgentType.TEACHER, "[Teacher AI]"
                )
                return True

    return False


async def _execute_student_turn(
    session,
    manager,
    room,
    student_agent,
    student_config,
    should_run,
    teacher_agent,
    history,
    room_id,
):
    can_student = room.ai_mode == "both"
    if can_student and student_agent and teacher_agent and should_run:
        force_reply = student_config.trigger_config is not None
        if force_reply or student_agent.should_reply(history, room.ai_frequency):
            print("[Agent] Student proposing contribution...")
            proposal = await student_agent.generate_proposal(history)

            # Ask Teacher Evaluation
            context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
            print(f"[Agent] Teacher evaluating proposal: {proposal[:50]}...")
            if await teacher_agent.evaluate_student_proposal(proposal, context_str):
                print("[Agent] Proposal APPROVED.")
                await _save_and_broadcast(
                    session, manager, proposal, room_id, AgentType.STUDENT, "[Student AI]"
                )
            else:
                print("[Agent] Proposal DENIED by Teacher.")


async def _save_and_broadcast(session, manager, content, room_id, agent_type, prefix):
    msg = Message(content=content, room_id=UUID(room_id), agent_type=agent_type)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    timestamp = msg.created_at.isoformat() + "Z"
    await manager.broadcast(f"{prefix}|{timestamp}|{content}", room_id)


async def check_and_process_time_triggers(
    room_id: str, session: AsyncSession, manager: ConnectionManager
):
    room = await session.get(Room, UUID(room_id))
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

    history = await _get_history(session, UUID(room_id), teacher_config, student_config)

    if teacher_action and teacher_config.has_api_key:
        agent = TeacherAgent(
            teacher_config.model_provider,
            teacher_config.encrypted_api_key,
            teacher_config.system_prompt,
            teacher_config.model,
        )
        reply = await agent.generate_reply(history)
        await _save_and_broadcast(
            session, manager, reply, room_id, AgentType.TEACHER, "[Teacher AI]"
        )

    elif student_action:
        # Construct Agents
        key = student_config.encrypted_api_key or (
            teacher_config.encrypted_api_key if teacher_config else None
        )
        if key:
            s_agent = StudentAgent(
                student_config.model_provider,
                key,
                student_config.system_prompt,
                student_config.model,
            )
            proposal = await s_agent.generate_proposal(history)

            # Teacher Eval
            if teacher_config and teacher_config.has_api_key:
                t_agent = TeacherAgent(
                    teacher_config.model_provider,
                    teacher_config.encrypted_api_key,
                    teacher_config.system_prompt,
                    teacher_config.model,
                )
                context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
                if await t_agent.evaluate_student_proposal(proposal, context_str):
                    await _save_and_broadcast(
                        session, manager, proposal, room_id, AgentType.STUDENT, "[Student AI]"
                    )


async def _get_time_context(session: AsyncSession, room_id: UUID) -> Tuple[float, float, float]:
    last_msg_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_msg = (await session.exec(last_msg_query)).first()

    silence_duration = 999999
    if last_msg and last_msg.created_at:
        try:
            silence_duration = (datetime.utcnow() - last_msg.created_at).total_seconds()
        except Exception:
            # Fallback for TZ mixup
            silence_duration = (
                datetime.utcnow() - last_msg.created_at.replace(tzinfo=None)
            ).total_seconds()

    # Last Teacher
    t_last = (
        await session.exec(
            select(Message)
            .where(Message.room_id == room_id, Message.agent_type == AgentType.TEACHER)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).first()
    t_since = (datetime.utcnow() - t_last.created_at).total_seconds() if t_last else 999999

    # Last Student
    s_last = (
        await session.exec(
            select(Message)
            .where(Message.room_id == room_id, Message.agent_type == AgentType.STUDENT)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).first()
    s_since = (datetime.utcnow() - s_last.created_at).total_seconds() if s_last else 999999

    return silence_duration, t_since, s_since


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
