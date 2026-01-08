from typing import List, Optional, Any
from uuid import UUID
import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.db import get_session
from app.models.message import Message
from app.models.room import Room
from app.models.course import Course
from app.models.user import User
from app.models.agent_config import AgentConfig, AgentType
from app.api import deps
from app.core import security
from jose import jwt, JWTError
from app.core.config import settings
from app.core.specialized_agents import TeacherAgent, StudentAgent

router = APIRouter()

@router.get("/messages/{room_id}", response_model=List[Any])
async def get_room_messages(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get chat history for a room.
    """
    query = select(Message, User.email).outerjoin(User, Message.sender_id == User.id).where(Message.room_id == room_id).order_by(Message.created_at.asc())
    result = await session.exec(query)
    
    messages_out = []
    for msg, email in result:
        sender = email if email else (f"{msg.agent_type.capitalize()} AI" if msg.agent_type else "Unknown")
        messages_out.append({
            "sender": sender,
            "content": msg.content,
            "agent_type": msg.agent_type,
            "sender_id": msg.sender_id
        })
    
    return messages_out

class ConnectionManager:
    def __init__(self):
        # Dictionary to store connections: room_id -> List of WebSockets
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)

manager = ConnectionManager()

async def get_current_user_ws(token: str, session: AsyncSession) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = payload.get("sub")
        if token_data is None:
            return None
    except JWTError:
        return None
        
    user = await session.get(User, token_data)
    return user

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
        await manager.broadcast(f"[Teacher AI]: {reply}", room_id)
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
                await manager.broadcast(f"[Student AI]: {proposal}", room_id)
            else:
                print(f"[Agent] Proposal DENIED by Teacher.")

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: str, 
    token: str = Query(...),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    user = await get_current_user_ws(token, session)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Save User Message
            user_msg = Message(
                content=data,
                room_id=UUID(room_id),
                sender_id=user.id
            )
            session.add(user_msg)
            await session.commit() # Commit to get ID and timestamp
            await session.refresh(user_msg)
            
            # Broadcast User Message
            await manager.broadcast(f"{user.email}: {data}", room_id)
            
            # Trigger Agents
            asyncio.create_task(process_agents(room_id, session, manager, user_msg))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(f"Client #{user.email} left", room_id)
