"""
A2A Orchestrator Service.

This module handles the A2A protocol workflow for agent communication,
separating the orchestration logic from the execution service.
"""

import structlog
from typing import Optional, Dict, Any

from app.core.a2a import (
    A2AMessage,
    MessageType,
    AgentId,
    HybridDispatcher,
    DispatchMode,
    create_hybrid_dispatcher,
    GraphExecutor,
    create_student_teacher_workflow,
    WorkflowGraph,
)

if False:  # TYPE_CHECKING
    from app.core.a2a.store import A2AMessageStore
from app.services.agents.std_agents import StudentAgent, TeacherAgent

logger = structlog.get_logger()


class A2AOrchestrator:
    """
    Orchestrates A2A protocol communication using Graph Workflows.
    
    This replaces the legacy imperative orchestration with a declarative
    GraphExecutor, enabling flexible and resilient agent workflows.
    """
    
    def __init__(self):
        # Dispatcher initialized in async method or lazily
        self._dispatcher: Optional[HybridDispatcher] = None
        self._executor: Optional[GraphExecutor] = None
        self._graph: Optional[WorkflowGraph] = None
        
        self._teacher: Optional[TeacherAgent] = None
        self._student: Optional[StudentAgent] = None
        self._store: Optional["A2AMessageStore"] = None
        
    @property
    def dispatcher(self) -> HybridDispatcher:
        """Access the underlying dispatcher."""
        if not self._dispatcher:
            raise RuntimeError("Orchestrator not initialized. Call register_agents first.")
        return self._dispatcher
    
    async def initialize(self) -> None:
        """Async initialization for distributed connections."""
        if not self._dispatcher:
            # Use AUTO mode to support both local and distributed deployments
            self._dispatcher = await create_hybrid_dispatcher(mode=DispatchMode.AUTO)
            
            # Setup Workflow
            self._graph = create_student_teacher_workflow()
            self._executor = GraphExecutor(self._graph, self._dispatcher)

            # Register standard actions
            self._executor.register_action("broadcast", self._broadcast_action)

    async def register_agents(
        self,
        teacher: TeacherAgent,
        student: StudentAgent,
        store: Optional["A2AMessageStore"] = None,
    ) -> None:
        """
        Register agents and setup the graph executor.
        """
        await self.initialize()
        
        self._teacher = teacher
        self._student = student
        self._store = store
        
        # Register Workflow Handlers (Agent adapters)
        if self._executor:
            self._executor.register_agent("teacher", teacher.handle_workflow_step)
            self._executor.register_agent("student", student.handle_workflow_step)
            self._executor.register_condition("is_approved", self._check_approval_condition)
        
        # Also register for direct dispatch (legacy/direct support)
        # Note: HybridDispatcher handles registration unified
        self._dispatcher.register(AgentId.TEACHER, teacher.receive_message)
        self._dispatcher.register(AgentId.STUDENT, student.receive_message)
        
        # Configure persistence middleware
        if self._store:
            async def persistence_middleware(msg: A2AMessage):
                try:
                    await self._store.save(msg)
                except Exception as e:
                    logger.error("a2a_persistence_failed", error=str(e), message_id=str(msg.id))
            
            self._dispatcher.add_middleware(persistence_middleware)
            
        logger.info("a2a_orchestrator_initialized", mode=self._dispatcher.mode)

    async def request_evaluation(
        self,
        proposal: str,
        context: str,
        room_id: str,
        message_history: Optional[list] = None
    ) -> Optional[A2AMessage]:
        """
        Execute the Student -> Teacher evaluation flow using Graph Executor.
        
        Args:
            proposal: Initial proposal text (optional override)
            context: Context string
            room_id: Room ID
            message_history: List of chat messages for Student to generate proposal
        """
        if not self._executor:
            raise RuntimeError("Executor not initialized")
            
        # Prepare initial context data for the workflow
        initial_data = {
            "room_id": room_id,
            "context": context,
            "message_history": message_history or [],
            "proposal_override": proposal  # Optional: force a specific proposal
        }
        
        logger.info("a2a_workflow_start", graph="student_teacher_review", room_id=room_id)
        
        # Execute the full graph
        # The result will be the final message of the flow (e.g. Broadcast or End)
        result = await self._executor.execute(initial_data)
        
        return result

    # === Helper Handlers for Graph ===

    def _check_approval_condition(self, message: Optional[A2AMessage], context: Any) -> str:
        """Condition handler for 'is_approved' node."""
        if not message or message.type != MessageType.EVALUATION_RESULT:
            return "rejected"
        
        content = message.content
        is_approved = False
        
        if isinstance(content, dict):
            is_approved = content.get("approved", False)
        elif hasattr(content, "approved"):
            is_approved = content.approved
            
        return "approved" if is_approved else "rejected"

    async def _broadcast_action(self, message: Optional[A2AMessage], context: Any) -> None:
        """Action handler for 'broadcast' node."""
        # In a real system, this might push to a websocket via another service.
        # For now, we ensure the message allows downstream processing or logging.
        if message:
            proposal = str(message.content) if isinstance(message.content, str) else str(message.content.get("proposal", ""))
            
            # Create Broadcast Message
            broadcast_msg = A2AMessage(
                type=MessageType.BROADCAST,
                sender_id=AgentId.STUDENT, # Student is technically the broadcaster
                recipient_id=AgentId.BROADCAST,
                content=proposal,
                metadata={"original_request_id": str(message.id)}
            )
            
            logger.info(
                "a2a_broadcast_triggered",
                content=proposal[:50],
                sender=message.sender_id
            )
            
            # Persist if store available
            if self._store:
                try:
                    await self._store.save(broadcast_msg)
                except Exception as e:
                    logger.error("a2a_broadcast_save_failed", error=str(e))

            # Optional: If using distributed dispatcher, we might want to actually dispatch it 
            # so other subscribers (WebSockets) pick it up.
            try:
                # We use dispatch but we don't expect a reply
                await self._dispatcher.dispatch(broadcast_msg)
            except Exception as e:
                logger.warning("a2a_broadcast_dispatch_failed", error=str(e))
                
        pass

    # === Legacy Methods Support (Deprecated but kept for compat) ===
    
    async def process_approval(self, eval_result: A2AMessage) -> Optional[A2AMessage]:
        """Process approval (Legacy direct dispatch)."""
        return await self._dispatcher.dispatch(eval_result)
    
    def is_approved(self, eval_result: Optional[A2AMessage]) -> bool:
        """Check approval status (Legacy)."""
        return self._check_approval_condition(eval_result, None) == "approved"
    
    def get_proposal_from_result(self, eval_result: A2AMessage) -> str:
        """Extract proposal (Legacy)."""
        content = eval_result.content
        if isinstance(content, dict):
            return content.get("proposal", "")
        elif hasattr(content, "proposal"):
            return content.proposal
        return ""
