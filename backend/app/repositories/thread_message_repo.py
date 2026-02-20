from typing import List
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.thread import (
    ThreadMessage,
    ThreadMessageCreate,
    ThreadMessageUpdate,
)
from app.repositories.base_repo import BaseRepository


class RepositoryThreadMessage(BaseRepository[ThreadMessage, ThreadMessageCreate, ThreadMessageUpdate]):
    async def get_multi_by_thread(
        self, session: AsyncSession, *, thread_id: UUID, skip: int = 0, limit: int = 1000
    ) -> List[ThreadMessage]:
        query = (
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread_id)
            .order_by(ThreadMessage.created_at.asc())  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def append_message(
        self, session: AsyncSession, *, thread_id: UUID, role: str, content: str, metadata_json: str = None
    ) -> ThreadMessage:
        msg = ThreadMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg


thread_message_repo = RepositoryThreadMessage(ThreadMessage)
