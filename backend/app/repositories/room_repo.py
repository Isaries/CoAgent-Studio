from typing import Optional
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.room import Room


class RoomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, room_id: UUID) -> Optional[Room]:
        return await self.session.get(Room, room_id)
