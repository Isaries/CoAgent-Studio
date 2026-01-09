from datetime import datetime
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from zoneinfo import ZoneInfo

from app.core.socket_manager import ConnectionManager
from app.core.specialized_agents import StudentAgent, TeacherAgent
from app.models.agent_config import AgentConfig, AgentType
from app.models.message import Message
from app.models.room import Room


def is_agent_scheduled_now(config: AgentConfig) -> bool:
    """Check if agent is allowed to run at this current time (UTC+8)."""
    if not config.schedule_config:
        return True # Default to always active if no schedule

    schedule = config.schedule_config
    if not isinstance(schedule, dict):
        return True # Malformed

    # 1. Check Specific Rules (Priority: Override)
    # If ANY specific rule matches CURRENT DATE, we obey ONLY specific rules (ignore general).
    # If matches date but not time -> return False (Override implies "Only these times are allowed today")

    # Current Time in UTC+8
    tz = ZoneInfo("Asia/Taipei")
    now = datetime.now(tz)
    current_date_str = now.strftime("%Y-%m-%d")
    current_time = now.time()
    weekday = now.weekday() # 0=Mon, 6=Sun

    specific_rules = schedule.get("specific", [])
    if isinstance(specific_rules, list):
        todays_specifics = [r for r in specific_rules if r.get("date") == current_date_str]

        if todays_specifics:
            # We have at least one specific rule for today.
            # Check if *any* of them allow now.
            for rule in todays_specifics:
                try:
                    start = datetime.strptime(rule["start"], "%H:%M").time()
                    end = datetime.strptime(rule["end"], "%H:%M").time()
                    if start <= current_time <= end:
                        return True
                except:
                    continue
            return False # Specific rules exist for today but none match current time -> BLOCKED

    # 2. Check General Pattern (Fallback)
    general = schedule.get("general", {})
    if not general:
        # Support legacy format fallback if necessary, or just Default Open
        if "mode" in schedule and "general" not in schedule:
            general = schedule # Treat root as general
        else:
            return True # Default open if no general config

    mode = general.get("mode", "none")

    if mode == "none":
        return True

    # Global Date Range Check (common for range_daily and range_weekly)
    if mode in ["range_daily", "range_weekly"]:
        s_date = general.get("start_date")
        e_date = general.get("end_date")
        if s_date and e_date:
            if not (s_date <= current_date_str <= e_date):
                return False # Outside valid date range
        # If dates missing, assume open range? Or strictly require?
        # Let's assume open if missing, or strict. UI forces input.
        # But if user leaves blank, maybe valid? Let's check dates only if present.

    # Check Time Rules
    # If no rules exist, and mode is set, what to do?
    # UI shows "Agent will NOT be active". So return False.
    g_rules = general.get("rules", [])
    if not g_rules:
        # Backward compatibility: Check if start_time/end_time exist at root of general
        # If migration didn't happen perfect, logic might still be old.
        # But for new "Multiple" feature, we strictly check rules.
        # If user selected a mode but added no rules -> inactive.
        return False

    for rule in g_rules:
        try:
            start_str = rule.get("start_time")
            end_str = rule.get("end_time")

            if not start_str or not end_str:
                continue

            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()

            # Check Weekdays for Weekly Mode
            if mode == "range_weekly":
                allowed_days = rule.get("days", [])
                if weekday not in allowed_days:
                    continue

            # Time Check
            if start <= current_time <= end:
                return True # Matched a rule
        except:
            continue

    return False # No rules matched

async def get_message_count_gap(room_id: UUID, session: AsyncSession) -> int:
    """Count user messages since the last Agent message."""
    # Find last agent message
    query = select(Message).where(Message.room_id == room_id).where(Message.agent_type.isnot(None)).order_by(Message.created_at.desc()).limit(1)
    result = await session.exec(query)
    last_agent_msg = result.first()

    count_query = select(col(Message.id)).where(Message.room_id == room_id).where(Message.agent_type.is_(None))
    if last_agent_msg:
        count_query = count_query.where(Message.created_at > last_agent_msg.created_at)

    # Execute count
    # Note: SQLModel/SQLAlchemy counting might vary, executing simply
    results = await session.exec(count_query)
    return len(results.all())

async def process_agents(room_id: str, session: AsyncSession, manager: ConnectionManager, last_message: Message):
    """
    Trigger Agent logic.
    For now, we process sequentially. In production, use background tasks.
    """
    # 1. Get Room Settings
    room = await session.get(Room, UUID(room_id))
    if not room or room.ai_mode == "off":
        return

    # 2. Get Course Configs (Agents)
    query = select(AgentConfig).where(AgentConfig.course_id == room.course_id).order_by(AgentConfig.updated_at.desc())
    result = await session.exec(query)
    configs = result.all()

    # Select Active or Fallback to Latest
    teacher_config = next((c for c in configs if c.type == AgentType.TEACHER and c.is_active), None)
    if not teacher_config:
        teacher_config = next((c for c in configs if c.type == AgentType.TEACHER), None)

    student_config = next((c for c in configs if c.type == AgentType.STUDENT and c.is_active), None)
    if not student_config:
        student_config = next((c for c in configs if c.type == AgentType.STUDENT), None)

    # --- Check Schedules ---
    if teacher_config and not is_agent_scheduled_now(teacher_config):
        teacher_config = None # Disable if off-schedule
    if student_config and not is_agent_scheduled_now(student_config):
        student_config = None

    if not teacher_config and not student_config:
        return

    # --- Check Trigger Logic (Message Count) ---
    msg_gap = await get_message_count_gap(UUID(room_id), session)

    teacher_should_run = False
    if teacher_config:
        t_trigger = teacher_config.trigger_config or {}
        if t_trigger.get("type") == "message_count":
             if msg_gap >= t_trigger.get("value", 10):
                 teacher_should_run = True
        elif not t_trigger: # Fallback to existing logic if no trigger config? Or default off?
            # Let's keep existing logic (Probability/Mention) if no advanced config is present
            teacher_should_run = True

    student_should_run = False
    if student_config:
        s_trigger = student_config.trigger_config or {}
        if s_trigger.get("type") == "message_count":
             if msg_gap >= s_trigger.get("value", 10):
                 student_should_run = True
        elif not s_trigger:
            student_should_run = True

    # helper to process history
    limit = max(teacher_config.context_window if teacher_config else 10, student_config.context_window if student_config else 10)
    hist_query = select(Message).where(Message.room_id == UUID(room_id)).order_by(Message.created_at.desc()).limit(limit)
    hist_result = await session.exec(hist_query)
    history = list(reversed(hist_result.all()))

    teacher_agent = None
    if teacher_config and teacher_config.encrypted_api_key:
        teacher_agent = TeacherAgent(
            provider=teacher_config.model_provider,
            api_key=teacher_config.encrypted_api_key,
            system_prompt=teacher_config.system_prompt,
            model=teacher_config.model
        )

    student_agent = None
    if student_config: # Student might use Teacher's key if configured to shared
        key = student_config.encrypted_api_key or (teacher_config.encrypted_api_key if teacher_config else None)
        if key:
            student_agent = StudentAgent(
                provider=student_config.model_provider,
                api_key=key,
                system_prompt=student_config.system_prompt,
                model=student_config.model
            )

    # --- Orchestration Logic ---

    # 1. Teacher Turn
    can_teacher = room.ai_mode in ["teacher_only", "both"]
    if can_teacher and teacher_agent and teacher_should_run:
        # Check standard should_reply (Mention or Config Trigger satisfied)
        # If specific config satisfied (msg_count), we force True, otherwise use probability
        force_reply = (teacher_config.trigger_config is not None)

        if force_reply or teacher_agent.should_reply(history, room.ai_frequency):
            print("[Agent] Teacher deciding to reply...")
            reply = await teacher_agent.generate_reply(history)

            # Save & Broadcast
            msg = Message(content=reply, room_id=UUID(room_id), agent_type=AgentType.TEACHER)
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
            timestamp = msg.created_at.isoformat() + "Z"
            await manager.broadcast(f"[Teacher AI]|{timestamp}|{reply}", room_id)
            return

    # 2. Student Turn (only if Teacher didn't speak)
    can_student = room.ai_mode == "both"
    if can_student and student_agent and teacher_agent and student_should_run:
        force_reply = (student_config.trigger_config is not None)

        if force_reply or student_agent.should_reply(history, room.ai_frequency):
            print("[Agent] Student proposing contribution...")
            proposal = await student_agent.generate_proposal(history)

            # Ask Teacher for Permission
            context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
            print(f"[Agent] Teacher evaluating proposal: {proposal[:50]}...")
            is_approved = await teacher_agent.evaluate_student_proposal(proposal, context_str)

            if is_approved:
                print("[Agent] Proposal APPROVED.")
                msg = Message(content=proposal, room_id=UUID(room_id), agent_type=AgentType.STUDENT)
                session.add(msg)
                await session.commit()
                await session.refresh(msg)
                timestamp = msg.created_at.isoformat() + "Z"
                await manager.broadcast(f"[Student AI]|{timestamp}|{proposal}", room_id)
            else:
                print("[Agent] Proposal DENIED by Teacher.")

async def check_and_process_time_triggers(room_id: str, session: AsyncSession, manager: ConnectionManager):
    """
    Called periodically by background monitor to check time-based triggers.
    """
    # 1. Get Room Settings
    room = await session.get(Room, UUID(room_id))
    if not room or room.ai_mode == "off":
        return

    # 2. Get Configs
    query = select(AgentConfig).where(AgentConfig.course_id == room.course_id).order_by(AgentConfig.updated_at.desc())
    result = await session.exec(query)
    configs = result.all()

    teacher_config = next((c for c in configs if c.type == AgentType.TEACHER and c.is_active), None)
    if not teacher_config: # Retry non-active if that's the logic (or strictly active?)
         # Logic says "Select Active or Fallback".
         teacher_config = next((c for c in configs if c.type == AgentType.TEACHER), None)

    student_config = next((c for c in configs if c.type == AgentType.STUDENT and c.is_active), None)
    if not student_config:
         student_config = next((c for c in configs if c.type == AgentType.STUDENT), None)

    # Schedule Check
    if teacher_config and not is_agent_scheduled_now(teacher_config):
        teacher_config = None
    if student_config and not is_agent_scheduled_now(student_config):
        student_config = None

    if not teacher_config and not student_config:
        return

    # 3. Get Time Context
    # We need last message from ANYONE (for silence) and last message from EACH agent (for interval).

    # Last message in room
    last_msg_query = select(Message).where(Message.room_id == UUID(room_id)).order_by(Message.created_at.desc()).limit(1)
    last_msg_res = await session.exec(last_msg_query)
    last_msg = last_msg_res.first()

    now = datetime.now()
    if last_msg and last_msg.created_at:
        # Ensure timezone awareness compatibility.
        # DB usually returns naive UTC or aware UTC. SQLModel defaults?
        # Assuming UTC.
        last_msg_time = last_msg.created_at
        if last_msg_time.tzinfo is None:
            last_msg_time = last_msg_time.replace(tzinfo=None) # Treat as naive UTC if needed or just compare

        # We'll use naive check if both naive, or aware if both aware.
        # Safer: (datetime.utcnow() - last_msg.created_at).total_seconds() if stored as UTC
        silence_duration = (datetime.utcnow() - last_msg.created_at).total_seconds()
    else:
        silence_duration = 999999 # Infinite silence if no messages

    # Last Teacher Message
    t_last_query = select(Message).where(Message.room_id == UUID(room_id)).where(Message.agent_type == AgentType.TEACHER).order_by(Message.created_at.desc()).limit(1)
    t_last = (await session.exec(t_last_query)).first()
    t_since = (datetime.utcnow() - t_last.created_at).total_seconds() if t_last else 999999

    # Last Student Message
    s_last_query = select(Message).where(Message.room_id == UUID(room_id)).where(Message.agent_type == AgentType.STUDENT).order_by(Message.created_at.desc()).limit(1)
    s_last = (await session.exec(s_last_query)).first()
    s_since = (datetime.utcnow() - s_last.created_at).total_seconds() if s_last else 999999

    # 4. Check Triggers
    teacher_action = False
    if teacher_config:
        t_conf = teacher_config.trigger_config or {}
        if t_conf.get("type") == "time_interval":
            interval = float(t_conf.get("value", 60))
            if t_since >= interval:
                teacher_action = True

    student_action = False
    if student_config and not teacher_action: # Priority: Teacher
        s_conf = student_config.trigger_config or {}
        if s_conf.get("type") == "time_interval":
            interval = float(s_conf.get("value", 60))
            if s_since >= interval:
                student_action = True
        elif s_conf.get("type") == "silence":
            threshold = float(s_conf.get("value", 60))
            if silence_duration >= threshold:
                student_action = True

    # 5. Execute
    # helper for history
    limit = max(teacher_config.context_window if teacher_config else 10, student_config.context_window if student_config else 10)
    hist_query = select(Message).where(Message.room_id == UUID(room_id)).order_by(Message.created_at.desc()).limit(limit)
    history = list(reversed((await session.exec(hist_query)).all()))

    if teacher_action and teacher_config.has_api_key:
         agent = TeacherAgent(teacher_config.model_provider, teacher_config.encrypted_api_key, teacher_config.system_prompt, teacher_config.model)
         reply = await agent.generate_reply(history)
         msg = Message(content=reply, room_id=UUID(room_id), agent_type=AgentType.TEACHER)
         session.add(msg)
         await session.commit()
         await session.refresh(msg)
         await manager.broadcast(f"[Teacher AI]|{msg.created_at.isoformat()}Z|{reply}", room_id)

    elif student_action:
         # Student always proposes? Or if time-triggered, does it just speak?
         # "Student... (C) Silence > T seconds"
         # If silence, usually implies encouraging conversation.
         # Let's stick to Proposal flow for consistency, OR skip if silence?
         # If silence, Teacher didn't speak.
         # Let's allow Student to speak directly? No, system assumes Student needs approval generally?
         # The requirement didn't specify turn exemption. "Student Agent... (C) Silence...".
         # Let's follow standard flow: Proposal -> Teacher Eval.
         # But if Teacher is "Time Interval" triggered, Teacher speaks.

         key = student_config.encrypted_api_key or (teacher_config.encrypted_api_key if teacher_config else None)
         if key:
             agent = StudentAgent(student_config.model_provider, key, student_config.system_prompt, student_config.model)

             # If trigger is silence, maybe context is "It's quiet..."
             proposal = await agent.generate_proposal(history)

             # Evaluate
             if teacher_config and teacher_config.has_api_key:
                 t_agent = TeacherAgent(teacher_config.model_provider, teacher_config.encrypted_api_key, teacher_config.system_prompt, teacher_config.model)
                 context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
                 if await t_agent.evaluate_student_proposal(proposal, context_str):
                     msg = Message(content=proposal, room_id=UUID(room_id), agent_type=AgentType.STUDENT)
                     session.add(msg)
                     await session.commit()
                     await session.refresh(msg)
                     await manager.broadcast(f"[Student AI]|{msg.created_at.isoformat()}Z|{proposal}", room_id)
