from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.user import User, UserCreate, UserRead, UserUpdate
from app.services.permission_service import permission_service
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=UserRead)
async def update_user_me(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update own user (display name, avatar, etc).
    """
    service = UserService(session)
    return await service.update_user_me(user_in, current_user)


@router.get("/", response_model=List[UserRead])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve users. Admin or Super Admin.
    """
    if not await permission_service.check(current_user, "list_users", None, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = UserService(session)
    return await service.get_users(skip, limit)


@router.get("/search", response_model=List[UserRead])
async def search_users(
    q: str,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
    limit: int = 10,
) -> Any:
    """
    Search users by email, full_name, or username.
    Accessible to authenticated users (for enrollment).
    """
    service = UserService(session)
    return await service.search_users(q, limit)


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a user (e.g. role promotion). Admin only.
    """
    user_to_edit = await session.get(User, user_id)
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="User not found")

    if not await permission_service.check(current_user, "manage_users", user_to_edit, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = UserService(session)
    return await service.update_user(user_id, user_in, current_user)


@router.delete("/{user_id}", response_model=UserRead)
async def delete_user(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a user.
    """
    user_to_delete = await session.get(User, user_id)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    if not await permission_service.check(current_user, "manage_users", user_to_delete, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = UserService(session)
    return await service.delete_user(user_id, current_user)


@router.post("/", response_model=UserRead)
async def create_user(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new user (Admin only).
    """
    if not await permission_service.check(current_user, "manage_users", None, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    service = UserService(session)
    return await service.create_user(user_in, current_user)


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    *,
    session: AsyncSession = Depends(deps.get_session),
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload user avatar.
    """
    service = UserService(session)
    return await service.upload_avatar(file, current_user)
