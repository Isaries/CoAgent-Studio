from typing import List, Tuple, Optional
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message
from app.models.user import User


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_room_history_with_users(self, room_id: UUID) -> List[Tuple[Message, Optional[User]]]:
        """
        Get all messages for a room, including sender info.
        """
        query = (
            select(Message, User)
            .outerjoin(User, col(Message.sender_id) == col(User.id))
            .where(Message.room_id == room_id)
            .order_by(col(Message.created_at).asc())
        )
        result = await self.session.exec(query)
        return result.all()

    async def create(self, content: str, room_id: UUID, sender_id: UUID) -> Message:
        msg = Message(content=content, room_id=room_id, sender_id=sender_id)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg
