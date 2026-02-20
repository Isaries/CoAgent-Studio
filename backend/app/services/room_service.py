from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig
from app.models.room import Room, RoomCreate, RoomUpdate
from app.models.user import User
from app.repositories.course_repo import course_repo
from app.repositories.room_repo import room_repo
from app.services.permission_service import permission_service


class RoomService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = room_repo
        self.course_repo = course_repo

    async def create_room(self, room_in: RoomCreate, user: User) -> Room:
        course = await self.course_repo.get(self.session, id=room_in.course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if not await permission_service.check(user, "create", course, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.create(self.session, obj_in=room_in)

    async def get_rooms_by_course(self, course_id: UUID) -> List[Room]:
        return await self.repo.get_multi_by_course(self.session, course_id=course_id)

    async def get_room(self, room_id: UUID) -> Room:
        room = await self.repo.get(self.session, id=room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return room

    async def update_room(self, room_id: UUID, room_in: RoomUpdate, user: User) -> Room:
        room = await self.get_room(room_id)

        if not await permission_service.check(user, "update", room, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.update(self.session, db_obj=room, obj_in=room_in)

    async def delete_room(self, room_id: UUID, user: User) -> None:
        room = await self.get_room(room_id)

        if not await permission_service.check(user, "delete", room, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        await self.repo.cascade_delete_room(self.session, room=room)

    async def assign_user(self, room_id: UUID, user_email: Optional[str], user_id: Optional[UUID], current_user: User) -> str:
        room = await self.get_room(room_id)

        if not await permission_service.check(current_user, "assign", room, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        user_to_assign = None
        if user_id:
            user_to_assign = await self.session.get(User, user_id)
        elif user_email:
            user_to_assign = await self.course_repo.get_user_by_email(self.session, email=user_email)

        if not user_to_assign:
            raise HTTPException(status_code=404, detail="User not found")

        link = await self.repo.get_user_link(self.session, user_id=user_to_assign.id, room_id=room_id)
        if link:
            return "User already assigned to room"

        await self.repo.create_user_link(self.session, user_id=user_to_assign.id, room_id=room_id)
        return f"User {user_to_assign.full_name or user_to_assign.username or user_to_assign.email} assigned to room"

    async def assign_agent(self, room_id: UUID, agent_id: UUID, current_user: User) -> str:
        room = await self.get_room(room_id)

        if not await permission_service.check(current_user, "update", room, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        # In a real 3 tier we would use AgentConfigRepo. 
        from app.models.agent_config import AgentConfig
        agent = await self.session.get(AgentConfig, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        link = await self.repo.get_agent_link(self.session, room_id=room_id, agent_id=agent_id)
        if link:
            return "Agent already assigned to room"

        await self.repo.create_agent_link(self.session, room_id=room_id, agent_id=agent_id)
        return "Agent assigned to room"

    async def remove_agent(self, room_id: UUID, agent_id: UUID, current_user: User) -> str:
        room = await self.get_room(room_id)

        if not await permission_service.check(current_user, "update", room, self.session):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        link = await self.repo.get_agent_link(self.session, room_id=room_id, agent_id=agent_id)
        if not link:
            raise HTTPException(status_code=404, detail="Agent not assigned to this room")

        await self.repo.remove_agent_link(self.session, link=link)
        return "Agent removed from room"

    async def get_agents(self, room_id: UUID) -> List[AgentConfig]:
        room = await self.get_room(room_id)
        return await self.repo.get_agents_by_room(self.session, room_id=room_id)
