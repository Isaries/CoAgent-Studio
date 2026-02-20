from typing import List, Optional
from uuid import UUID

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig
from app.models.message import Message
from app.models.room import (
    Room,
    RoomCreate,
    RoomUpdate,
    UserRoomLink,
    RoomAgentLink,
)
from app.models.user import User
from app.repositories.base_repo import BaseRepository


class RepositoryRoom(BaseRepository[Room, RoomCreate, RoomUpdate]):
    async def get_multi_by_course(
        self, session: AsyncSession, *, course_id: UUID
    ) -> List[Room]:
        query = select(Room).where(Room.course_id == course_id)
        result = await session.exec(query)
        return result.all()

    async def get_user_link(
        self, session: AsyncSession, *, user_id: UUID, room_id: UUID
    ) -> Optional[UserRoomLink]:
        return await session.get(UserRoomLink, (user_id, room_id))

    async def create_user_link(
        self, session: AsyncSession, *, user_id: UUID, room_id: UUID
    ) -> UserRoomLink:
        link = UserRoomLink(user_id=user_id, room_id=room_id)
        session.add(link)
        await session.commit()
        return link

    async def get_agent_link(
        self, session: AsyncSession, *, room_id: UUID, agent_id: UUID
    ) -> Optional[RoomAgentLink]:
        return await session.get(RoomAgentLink, (room_id, agent_id))

    async def create_agent_link(
        self, session: AsyncSession, *, room_id: UUID, agent_id: UUID
    ) -> RoomAgentLink:
        link = RoomAgentLink(room_id=room_id, agent_id=agent_id)
        session.add(link)
        await session.commit()
        return link

    async def remove_agent_link(
        self, session: AsyncSession, *, link: RoomAgentLink
    ) -> None:
        await session.delete(link)
        await session.commit()

    async def get_agents_by_room(
        self, session: AsyncSession, *, room_id: UUID
    ) -> List[AgentConfig]:
        query = (
            select(AgentConfig)
            .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
            .where(RoomAgentLink.room_id == room_id)
        )
        result = await session.exec(query)
        return result.all()

    async def cascade_delete_room(self, session: AsyncSession, *, room: Room) -> None:
        # Delete Messages
        await session.exec(delete(Message).where(Message.room_id == room.id))
        # Delete UserRoomLinks
        await session.exec(delete(UserRoomLink).where(UserRoomLink.room_id == room.id))
        
        await session.delete(room)
        await session.commit()


room_repo = RepositoryRoom(Room)
