from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, SQLModel

from app.api import deps
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.room import Room, RoomCreate, RoomRead, RoomUpdate

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
    course = await session.get(Course, room_in.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
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
    query = select(Room).where(Room.course_id == course_id)
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
    room = await session.get(Room, room_id)
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
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    course = await session.get(Course, room.course_id) # Need to check course ownership
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
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
):
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    # Verify Course Ownership
    course = await session.get(Course, room.course_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
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
):
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    course = await session.get(Course, room.course_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Find user
    user_to_assign = None
    if assignment.user_id:
        user_to_assign = await session.get(User, assignment.user_id)
    elif assignment.user_email:
        query = select(User).where(User.email == assignment.user_email)
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
    
    return {"message": f"User {user_to_assign.full_name or user_to_assign.username or user_to_assign.email} assigned to room"}
