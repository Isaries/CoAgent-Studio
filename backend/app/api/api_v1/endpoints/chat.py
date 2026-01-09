import asyncio
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.db import get_session
from app.core.socket_manager import manager
from app.models.message import Message
from app.models.user import User
from app.services.agent_service import process_agents

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
    query = select(Message, User).outerjoin(User, Message.sender_id == User.id).where(Message.room_id == room_id).order_by(Message.created_at.asc())
    result = await session.exec(query)

    messages_out = []
    for msg, user in result:
        sender = "Unknown"
        if user:
             sender = user.full_name or user.username or user.email or "Unknown"
        elif msg.agent_type:
             sender = f"{msg.agent_type.capitalize()} AI"

        messages_out.append({
            "sender": sender,
            "content": msg.content,
            "agent_type": msg.agent_type,
            "sender_id": msg.sender_id,
            "created_at": (msg.created_at.isoformat() + "Z") if msg.created_at else None
        })

    return messages_out

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

            # Broadcast User Message (with format "name|timestamp|content")
            display_name = user.full_name or user.username or user.email or "Unknown"
            timestamp = (user_msg.created_at.isoformat() + "Z") if user_msg.created_at else ""
            await manager.broadcast(f"{display_name}|{timestamp}|{data}", room_id)

            # Trigger Agents
            asyncio.create_task(process_agents(room_id, session, manager, user_msg))

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(f"Client #{user.email} left", room_id)
