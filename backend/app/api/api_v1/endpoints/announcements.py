from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.announcement import Announcement, AnnouncementCreate, AnnouncementRead
from app.models.space import Space
from app.models.user import User, UserRole

router = APIRouter()


class AnnouncementUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None


@router.post("/", response_model=AnnouncementRead)
async def create_announcement(
    *,
    session: AsyncSession = Depends(deps.get_session),
    announcement_in: AnnouncementCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Announcement:  # type: ignore[func-returns-value]
    """
    Create announcement.
    Allowed: Admin, Teacher (if owner), or TA (if enrolled - logic to be added).
    For now: Admin or Space Owner.
    """
    space = await session.get(Space, announcement_in.space_id)  # type: ignore[func-returns-value]
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if (
        current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        and space.owner_id != current_user.id
    ):
        # Check if user is TA
        from app.models.space import UserSpaceLink

        link = await session.get(UserSpaceLink, (current_user.id, space.id))
        is_ta = link and link.role == "ta"

        if not is_ta:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    announcement = Announcement(**announcement_in.model_dump(), author_id=current_user.id)
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    return announcement


@router.get("/", response_model=List[AnnouncementRead])
async def read_announcements(
    space_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get announcements for a space.
    """
    query: Any = (
        select(Announcement)
        .where(Announcement.space_id == space_id)
        .order_by(col(Announcement.created_at).desc())
    )
    result = await session.exec(query)
    return result.all()


@router.get("/{announcement_id}", response_model=AnnouncementRead)
async def read_announcement(
    announcement_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get a single announcement by ID.
    """
    announcement = await session.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


@router.put("/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement(
    *,
    session: AsyncSession = Depends(deps.get_session),
    announcement_id: UUID,
    announcement_in: AnnouncementUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update an announcement.
    Allowed: Admin, or the original author.
    """
    announcement = await session.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Permission check: Admin or original author
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        and announcement.author_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = announcement_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}", status_code=204)
async def delete_announcement(
    announcement_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete an announcement.
    Allowed: Admin, or the original author.
    """
    announcement = await session.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Permission check: Admin or original author
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        and announcement.author_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await session.delete(announcement)
    await session.commit()
    return None
