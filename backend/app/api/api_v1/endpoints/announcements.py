from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.api import deps
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.announcement import Announcement, AnnouncementCreate, AnnouncementRead

router = APIRouter()

@router.post("/", response_model=AnnouncementRead)
async def create_announcement(
    *,
    session: AsyncSession = Depends(deps.get_session),
    announcement_in: AnnouncementCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create announcement.
    Allowed: Admin, Teacher (if owner), or TA (if enrolled - logic to be added).
    For now: Admin or Course Owner.
    """
    course = await session.get(Course, announcement_in.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if current_user.role != UserRole.ADMIN and course.owner_id != current_user.id:
        # Check if user is TA
        from app.models.course import UserCourseLink
        link = await session.get(UserCourseLink, (current_user.id, course.id))
        is_ta = link and link.role == "ta"
        
        if not is_ta:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    announcement = Announcement.model_validate(announcement_in)
    announcement.author_id = current_user.id
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    return announcement

@router.get("/", response_model=List[AnnouncementRead])
async def read_announcements(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get announcements for a course.
    """
    query = select(Announcement).where(Announcement.course_id == course_id).order_by(Announcement.created_at.desc())
    result = await session.exec(query)
    return result.all()
