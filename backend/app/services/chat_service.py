from typing import Any, List
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message
from app.models.user import User


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_room_messages(self, room_id: UUID) -> List[Any]:
        """
        Get chat history for a room, handling formatting.
        """
        query = (
            select(Message, User)
            .outerjoin(User, Message.sender_id == User.id)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.session.exec(query)

        messages_out = []
        for msg, user in result:
            sender = "Unknown"
            if user:
                sender = user.full_name or user.username or user.email or "Unknown"
            elif msg.agent_type:
                sender = f"{msg.agent_type.capitalize()} AI"

            messages_out.append(
                {
                    "sender": sender,
                    "content": msg.content,
                    "agent_type": msg.agent_type,
                    "sender_id": msg.sender_id,
                    "created_at": (msg.created_at.isoformat() + "Z") if msg.created_at else None,
                }
            )
        return messages_out

    async def save_user_message(self, room_id: str, user: User, content: str) -> Message:
        """
        Save a user message to the database.
        """
        # room_id is passed as str from websocket, convert to UUID
        user_msg = Message(content=content, room_id=UUID(room_id), sender_id=user.id)
        self.session.add(user_msg)
        await self.session.commit()
        await self.session.refresh(user_msg)
        return user_msg
