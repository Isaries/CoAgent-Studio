"""
Workflow Models for Dynamic Multi-Agent Graph Engine.

Stores the visual workflow graph topology (nodes & edges) created by the
frontend canvas, and tracks each execution run for debugging and replay.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


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
# RoomWorkflow – the blueprint / topology
# ---------------------------------------------------------------------------

class RoomWorkflowBase(SQLModel):
    """Shared fields for RoomWorkflow create / read schemas."""
    name: str = Field(default="Default Workflow")
    is_active: bool = Field(default=True)


class RoomWorkflow(RoomWorkflowBase, table=True):
    """
    Stores the visual graph topology for a room.

    One room has at most one active workflow.  The ``graph_data`` JSONB
    column holds the full node/edge structure exported by the frontend
    canvas (Vue Flow / React Flow format).

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
    __tablename__ = "room_workflow"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", unique=True, index=True)

    graph_data: Dict[str, Any] = Field(
        default_factory=lambda: {"nodes": [], "edges": []},
        sa_column=Column(JSONB, nullable=False),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")


class RoomWorkflowCreate(RoomWorkflowBase):
    room_id: UUID
    graph_data: Dict[str, Any] = Field(default_factory=lambda: {"nodes": [], "edges": []})


class RoomWorkflowRead(RoomWorkflowBase):
    id: UUID
    room_id: UUID
    graph_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RoomWorkflowUpdate(SQLModel):
    name: Optional[str] = None
    graph_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# WorkflowRun – execution instance
# ---------------------------------------------------------------------------

class WorkflowRun(SQLModel, table=True):
    """
    Tracks a single execution of a workflow graph.

    Each time a user message (or timer event) triggers the graph engine,
    a new ``WorkflowRun`` is created.  The ``state_snapshot`` stores the
    LangGraph checkpoint so the run can be paused and resumed.
    """
    __tablename__ = "workflow_run"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="room.id", index=True)
    workflow_id: UUID = Field(foreign_key="room_workflow.id", index=True)
    trigger_message_id: Optional[UUID] = Field(
        default=None, foreign_key="message.id"
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
    room_id: UUID
    workflow_id: UUID
    status: str
    execution_log: Optional[List[Dict[str, Any]]] = []
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
