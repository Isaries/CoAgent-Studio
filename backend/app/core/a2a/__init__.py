# A2A Core Module
from .base import A2AAgentMixin, AgentId

# P1.5: Dynamic Workflow Compiler (LangGraph)
from .compiler import MultiAgentState, WorkflowCompiler
from .dispatcher import A2ADispatcher

# P3: Distributed Messaging (Redis Streams)
from .distributed import (
    DistributedDispatcher,
    DistributedDispatcherConfig,
    create_distributed_dispatcher,
)

# P4: External Agent Integration
from .external_adapter import (
    AuthType,
    ExternalAgentAdapter,
)
from .hybrid import (
    DispatchMode,
    HybridDispatcher,
    create_hybrid_dispatcher,
)
from .models import A2AMessage, MessageType

# P0: Structured Payloads
from .payloads import (
    PAYLOAD_SCHEMA_REGISTRY,
    A2APayload,
    BroadcastPayload,
    EvaluationRequestPayload,
    EvaluationResultPayload,
    ProposalPayload,
    SystemPayload,
    UserMessagePayload,
    create_evaluation_request,
    create_evaluation_result,
    validate_payload,
)

# P2: Resilience Patterns
from .resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    MaxRetriesExceededError,
    get_circuit_breaker,
    reset_all_breakers,
    retry_with_backoff,
    with_resilience,
    with_timeout,
)
from .store import A2AMessageRecord, A2AMessageStore

# P1: Declarative Workflow Graph DSL
from .workflow_graph import (
    GraphExecutor,
    NodeType,
    WorkflowContext,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    create_student_teacher_workflow,
)

__all__ = [
    # Core
    "A2AMessage",
    "MessageType",
    "A2ADispatcher",
    "AgentId",
    "A2AAgentMixin",
    "A2AMessageStore",
    "A2AMessageRecord",
    # Payloads
    "A2APayload",
    "EvaluationRequestPayload",
    "EvaluationResultPayload",
    "BroadcastPayload",
    "ProposalPayload",
    "SystemPayload",
    "UserMessagePayload",
    "validate_payload",
    "create_evaluation_request",
    "create_evaluation_result",
    "PAYLOAD_SCHEMA_REGISTRY",
    # P1: Declarative DSL
    "WorkflowGraph",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowContext",
    "NodeType",
    "GraphExecutor",
    "create_student_teacher_workflow",
    # Compiler
    "WorkflowCompiler",
    "MultiAgentState",
    # Resilience
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "MaxRetriesExceededError",
    "get_circuit_breaker",
    "reset_all_breakers",
    "retry_with_backoff",
    "with_resilience",
    "with_timeout",
    # Distributed
    "DistributedDispatcher",
    "DistributedDispatcherConfig",
    "create_distributed_dispatcher",
    "HybridDispatcher",
    "DispatchMode",
    "create_hybrid_dispatcher",
    # External
    "ExternalAgentAdapter",
    "AuthType",
]
