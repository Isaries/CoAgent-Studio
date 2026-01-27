"""
A2A Protocol Base Classes and Enums.

This module defines the abstract base class for A2A-compliant agents
and type-safe enumerations for agent identification.
"""

from abc import abstractmethod
from enum import Enum
from typing import Optional

from app.core.a2a.models import A2AMessage


class AgentId(str, Enum):
    """
    Type-safe enumeration of agent identifiers.
    
    Use these instead of hardcoded strings to prevent typos
    and enable IDE autocompletion.
    """
    TEACHER = "teacher"
    STUDENT = "student"
    SYSTEM = "system"
    BROADCAST = "broadcast"
    ALL = "all"


class A2AAgentMixin:
    """
    Mixin class that defines the A2A protocol interface for agents.
    
    Any agent that participates in A2A communication must implement
    the `receive_message` method. This mixin provides the interface
    contract without affecting the inheritance hierarchy.
    
    Example:
        class MyAgent(AgentCore, A2AAgentMixin):
            async def receive_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
                if msg.type == MessageType.SOME_TYPE:
                    return msg.reply(...)
                return None
    """
    
    @abstractmethod
    async def receive_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """
        Handle an incoming A2A message.
        
        This method is called by the A2ADispatcher when a message is
        routed to this agent. The agent should inspect the message type
        and return an appropriate response, or None if no response is needed.
        
        Args:
            msg: The incoming A2AMessage
            
        Returns:
            A response A2AMessage, or None if no response
        """
        pass
