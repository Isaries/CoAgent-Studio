from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.space import (
    Space,
    SpaceCreate,
    SpaceUpdate,
    UserSpaceLink,
)
from app.models.user import User
from app.repositories.base_repo import BaseRepository


class RepositorySpace(BaseRepository[Space, SpaceCreate, SpaceUpdate]):
    async def get_multi_with_owner(
        self, session: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Space, Optional[str]]]:
        """Get all spaces with owner name, used for admins."""
        query = (
            select(Space, User.full_name)
            .join(User, col(Space.owner_id) == col(User.id))
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def get_multi_by_user_with_owner(
        self, session: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Space, Optional[str]]]:
        """Get spaces owned by or enrolled in by a user."""
        query = (
            select(Space, User.full_name)
            .join(User, col(Space.owner_id) == col(User.id))
            .distinct()
            .outerjoin(UserSpaceLink, col(Space.id) == col(UserSpaceLink.space_id))
            .where(
                or_(
                    col(Space.owner_id) == user_id,
                    col(UserSpaceLink.user_id) == user_id,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def get_user_link(
        self, session: AsyncSession, *, user_id: UUID, space_id: UUID
    ) -> Optional[UserSpaceLink]:
        return await session.get(UserSpaceLink, (user_id, space_id))

    async def create_user_link(
        self, session: AsyncSession, *, user_id: UUID, space_id: UUID, role: str
    ) -> UserSpaceLink:
        link = UserSpaceLink(
            user_id=user_id,
            space_id=space_id,
            role=role,
        )
        session.add(link)
        await session.commit()
        return link

    async def get_space_members(
        self, session: AsyncSession, *, space_id: UUID
    ) -> List[Tuple[User, str]]:
        query = (
            select(User, UserSpaceLink.role)
            .join(UserSpaceLink, User.id == UserSpaceLink.user_id)
            .where(UserSpaceLink.space_id == space_id)
        )
        result = await session.exec(query)
        return result.all()

    async def get_user_by_email(self, session: AsyncSession, *, email: str) -> Optional[User]:
        return (await session.exec(select(User).where(User.email == email))).first()

    async def update_user_link(
        self, session: AsyncSession, *, link: UserSpaceLink
    ) -> UserSpaceLink:
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link

    async def remove_user_link(self, session: AsyncSession, *, link: UserSpaceLink) -> None:
        await session.delete(link)
        await session.commit()


space_repo = RepositorySpace(Space)
