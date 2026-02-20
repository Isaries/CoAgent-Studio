from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.project import Project, ProjectCreate
from app.models.user import User
from app.repositories.organization_repo import organization_repo
from app.repositories.project_repo import project_repo


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = project_repo
        self.org_repo = organization_repo

    async def get_projects_for_user(
        self, user: User, org_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return await self.repo.get_multi_by_user(
            self.session, user_id=user.id, org_id=org_id, skip=skip, limit=limit
        )

    async def create_project(self, project_in: ProjectCreate, user: User) -> Project:
        # Verify org access
        org_link = await self.org_repo.get_user_link(
            self.session, user_id=user.id, org_id=project_in.organization_id
        )
        if not org_link or org_link.role not in ["super_admin", "admin", "owner", "member"]:
            raise HTTPException(status_code=403, detail="Not enough permissions in organization")

        # Create project
        project = await self.repo.create(self.session, obj_in=project_in)

        # Link user as project admin
        await self.repo.create_user_link(
            self.session, user_id=user.id, project_id=project.id, role="admin"
        )

        return project

    async def get_project(self, project_id: UUID, user: User) -> Project:
        # Check access
        link = await self.repo.get_user_link(self.session, user_id=user.id, project_id=project_id)
        if not link:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        project = await self.repo.get(self.session, id=project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return project
