from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.message import Message
from app.models.room import Room
from app.models.agent_config import AgentConfig, AgentType
from app.core.specialized_agents import TeacherAgent, StudentAgent
from app.core.socket_manager import ConnectionManager

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
    # Note: Assuming Room has course_id. The original code used room.course_id
    query = select(AgentConfig).where(AgentConfig.course_id == room.course_id)
    result = await session.exec(query)
    configs = result.all()
    
    teacher_config = next((c for c in configs if c.type == AgentType.TEACHER), None)
    student_config = next((c for c in configs if c.type == AgentType.STUDENT), None)
    
    # helper to process history
    hist_query = select(Message).where(Message.room_id == UUID(room_id)).order_by(Message.created_at.desc()).limit(15)
    hist_result = await session.exec(hist_query)
    history = list(reversed(hist_result.all()))

    teacher_agent = None
    if teacher_config and teacher_config.encrypted_api_key:
        teacher_agent = TeacherAgent(
            provider=teacher_config.model_provider,
            api_key=teacher_config.encrypted_api_key,
            system_prompt=teacher_config.system_prompt
        )

    student_agent = None
    if student_config and teacher_config.encrypted_api_key: # Start with Teacher's key for MVP if student key missing
        # In this system, we might assume user provides one key for both, or separate.
        # For now, let's look for Student Key, falling back to Teacher Key (or shared course key logic).
        # We'll stick to config strictness:
        key = student_config.encrypted_api_key or teacher_config.encrypted_api_key
        if key:
            student_agent = StudentAgent(
                provider=student_config.model_provider,
                api_key=key,
                system_prompt=student_config.system_prompt
            )

    # --- Orchestration Logic ---

    # 1. Teacher Turn
    # The Teacher has priority. If Teacher speaks, Student listens.
    can_teacher = room.ai_mode in ["teacher_only", "both"]
    if can_teacher and teacher_agent and teacher_agent.should_reply(history, room.ai_frequency):
        print(f"[Agent] Teacher deciding to reply...")
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
    if can_student and student_agent and teacher_agent: # Student needs Teacher to exist for permission
        if student_agent.should_reply(history, room.ai_frequency):
            print(f"[Agent] Student proposing contribution...")
            proposal = await student_agent.generate_proposal(history)
            
            # Ask Teacher for Permission
            context_str = "\n".join([f"{m.sender_id}: {m.content}" for m in history])
            print(f"[Agent] Teacher evaluating proposal: {proposal[:50]}...")
            is_approved = await teacher_agent.evaluate_student_proposal(proposal, context_str)
            
            if is_approved:
                print(f"[Agent] Proposal APPROVED.")
                msg = Message(content=proposal, room_id=UUID(room_id), agent_type=AgentType.STUDENT)
                session.add(msg)
                await session.commit()
                await session.refresh(msg)
                timestamp = msg.created_at.isoformat() + "Z"
                await manager.broadcast(f"[Student AI]|{timestamp}|{proposal}", room_id)
            else:
                print(f"[Agent] Proposal DENIED by Teacher.")
