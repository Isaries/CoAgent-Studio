from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.course import Course
from app.models.message import Message
from app.models.agent_config import AgentConfigRead
from app.models.room import Room, RoomCreate, RoomRead, RoomUpdate, UserRoomLink, RoomAgentLink
from app.models.user import User
from app.services.permission_service import permission_service

router = APIRouter()


@router.post("/", response_model=RoomRead)
async def create_room(
    *,
    session: AsyncSession = Depends(deps.get_session),
    room_in: RoomCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a room in a course.
    Allowed: Admin, or Owner of the course.
    """
    course = await session.get(Course, room_in.course_id)  # type: ignore[func-returns-value]
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if not await permission_service.check(current_user, "create", course, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    room = Room.model_validate(room_in)
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


@router.get("/", response_model=List[RoomRead])
async def read_rooms(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve rooms for a specific course.
    """
    query: Any = select(Room).where(Room.course_id == course_id)
    result = await session.exec(query)
    return result.all()


@router.get("/{room_id}", response_model=RoomRead)
async def read_room(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get a specific room by id.
    """
    room = await session.get(Room, room_id)  # type: ignore[func-returns-value]
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    # Optional: Check if user has access to the course the room belongs to
    # course = await session.get(Course, room.course_id)
    # ... check permissions ...
    return room


@router.put("/{room_id}", response_model=RoomRead)
async def update_room(
    *,
    session: AsyncSession = Depends(deps.get_session),
    room_id: UUID,
    room_in: RoomUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update room (including AI settings).
    Allowed: Admin, or Owner of the course.
    """
    room = await session.get(Room, room_id)  # type: ignore[func-returns-value]
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "update", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    room_data = room.dict(exclude_unset=True)
    update_data = room_in.dict(exclude_unset=True)

    for field in room_data:
        if field in update_data:
            setattr(room, field, update_data[field])

    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    room = await session.get(Room, room_id)  # type: ignore[func-returns-value]
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "delete", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    from sqlmodel import delete

    # Delete Messages
    await session.exec(delete(Message).where(Message.room_id == room_id))
    # Delete UserRoomLinks
    await session.exec(delete(UserRoomLink).where(UserRoomLink.room_id == room_id))

    await session.delete(room)
    await session.commit()
    return


class AssignmentRequest(SQLModel):
    user_email: Optional[str] = None
    user_id: Optional[UUID] = None


@router.post("/{room_id}/assign")
async def assign_user_to_room(
    room_id: UUID,
    assignment: AssignmentRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    room = await session.get(Room, room_id)  # type: ignore[func-returns-value]
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "assign", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Find user
    user_to_assign = None
    if assignment.user_id:
        user_to_assign = await session.get(User, assignment.user_id)
    elif assignment.user_email:
        query: Any = select(User).where(User.email == assignment.user_email)
        result = await session.exec(query)
        user_to_assign = result.first()

    if not user_to_assign:
        raise HTTPException(status_code=404, detail="User not found")

    from app.models.room import UserRoomLink

    # Check if already assigned
    link = await session.get(UserRoomLink, (user_to_assign.id, room_id))
    if link:
        return {"message": "User already assigned to room"}

    new_link = UserRoomLink(user_id=user_to_assign.id, room_id=room_id)
    session.add(new_link)
    await session.commit()

    return {
        "message": f"User {user_to_assign.full_name or user_to_assign.username or user_to_assign.email} assigned to room"
    }


@router.post("/{room_id}/agents/{agent_id}")
async def assign_agent_to_room(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "update", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    from app.models.agent_config import AgentConfig
    # We should also check if the user has permission to deploy this AgentConfig, 
    # but for now we'll just check if it exists.
    agent = await session.get(AgentConfig, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if already assigned
    link = await session.get(RoomAgentLink, (room_id, agent_id))
    if link:
        return {"message": "Agent already assigned to room"}

    new_link = RoomAgentLink(room_id=room_id, agent_id=agent_id)
    session.add(new_link)
    await session.commit()

    return {"message": "Agent assigned to room"}


@router.delete("/{room_id}/agents/{agent_id}")
async def remove_agent_from_room(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "update", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    link = await session.get(RoomAgentLink, (room_id, agent_id))
    if not link:
        raise HTTPException(status_code=404, detail="Agent not assigned to this room")

    await session.delete(link)
    await session.commit()
    return {"message": "Agent removed from room"}


@router.get("/{room_id}/agents", response_model=List[AgentConfigRead])
async def read_room_agents(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    from app.models.agent_config import AgentConfig
    query: Any = (
        select(AgentConfig)
        .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
        .where(RoomAgentLink.room_id == room_id)
    )
    result = await session.exec(query)
    configs = result.all()
    
    # Masking keys would be needed, but AgentConfigRead schema usually handles or endpoints do it
    from app.core.security import mask_api_key
    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)
        
    return response_data
