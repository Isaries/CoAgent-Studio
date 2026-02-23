from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.audit_service import log_change
from app.models.agent_config import AgentConfigRead
from app.models.room import Room, RoomCreate, RoomRead, RoomUpdate, RoomAgentLink
from app.models.user import User, UserRole
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


# ============================================================
# Room Agent Link Settings CRUD
# ============================================================

class RoomAgentLinkUpdate(BaseModel):
    """Update schema for RoomAgentLink per-room settings."""
    is_active: Optional[bool] = None
    schedule_config: Optional[Dict[str, Any]] = None
    trigger_config: Optional[Dict[str, Any]] = None


@router.get("/{room_id}/agents/{agent_id}/settings")
async def get_room_agent_settings(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get per-room settings for a specific agent link."""
    result = await session.exec(
        select(RoomAgentLink).where(
            RoomAgentLink.room_id == room_id,
            RoomAgentLink.agent_id == agent_id,
        )
    )
    link = result.first()
    if not link:
        raise HTTPException(404, "RoomAgentLink not found")

    return {
        "room_id": str(link.room_id),
        "agent_id": str(link.agent_id),
        "is_active": link.is_active,
        "schedule_config": link.schedule_config,
        "trigger_config": link.trigger_config,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "updated_at": link.updated_at.isoformat() if link.updated_at else None,
    }


@router.put("/{room_id}/agents/{agent_id}/settings")
async def update_room_agent_settings(
    room_id: UUID,
    agent_id: UUID,
    data: RoomAgentLinkUpdate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update per-room schedule/trigger settings for a specific agent link."""
    # Permission check: must be admin or teacher
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]:
        raise HTTPException(403, "Not enough permissions")

    result = await session.exec(
        select(RoomAgentLink).where(
            RoomAgentLink.room_id == room_id,
            RoomAgentLink.agent_id == agent_id,
        )
    )
    link = result.first()
    if not link:
        raise HTTPException(404, "RoomAgentLink not found")

    old_values = {
        "is_active": link.is_active,
        "schedule_config": link.schedule_config,
        "trigger_config": link.trigger_config,
    }

    # Apply updates
    from datetime import datetime
    if data.is_active is not None:
        link.is_active = data.is_active
    if data.schedule_config is not None:
        link.schedule_config = data.schedule_config
    if data.trigger_config is not None:
        link.trigger_config = data.trigger_config
    link.updated_at = datetime.utcnow()
    link.updated_by = current_user.id

    session.add(link)

    # Audit log
    new_values = {
        "is_active": link.is_active,
        "schedule_config": link.schedule_config,
        "trigger_config": link.trigger_config,
    }
    await log_change(
        session,
        entity_type="room_agent_link",
        entity_id=f"{room_id}:{agent_id}",
        action="update_settings",
        actor_id=current_user.id,
        old_value=old_values,
        new_value=new_values,
    )

    await session.commit()
    return {"message": "Settings updated", **new_values}


@router.post("/{room_id}/agents/{agent_id}/sync-to-course")
async def sync_agent_settings_to_course(
    room_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Copy this RoomAgentLink's settings to all rooms in the same course.
    One-time copy operation. Only admin/teacher can perform.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]:
        raise HTTPException(403, "Not enough permissions")

    # 1. Get source link
    source_result = await session.exec(
        select(RoomAgentLink).where(
            RoomAgentLink.room_id == room_id,
            RoomAgentLink.agent_id == agent_id,
        )
    )
    source = source_result.first()
    if not source:
        raise HTTPException(404, "RoomAgentLink not found")

    # 2. Get course_id from Room
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    course_id = room.course_id

    # 3. Get all rooms in the same course
    sibling_result = await session.exec(
        select(Room.id).where(Room.course_id == course_id, Room.id != room_id)
    )
    sibling_ids = sibling_result.all()

    # 4. Upsert RoomAgentLink for each sibling
    from datetime import datetime
    synced_count = 0
    for sib_room_id in sibling_ids:
        existing_result = await session.exec(
            select(RoomAgentLink).where(
                RoomAgentLink.room_id == sib_room_id,
                RoomAgentLink.agent_id == agent_id,
            )
        )
        link = existing_result.first()
        if link:
            link.is_active = source.is_active
            link.schedule_config = source.schedule_config
            link.trigger_config = source.trigger_config
            link.updated_at = datetime.utcnow()
            link.updated_by = current_user.id
        else:
            link = RoomAgentLink(
                room_id=sib_room_id,
                agent_id=agent_id,
                is_active=source.is_active,
                schedule_config=source.schedule_config,
                trigger_config=source.trigger_config,
                updated_by=current_user.id,
            )
        session.add(link)
        synced_count += 1

    # Audit log
    await log_change(
        session,
        entity_type="room_agent_link",
        entity_id=f"{room_id}:{agent_id}",
        action="sync_to_course",
        actor_id=current_user.id,
        new_value={
            "is_active": source.is_active,
            "schedule_config": source.schedule_config,
            "trigger_config": source.trigger_config,
        },
        metadata={"course_id": str(course_id), "synced_rooms": synced_count},
    )

    await session.commit()
    return {"message": f"Settings synced to {synced_count} rooms"}
