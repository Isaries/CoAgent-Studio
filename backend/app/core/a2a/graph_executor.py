"""
A2A Workflow Graph Executor.

Executes a WorkflowGraph by traversing nodes and dispatching messages
according to the graph's structure and conditions.
"""

import structlog
from typing import Any, Awaitable, Callable, Dict, Optional

from .dispatcher import A2ADispatcher
from .models import A2AMessage, MessageType
from .workflow import WorkflowGraph, WorkflowNode, WorkflowContext, NodeType
from .payloads import (
    EvaluationRequestPayload,
    EvaluationResultPayload,
    create_evaluation_request,
)

logger = structlog.get_logger()

# Type aliases
AgentHandler = Callable[[WorkflowContext], Awaitable[A2AMessage]]
ConditionHandler = Callable[[A2AMessage, WorkflowContext], str]
ActionHandler = Callable[[A2AMessage, WorkflowContext], Awaitable[None]]


class GraphExecutor:
    """
    Executes a WorkflowGraph by traversing nodes and dispatching messages.
    
    The executor maintains:
    - Agent handlers: Functions that process a node and return a message
    - Condition handlers: Functions that evaluate a condition and return an edge label
    - Action handlers: Functions that perform side effects (e.g., broadcast)
    
    Example:
        executor = GraphExecutor(graph, dispatcher)
        
        # Register handlers
        executor.register_agent("student", student_handler)
        executor.register_agent("teacher", teacher_handler)
        executor.register_condition("is_approved", check_approval)
        executor.register_action("broadcast", broadcast_handler)
        
        # Execute
        result = await executor.execute(initial_context)
    """
    
    def __init__(
        self,
        graph: WorkflowGraph,
        dispatcher: Optional[A2ADispatcher] = None,
        max_iterations: int = 50,
    ):
        """
        Initialize the executor.
        
        Args:
            graph: The workflow graph to execute
            dispatcher: Optional A2ADispatcher for message routing
            max_iterations: Maximum node transitions to prevent infinite loops
        """
        self._graph = graph
        self._dispatcher = dispatcher
        self._max_iterations = max_iterations
        
        self._agent_handlers: Dict[str, AgentHandler] = {}
        self._condition_handlers: Dict[str, ConditionHandler] = {}
        self._action_handlers: Dict[str, ActionHandler] = {}
    
    def register_agent(self, agent_id: str, handler: AgentHandler) -> "GraphExecutor":
        """
        Register an agent handler.
        
        Args:
            agent_id: The agent identifier (matches node.handler)
            handler: Async function that takes context and returns A2AMessage
        """
        self._agent_handlers[agent_id] = handler
        return self
    
    def register_condition(self, name: str, handler: ConditionHandler) -> "GraphExecutor":
        """
        Register a condition handler.
        
        Args:
            name: The condition name (matches node.handler)
            handler: Function that takes (message, context) and returns edge label
        """
        self._condition_handlers[name] = handler
        return self
    
    def register_action(self, name: str, handler: ActionHandler) -> "GraphExecutor":
        """
        Register an action handler.
        
        Args:
            name: The action name (matches node.handler)
            handler: Async function that takes (message, context) and performs side effect
        """
        self._action_handlers[name] = handler
        return self
    
    async def execute(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[A2AMessage]:
        """
        Execute the workflow from start to end.
        
        Args:
            initial_data: Initial context data (e.g., proposal, room_id)
            
        Returns:
            The final A2AMessage from the workflow, or None
            
        Raises:
            ValueError: If graph is invalid or max iterations exceeded
        """
        # Validate graph
        errors = self._graph.validate()
        if errors:
            raise ValueError(f"Invalid workflow graph: {errors}")
        
        # Initialize context
        context = WorkflowContext(data=initial_data or {})
        current_node_id = self._graph.start_node
        iterations = 0
        last_message: Optional[A2AMessage] = None
        
        logger.info(
            "workflow_execution_started",
            graph=self._graph.name,
            start_node=current_node_id,
        )
        
        while current_node_id and iterations < self._max_iterations:
            iterations += 1
            node = self._graph.nodes.get(current_node_id)
            
            if not node:
                logger.error("workflow_node_not_found", node_id=current_node_id)
                break
            
            context.history.append(current_node_id)
            
            logger.debug(
                "workflow_node_enter",
                node_id=current_node_id,
                node_type=node.type.value,
                iteration=iterations,
            )
            
            # Process node based on type
            if node.type == NodeType.END:
                logger.info(
                    "workflow_execution_completed",
                    graph=self._graph.name,
                    final_node=current_node_id,
                    iterations=iterations,
                    status=node.config.get("status", "completed"),
                )
                break
            
            elif node.type == NodeType.START:
                # Just pass through
                pass
            
            elif node.type == NodeType.AGENT:
                last_message = await self._execute_agent_node(node, context)
                context.last_result = last_message
            
            elif node.type == NodeType.CONDITION:
                condition_result = self._execute_condition_node(node, last_message, context)
                context.condition_result = condition_result
            
            elif node.type == NodeType.ACTION:
                await self._execute_action_node(node, last_message, context)
            
            # Find next node
            next_node_id = self._graph.get_next_node(
                current_node_id,
                context.condition_result if node.type == NodeType.CONDITION else None,
            )
            
            # Clear condition result after use
            if node.type != NodeType.CONDITION:
                context.condition_result = None
            
            current_node_id = next_node_id
        
        if iterations >= self._max_iterations:
            logger.error(
                "workflow_max_iterations_exceeded",
                graph=self._graph.name,
                max=self._max_iterations,
            )
            raise ValueError(f"Workflow exceeded maximum iterations ({self._max_iterations})")
        
        return last_message
    
    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: WorkflowContext,
    ) -> Optional[A2AMessage]:
        """Execute an AGENT node."""
        handler_id = node.handler
        if not handler_id:
            logger.warning("workflow_agent_no_handler", node_id=node.id)
            return None
        
        handler = self._agent_handlers.get(handler_id)
        if not handler:
            logger.warning("workflow_agent_handler_not_found", handler=handler_id)
            return None
        
        try:
            message = await handler(context)
            logger.info(
                "workflow_agent_executed",
                node_id=node.id,
                agent=handler_id,
                message_type=message.type.value if message else None,
            )
            return message
        except Exception as e:
            logger.error(
                "workflow_agent_error",
                node_id=node.id,
                agent=handler_id,
                error=str(e),
            )
            raise
    
    def _execute_condition_node(
        self,
        node: WorkflowNode,
        message: Optional[A2AMessage],
        context: WorkflowContext,
    ) -> str:
        """Execute a CONDITION node and return the result label."""
        handler_name = node.handler
        if not handler_name:
            logger.warning("workflow_condition_no_handler", node_id=node.id)
            return "default"
        
        handler = self._condition_handlers.get(handler_name)
        if not handler:
            # Built-in condition: is_approved
            if handler_name == "is_approved":
                return self._builtin_is_approved(message)
            
            logger.warning("workflow_condition_handler_not_found", handler=handler_name)
            return "default"
        
        try:
            result = handler(message, context)
            logger.info(
                "workflow_condition_evaluated",
                node_id=node.id,
                condition=handler_name,
                result=result,
            )
            return result
        except Exception as e:
            logger.error(
                "workflow_condition_error",
                node_id=node.id,
                condition=handler_name,
                error=str(e),
            )
            return "error"
    
    async def _execute_action_node(
        self,
        node: WorkflowNode,
        message: Optional[A2AMessage],
        context: WorkflowContext,
    ) -> None:
        """Execute an ACTION node."""
        handler_name = node.handler
        if not handler_name:
            logger.warning("workflow_action_no_handler", node_id=node.id)
            return
        
        handler = self._action_handlers.get(handler_name)
        if not handler:
            logger.warning("workflow_action_handler_not_found", handler=handler_name)
            return
        
        try:
            await handler(message, context)
            logger.info(
                "workflow_action_executed",
                node_id=node.id,
                action=handler_name,
            )
        except Exception as e:
            logger.error(
                "workflow_action_error",
                node_id=node.id,
                action=handler_name,
                error=str(e),
            )
            raise
    
    def _builtin_is_approved(self, message: Optional[A2AMessage]) -> str:
        """Built-in condition handler for checking approval status."""
        if not message:
            return "rejected"
        
        if message.type != MessageType.EVALUATION_RESULT:
            return "rejected"
        
        content = message.content
        
        # Handle EvaluationResultPayload
        if isinstance(content, EvaluationResultPayload):
            return "approved" if content.approved else "rejected"
        
        # Handle dict
        if isinstance(content, dict):
            return "approved" if content.get("approved") else "rejected"
        
        return "rejected"
