from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig
from app.models.message import Message
from app.models.thread import (
    AgentThread,
    AgentThreadCreate,
    ThreadMessage,
)
from app.models.user import User
from app.repositories.thread_message_repo import thread_message_repo
from app.repositories.thread_repo import thread_repo


class ThreadService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = thread_repo
        self.message_repo = thread_message_repo

    async def create_thread(self, thread_in: AgentThreadCreate, user: User) -> AgentThread:
        agent_config = await self.session.get(AgentConfig, thread_in.agent_id)
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent not found")

        # In a real 3 tier, we'd check Project permissions via ProjectRepo
        # For simplicity based on legacy logic, we create it
        return await self.repo.create(self.session, obj_in=thread_in, user_id=user.id)

    async def get_thread(self, thread_id: UUID, user: User) -> AgentThread:
        thread = await self.repo.get(self.session, id=thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return thread

    async def get_thread_messages(self, thread_id: UUID, user: User) -> List[ThreadMessage]:
        thread = await self.get_thread(thread_id, user)
        return await self.message_repo.get_multi_by_thread(self.session, thread_id=thread.id)

    async def _initialize_agent(self, agent_config: AgentConfig) -> Any:
        from app.factories.agent_factory import AgentFactory
        from app.services.user_key_service import UserKeyService

        key_service = UserKeyService(self.session)
        decrypted_keys = []
        if agent_config.user_key_ids and agent_config.created_by:
            for k_id in agent_config.user_key_ids:
                try:
                    dk = await key_service.get_decrypted_key(k_id, agent_config.created_by)
                    if dk:
                        decrypted_keys.append(dk)
                except Exception:
                    pass

        agent = AgentFactory.create_agent(agent_config, api_keys=decrypted_keys)
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to initialize agent")
        return agent

    async def generate_stateless_response(
        self, agent_id: UUID, message_content: str, metadata_json: Optional[str], user: User
    ) -> str:
        agent_config = await self.session.get(AgentConfig, agent_id)
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent = await self._initialize_agent(agent_config)

        temp_history = [
            Message(
                sender_id=str(user.id),
                content=message_content,
                room_id=UUID("00000000-0000-0000-0000-000000000000"),
            )
        ]

        reply = await agent.generate_reply(temp_history)

        if isinstance(reply, list):
            reply = f"System: Executed {len(reply)} tools."

        return reply

    async def process_thread_message(
        self, thread_id: UUID, message_content: str, metadata_json: Optional[str], user: User
    ) -> ThreadMessage:
        thread = await self.get_thread(thread_id, user)

        # 1. Save User Message
        user_msg = await self.message_repo.append_message(
            self.session,
            thread_id=thread.id,
            role="user",
            content=message_content,
            metadata_json=metadata_json,
        )

        # 2. Trigger Agent Execution
        agent_config = await self.session.get(AgentConfig, thread.agent_id)
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")
            
        agent = await self._initialize_agent(agent_config)

        # Load history
        thread_history = await self.message_repo.get_multi_by_thread(self.session, thread_id=thread.id)

        # Construct payload for AgentCore
        simulated_history = []
        for th in thread_history:
            simulated_history.append(
                Message(
                    sender_id=str(user.id) if th.role == "user" else "agent",
                    content=th.content,
                    room_id=UUID("00000000-0000-0000-0000-000000000000"),
                )
            )

        reply = await agent.generate_reply(simulated_history)

        if isinstance(reply, list):
            reply = f"System: Executed {len(reply)} tools."

        # 3. Save Agent Message
        agent_msg = await self.message_repo.append_message(
            self.session,
            thread_id=thread.id,
            role="assistant",
            content=reply,
        )

        return agent_msg
