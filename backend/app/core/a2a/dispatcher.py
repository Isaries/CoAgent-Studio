"""
A2A Protocol Dispatcher.

The Dispatcher is the central message router for Agent-to-Agent communication.
It manages agent registration, message routing, and middleware hooks.
"""

import structlog
from typing import Awaitable, Callable, Dict, List, Optional

from .models import A2AMessage, MessageType

logger = structlog.get_logger()

# Type alias for agent message handlers
MessageHandler = Callable[[A2AMessage], Awaitable[Optional[A2AMessage]]]
Middleware = Callable[[A2AMessage], Awaitable[None]]


class A2ADispatcher:
    """
    Central message dispatcher for A2A protocol.
    
    Agents register their handlers, and the dispatcher routes messages
    between them based on recipient_id.
    
    Example:
        dispatcher = A2ADispatcher()
        dispatcher.register("teacher", teacher_agent.receive_message)
        dispatcher.register("student", student_agent.receive_message)
        
        response = await dispatcher.dispatch(message)
    """

    def __init__(self):
        self._handlers: Dict[str, MessageHandler] = {}
        self._middleware: List[Middleware] = []
        self._broadcast_handler: Optional[Callable[[A2AMessage], Awaitable[None]]] = None

    def register(self, agent_id: str, handler: MessageHandler) -> None:
        """
        Register an agent's message handler.
        
        Args:
            agent_id: Unique identifier for the agent (e.g., "teacher", "student")
            handler: Async function that receives A2AMessage and returns optional response
        """
        self._handlers[agent_id] = handler
        logger.info("a2a_agent_registered", agent_id=agent_id)

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the dispatcher."""
        if agent_id in self._handlers:
            del self._handlers[agent_id]
            logger.info("a2a_agent_unregistered", agent_id=agent_id)

    def set_broadcast_handler(self, handler: Callable[[A2AMessage], Awaitable[None]]) -> None:
        """
        Set the handler for broadcast messages.
        This is typically the function that sends messages to WebSocket/Redis.
        """
        self._broadcast_handler = handler

    def add_middleware(self, fn: Middleware) -> None:
        """
        Add middleware that runs for every dispatched message.
        Useful for logging, auditing, rate limiting, etc.
        """
        self._middleware.append(fn)

    async def dispatch(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """
        Route a message to its recipient and return the response.
        
        Args:
            msg: The A2AMessage to dispatch
            
        Returns:
            Response message from the recipient, or None if no response
        """
        # Run all middleware
        for mw in self._middleware:
            try:
                await mw(msg)
            except Exception as e:
                logger.error("a2a_middleware_error", error=str(e), message_id=str(msg.id))

        logger.info(
            "a2a_dispatch",
            message_id=str(msg.id),
            type=msg.type.value,
            sender=msg.sender_id,
            recipient=msg.recipient_id,
        )

        # Handle broadcast messages
        if msg.recipient_id == "broadcast":
            if self._broadcast_handler:
                await self._broadcast_handler(msg)
            return None

        # Handle "all" recipient (notify all agents)
        if msg.recipient_id == "all":
            for agent_id, handler in self._handlers.items():
                if agent_id != msg.sender_id:
                    try:
                        await handler(msg)
                    except Exception as e:
                        logger.error("a2a_handler_error", agent_id=agent_id, error=str(e))
            return None

        # Route to specific recipient
        handler = self._handlers.get(msg.recipient_id)
        if handler:
            try:
                return await handler(msg)
            except Exception as e:
                logger.error(
                    "a2a_handler_error",
                    agent_id=msg.recipient_id,
                    error=str(e),
                    message_id=str(msg.id),
                )
                return None
        else:
            logger.warning("a2a_no_handler", recipient=msg.recipient_id)
            return None

    @property
    def registered_agents(self) -> List[str]:
        """Return list of registered agent IDs."""
        return list(self._handlers.keys())
