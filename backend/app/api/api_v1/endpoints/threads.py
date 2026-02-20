from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.thread import (
    AgentThreadCreate,
    AgentThreadRead,
    ThreadMessageRead,
)
from app.models.user import User
from app.services.thread_service import ThreadService

router = APIRouter()

# --- Schemas ---
class ChatRequest(BaseModel):
    message: str
    metadata_json: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    metadata_json: Optional[str] = None


@router.post("/stateless/{agent_id}", response_model=ChatResponse)
async def generate_stateless_response(
    agent_id: UUID,
    request: ChatRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate a response from an agent without persisting history (Stateless).
    Ideal for quick testing inside the Project Workspace.
    """
    service = ThreadService(session)
    reply = await service.generate_stateless_response(
        agent_id, request.message, request.metadata_json, current_user
    )
    return {"reply": reply}


# --- Thread Management ---

@router.post("/", response_model=AgentThreadRead)
async def create_thread(
    *,
    session: AsyncSession = Depends(deps.get_session),
    thread_in: AgentThreadCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new Thread for persistent testing interactions.
    """
    service = ThreadService(session)
    return await service.create_thread(thread_in, current_user)


@router.get("/{thread_id}", response_model=AgentThreadRead)
async def get_thread(
    thread_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = ThreadService(session)
    return await service.get_thread(thread_id, current_user)


@router.post("/{thread_id}/messages", response_model=ThreadMessageRead)
async def send_message_to_thread(
    thread_id: UUID,
    request: ChatRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Send a message to a thread and trigger an agent response.
    """
    service = ThreadService(session)
    return await service.process_thread_message(
        thread_id, request.message, request.metadata_json, current_user
    )


@router.get("/{thread_id}/messages", response_model=List[ThreadMessageRead])
async def get_thread_messages(
    thread_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    service = ThreadService(session)
    return await service.get_thread_messages(thread_id, current_user)
