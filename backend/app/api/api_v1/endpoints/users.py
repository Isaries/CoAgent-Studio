from typing import Any, List
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.config import settings
from app.models.user import User, UserRead, UserUpdate, UserRole, UserCreate

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
    user_data = current_user.dict(exclude_unset=True)
    update_data = user_in.dict(exclude_unset=True)

    # Restrict what users can update for themselves (security)
    # Don't allow role or email changes via this endpoint for now
    if "role" in update_data:
        del update_data["role"]
    if "email" in update_data:
        del update_data["email"] # Email change usually requires re-verification

    # Handle password update
    if "password" in update_data and update_data["password"]:
        from app.core.security import get_password_hash
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        current_user.hashed_password = hashed_password

    for field in user_data:
        if field in update_data:
            setattr(current_user, field, update_data[field])

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user

@router.get("/", response_model=List[UserRead])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve users. Only Admin.
    """
    query = select(User).offset(skip).limit(limit)
    result = await session.exec(query)
    return result.all()

@router.get("/search", response_model=List[UserRead])
async def search_users(
    q: str,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
    limit: int = 10
) -> Any:
    """
    Search users by email, full_name, or username.
    Accessible to authenticated users (for enrollment).
    """
    from sqlmodel import or_, col
    query = select(User).where(
        or_(
            col(User.email).contains(q),
            col(User.full_name).contains(q),
            col(User.username).contains(q)
        )
    ).limit(limit)
    
    result = await session.exec(query)
    return result.all()

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update a user (e.g. role promotion). Only Admin.
    """
    query = select(User).where(User.id == user_id)
    result = await session.exec(query)
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this user_id does not exist in the system",
        )
    
    user_data = user.dict(exclude_unset=True)
    update_data = user_in.dict(exclude_unset=True)
    
    # Handle password update if separately (simple logic for now)
    if "password" in update_data and update_data["password"]:
        from app.core.security import get_password_hash
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        user.hashed_password = hashed_password
        
    for field in user_data:
        if field in update_data:
            setattr(user, field, update_data[field])

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
@router.post("/", response_model=UserRead)
async def create_user(
    *,
    session: AsyncSession = Depends(deps.get_session),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new user (Admin only).
    """
    from app.models.user import User
    from app.core import security
    
    # Check if user with this email or username already exists
    from sqlmodel import or_
    query = select(User).where(
        or_(
            User.email == user_in.email,
            (User.username == user_in.username) if user_in.username else False
        )
    )
    result = await session.exec(query)
    if result.first():
        raise HTTPException(
            status_code=400,
            detail="The user with this username or email already exists in the system",
        )
        
    user = User.model_validate(user_in)
    if user_in.password:
        user.hashed_password = security.get_password_hash(user_in.password)
        
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
