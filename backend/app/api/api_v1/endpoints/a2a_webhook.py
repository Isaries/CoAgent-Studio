"""
A2A Webhook API Endpoints.

Receives messages from external agents and injects them into the A2A system.
"""

import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select

from app.core.db import get_session
from app.core.a2a.models import A2AMessage, MessageType
from app.core.a2a.store import A2AMessageStore
from app.core.socket_manager import manager

from app.models.agent_config import AgentConfig

logger = structlog.get_logger()

router = APIRouter(prefix="/a2a", tags=["A2A Webhook"])


class A2AWebhookPayload(BaseModel):
    """Incoming webhook payload from external agent."""
    id: Optional[str] = None
    type: str = "broadcast"
    sender_id: str
    recipient_id: str = "broadcast"
    content: Any
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class A2AWebhookResponse(BaseModel):
    """Response for webhook."""
    success: bool
    message_id: Optional[str] = None
    dispatched: bool = False
    error: Optional[str] = None


@router.post("/webhook", response_model=A2AWebhookResponse)
async def receive_external_agent_message(
    payload: A2AWebhookPayload,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token"),
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-ID"),
    session=Depends(get_session),
):
    """
    Receive a message from an external agent and dispatch it.
    
    The external agent must include:
    - X-Agent-ID header: UUID of the registered external agent
    - X-Agent-Token header: Authentication token (matches callback_token in external_config)
    
    The message will be validated, persisted, and dispatched to the room.
    """
    if not x_agent_id:
        raise HTTPException(status_code=400, detail="X-Agent-ID header required")
    
    try:
        agent_uuid = UUID(x_agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Agent-ID format")
    
    # Validate agent exists and is external
    query = select(AgentConfig).where(
        AgentConfig.id == agent_uuid,
        AgentConfig.is_external == True,
    )
    result = await session.exec(query)
    agent_config = result.first()
    
    if not agent_config:
        raise HTTPException(status_code=404, detail="External agent not found")
    
    # Validate token
    external_config = agent_config.external_config or {}
    expected_token = external_config.get("callback_token")
    
    if expected_token and x_agent_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    
    # Extract room_id from metadata (required for broadcast)
    room_id = (payload.metadata or {}).get("room_id")
    
    # Create A2A message
    a2a_message = A2AMessage(
        type=MessageType(payload.type),
        sender_id=payload.sender_id,
        recipient_id=payload.recipient_id,
        content=payload.content,
        correlation_id=UUID(payload.correlation_id) if payload.correlation_id else None,
        metadata={
            **(payload.metadata or {}),
            "external_agent_id": str(agent_uuid),
            "external_agent_name": agent_config.name,
            "received_at": datetime.utcnow().isoformat(),
        },
    )
    
    # Persist message to database
    try:
        store = A2AMessageStore(session)
        await store.save(a2a_message, room_id=room_id)
    except Exception as e:
        logger.warning("a2a_message_persist_failed", error=str(e), message_id=str(a2a_message.id))
    
    # Dispatch message
    dispatched = False
    dispatch_error = None
    
    if payload.recipient_id == "broadcast" and room_id:
        # Broadcast to room via WebSocket
        try:
            broadcast_payload = {
                "type": "a2a_external_message",
                "agent_id": str(agent_uuid),
                "agent_name": agent_config.name,
                "agent_type": agent_config.type,
                "message_type": payload.type,
                "content": payload.content,
                "message_id": str(a2a_message.id),
                "correlation_id": payload.correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await manager.broadcast(broadcast_payload, room_id)
            dispatched = True
            
            logger.info(
                "external_message_dispatched",
                agent_id=str(agent_uuid),
                agent_type=agent_config.type,
                message_type=payload.type,
                message_id=str(a2a_message.id),
                room_id=room_id,
            )
        except Exception as e:
            dispatch_error = str(e)
            logger.error("external_message_dispatch_failed", error=str(e), message_id=str(a2a_message.id))
    
    elif payload.recipient_id != "broadcast":
        # Point-to-point dispatch to specific agent
        try:
            target_agent_id = UUID(payload.recipient_id)
            
            # Look up target agent config
            target_query = select(AgentConfig).where(AgentConfig.id == target_agent_id)
            target_result = await session.exec(target_query)
            target_config = target_result.first()
            
            if not target_config:
                dispatch_error = f"Target agent {payload.recipient_id} not found"
            elif target_config.is_external:
                # Forward to external agent via HTTP
                from app.core.a2a.external_adapter import ExternalAgentAdapter
                
                adapter = ExternalAgentAdapter(target_config)
                response = await adapter.receive_message(a2a_message)
                dispatched = True
                
                logger.info(
                    "external_message_p2p_dispatched",
                    source_agent=str(agent_uuid),
                    target_agent=str(target_agent_id),
                    message_id=str(a2a_message.id),
                )
                
                # If target responded, broadcast response to room
                if response and response.content and room_id:
                    response_payload = {
                        "type": "a2a_external_message",
                        "agent_id": str(target_config.id),
                        "agent_name": target_config.name,
                        "agent_type": target_config.type,
                        "message_type": "response",
                        "content": response.content,
                        "message_id": str(response.id),
                        "correlation_id": str(a2a_message.id),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await manager.broadcast(response_payload, room_id)
            else:
                # Internal agent - store message for pickup
                # Internal agents will receive via normal execution flow
                dispatched = True
                logger.info(
                    "external_message_p2p_internal",
                    source_agent=str(agent_uuid),
                    target_agent=str(target_agent_id),
                    message_id=str(a2a_message.id),
                    note="Message stored for internal agent pickup",
                )
                
        except ValueError:
            dispatch_error = f"Invalid recipient_id format: {payload.recipient_id}"
        except Exception as e:
            dispatch_error = str(e)
            logger.error("external_message_p2p_failed", error=str(e), message_id=str(a2a_message.id))
    else:
        # Missing room_id for broadcast
        logger.warning(
            "external_message_no_room",
            agent_id=str(agent_uuid),
            message_id=str(a2a_message.id),
            note="Broadcast requires room_id in metadata",
        )
    
    return A2AWebhookResponse(
        success=True,
        message_id=str(a2a_message.id),
        dispatched=dispatched,
        error=dispatch_error,
    )


@router.get("/health")
async def a2a_health():
    """Health check endpoint for external agents to verify connectivity."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


