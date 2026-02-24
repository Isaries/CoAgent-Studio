from typing import Any, List, Optional
from uuid import UUID

# Process agents is now run_agent_cycle_task in worker, handled via arq
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.db import get_session, get_session_context
from app.core.socket_manager import manager
from app.models.user import User
from app.schemas.socket import SocketMessage
from app.services.chat_service import ChatService
from app.services.permission_service import permission_service
from app.models.room import Room

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
    # Check permissions
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "read", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    chat_service = ChatService(session)
    return await chat_service.get_room_messages(room_id)


async def get_current_user_ws(token: str, session: AsyncSession) -> Optional[User]:  # type: ignore[func-returns-value]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = payload.get("sub")
        if token_data is None:
            return None
    except JWTError:
        return None

    user = await session.get(User, token_data)  # type: ignore[func-returns-value]
    return user


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: Optional[str] = Query(None),
) -> None:
    # Authenticate via Query Token OR Cookie
    if not token:
        token = websocket.cookies.get("access_token")

    if not token:
        await websocket.close(code=1008)
        return

    # --- Auth & permission check: use a short-lived session ---
    async with get_session_context() as session:
        user = await get_current_user_ws(token, session)
        if not user:
            await websocket.close(code=1008)
            return

        # Snapshot user info before session closes (for broadcasting later)
        user_id = user.id
        user_email = user.email
        display_name = user.full_name or user.username or user.email or "Unknown"

        # Check Permissions for Room
        try:
            r_uuid = UUID(room_id)
            room = await session.get(Room, r_uuid)
            if not room:
                await websocket.close(code=1008)
                return

            if not await permission_service.check(user, "read", room, session):
                await websocket.close(code=1008)
                return

        except ValueError:
            await websocket.close(code=1008)
            return

    # --- Session is now released; enter message loop ---
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()

            # Each message gets its own short-lived session
            async with get_session_context() as msg_session:
                chat_service = ChatService(msg_session)
                user_msg = await chat_service.save_user_message(room_id, user_id, data)
                timestamp = (user_msg.created_at.isoformat() + "Z") if user_msg.created_at else ""
                msg_id = str(user_msg.id)

            # Broadcast User Message (JSON) — no DB session needed
            socket_msg = SocketMessage(
                type="message",
                sender=display_name,
                content=data,
                timestamp=timestamp,
                room_id=room_id,
                metadata={"is_ai": False, "sender_id": str(user_id)},
            )
            await manager.broadcast(socket_msg.model_dump(), room_id)

            # --- Phase 1: State Tracking (Update last activity) ---
            if manager.broker.redis_client:
                import time
                await manager.broker.redis_client.set(
                    f"room_activity:{room_id}", 
                    str(time.time()),
                    ex=86400 * 7 # 7 days expiry
                )

            # --- Phase 2: Trigger Dispatch (Enqueue Event) ---
            if hasattr(websocket.app.state, "arq_pool"):
                 payload = {
                     "type": "user_message",
                     "content": data,
                     "sender_id": str(user_id)
                 }
                 await websocket.app.state.arq_pool.enqueue_job(
                     "dispatch_event_task", 
                     "user_message", 
                     room_id, 
                     payload
                 )
            else:
                 print("ARQ Pool not initialized")

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        # Broadcast System Message
        sys_msg = SocketMessage(
            type="system",
            sender="System",
            content=f"Client #{user_email} left",
            timestamp="",  # Use current time if needed
            room_id=room_id,
        )
        await manager.broadcast(sys_msg.model_dump(), room_id)
