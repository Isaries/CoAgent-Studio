# A2A Protocol Implementation in CoAgent-Studio

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Components](#core-components)
- [Message Flow](#message-flow)
- [Advanced Features](#advanced-features)
- [Integration Guide](#integration-guide)
- [API Reference](#api-reference)
- [Examples](#examples)

---

## Overview

CoAgent-Studio implements a comprehensive **Agent-to-Agent (A2A) Protocol** for managing structured communication between multiple AI agents. This protocol is based on the [A2A Protocol Specification](https://a2a-protocol.org) and optimized for educational scenarios involving Teacher-Student interactions.

### Key Features

- **Standardized Messaging**: Type-safe message envelopes with correlation tracking
- **Declarative Workflows**: Graph-based workflow definitions for complex agent interactions
- **Flexible Routing**: Support for point-to-point broadcast and distributed messaging
- **Resilience Patterns**: Built-in circuit breakers retry mechanisms and timeout protection
- **Persistence**: Complete audit trail of all agent communications
- **Scalability**: Seamless transition from local to distributed deployments

### Design Principles

1. **Separation of Concerns**: Clear layering between protocol routing workflow and application logic
2. **Type Safety**: Pydantic-based payload validation for compile-time error detection
3. **Extensibility**: Easy addition of new agents message types and workflows
4. **Observability**: Comprehensive logging tracing and persistence
5. **Resilience**: Fault-tolerant design with automatic recovery mechanisms

---

## Architecture

### Layered Architecture

The A2A protocol implementation follows a five-layer architecture with clear dependency relationships:

```
┌─────────────────────────────────────────┐
│  Application Layer                      │  ← Highest abstraction
│  - agent_execution_service.py           │    (Business logic)
│  - A2AOrchestrator                      │
└─────────────────────────────────────────┘
              ↓ depends on
┌─────────────────────────────────────────┐
│  Workflow Layer                         │  ← Process orchestration
│  - WorkflowGraph                        │
│  - GraphExecutor                        │
└─────────────────────────────────────────┘
              ↓ depends on
┌─────────────────────────────────────────┐
│  Routing Layer                          │  ← Message dispatch
│  - A2ADispatcher                        │
│  - HybridDispatcher                     │
│  - DistributedDispatcher                │
└─────────────────────────────────────────┘
              ↓ depends on
┌─────────────────────────────────────────┐
│  Protocol Layer                         │  ← Message format
│  - A2AMessage                           │
│  - MessageType                          │
│  - Structured Payloads                  │
└─────────────────────────────────────────┘
              ↓ depends on
┌─────────────────────────────────────────┐
│  Persistence Layer                      │  ← Data storage
│  - A2AMessageStore                      │    (Lowest level)
│  - A2AMessageRecord                     │
└─────────────────────────────────────────┘
```

**Key Principles**:
- **Dependency Direction**: Each layer depends on the layers below it (top-down dependency)
- **Call Flow**: Execution flows from top to bottom (Application calls Workflow calls Routing etc)
- **Service Provision**: Each layer provides services to the layers above it (bottom-up service)
- **Unidirectional**: Lower layers never depend on upper layers (enables independent testing and replacement)

### Component Overview

| Layer | Components | Responsibilities | Abstraction Level |
|-------|-----------|------------------|-------------------|
| **Application** | A2AOrchestrator Services | High-level orchestration and business logic | Highest (Business) |
| **Workflow** | WorkflowGraph GraphExecutor | Define and execute agent interaction flows | High (Process) |
| **Routing** | Dispatcher HybridDispatcher | Route messages between agents | Medium (Communication) |
| **Protocol** | A2AMessage MessageType Payloads | Define standardized message format | Low (Data) |
| **Persistence** | A2AMessageStore Database | Store and query messages | Lowest (Storage) |

---

## Core Components

### 1. Protocol Layer

#### A2AMessage - Standardized Message Envelope

**Location**: `backend/app/core/a2a/models.py`

The `A2AMessage` is the fundamental unit of communication in the A2A protocol.

```python
@dataclass
class A2AMessage:
    type: MessageType              # Message type from enum
    sender_id: str                 # Sender identifier
    recipient_id: str              # Recipient identifier
    content: Any                   # Message payload
    id: UUID                       # Unique message ID
    correlation_id: Optional[UUID] # Links related messages
    metadata: dict                 # Additional context
    created_at: datetime           # Creation timestamp
```

**Key Features**:

- **Correlation Tracking**: The `correlation_id` field links related messages into conversation threads
- **Reply Method**: Automatically creates reply messages while preserving correlation
- **Flexible Content**: Supports both structured payloads and simple strings
- **Metadata**: Carries contextual information like room_id and message history

**Example**:

```python
# Create a message
message = A2AMessage(
    type=MessageType.PROPOSAL,
    sender_id="student",
    recipient_id="teacher",
    content="This is my answer to the question",
    metadata={"room_id": "room-123"}
)

# Create a reply
reply = message.reply(
    type=MessageType.EVALUATION_RESULT,
    sender_id="teacher",
    content={"approved": True, "score": 85}
)
# reply.correlation_id == message.id (automatic)
```

#### MessageType - Message Type Enumeration

```python
class MessageType(str, Enum):
    USER_MESSAGE = "user_message"           # From human users
    PROPOSAL = "proposal"                   # Agent draft content
    EVALUATION_REQUEST = "evaluation_request" # Request for review
    EVALUATION_RESULT = "evaluation_result"   # Review outcome
    BROADCAST = "broadcast"                 # Final message to room
    SYSTEM = "system"                       # System events
```

**Usage Patterns**:

- `USER_MESSAGE`: Human user sends a message to the chat
- `PROPOSAL`: Student agent drafts a response
- `EVALUATION_REQUEST`: Student asks Teacher to review the draft
- `EVALUATION_RESULT`: Teacher approves or rejects the proposal
- `BROADCAST`: Approved message is sent to the chat room
- `SYSTEM`: Join leave or error notifications

#### Structured Payloads

**Location**: `backend/app/core/a2a/payloads.py`

Each message type has a corresponding Pydantic model for type-safe content validation.

**EvaluationRequestPayload**:

```python
class EvaluationRequestPayload(BaseModel):
    proposal: str = Field(..., min_length=1, max_length=50000)
    context: str = Field(default="")
    urgency: Literal["low", "normal", "high"] = Field(default="normal")
```

**EvaluationResultPayload**:

```python
class EvaluationResultPayload(BaseModel):
    approved: bool = Field(...)
    proposal: str = Field(...)
    score: Optional[float] = Field(None, ge=0, le=100)
    feedback: Optional[str] = Field(None)
```

**Benefits**:

- Compile-time type checking
- IDE autocomplete support
- Automatic validation of field constraints
- Self-documenting API
- Extensibility via `extra = "allow"`

---

### 2. Routing Layer

#### A2ADispatcher - Core Message Router

**Location**: `backend/app/core/a2a/dispatcher.py`

The dispatcher is the central hub for routing messages between agents.

**Responsibilities**:

- Register and manage agent handlers
- Route messages based on recipient_id
- Execute middleware for cross-cutting concerns
- Handle special routing cases (broadcast all)

**Key Methods**:

```python
class A2ADispatcher:
    def register(self, agent_id: str, handler: MessageHandler) -> None:
        """Register an agent's message handler"""
        
    async def dispatch(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """Route message to recipient and return response"""
        
    def add_middleware(self, fn: Middleware) -> None:
        """Add middleware for logging auditing etc"""
        
    def set_broadcast_handler(self, handler: BroadcastHandler) -> None:
        """Set handler for broadcast messages"""
```

**Routing Logic**:

```python
async def dispatch(self, msg: A2AMessage) -> Optional[A2AMessage]:
    # 1. Execute all middleware
    for mw in self._middleware:
        await mw(msg)
    
    # 2. Handle special recipients
    if msg.recipient_id == "broadcast":
        await self._broadcast_handler(msg)
        return None
    
    if msg.recipient_id == "all":
        for agent_id, handler in self._handlers.items():
            if agent_id != msg.sender_id:
                await handler(msg)
        return None
    
    # 3. Point-to-point routing
    handler = self._handlers.get(msg.recipient_id)
    if handler:
        return await handler(msg)
    
    return None
```

#### HybridDispatcher - Multi-Mode Dispatcher

**Location**: `backend/app/core/a2a/hybrid.py`

Supports three dispatch modes for different deployment scenarios:

```python
class DispatchMode(str, Enum):
    LOCAL = "local"           # In-memory dispatch
    DISTRIBUTED = "distributed"  # Redis Streams
    AUTO = "auto"             # Auto-detect best mode
```

**Mode Selection**:

- **LOCAL**: Development and testing (fast simple)
- **DISTRIBUTED**: Production with multiple workers (scalable fault-tolerant)
- **AUTO**: Automatically uses DISTRIBUTED if Redis is available otherwise falls back to LOCAL

**Example**:

```python
# Create dispatcher with auto mode
dispatcher = await create_hybrid_dispatcher(mode=DispatchMode.AUTO)

# Register agents
dispatcher.register("teacher", teacher_agent.receive_message)
dispatcher.register("student", student_agent.receive_message)

# Dispatch message
response = await dispatcher.dispatch(message)
```

---

### 3. Workflow Layer

#### WorkflowGraph - Declarative Workflow Definition

**Location**: `backend/app/core/a2a/workflow.py`

Workflows are defined as directed graphs with nodes representing agents or conditions and edges representing transitions.

**Node Types**:

```python
class NodeType(str, Enum):
    AGENT = "agent"         # Agent processing node
    CONDITION = "condition" # Decision node
    ACTION = "action"       # Side-effect node
    START = "start"         # Entry point
    END = "end"            # Exit point
```

**Graph Components**:

```python
@dataclass
class WorkflowNode:
    id: str                          # Unique node identifier
    type: NodeType                   # Node type
    handler: Optional[str] = None    # Handler name
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowEdge:
    from_node: str                   # Source node
    to_node: str                     # Target node
    condition: Optional[str] = None  # Edge condition label
    priority: int = 0                # Priority for multiple edges
```

**Example - Student-Teacher Review Workflow**:

```
┌──────────┐
│  START   │
└────┬─────┘
     │
     ▼
┌──────────────┐
│   Student    │ ← Generate proposal
│  (propose)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Teacher    │ ← Evaluate proposal
│  (evaluate)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ is_approved? │ ← Condition check
└──┬────────┬──┘
   │        │
approved  rejected
   │        │
   ▼        ▼
┌─────┐  ┌─────┐
│Broad│  │ END │
│cast │  └─────┘
└──┬──┘
   │
   ▼
┌─────┐
│ END │
└─────┘
```

**Implementation**:

```python
def create_student_teacher_workflow() -> WorkflowGraph:
    graph = WorkflowGraph("student_teacher_review")
    
    # Define nodes
    graph.add_node(WorkflowNode("start", NodeType.START))
    graph.add_node(WorkflowNode("student_propose", NodeType.AGENT, 
                                handler="student"))
    graph.add_node(WorkflowNode("teacher_eval", NodeType.AGENT, 
                                handler="teacher"))
    graph.add_node(WorkflowNode("is_approved", NodeType.CONDITION, 
                                handler="is_approved"))
    graph.add_node(WorkflowNode("broadcast", NodeType.ACTION, 
                                handler="broadcast"))
    graph.add_node(WorkflowNode("end", NodeType.END))
    
    # Define edges
    graph.add_edge(WorkflowEdge("start", "student_propose"))
    graph.add_edge(WorkflowEdge("student_propose", "teacher_eval"))
    graph.add_edge(WorkflowEdge("teacher_eval", "is_approved"))
    graph.add_edge(WorkflowEdge("is_approved", "broadcast", 
                                condition="approved"))
    graph.add_edge(WorkflowEdge("is_approved", "end", 
                                condition="rejected"))
    graph.add_edge(WorkflowEdge("broadcast", "end"))
    
    return graph
```

#### GraphExecutor - Workflow Execution Engine

**Location**: `backend/app/core/a2a/graph_executor.py`

Executes workflow graphs by traversing nodes and dispatching messages.

**Responsibilities**:

- Traverse the workflow graph from START to END
- Execute agent handlers for AGENT nodes
- Evaluate conditions for CONDITION nodes
- Perform actions for ACTION nodes
- Manage execution context and prevent infinite loops

**Execution Context**:

```python
@dataclass
class WorkflowContext:
    data: Dict[str, Any]             # Arbitrary context data
    history: List[str]               # Visited node IDs
    last_result: Any                 # Last node result
    condition_result: Optional[str]  # Last condition outcome
```

**Execution Flow**:

```python
async def execute(self, initial_data: Dict) -> Optional[A2AMessage]:
    context = WorkflowContext(data=initial_data)
    current_node_id = self.graph.start_node()
    iterations = 0
    
    while current_node_id != "end" and iterations < self.max_iterations:
        node = self.graph.nodes[current_node_id]
        context.history.append(current_node_id)
        
        if node.type == NodeType.AGENT:
            # Execute agent handler
            handler = self._agent_handlers[node.handler]
            message = await handler(context)
            context.last_result = message
            
        elif node.type == NodeType.CONDITION:
            # Evaluate condition
            handler = self._condition_handlers[node.handler]
            result = handler(context.last_result, context)
            context.condition_result = result
            
        elif node.type == NodeType.ACTION:
            # Perform action
            handler = self._action_handlers[node.handler]
            await handler(context.last_result, context)
        
        # Get next node based on condition result
        current_node_id = self.graph.get_next_node(
            current_node_id,
            context.condition_result
        )
        iterations += 1
    
    return context.last_result
```

---

### 4. Application Layer

#### A2AOrchestrator - High-Level Orchestration Service

**Location**: `backend/app/services/a2a_orchestrator.py`

Provides a simplified API for using the A2A protocol in application code.

**Responsibilities**:

- Initialize dispatcher and executor
- Register agents and handlers
- Configure persistence middleware
- Provide high-level workflow execution methods

**Initialization**:

```python
class A2AOrchestrator:
    async def register_agents(
        self,
        teacher: TeacherAgent,
        student: StudentAgent,
        store: Optional[A2AMessageStore] = None
    ) -> None:
        # 1. Initialize HybridDispatcher (AUTO mode)
        self._dispatcher = await create_hybrid_dispatcher(
            mode=DispatchMode.AUTO
        )
        
        # 2. Create workflow graph
        self._graph = create_student_teacher_workflow()
        
        # 3. Initialize GraphExecutor
        self._executor = GraphExecutor(self._graph, self._dispatcher)
        
        # 4. Register agent handlers
        self._executor.register_agent("teacher", 
                                     teacher.handle_workflow_step)
        self._executor.register_agent("student", 
                                     student.handle_workflow_step)
        
        # 5. Register condition and action handlers
        self._executor.register_condition("is_approved", 
                                         self._check_approval_condition)
        self._executor.register_action("broadcast", 
                                      self._broadcast_action)
        
        # 6. Setup persistence middleware
        if store:
            async def persistence_middleware(msg: A2AMessage):
                await store.save(msg)
            self._dispatcher.add_middleware(persistence_middleware)
```

**Workflow Execution**:

```python
async def request_evaluation(
    self,
    proposal: str,
    context: str,
    room_id: str
) -> Optional[A2AMessage]:
    """Execute Student → Teacher evaluation flow"""
    
    initial_data = {
        "room_id": room_id,
        "context": context,
        "proposal_override": proposal
    }
    
    # Execute the full workflow graph
    result = await self._executor.execute(initial_data)
    
    return result
```

#### Agent Integration

Agents must implement the `A2AAgentMixin` interface:

```python
class A2AAgentMixin:
    @abstractmethod
    async def receive_message(
        self, 
        msg: A2AMessage
    ) -> Optional[A2AMessage]:
        """Handle incoming A2A message"""
        pass
```

**Example Implementation**:

```python
class TeacherAgent(AgentCore, A2AAgentMixin):
    async def receive_message(
        self, 
        msg: A2AMessage
    ) -> Optional[A2AMessage]:
        if msg.type == MessageType.EVALUATION_REQUEST:
            # Extract proposal and context
            payload = msg.content
            proposal = payload.proposal if hasattr(payload, 'proposal') else str(payload)
            
            # Evaluate proposal
            approved = await self.evaluate_student_proposal(proposal)
            
            # Return evaluation result
            return msg.reply(
                type=MessageType.EVALUATION_RESULT,
                sender_id="teacher",
                content=EvaluationResultPayload(
                    approved=approved,
                    proposal=proposal,
                    score=85.0 if approved else 40.0
                )
            )
        
        return None
```

---

### 5. Persistence Layer

#### A2AMessageStore - Message Repository

**Location**: `backend/app/core/a2a/store.py`

Provides persistence for A2A messages enabling audit trails debugging and analytics.

**Database Model**:

```python
class A2AMessageRecord(SQLModel, table=True):
    __tablename__ = "a2a_messages"
    
    id: int                          # Primary key
    message_id: str                  # A2A Message UUID
    correlation_id: Optional[str]    # Conversation thread ID
    type: str                        # Message type
    sender_id: str                   # Sender identifier
    recipient_id: str                # Recipient identifier
    content: str                     # JSON-serialized content
    room_id: Optional[str]           # Room identifier
    created_at: datetime             # Creation timestamp
```

**Repository Methods**:

```python
class A2AMessageStore:
    async def save(self, msg: A2AMessage) -> A2AMessageRecord:
        """Persist message to database"""
        
    async def get_by_message_id(
        self, 
        message_id: UUID
    ) -> Optional[A2AMessageRecord]:
        """Retrieve specific message"""
        
    async def get_by_correlation_id(
        self, 
        correlation_id: UUID
    ) -> List[A2AMessageRecord]:
        """Get all messages in a conversation thread"""
        
    async def get_by_room(
        self,
        room_id: str,
        limit: int = 100,
        message_type: Optional[MessageType] = None
    ) -> List[A2AMessageRecord]:
        """Get messages for a specific room"""
```

---

## Message Flow

### Layer Interaction During Execution

Understanding how layers interact is crucial to grasping the A2A protocol. Here is how a typical request flows through all five layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                               │
│ agent_execution_service calls:                                 │
│   orchestrator.request_evaluation(proposal, context, room_id)  │
└────────────────────────┬────────────────────────────────────────┘
                         │ calls
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ WORKFLOW LAYER                                                  │
│ GraphExecutor executes workflow graph:                         │
│   - Traverses nodes (START → Student → Teacher → Condition)   │
│   - Calls agent handlers for each AGENT node                   │
└────────────────────────┬────────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ROUTING LAYER                                                   │
│ Dispatcher routes messages:                                    │
│   - dispatcher.dispatch(message)                               │
│   - Executes middleware (including persistence)                │
│   - Routes to target agent handler                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ creates
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PROTOCOL LAYER                                                  │
│ Standardized message objects:                                  │
│   - A2AMessage(type, sender, recipient, content)               │
│   - Structured payloads (EvaluationRequestPayload etc)         │
└────────────────────────┬────────────────────────────────────────┘
                         │ saved by
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PERSISTENCE LAYER                                               │
│ Database operations:                                            │
│   - store.save(message) → INSERT INTO a2a_messages             │
│   - Audit trail and message history                            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- Each layer only knows about the layer directly below it
- Application Layer does not directly interact with Routing or Protocol layers
- Persistence happens via middleware in the Routing Layer
- Messages flow down through layers and responses flow back up

### Complete Student-Teacher Interaction Flow


```
1. User sends message
   ↓
2. agent_execution_service triggered
   ↓
3. Create A2AOrchestrator
   ↓
4. Register TeacherAgent and StudentAgent
   ↓
5. Execute Student-Teacher workflow:
   
   a. START node
      ↓
   b. Student generates proposal
      - Calls student.handle_workflow_step(context)
      - Returns A2AMessage(type=PROPOSAL, content=proposal_text)
      ↓
   c. Teacher evaluates proposal
      - Calls teacher.handle_workflow_step(context)
      - Receives proposal from context
      - Returns A2AMessage(type=EVALUATION_RESULT, 
                          content={approved, score})
      ↓
   d. Condition check (is_approved)
      - Examines approved field
      - Returns "approved" or "rejected"
      ↓
   e. If approved:
      - Execute broadcast action
      - Save message to database
      - Send to WebSocket/Redis
      ↓
   f. END node
   
6. All messages persisted via middleware to a2a_messages table
   ↓
7. Frontend receives A2A trace events and displays flow
```

### Message Sequence Example

```python
# 1. Student Proposal
proposal_msg = A2AMessage(
    type=MessageType.PROPOSAL,
    sender_id="student",
    recipient_id="teacher",
    content=ProposalPayload(draft="This is my answer"),
    metadata={"room_id": "room-123"}
)

# 2. Evaluation Request (auto-converted)
eval_request = A2AMessage(
    type=MessageType.EVALUATION_REQUEST,
    sender_id="student",
    recipient_id="teacher",
    content=EvaluationRequestPayload(
        proposal="This is my answer",
        context="Previous conversation history"
    ),
    correlation_id=proposal_msg.id
)

# 3. Teacher Evaluation Result
eval_result = A2AMessage(
    type=MessageType.EVALUATION_RESULT,
    sender_id="teacher",
    recipient_id="student",
    content=EvaluationResultPayload(
        approved=True,
        proposal="This is my answer",
        score=85.0,
        feedback="Correct and complete answer"
    ),
    correlation_id=proposal_msg.id
)

# 4. Broadcast Message
broadcast_msg = A2AMessage(
    type=MessageType.BROADCAST,
    sender_id="student",
    recipient_id="broadcast",
    content=BroadcastPayload(content="This is my answer"),
    correlation_id=proposal_msg.id
)
```

---

## Advanced Features

### 1. Resilience Patterns

**Location**: `backend/app/core/a2a/resilience.py`

#### Circuit Breaker

Prevents cascading failures by opening the circuit after a threshold of failures.

```python
class CircuitBreaker:
    states: CLOSED → OPEN → HALF_OPEN → CLOSED
    
    # Configuration
    failure_threshold: int = 5      # Failures before opening
    timeout: float = 60.0           # Seconds before half-open
    success_threshold: int = 2      # Successes to close
```

**Usage**:

```python
breaker = get_circuit_breaker("teacher_agent")

try:
    async with breaker:
        result = await teacher_agent.evaluate(proposal)
except CircuitOpenError:
    # Circuit is open use fallback
    result = fallback_evaluation()
```

#### Retry with Exponential Backoff

```python
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2
)
async def unreliable_operation():
    # Automatically retries with delays: 1s 2s 4s
    pass
```

#### Timeout Protection

```python
@with_timeout(seconds=30)
async def slow_operation():
    # Automatically cancelled after 30 seconds
    pass
```

### 2. Distributed Messaging

**Location**: `backend/app/core/a2a/distributed.py`

Uses **Redis Streams** for distributed agent communication.

**Features**:

- Horizontal scaling with multiple workers
- Message persistence and replay
- At-least-once delivery guarantee
- Consumer groups for load balancing

**Configuration**:

```python
config = DistributedDispatcherConfig(
    redis_url="redis://localhost:6379",
    stream_name="a2a_messages",
    consumer_group="workers",
    consumer_name="worker-1",
    block_ms=1000,
    max_messages=10
)

dispatcher = await create_distributed_dispatcher(config)
```

### 3. External Agent Integration

**Location**: `backend/app/core/a2a/external_adapter.py`

Integrate external agents via HTTP or WebSocket.

**Supported Authentication**:

- Bearer Token
- API Key
- Basic Auth
- Custom Headers

**Example**:

```python
adapter = ExternalAgentAdapter(
    agent_id="external_grader",
    endpoint_url="https://api.example.com/grade",
    auth_type=AuthType.BEARER,
    auth_credentials="your-token-here"
)

# Use like any other agent
response = await adapter.receive_message(message)
```

---

## Integration Guide

### Step 1: Implement Agent Interface

```python
from app.core.a2a import A2AAgentMixin A2AMessage MessageType

class MyCustomAgent(AgentCore, A2AAgentMixin):
    async def receive_message(
        self, 
        msg: A2AMessage
    ) -> Optional[A2AMessage]:
        if msg.type == MessageType.EVALUATION_REQUEST:
            # Handle evaluation request
            result = await self.process_request(msg.content)
            return msg.reply(
                type=MessageType.EVALUATION_RESULT,
                sender_id="my_agent",
                content=result
            )
        return None
    
    async def handle_workflow_step(
        self, 
        context: WorkflowContext
    ) -> A2AMessage:
        # Extract data from context
        data = context.data
        
        # Perform agent logic
        result = await self.perform_task(data)
        
        # Return message
        return A2AMessage(
            type=MessageType.PROPOSAL,
            sender_id="my_agent",
            recipient_id="teacher",
            content=result
        )
```

### Step 2: Create Custom Workflow

```python
from app.core.a2a import WorkflowGraph WorkflowNode WorkflowEdge NodeType

def create_custom_workflow() -> WorkflowGraph:
    graph = WorkflowGraph("my_custom_workflow")
    
    # Add nodes
    graph.add_node(WorkflowNode("start", NodeType.START))
    graph.add_node(WorkflowNode("agent1", NodeType.AGENT, handler="agent1"))
    graph.add_node(WorkflowNode("agent2", NodeType.AGENT, handler="agent2"))
    graph.add_node(WorkflowNode("check", NodeType.CONDITION, handler="my_condition"))
    graph.add_node(WorkflowNode("end", NodeType.END))
    
    # Add edges
    graph.add_edge(WorkflowEdge("start", "agent1"))
    graph.add_edge(WorkflowEdge("agent1", "agent2"))
    graph.add_edge(WorkflowEdge("agent2", "check"))
    graph.add_edge(WorkflowEdge("check", "end", condition="success"))
    graph.add_edge(WorkflowEdge("check", "agent1", condition="retry"))
    
    return graph
```

### Step 3: Register and Execute

```python
from app.core.a2a import GraphExecutor create_hybrid_dispatcher DispatchMode

# Initialize dispatcher
dispatcher = await create_hybrid_dispatcher(mode=DispatchMode.AUTO)

# Create workflow and executor
graph = create_custom_workflow()
executor = GraphExecutor(graph, dispatcher)

# Register agents
executor.register_agent("agent1", agent1.handle_workflow_step)
executor.register_agent("agent2", agent2.handle_workflow_step)

# Register condition handler
def my_condition(message, context):
    return "success" if message.content.get("valid") else "retry"

executor.register_condition("my_condition", my_condition)

# Execute workflow
result = await executor.execute({"initial_data": "value"})
```

---

## API Reference

### Core Classes

#### A2AMessage

```python
@dataclass
class A2AMessage:
    type: MessageType
    sender_id: str
    recipient_id: str
    content: Any
    id: UUID = field(default_factory=uuid4)
    correlation_id: Optional[UUID] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def reply(
        self,
        type: MessageType,
        content: Any,
        sender_id: str,
        recipient_id: Optional[str] = None
    ) -> A2AMessage
```

#### A2ADispatcher

```python
class A2ADispatcher:
    def register(self, agent_id: str, handler: MessageHandler) -> None
    def unregister(self, agent_id: str) -> None
    def add_middleware(self, fn: Middleware) -> None
    def set_broadcast_handler(self, handler: BroadcastHandler) -> None
    async def dispatch(self, msg: A2AMessage) -> Optional[A2AMessage]
    
    @property
    def registered_agents(self) -> List[str]
```

#### WorkflowGraph

```python
class WorkflowGraph:
    def __init__(self, name: str = "default")
    def add_node(self, node: WorkflowNode) -> WorkflowGraph
    def add_edge(self, edge: WorkflowEdge) -> WorkflowGraph
    def set_start(self, node_id: str) -> WorkflowGraph
    def start_node(self) -> str
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]
    def get_next_node(self, current_id: str, condition: Optional[str] = None) -> Optional[str]
    def validate(self) -> List[str]
    def to_dict(self) -> Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowGraph
```

#### GraphExecutor

```python
class GraphExecutor:
    def __init__(
        self,
        graph: WorkflowGraph,
        dispatcher: Optional[A2ADispatcher] = None,
        max_iterations: int = 50
    )
    
    def register_agent(self, agent_id: str, handler: AgentHandler) -> None
    def register_condition(self, name: str, handler: ConditionHandler) -> None
    def register_action(self, name: str, handler: ActionHandler) -> None
    async def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> Optional[A2AMessage]
```

#### A2AOrchestrator

```python
class A2AOrchestrator:
    async def initialize(self) -> None
    async def register_agents(
        self,
        teacher: TeacherAgent,
        student: StudentAgent,
        store: Optional[A2AMessageStore] = None
    ) -> None
    async def request_evaluation(
        self,
        proposal: str,
        context: str,
        room_id: str,
        message_history: Optional[list] = None
    ) -> Optional[A2AMessage]
    
    @property
    def dispatcher(self) -> HybridDispatcher
```

### Payload Models

#### EvaluationRequestPayload

```python
class EvaluationRequestPayload(BaseModel):
    proposal: str
    context: str = ""
    urgency: Literal["low", "normal", "high"] = "normal"
```

#### EvaluationResultPayload

```python
class EvaluationResultPayload(BaseModel):
    approved: bool
    proposal: str
    score: Optional[float] = None
    feedback: Optional[str] = None
```

### Utility Functions

```python
# Payload validation
def validate_payload(message_type: MessageType, content: Any) -> A2APayload

# Factory functions
def create_evaluation_request(
    proposal: str,
    context: str = "",
    urgency: Literal["low", "normal", "high"] = "normal"
) -> EvaluationRequestPayload

def create_evaluation_result(
    approved: bool,
    proposal: str,
    score: Optional[float] = None,
    feedback: Optional[str] = None
) -> EvaluationResultPayload

# Workflow templates
def create_student_teacher_workflow() -> WorkflowGraph
def create_direct_broadcast_workflow() -> WorkflowGraph

# Dispatcher creation
async def create_hybrid_dispatcher(mode: DispatchMode = DispatchMode.AUTO) -> HybridDispatcher
async def create_distributed_dispatcher(config: DistributedDispatcherConfig) -> DistributedDispatcher

# Resilience utilities
def get_circuit_breaker(name: str) -> CircuitBreaker
def reset_all_breakers() -> None
async def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0)
async def with_resilience(operation, circuit_name: str, timeout: float = 30.0)
async def with_timeout(seconds: float)
```

---

## Examples

### Example 1: Simple Point-to-Point Communication

```python
from app.core.a2a import A2ADispatcher A2AMessage MessageType

# Create dispatcher
dispatcher = A2ADispatcher()

# Define agent handlers
async def teacher_handler(msg: A2AMessage) -> Optional[A2AMessage]:
    if msg.type == MessageType.EVALUATION_REQUEST:
        return msg.reply(
            type=MessageType.EVALUATION_RESULT,
            sender_id="teacher",
            content={"approved": True}
        )
    return None

async def student_handler(msg: A2AMessage) -> Optional[A2AMessage]:
    if msg.type == MessageType.EVALUATION_RESULT:
        print(f"Received evaluation: {msg.content}")
    return None

# Register agents
dispatcher.register("teacher", teacher_handler)
dispatcher.register("student", student_handler)

# Send message
request = A2AMessage(
    type=MessageType.EVALUATION_REQUEST,
    sender_id="student",
    recipient_id="teacher",
    content={"proposal": "My answer"}
)

response = await dispatcher.dispatch(request)
print(f"Response: {response.content}")
```

### Example 2: Workflow with Condition

```python
from app.core.a2a import WorkflowGraph GraphExecutor WorkflowNode WorkflowEdge NodeType

# Create workflow
graph = WorkflowGraph("approval_flow")
graph.add_node(WorkflowNode("start", NodeType.START))
graph.add_node(WorkflowNode("draft", NodeType.AGENT, handler="drafter"))
graph.add_node(WorkflowNode("review", NodeType.AGENT, handler="reviewer"))
graph.add_node(WorkflowNode("check", NodeType.CONDITION, handler="is_approved"))
graph.add_node(WorkflowNode("publish", NodeType.ACTION, handler="publish"))
graph.add_node(WorkflowNode("end", NodeType.END))

graph.add_edge(WorkflowEdge("start", "draft"))
graph.add_edge(WorkflowEdge("draft", "review"))
graph.add_edge(WorkflowEdge("review", "check"))
graph.add_edge(WorkflowEdge("check", "publish", condition="approved"))
graph.add_edge(WorkflowEdge("check", "end", condition="rejected"))
graph.add_edge(WorkflowEdge("publish", "end"))

# Create executor
executor = GraphExecutor(graph)

# Register handlers
async def drafter(context):
    return A2AMessage(
        type=MessageType.PROPOSAL,
        sender_id="drafter",
        recipient_id="reviewer",
        content="Draft content"
    )

async def reviewer(context):
    return A2AMessage(
        type=MessageType.EVALUATION_RESULT,
        sender_id="reviewer",
        recipient_id="drafter",
        content={"approved": True}
    )

def is_approved(message, context):
    return "approved" if message.content.get("approved") else "rejected"

async def publish(message, context):
    print(f"Publishing: {message.content}")

executor.register_agent("drafter", drafter)
executor.register_agent("reviewer", reviewer)
executor.register_condition("is_approved", is_approved)
executor.register_action("publish", publish)

# Execute
result = await executor.execute()
```

### Example 3: Persistence and Audit Trail

```python
from app.core.a2a import A2AMessageStore A2ADispatcher

# Create store
store = A2AMessageStore(session)

# Create dispatcher with persistence middleware
dispatcher = A2ADispatcher()

async def persistence_middleware(msg: A2AMessage):
    await store.save(msg)
    print(f"Saved message {msg.id}")

dispatcher.add_middleware(persistence_middleware)

# All dispatched messages are automatically persisted
await dispatcher.dispatch(message)

# Query messages
messages = await store.get_by_room("room-123", limit=50)
thread = await store.get_by_correlation_id(correlation_id)
```

### Example 4: Distributed Deployment

```python
from app.core.a2a import create_distributed_dispatcher DistributedDispatcherConfig

# Configure distributed dispatcher
config = DistributedDispatcherConfig(
    redis_url="redis://localhost:6379",
    stream_name="a2a_messages",
    consumer_group="workers",
    consumer_name="worker-1"
)

# Create dispatcher
dispatcher = await create_distributed_dispatcher(config)

# Register agents (same as local)
dispatcher.register("teacher", teacher_handler)
dispatcher.register("student", student_handler)

# Messages are now distributed via Redis Streams
await dispatcher.dispatch(message)
```

---

## File Structure

```
backend/app/core/a2a/
├── __init__.py              # Module exports
├── models.py                # A2AMessage MessageType
├── base.py                  # AgentId A2AAgentMixin
├── dispatcher.py            # A2ADispatcher (basic routing)
├── payloads.py              # Structured payload definitions
├── store.py                 # A2AMessageStore (persistence)
├── workflow.py              # WorkflowGraph (workflow definition)
├── graph_executor.py        # GraphExecutor (workflow execution)
├── resilience.py            # Circuit Breaker Retry Timeout
├── distributed.py           # DistributedDispatcher (Redis Streams)
├── hybrid.py                # HybridDispatcher (multi-mode)
└── external_adapter.py      # ExternalAgentAdapter (external integration)

backend/app/services/
└── a2a_orchestrator.py      # A2AOrchestrator (high-level orchestration)

backend/app/services/execution/
└── agent_execution_service.py  # Business logic using A2A
```

---

## Best Practices

### 1. Message Design

- Use structured payloads for type safety
- Include correlation_id for conversation tracking
- Add relevant metadata (room_id user_id etc)
- Keep content focused and single-purpose

### 2. Workflow Design

- Keep workflows simple and linear when possible
- Use conditions for branching logic
- Avoid cycles unless necessary (use max_iterations protection)
- Validate workflows before deployment

### 3. Error Handling

- Use circuit breakers for external dependencies
- Implement retry logic for transient failures
- Set appropriate timeouts for all operations
- Log errors with context for debugging

### 4. Performance

- Use LOCAL mode for development
- Use DISTRIBUTED mode for production
- Configure appropriate pool sizes for Redis
- Monitor message queue lengths

### 5. Testing

- Test each agent handler independently
- Test workflows with mock agents
- Test condition handlers with edge cases
- Use integration tests for end-to-end flows

---

## Troubleshooting

### Common Issues

**Issue**: Messages not being routed

**Solution**: Check that agents are registered with correct IDs and that recipient_id matches registered agent_id

**Issue**: Workflow stuck in infinite loop

**Solution**: Check for cycles in workflow graph and ensure max_iterations is set appropriately

**Issue**: Circuit breaker constantly open

**Solution**: Check failure_threshold and timeout settings and investigate underlying service issues

**Issue**: Distributed mode not working

**Solution**: Verify Redis connection and ensure consumer group is created and check Redis Streams configuration

---

## Performance Considerations

### Scalability

- **Local Mode**: Single process limited by memory and CPU
- **Distributed Mode**: Horizontal scaling with multiple workers
- **Message Throughput**: Depends on Redis performance and network latency
- **Workflow Complexity**: Linear workflows are faster than complex branching

### Optimization Tips

1. Use connection pooling for database and Redis
2. Batch message persistence when possible
3. Use async operations throughout
4. Monitor and tune circuit breaker thresholds
5. Consider message size limits for large payloads

---

## Security Considerations

### Authentication

- External agents require authentication (Bearer API Key Basic)
- Internal agents trusted by default
- Consider adding agent authentication for production

### Authorization

- Implement agent-level permissions
- Validate message sender_id
- Restrict sensitive operations to authorized agents

### Data Protection

- Encrypt sensitive data in message content
- Use HTTPS for external agent communication
- Implement audit logging for compliance

---

## Future Enhancements

### Planned Features

- **Message Prioritization**: Priority queues for urgent messages
- **Dead Letter Queue**: Handle failed messages gracefully
- **Message Replay**: Replay historical messages for debugging
- **Workflow Versioning**: Support multiple workflow versions
- **Agent Discovery**: Dynamic agent registration and discovery
- **Metrics and Monitoring**: Built-in metrics collection
- **GraphQL API**: Alternative API for workflow management

---

## Contributing

### Adding New Message Types

1. Add enum value to `MessageType`
2. Create Pydantic payload model in `payloads.py`
3. Register in `PAYLOAD_SCHEMA_REGISTRY`
4. Update documentation

### Adding New Agents

1. Implement `A2AAgentMixin` interface
2. Implement `handle_workflow_step` method
3. Register with dispatcher
4. Add to workflow graph if needed

### Adding New Workflows

1. Define workflow graph structure
2. Create factory function
3. Add tests for workflow validation
4. Document workflow purpose and usage

---

## License

This A2A Protocol implementation is part of CoAgent-Studio and follows the same license terms.

---

## References

- [A2A Protocol Specification](https://a2a-protocol.org)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [Redis Streams](https://redis.io/docs/data-types/streams)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)

---

## Quick Reference Summary

### Architecture at a Glance

The A2A protocol uses a **five-layer architecture** where each layer depends on the one below it:

1. **Application Layer** (Highest) - Business logic and orchestration
2. **Workflow Layer** - Process definition and execution
3. **Routing Layer** - Message dispatch and delivery
4. **Protocol Layer** - Standardized message format
5. **Persistence Layer** (Lowest) - Data storage and retrieval

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `A2AMessage` | Standardized message envelope | `core/a2a/models.py` |
| `A2ADispatcher` | Routes messages between agents | `core/a2a/dispatcher.py` |
| `WorkflowGraph` | Defines agent interaction flows | `core/a2a/workflow.py` |
| `GraphExecutor` | Executes workflow graphs | `core/a2a/graph_executor.py` |
| `A2AOrchestrator` | High-level API for workflows | `services/a2a_orchestrator.py` |
| `A2AMessageStore` | Persists messages to database | `core/a2a/store.py` |

### Message Types

- `USER_MESSAGE` - From human users
- `PROPOSAL` - Agent draft content
- `EVALUATION_REQUEST` - Request for review
- `EVALUATION_RESULT` - Review outcome
- `BROADCAST` - Final message to room
- `SYSTEM` - System events

### Dispatch Modes

- `LOCAL` - In-memory (development)
- `DISTRIBUTED` - Redis Streams (production)
- `AUTO` - Automatically selects best mode

### Typical Usage Pattern

```python
# 1. Create orchestrator
orchestrator = A2AOrchestrator()

# 2. Register agents
await orchestrator.register_agents(teacher, student, store)

# 3. Execute workflow
result = await orchestrator.request_evaluation(proposal, context, room_id)

# 4. Check result
if orchestrator.is_approved(result):
    # Handle approved case
    pass
```

---

## Support

For questions issues or contributions please refer to the main CoAgent-Studio repository.

