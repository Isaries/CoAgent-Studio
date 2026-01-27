"""
A2A Protocol Structured Payloads.

Defines strongly-typed Pydantic models for each MessageType's content,
enabling compile-time validation and better IDE support.
"""

from typing import Optional, Union, Literal, Any
from pydantic import BaseModel, Field


class EvaluationRequestPayload(BaseModel):
    """
    Payload for EVALUATION_REQUEST messages.
    Sent from Student → Teacher to request proposal review.
    """
    proposal: str = Field(..., min_length=1, max_length=50000, description="The proposed message content")
    context: str = Field(default="", description="Chat history context for evaluation")
    urgency: Literal["low", "normal", "high"] = Field(default="normal", description="Priority level")
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class EvaluationResultPayload(BaseModel):
    """
    Payload for EVALUATION_RESULT messages.
    Sent from Teacher → Student with evaluation outcome.
    """
    approved: bool = Field(..., description="Whether the proposal was approved")
    proposal: str = Field(..., description="The original proposal being evaluated")
    score: Optional[float] = Field(None, ge=0, le=100, description="Optional quality score (0-100)")
    feedback: Optional[str] = Field(None, description="Optional feedback or reason for decision")
    
    class Config:
        extra = "allow"


class BroadcastPayload(BaseModel):
    """
    Payload for BROADCAST messages.
    The final message to be sent to the chat room.
    """
    content: str = Field(..., min_length=1, description="Message content to broadcast")
    format: Literal["text", "markdown", "html"] = Field(default="text", description="Content format")
    
    class Config:
        extra = "allow"


class ProposalPayload(BaseModel):
    """
    Payload for PROPOSAL messages.
    Initial draft from an agent before evaluation.
    """
    draft: str = Field(..., min_length=1, description="Draft content")
    intent: Optional[str] = Field(None, description="Intent or goal of this proposal")
    annotations: Optional[dict] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        extra = "allow"


class SystemPayload(BaseModel):
    """
    Payload for SYSTEM messages.
    Used for joins, leaves, errors, and other system events.
    """
    event: Literal["join", "leave", "error", "info", "warning"] = Field(..., description="Event type")
    message: str = Field(..., description="Human-readable message")
    details: Optional[dict] = Field(default_factory=dict, description="Additional event details")
    
    class Config:
        extra = "allow"


class UserMessagePayload(BaseModel):
    """
    Payload for USER_MESSAGE messages.
    Messages originating from human users.
    """
    content: str = Field(..., min_length=1, description="User's message content")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    class Config:
        extra = "allow"


# Union of all payload types for flexible typing
A2APayload = Union[
    EvaluationRequestPayload,
    EvaluationResultPayload,
    BroadcastPayload,
    ProposalPayload,
    SystemPayload,
    UserMessagePayload,
    str,  # Fallback for simple string messages
    dict,  # Fallback for unstructured data
]


# Registry mapping MessageType to expected payload class
from .models import MessageType

PAYLOAD_SCHEMA_REGISTRY: dict[MessageType, type[BaseModel]] = {
    MessageType.EVALUATION_REQUEST: EvaluationRequestPayload,
    MessageType.EVALUATION_RESULT: EvaluationResultPayload,
    MessageType.BROADCAST: BroadcastPayload,
    MessageType.PROPOSAL: ProposalPayload,
    MessageType.SYSTEM: SystemPayload,
    MessageType.USER_MESSAGE: UserMessagePayload,
}


def validate_payload(message_type: MessageType, content: Any) -> A2APayload:
    """
    Validate and coerce content to the appropriate payload type.
    
    Args:
        message_type: The type of A2A message
        content: The raw content to validate
        
    Returns:
        Validated payload object
        
    Raises:
        ValueError: If content doesn't match expected schema
    """
    schema = PAYLOAD_SCHEMA_REGISTRY.get(message_type)
    
    if schema is None:
        # No schema defined, return as-is
        return content
    
    # Already validated
    if isinstance(content, schema):
        return content
    
    # String content - wrap in appropriate field
    if isinstance(content, str):
        if message_type == MessageType.EVALUATION_REQUEST:
            return EvaluationRequestPayload(proposal=content)
        elif message_type == MessageType.BROADCAST:
            return BroadcastPayload(content=content)
        elif message_type == MessageType.PROPOSAL:
            return ProposalPayload(draft=content)
        elif message_type == MessageType.USER_MESSAGE:
            return UserMessagePayload(content=content)
        else:
            return content
    
    # Dict content - try to parse as schema
    if isinstance(content, dict):
        try:
            return schema.model_validate(content)
        except Exception as e:
            # Fallback to raw dict if validation fails
            import structlog
            logger = structlog.get_logger()
            logger.warning(
                "payload_validation_failed",
                message_type=message_type.value,
                error=str(e),
            )
            return content
    
    return content


def create_evaluation_request(
    proposal: str,
    context: str = "",
    urgency: Literal["low", "normal", "high"] = "normal",
) -> EvaluationRequestPayload:
    """Factory function for creating evaluation request payloads."""
    return EvaluationRequestPayload(
        proposal=proposal,
        context=context,
        urgency=urgency,
    )


def create_evaluation_result(
    approved: bool,
    proposal: str,
    score: Optional[float] = None,
    feedback: Optional[str] = None,
) -> EvaluationResultPayload:
    """Factory function for creating evaluation result payloads."""
    return EvaluationResultPayload(
        approved=approved,
        proposal=proposal,
        score=score,
        feedback=feedback,
    )
