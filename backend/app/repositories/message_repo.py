from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message
from app.models.user import User


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_room_history_with_users(
        self, room_id: UUID, *, limit: int = 500
    ) -> List[Tuple[Message, Optional[User]]]:
        """
        Get recent messages for a room, including sender info.
        Returns the last `limit` messages ordered ascending by created_at.
        """
        query = (
            select(Message, User)
            .outerjoin(User, col(Message.sender_id) == col(User.id))
            .where(Message.room_id == room_id)
            .order_by(col(Message.created_at).desc())
            .limit(limit)
        )
        result = await self.session.exec(query)
        rows = result.all()
        return list(reversed(rows))

    async def create(self, content: str, room_id: UUID, sender_id: UUID) -> Message:
        msg = Message(content=content, room_id=room_id, sender_id=sender_id)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg
