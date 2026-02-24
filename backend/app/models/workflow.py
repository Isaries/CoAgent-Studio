"""
Workflow Models for Dynamic Multi-Agent Graph Engine.

Stores the visual workflow graph topology (nodes & edges) created by the
frontend canvas, and tracks each execution run for debugging and replay.

NOTE: Workflows are now **decoupled from Rooms**.  A Workflow is a
first-class, top-level resource that can be attached to any surface
(Room, API endpoint, Webhook, batch job, etc.) via its UUID.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkflowStatus(str, Enum):
    """Status of a single workflow execution run."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"          # Waiting for human-in-the-loop / timer
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowNodeType(str, Enum):
    """Canonical node types supported by the graph engine."""
    AGENT = "agent"            # LLM-powered agent node
    ROUTER = "router"          # Conditional branching node
    ACTION = "action"          # Side-effect node (broadcast, tool call, etc.)
    START = "start"            # Entry point
    END = "end"                # Terminal node
    MERGE = "merge"            # Wait-for-all parallel join
    TOOL = "tool"              # External tool invocation


class WorkflowEdgeType(str, Enum):
    """Semantic relationship type carried by an edge."""
    EVALUATE = "evaluate"      # Target must approve source's output
    FORWARD = "forward"        # Pass data downstream (default)
    SUMMARIZE = "summarize"    # Target summarises multiple inputs
    CRITIQUE = "critique"      # Target provides feedback (non-blocking)
    TRIGGER = "trigger"        # Source's completion triggers target


# ---------------------------------------------------------------------------
# Workflow – the blueprint / topology (decoupled from Room)
# ---------------------------------------------------------------------------

class WorkflowBase(SQLModel):
    """Shared fields for Workflow create / read schemas."""
    name: str = Field(default="Default Workflow")
    is_active: bool = Field(default=True)


class Workflow(WorkflowBase, table=True):
    """
    Stores a visual graph topology.

    A Workflow is a **top-level resource** – it does NOT belong to any Room.
    Rooms (or other surfaces) can reference a Workflow by setting their
    ``attached_workflow_id`` field.

    The ``graph_data`` JSONB column holds the full node/edge structure
    exported by the frontend canvas (Vue Flow format).

    graph_data schema:
    {
      "nodes": [
        {"id": "uuid-1", "type": "agent", "config": {"agent_id": "..."}, "position": {"x": 0, "y": 0}},
        {"id": "uuid-2", "type": "router", "config": {"expression": "..."}},
        ...
      ],
      "edges": [
        {"id": "edge-1", "source": "uuid-1", "target": "uuid-2", "type": "evaluate"},
        ...
      ]
    }
    """
    __tablename__ = "workflow"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    graph_data: Dict[str, Any] = Field(
        default_factory=lambda: {"nodes": [], "edges": []},
        sa_column=Column(JSONB, nullable=False),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")


class WorkflowCreate(WorkflowBase):
    graph_data: Dict[str, Any] = Field(default_factory=lambda: {"nodes": [], "edges": []})


class WorkflowRead(WorkflowBase):
    id: UUID
    graph_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowUpdate(SQLModel):
    name: Optional[str] = None
    graph_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# WorkflowRun – execution instance (decoupled from Room)
# ---------------------------------------------------------------------------

class WorkflowRun(SQLModel, table=True):
    """
    Tracks a single execution of a workflow graph.

    Each time a trigger event fires (user message, timer, webhook, etc.),
    a new ``WorkflowRun`` is created.  The ``state_snapshot`` stores the
    LangGraph checkpoint so the run can be paused and resumed.

    ``session_id`` is a generic string identifier that ties the run back
    to its source context (e.g. a Room ID, an API request ID, a thread ID).
    """
    __tablename__ = "workflow_run"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)

    # Generic context identifier (replaces old room_id binding)
    session_id: str = Field(index=True)

    # The full trigger payload that initiated this run
    trigger_payload: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB)
    )

    status: str = Field(default=WorkflowStatus.PENDING.value)

    # LangGraph checkpoint – enables pause / resume / replay
    state_snapshot: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Ordered log of node executions for the trace UI
    execution_log: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, sa_column=Column(JSONB)
    )

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Error details if status == FAILED
    error_message: Optional[str] = None


class WorkflowRunRead(SQLModel):
    id: UUID
    workflow_id: UUID
    session_id: str
    status: str
    execution_log: Optional[List[Dict[str, Any]]] = []
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Backward-compatible aliases (ease migration for existing code)
# ---------------------------------------------------------------------------
RoomWorkflow = Workflow
RoomWorkflowBase = WorkflowBase
RoomWorkflowCreate = WorkflowCreate
RoomWorkflowRead = WorkflowRead
RoomWorkflowUpdate = WorkflowUpdate
