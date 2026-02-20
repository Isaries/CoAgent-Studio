from typing import List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.thread import (
    AgentThread,
    AgentThreadCreate,
    AgentThreadUpdate,
)
from app.repositories.base_repo import BaseRepository


class RepositoryThread(BaseRepository[AgentThread, AgentThreadCreate, AgentThreadUpdate]):
    async def get_multi_by_user(
        self, session: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[AgentThread]:
        query = (
            select(AgentThread)
            .where(AgentThread.user_id == user_id)
            .order_by(AgentThread.created_at.desc())  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def get_multi_by_project(
        self, session: AsyncSession, *, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[AgentThread]:
        query = (
            select(AgentThread)
            .where(AgentThread.project_id == project_id)
            .order_by(AgentThread.created_at.desc())  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()


thread_repo = RepositoryThread(AgentThread)
