from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.models.agent_config import AgentConfig
from app.models.thread import (
    AgentThread, AgentThreadCreate, AgentThreadRead,
    ThreadMessage, ThreadMessageCreate, ThreadMessageRead
)
from app.models.user import User

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
    # 1. Verify agent exists & access
    agent_config = await session.get(AgentConfig, agent_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # TODO: Verify user has access to agent_config.project_id via UserProjectLink
    
    # 2. Generate response via AgentCore
    from app.factories.agent_factory import AgentFactory
    
    # Simple history setup for stateless
    from app.models.message import Message
    temp_history = [Message(sender_id=str(current_user.id), content=request.message, room_id=UUID('00000000-0000-0000-0000-000000000000'))]
    
    # Try fetching saved user keys to use
    from app.services.user_key_service import UserKeyService
    key_service = UserKeyService(session)
    decrypted_keys = []
    if agent_config.user_key_ids and agent_config.created_by:
        for k_id in agent_config.user_key_ids:
            try:
                dk = await key_service.get_decrypted_key(k_id, agent_config.created_by)
                if dk: decrypted_keys.append(dk)
            except Exception: pass

    agent = AgentFactory.create_agent(agent_config, api_keys=decrypted_keys)
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to initialize agent")

    # In AgentCore, we can just use generate_reply (assuming it accepts this shape)
    reply = await agent.generate_reply(temp_history)
    
    # handle tool call responses directly (simplified for testing)
    if isinstance(reply, list):
         reply = f"System: Executed {len(reply)} tools."
         
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
    agent = await session.get(AgentConfig, thread_in.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    thread = AgentThread(
        project_id=thread_in.project_id,
        agent_id=thread_in.agent_id,
        user_id=current_user.id,
        name=thread_in.name,
    )
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread


@router.get("/{thread_id}", response_model=AgentThreadRead)
async def get_thread(
    thread_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    thread = await session.get(AgentThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    if thread.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return thread


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
    thread = await session.get(AgentThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    if thread.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 1. Save User Message
    user_msg = ThreadMessage(
        thread_id=thread.id,
        role="user",
        content=request.message,
        metadata_json=request.metadata_json
    )
    session.add(user_msg)
    await session.commit()
    
    # 2. Trigger Agent execution (stubbed/simplified for now)
    agent_config = await session.get(AgentConfig, thread.agent_id)
    
    from app.factories.agent_factory import AgentFactory
    
    # Load past history
    query = select(ThreadMessage).where(ThreadMessage.thread_id == thread.id).order_by(ThreadMessage.created_at.asc())
    hist_result = await session.exec(query)
    thread_history = hist_result.all()
    
    # Convert ThreadMessage to generic Message shape for AgentCore
    from app.models.message import Message
    simulated_history = []
    for th in thread_history:
        simulated_history.append(
            Message(sender_id=str(current_user.id) if th.role == "user" else "agent", content=th.content, room_id=UUID('00000000-0000-0000-0000-000000000000'))
        )
        
    # Keys
    from app.services.user_key_service import UserKeyService
    key_service = UserKeyService(session)
    decrypted_keys = []
    if agent_config.user_key_ids and agent_config.created_by:
        for k_id in agent_config.user_key_ids:
            try:
                dk = await key_service.get_decrypted_key(k_id, agent_config.created_by)
                if dk: decrypted_keys.append(dk)
            except Exception: pass

    agent = AgentFactory.create_agent(agent_config, api_keys=decrypted_keys)
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to initialize agent")
        
    reply = await agent.generate_reply(simulated_history)
    
    if isinstance(reply, list):
         reply = f"System: Executed {len(reply)} tools."
         
    # 3. Save Agent Message
    agent_msg = ThreadMessage(
        thread_id=thread.id,
        role="assistant",
        content=reply
    )
    session.add(agent_msg)
    await session.commit()
    await session.refresh(agent_msg)
    
    return agent_msg

@router.get("/{thread_id}/messages", response_model=List[ThreadMessageRead])
async def get_thread_messages(
    thread_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    thread = await session.get(AgentThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    query = select(ThreadMessage).where(ThreadMessage.thread_id == thread_id).order_by(ThreadMessage.created_at.asc())
    result = await session.exec(query)
    return result.all()
