"""
Declarative Workflow Graph DSL (P1).

A lightweight, pure-Python graph abstraction for defining multi-agent
workflows without LangGraph boilerplate.  Useful for tests, small
utility workflows, and prototyping before promoting to the full compiler.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.core.a2a.models import A2AMessage, MessageType


class NodeType(str, Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    CONDITION = "condition"
    ROUTER = "router"
    ACTION = "action"
    MERGE = "merge"
    TOOL = "tool"


@dataclass
class WorkflowNode:
    name: str
    type: NodeType
    handler: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEdge:
    source: str
    target: str
    condition: Optional[str] = None


@dataclass
class WorkflowContext:
    """Context passed to agent handlers during graph execution."""
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[A2AMessage] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


class WorkflowGraph:
    """
    Declarative, builder-style workflow graph.

    Usage::

        graph = (
            WorkflowGraph("my_flow")
            .add_node(WorkflowNode("start", NodeType.START))
            .add_node(WorkflowNode("agent", NodeType.AGENT, handler="my_agent"))
            .add_node(WorkflowNode("end", NodeType.END))
            .add_edge(WorkflowEdge("start", "agent"))
            .add_edge(WorkflowEdge("agent", "end"))
        )
    """

    def __init__(self, name: str = "workflow") -> None:
        self.name = name
        self.nodes: List[WorkflowNode] = []
        self.edges: List[WorkflowEdge] = []

    # ------------------------------------------------------------------ #
    # Builder API                                                          #
    # ------------------------------------------------------------------ #

    def add_node(self, node: WorkflowNode) -> "WorkflowGraph":
        self.nodes.append(node)
        return self

    def add_edge(self, edge: WorkflowEdge) -> "WorkflowGraph":
        self.edges.append(edge)
        return self

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def start_node(self) -> Optional[str]:
        for n in self.nodes:
            if n.type == NodeType.START:
                return n.name
        return None

    def _node_map(self) -> Dict[str, WorkflowNode]:
        return {n.name: n for n in self.nodes}

    # ------------------------------------------------------------------ #
    # Validation                                                           #
    # ------------------------------------------------------------------ #

    def validate(self) -> List[str]:
        errors: List[str] = []
        node_names = {n.name for n in self.nodes}

        # Must have exactly one start node
        starts = [n for n in self.nodes if n.type == NodeType.START]
        if len(starts) == 0:
            errors.append("No start node defined")
        elif len(starts) > 1:
            errors.append("Multiple start nodes defined")

        # Must have at least one end node
        ends = [n for n in self.nodes if n.type == NodeType.END]
        if len(ends) == 0:
            errors.append("No END node defined")

        # All edge sources/targets must reference defined nodes
        for edge in self.edges:
            if edge.source not in node_names:
                errors.append(f"Edge source '{edge.source}' references undefined node")
            if edge.target not in node_names:
                errors.append(f"Edge target '{edge.target}' references undefined node")

        return errors

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    def get_next_node(self, from_node: str, condition: Optional[str] = None) -> Optional[str]:
        """Return the name of the next node to visit from *from_node*."""
        candidates = [e for e in self.edges if e.source == from_node]
        if not candidates:
            return None

        if condition is not None:
            # Find conditional edge first
            for edge in candidates:
                if edge.condition == condition:
                    return edge.target

        # Fall back to unconditional edge
        for edge in candidates:
            if edge.condition is None:
                return edge.target

        # If all edges have conditions but none matched, return None
        return None

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [
                {"name": n.name, "type": n.type, "handler": n.handler, "config": n.config}
                for n in self.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "condition": e.condition}
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        g = cls(name=data.get("name", "workflow"))
        for nd in data.get("nodes", []):
            g.add_node(WorkflowNode(
                name=nd["name"],
                type=NodeType(nd["type"]),
                handler=nd.get("handler"),
                config=nd.get("config", {}),
            ))
        for ed in data.get("edges", []):
            g.add_edge(WorkflowEdge(
                source=ed["source"],
                target=ed["target"],
                condition=ed.get("condition"),
            ))
        return g


# --------------------------------------------------------------------------- #
# Graph Executor                                                               #
# --------------------------------------------------------------------------- #

class GraphExecutor:
    """Execute a WorkflowGraph by walking its nodes and calling handlers."""

    # Built-in condition evaluators
    _BUILTIN_CONDITIONS: Dict[str, Callable] = {}

    def __init__(self, graph: WorkflowGraph, max_steps: int = 50) -> None:
        self.graph = graph
        self.max_steps = max_steps
        self._agents: Dict[str, Callable] = {}

    def register_agent(self, name: str, handler: Callable) -> None:
        self._agents[name] = handler

    async def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> Optional[A2AMessage]:
        ctx = WorkflowContext(data=initial_data or {})
        node_map = self.graph._node_map()
        current = self.graph.start_node
        last_result: Optional[A2AMessage] = None
        steps = 0

        while current is not None and steps < self.max_steps:
            steps += 1
            node = node_map.get(current)
            if node is None:
                break

            if node.type == NodeType.END:
                break

            if node.type in (NodeType.AGENT, NodeType.ACTION, NodeType.TOOL):
                handler = self._agents.get(node.handler or "")
                if handler:
                    last_result = await handler(ctx)
                    if last_result:
                        ctx.history.append(last_result)
                current = self.graph.get_next_node(current)

            elif node.type == NodeType.CONDITION:
                # Evaluate condition handler to determine branch
                condition_key = None
                handler = self._agents.get(node.handler or "")
                if handler:
                    condition_key = await handler(ctx)
                elif node.handler == "is_approved":
                    # Built-in: check last result for approval
                    if last_result and isinstance(last_result.content, dict):
                        condition_key = "approved" if last_result.content.get("approved") else "rejected"
                    else:
                        condition_key = "approved"
                current = self.graph.get_next_node(current, condition_key)

            elif node.type in (NodeType.START, NodeType.MERGE, NodeType.ROUTER):
                current = self.graph.get_next_node(current)

            else:
                current = self.graph.get_next_node(current)

        return last_result


# --------------------------------------------------------------------------- #
# Predefined workflows                                                         #
# --------------------------------------------------------------------------- #

def create_student_teacher_workflow() -> WorkflowGraph:
    """Return a canonical student-teacher evaluation workflow."""
    return (
        WorkflowGraph("student_teacher")
        .add_node(WorkflowNode("start", NodeType.START))
        .add_node(WorkflowNode("student", NodeType.AGENT, handler="student_agent"))
        .add_node(WorkflowNode("teacher", NodeType.AGENT, handler="teacher_agent"))
        .add_node(WorkflowNode("evaluate", NodeType.CONDITION, handler="is_approved"))
        .add_node(WorkflowNode("end_approved", NodeType.END, config={"status": "approved"}))
        .add_node(WorkflowNode("end_revision", NodeType.END, config={"status": "needs_revision"}))
        .add_edge(WorkflowEdge("start", "student"))
        .add_edge(WorkflowEdge("student", "teacher"))
        .add_edge(WorkflowEdge("teacher", "evaluate"))
        .add_edge(WorkflowEdge("evaluate", "end_approved", condition="approved"))
        .add_edge(WorkflowEdge("evaluate", "end_revision", condition="rejected"))
    )
