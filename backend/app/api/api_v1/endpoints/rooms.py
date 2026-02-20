from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.agent_config import AgentConfigRead
from app.models.room import RoomCreate, RoomRead, RoomUpdate
from app.models.user import User
from app.services.room_service import RoomService

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
    service = RoomService(session)
    return await service.create_room(room_in, current_user)


@router.get("/", response_model=List[RoomRead])
async def read_rooms(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve rooms for a specific course.
    """
    service = RoomService(session)
    return await service.get_rooms_by_course(course_id)


@router.get("/{room_id}", response_model=RoomRead)
async def read_room(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get a specific room by id.
    """
    service = RoomService(session)
    return await service.get_room(room_id)


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
    service = RoomService(session)
    return await service.update_room(room_id, room_in, current_user)


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    service = RoomService(session)
    await service.delete_room(room_id, current_user)


class AssignmentRequest(BaseModel):
    user_email: Optional[str] = None
    user_id: Optional[UUID] = None


@router.post("/{room_id}/assign")
async def assign_user_to_room(
    room_id: UUID,
    assignment: AssignmentRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = RoomService(session)
    message = await service.assign_user(
        room_id, assignment.user_email, assignment.user_id, current_user
    )
    return {"message": message}


@router.post("/{room_id}/agents/{agent_id}")
async def assign_agent_to_room(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = RoomService(session)
    message = await service.assign_agent(room_id, agent_id, current_user)
    return {"message": message}


@router.delete("/{room_id}/agents/{agent_id}")
async def remove_agent_from_room(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = RoomService(session)
    message = await service.remove_agent(room_id, agent_id, current_user)
    return {"message": message}


@router.get("/{room_id}/agents", response_model=List[AgentConfigRead])
async def read_room_agents(
    room_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = RoomService(session)
    configs = await service.get_agents(room_id)
    
    from app.core.security import mask_api_key
    response_data = []
    for config in configs:
        c_read = AgentConfigRead.model_validate(config)
        if config.encrypted_api_key:
            c_read.masked_api_key = mask_api_key(config.encrypted_api_key)
        response_data.append(c_read)
        
    return response_data
