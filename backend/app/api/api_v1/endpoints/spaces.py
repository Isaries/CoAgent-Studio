from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.space import (
    SpaceCreate,
    SpaceMember,
    SpaceMemberUpdate,
    SpaceRead,
    SpaceUpdate,
)
from app.models.user import User, UserRole
from app.services.space_service import SpaceService
from pydantic import BaseModel

router = APIRouter()


@router.post("/", response_model=SpaceRead)
async def create_space(
    *,
    session: AsyncSession = Depends(deps.get_session),
    space_in: SpaceCreate,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Create new space.
    Allowed: Admin, Teacher.
    """
    service = SpaceService(session)
    return await service.create_space(space_in, current_user)


@router.get("/", response_model=List[SpaceRead])
async def read_spaces(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve spaces.
    Admins see all. Others see owned or enrolled.
    """
    service = SpaceService(session)
    results = await service.get_spaces(current_user, skip, limit)

    spaces = []
    for space, owner_name in results:
        space_read = SpaceRead.model_validate(space)
        space_read.owner_name = owner_name
        spaces.append(space_read)

    return spaces


@router.get("/{space_id}", response_model=SpaceRead)
async def read_space(
    space_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get space by ID.
    """
    service = SpaceService(session)
    space = await service.get_space_by_id(space_id)
    from app.services.permission_service import permission_service
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not await permission_service.check(current_user, "read", space, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return space


@router.put("/{space_id}", response_model=SpaceRead)
async def update_space(
    *,
    session: AsyncSession = Depends(deps.get_session),
    space_id: UUID,
    space_in: SpaceUpdate,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Update a space.
    Allowed: Admin, or Owner (Teacher).
    """
    service = SpaceService(session)
    return await service.update_space(space_id, space_in, current_user)


@router.delete("/{space_id}", response_model=SpaceRead)
async def delete_space(
    *,
    session: AsyncSession = Depends(deps.get_session),
    space_id: UUID,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Delete a space.
    Allowed: Admin, or Owner (Teacher).
    """
    service = SpaceService(session)
    return await service.delete_space(space_id, current_user)


class MemberRequest(BaseModel):
    user_email: Optional[str] = None
    user_id: Optional[UUID] = None
    role: str = "student"


@router.post("/{space_id}/members")
async def add_member(
    space_id: UUID,
    member: MemberRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Add a member by email or ID to a space.
    """
    service = SpaceService(session)
    message = await service.add_member(
        space_id, member.user_email, member.user_id, member.role, current_user
    )
    return {"message": message}


@router.get("/{space_id}/members", response_model=List[SpaceMember])
async def read_space_members(
    space_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all members of a space.
    Allowed: Admin, Teacher (Owner/TA).
    """
    service = SpaceService(session)
    members_list, owner_id = await service.get_members(space_id, current_user)

    members_dict = {}
    for user, role in members_list:
        members_dict[user.id] = SpaceMember(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=role,
        )

    if owner_id in members_dict:
        members_dict[owner_id].role = "teacher"
    else:
        owner = await session.get(User, owner_id)
        if owner:
            members_dict[owner.id] = SpaceMember(
                user_id=owner.id,
                email=owner.email,
                full_name=owner.full_name,
                avatar_url=owner.avatar_url,
                role="teacher",
            )

    return list(members_dict.values())


@router.put("/{space_id}/members/{user_id}", response_model=Any)
async def update_space_member_role(
    space_id: UUID,
    user_id: UUID,
    member_update: SpaceMemberUpdate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a member's role in a space (e.g. promote to TA).
    Allowed: Admin, Owner.
    """
    service = SpaceService(session)
    await service.update_member_role(space_id, user_id, member_update.role, current_user)
    return {"message": "Role updated"}


@router.delete("/{space_id}/members/{user_id}")
async def remove_space_member(
    space_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Remove a user from a space.
    Allowed: Admin, Owner, TA (Student only).
    """
    service = SpaceService(session)
    await service.remove_member(space_id, user_id, current_user)
    return {"message": "User removed from space"}


@router.get("/{space_id}/overview")
async def get_space_overview(
    space_id: UUID,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
):
    """Get real-time status of all rooms in a space."""
    from app.models.room import Room
    from app.models.message import Message

    rooms = await session.exec(select(Room).where(Room.space_id == space_id))
    rooms_list = rooms.all()

    rooms_dict = {}
    for room in rooms_list:
        # Get latest message timestamp
        latest_msg_query = (
            select(Message.created_at)
            .where(Message.room_id == room.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        result = await session.exec(latest_msg_query)
        last_message_at = result.first()

        rooms_dict[str(room.id)] = {
            "id": str(room.id),
            "name": room.name,
            "last_message_at": last_message_at,
            "active_users": 0,  # Populated by real-time socket tracking when available
        }

    return {"rooms": rooms_dict, "total_rooms": len(rooms_list)}
