from typing import Any, List
from uuid import UUID

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message
from app.repositories.message_repo import MessageRepository

logger = structlog.get_logger()


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.message_repo = MessageRepository(session)

    async def get_room_messages(self, room_id: UUID) -> List[Any]:
        """
        Get chat history for a room, handling formatting.
        """
        result = await self.message_repo.get_room_history_with_users(room_id)

        messages_out = []
        for msg, user in result:
            sender = "Unknown"
            if user:
                sender = user.full_name or user.username or user.email or "Unknown"
            elif msg.agent_type:
                # Fallback if no user linked (AI)
                sender = f"{msg.agent_type.capitalize()} AI"

            messages_out.append(
                {
                    "sender": sender,
                    "content": msg.content,
                    "agent_type": msg.agent_type,
                    "sender_id": msg.sender_id,
                    "created_at": (msg.created_at.isoformat() + "Z") if msg.created_at else None,
                }
            )
        return messages_out

    async def save_user_message(self, room_id: str, sender_id: UUID, content: str) -> Message:
        """
        Save a user message to the database.
        Also publishes a GraphRAG event for incremental ingestion.
        """
        # room_id is passed as str from websocket, convert to UUID
        msg = await self.message_repo.create(content, UUID(room_id), sender_id)

        # Publish GraphRAG ingestion event (non-fatal)
        try:
            from app.core.config import settings
            import redis.asyncio as aioredis

            r = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True
            )
            await r.xadd(
                "graphrag:events",
                {"type": "message", "room_id": room_id, "msg_id": str(msg.id)},
            )
            await r.aclose()
        except Exception as e:
            logger.debug("graphrag_event_publish_skipped", error=str(e))

        return msg

