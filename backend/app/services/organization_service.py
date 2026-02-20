from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.organization import Organization, OrganizationCreate
from app.models.user import User
from app.repositories.organization_repo import organization_repo


class OrganizationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = organization_repo

    async def get_organizations_for_user(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        return await self.repo.get_multi_by_user(
            self.session, user_id=user.id, skip=skip, limit=limit
        )

    async def create_organization(self, org_in: OrganizationCreate, user: User) -> Organization:
        # Create organization with user as owner
        org = await self.repo.create(self.session, obj_in=org_in, owner_id=user.id)

        # Create user link as owner
        await self.repo.create_user_link(
            self.session, user_id=user.id, org_id=org.id, role="owner"
        )
        return org

    async def get_organization(self, org_id: UUID, user: User) -> Organization:
        # Check permissions
        link = await self.repo.get_user_link(self.session, user_id=user.id, org_id=org_id)
        if not link:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        org = await self.repo.get(self.session, id=org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        return org
