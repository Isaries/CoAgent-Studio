from typing import List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    UserOrganizationLink,
)
from app.repositories.base_repo import BaseRepository


class RepositoryOrganization(BaseRepository[Organization, OrganizationCreate, OrganizationUpdate]):
    async def get_multi_by_user(
        self, session: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        statement = (
            select(Organization)
            .join(UserOrganizationLink)
            .where(UserOrganizationLink.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(statement)
        return result.all()

    async def get_user_link(
        self, session: AsyncSession, *, user_id: UUID, org_id: UUID
    ) -> Optional[UserOrganizationLink]:
        return await session.get(UserOrganizationLink, (user_id, org_id))

    async def create_user_link(
        self, session: AsyncSession, *, user_id: UUID, org_id: UUID, role: str
    ) -> UserOrganizationLink:
        link = UserOrganizationLink(
            user_id=user_id,
            organization_id=org_id,
            role=role,
        )
        session.add(link)
        await session.commit()
        return link


organization_repo = RepositoryOrganization(Organization)
