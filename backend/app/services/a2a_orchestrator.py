"""
A2A Orchestrator Service.

This module handles the A2A protocol workflow for agent communication,
separating the orchestration logic from the execution service.
"""

import structlog
from typing import Optional

from app.core.a2a import A2ADispatcher, A2AMessage, MessageType, AgentId
if False:  # TYPE_CHECKING
    from app.core.a2a.store import A2AMessageStore
from app.core.specialized_agents import StudentAgent, TeacherAgent

logger = structlog.get_logger()


class A2AOrchestrator:
    """
    Orchestrates A2A protocol communication between agents.
    
    This class encapsulates the Dispatcher lifecycle and provides
    high-level methods for common agent interaction patterns.
    
    Example:
        orchestrator = A2AOrchestrator()
        orchestrator.register_agents(teacher, student)
        result = await orchestrator.request_evaluation(proposal, context)
    """
    
    def __init__(self):
        self._dispatcher = A2ADispatcher()
        self._teacher: Optional[TeacherAgent] = None
        self._student: Optional[StudentAgent] = None
    
    @property
    def dispatcher(self) -> A2ADispatcher:
        """Access the underlying dispatcher for advanced use cases."""
        return self._dispatcher
    

    def register_agents(
        self,
        teacher: TeacherAgent,
        student: StudentAgent,
        store: Optional["A2AMessageStore"] = None,
    ) -> None:
        """
        Register teacher and student agents with the dispatcher.
        
        Args:
            teacher: The TeacherAgent instance
            student: The StudentAgent instance
            store: Optional A2AMessageStore for persistence
        """
        self._teacher = teacher
        self._student = student
        self._store = store  # type: ignore[name-defined] # handled by runtime import or forward ref
        
        self._dispatcher.register(AgentId.TEACHER, teacher.receive_message)
        self._dispatcher.register(AgentId.STUDENT, student.receive_message)
        
        # Configure persistence middleware if store provided
        if self._store:
            async def persistence_middleware(msg: A2AMessage):
                try:
                    await self._store.save(msg)
                except Exception as e:
                    logger.error("a2a_persistence_failed", error=str(e), message_id=str(msg.id))
            
            self._dispatcher.add_middleware(persistence_middleware)
            
        logger.info("a2a_orchestrator_agents_registered", persistence_enabled=bool(store))
    
    async def request_evaluation(
        self,
        proposal: str,
        context: str,
        room_id: str,
    ) -> Optional[A2AMessage]:
        """
        Execute the Student -> Teacher evaluation flow.
        """
        eval_request = A2AMessage(
            type=MessageType.EVALUATION_REQUEST,
            sender_id=AgentId.STUDENT,
            recipient_id=AgentId.TEACHER,
            content=proposal,
            metadata={"context": context, "room_id": room_id},
        )
        
        logger.info(
            "a2a_evaluation_requested",
            proposal_preview=proposal[:50] if proposal else "",
            room_id=room_id,
        )
        
        # Dispatch request (saved by middleware)
        response = await self._dispatcher.dispatch(eval_request)
        
        # Manually save response (since it's a return value, not a dispatch)
        if response and self._store:
            try:
                await self._store.save(response)
            except Exception as e:
                logger.error("a2a_persistence_failed_response", error=str(e))
                
        return response
    
    async def process_approval(self, eval_result: A2AMessage) -> Optional[A2AMessage]:
        """
        Process the Teacher's evaluation result through the Student.
        """
        return await self._dispatcher.dispatch(eval_result)
    
    def is_approved(self, eval_result: Optional[A2AMessage]) -> bool:
        """Check if an evaluation result indicates approval."""
        if not eval_result:
            return False
        if eval_result.type != MessageType.EVALUATION_RESULT:
            return False
        content = eval_result.content
        return isinstance(content, dict) and content.get("approved", False)
    
    def get_proposal_from_result(self, eval_result: A2AMessage) -> str:
        """Extract the original proposal from an evaluation result."""
        content = eval_result.content
        if isinstance(content, dict):
            return content.get("proposal", "")
        return ""
