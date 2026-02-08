# A2A Core Module
from .models import A2AMessage, MessageType
from .dispatcher import A2ADispatcher
from .base import AgentId, A2AAgentMixin
from .store import A2AMessageStore, A2AMessageRecord

# P0: Structured Payloads
from .payloads import (
    A2APayload,
    EvaluationRequestPayload,
    EvaluationResultPayload,
    BroadcastPayload,
    ProposalPayload,
    SystemPayload,
    UserMessagePayload,
    validate_payload,
    create_evaluation_request,
    create_evaluation_result,
    PAYLOAD_SCHEMA_REGISTRY,
)

# P1: Graph-based Workflow
from .workflow import (
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    WorkflowContext,
    NodeType,
    create_student_teacher_workflow,
    create_direct_broadcast_workflow,
)
from .graph_executor import GraphExecutor

# P2: Resilience Patterns
from .resilience import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    MaxRetriesExceededError,
    get_circuit_breaker,
    reset_all_breakers,
    retry_with_backoff,
    with_resilience,
    with_timeout,
)

# P3: Distributed Messaging (Redis Streams)
from .distributed import (
    DistributedDispatcher,
    DistributedDispatcherConfig,
    create_distributed_dispatcher,
)
from .hybrid import (
    HybridDispatcher,
    DispatchMode,
    create_hybrid_dispatcher,
)

# P4: External Agent Integration
from .external_adapter import (
    ExternalAgentAdapter,
    AuthType,
)

__all__ = [
    # Core
    "A2AMessage", "MessageType", "A2ADispatcher", 
    "AgentId", "A2AAgentMixin",
    "A2AMessageStore", "A2AMessageRecord",
    # Payloads
    "A2APayload", "EvaluationRequestPayload", "EvaluationResultPayload",
    "BroadcastPayload", "ProposalPayload", "SystemPayload", "UserMessagePayload",
    "validate_payload", "create_evaluation_request", "create_evaluation_result",
    "PAYLOAD_SCHEMA_REGISTRY",
    # Workflow
    "WorkflowGraph", "WorkflowNode", "WorkflowEdge", "WorkflowContext", "NodeType",
    "GraphExecutor", "create_student_teacher_workflow", "create_direct_broadcast_workflow",
    # Resilience
    "CircuitBreaker", "CircuitState", "CircuitOpenError", "MaxRetriesExceededError",
    "get_circuit_breaker", "reset_all_breakers", "retry_with_backoff",
    "with_resilience", "with_timeout",
    # Distributed
    "DistributedDispatcher", "DistributedDispatcherConfig", "create_distributed_dispatcher",
    "HybridDispatcher", "DispatchMode", "create_hybrid_dispatcher",
    # External
    "ExternalAgentAdapter", "AuthType",
]



