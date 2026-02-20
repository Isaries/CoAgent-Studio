from typing import List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    UserProjectLink,
)
from app.repositories.base_repo import BaseRepository


class RepositoryProject(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
    async def get_multi_by_user(
        self, session: AsyncSession, *, user_id: UUID, org_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        query = select(Project).join(UserProjectLink).where(UserProjectLink.user_id == user_id)
        if org_id:
            query = query.where(Project.organization_id == org_id)
            
        statement = query.offset(skip).limit(limit)
        result = await session.exec(statement)
        return result.all()

    async def get_user_link(
        self, session: AsyncSession, *, user_id: UUID, project_id: UUID
    ) -> Optional[UserProjectLink]:
        return await session.get(UserProjectLink, (user_id, project_id))

    async def create_user_link(
        self, session: AsyncSession, *, user_id: UUID, project_id: UUID, role: str
    ) -> UserProjectLink:
        link = UserProjectLink(
            user_id=user_id,
            project_id=project_id,
            role=role,
        )
        session.add(link)
        await session.commit()
        return link


project_repo = RepositoryProject(Project)
