"""
A2A Workflow Graph Definition.

Provides a declarative way to define agent interaction workflows
as directed graphs with nodes (agents/conditions) and edges (transitions).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class NodeType(str, Enum):
    """Type of workflow node."""
    AGENT = "agent"          # Agent processing node
    CONDITION = "condition"  # Conditional branching node
    ACTION = "action"        # Custom action node
    START = "start"          # Entry point
    END = "end"              # Terminal node


@dataclass
class WorkflowNode:
    """
    A node in the workflow graph.
    
    Attributes:
        id: Unique identifier for this node
        type: The type of node (agent, condition, etc.)
        handler: Agent ID or condition function name
        config: Additional configuration for the node
    """
    id: str
    type: NodeType
    handler: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class WorkflowEdge:
    """
    An edge connecting two nodes in the workflow.
    
    Attributes:
        from_node: Source node ID
        to_node: Target node ID
        condition: Optional condition label (e.g., "approved", "rejected")
        priority: Used for ordering when multiple edges match
    """
    from_node: str
    to_node: str
    condition: Optional[str] = None
    priority: int = 0


@dataclass
class WorkflowContext:
    """
    Execution context passed through the workflow.
    
    Attributes:
        data: Arbitrary data dictionary
        history: List of visited node IDs
        last_result: Result from the last executed node
        condition_result: Result from the last condition evaluation
    """
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    last_result: Any = None
    condition_result: Optional[str] = None
    
    def clone(self) -> "WorkflowContext":
        """Create a shallow copy of the context."""
        return WorkflowContext(
            data=self.data.copy(),
            history=self.history.copy(),
            last_result=self.last_result,
            condition_result=self.condition_result,
        )


class WorkflowGraph:
    """
    Declarative workflow definition using a directed graph.
    
    Example - Student-Teacher Review Flow:
    
        ┌──────────┐
        │  START   │
        └────┬─────┘
             ▼
        ┌──────────┐
        │ STUDENT  │ (generate proposal)
        └────┬─────┘
             ▼
        ┌──────────┐
        │ TEACHER  │ (evaluate)
        └────┬─────┘
             ▼
        ┌──────────┐
        │CONDITION │ (is_approved?)
        └──┬───┬───┘
     approved │ │ rejected
              ▼   ▼
        ┌─────────┐ ┌─────────┐
        │BROADCAST│ │  END    │
        └────┬────┘ └─────────┘
             ▼
        ┌─────────┐
        │   END   │
        └─────────┘
    
    Usage:
        graph = (
            WorkflowGraph("student_teacher_review")
            .add_node(WorkflowNode("start", NodeType.START))
            .add_node(WorkflowNode("student", NodeType.AGENT, handler="student"))
            .add_node(WorkflowNode("teacher", NodeType.AGENT, handler="teacher"))
            .add_node(WorkflowNode("check", NodeType.CONDITION, handler="is_approved"))
            .add_node(WorkflowNode("broadcast", NodeType.ACTION, handler="broadcast"))
            .add_node(WorkflowNode("end", NodeType.END))
            .add_edge(WorkflowEdge("start", "student"))
            .add_edge(WorkflowEdge("student", "teacher"))
            .add_edge(WorkflowEdge("teacher", "check"))
            .add_edge(WorkflowEdge("check", "broadcast", condition="approved"))
            .add_edge(WorkflowEdge("check", "end", condition="rejected"))
            .add_edge(WorkflowEdge("broadcast", "end"))
        )
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self._start_node: Optional[str] = None
    
    def add_node(self, node: WorkflowNode) -> "WorkflowGraph":
        """Add a node to the graph. Returns self for chaining."""
        self.nodes[node.id] = node
        
        # Auto-detect start node
        if node.type == NodeType.START:
            self._start_node = node.id
        
        return self
    
    def add_edge(self, edge: WorkflowEdge) -> "WorkflowGraph":
        """Add an edge to the graph. Returns self for chaining."""
        self.edges.append(edge)
        return self
    
    def set_start(self, node_id: str) -> "WorkflowGraph":
        """Explicitly set the start node. Returns self for chaining."""
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not found in graph")
        self._start_node = node_id
        return self
    
    @property
    def start_node(self) -> Optional[str]:
        """Get the start node ID."""
        return self._start_node
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges originating from a node, sorted by priority."""
        edges = [e for e in self.edges if e.from_node == node_id]
        return sorted(edges, key=lambda e: e.priority, reverse=True)
    
    def get_next_node(self, current_id: str, condition: Optional[str] = None) -> Optional[str]:
        """
        Find the next node based on current node and optional condition.
        
        Args:
            current_id: Current node ID
            condition: Optional condition to match (e.g., "approved")
            
        Returns:
            Next node ID, or None if no matching edge found
        """
        edges = self.get_outgoing_edges(current_id)
        
        for edge in edges:
            # Exact condition match
            if edge.condition == condition:
                return edge.to_node
            # Unconditional edge (fallback)
            if edge.condition is None and condition is None:
                return edge.to_node
        
        # Fallback: first unconditional edge
        for edge in edges:
            if edge.condition is None:
                return edge.to_node
        
        return None
    
    def validate(self) -> List[str]:
        """
        Validate the graph for common errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self._start_node:
            errors.append("No start node defined")
        
        # Check all edge references are valid
        for edge in self.edges:
            if edge.from_node not in self.nodes:
                errors.append(f"Edge references unknown node: {edge.from_node}")
            if edge.to_node not in self.nodes:
                errors.append(f"Edge references unknown node: {edge.to_node}")
        
        # Check for at least one END node
        has_end = any(n.type == NodeType.END for n in self.nodes.values())
        if not has_end:
            errors.append("No END node defined")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary for storage/debugging."""
        return {
            "name": self.name,
            "start_node": self._start_node,
            "nodes": {
                nid: {
                    "type": n.type.value,
                    "handler": n.handler,
                    "config": n.config,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "condition": e.condition,
                    "priority": e.priority,
                }
                for e in self.edges
            ],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """Deserialize graph from dictionary."""
        graph = cls(name=data.get("name", "default"))
        
        for node_id, node_data in data.get("nodes", {}).items():
            graph.add_node(WorkflowNode(
                id=node_id,
                type=NodeType(node_data["type"]),
                handler=node_data.get("handler"),
                config=node_data.get("config", {}),
            ))
        
        for edge_data in data.get("edges", []):
            graph.add_edge(WorkflowEdge(
                from_node=edge_data["from"],
                to_node=edge_data["to"],
                condition=edge_data.get("condition"),
                priority=edge_data.get("priority", 0),
            ))
        
        if data.get("start_node"):
            graph.set_start(data["start_node"])
        
        return graph


# === Pre-defined Workflow Templates ===

def create_student_teacher_workflow() -> WorkflowGraph:
    """
    Create the default Student-Teacher review workflow.
    
    Flow: Student proposes → Teacher evaluates → Broadcast if approved
    """
    return (
        WorkflowGraph("student_teacher_review")
        .add_node(WorkflowNode("start", NodeType.START))
        .add_node(WorkflowNode("generate_proposal", NodeType.AGENT, handler="student"))
        .add_node(WorkflowNode("evaluate", NodeType.AGENT, handler="teacher"))
        .add_node(WorkflowNode("check_approval", NodeType.CONDITION, handler="is_approved"))
        .add_node(WorkflowNode("broadcast", NodeType.ACTION, handler="broadcast"))
        .add_node(WorkflowNode("end_approved", NodeType.END, config={"status": "approved"}))
        .add_node(WorkflowNode("end_rejected", NodeType.END, config={"status": "rejected"}))
        .add_edge(WorkflowEdge("start", "generate_proposal"))
        .add_edge(WorkflowEdge("generate_proposal", "evaluate"))
        .add_edge(WorkflowEdge("evaluate", "check_approval"))
        .add_edge(WorkflowEdge("check_approval", "broadcast", condition="approved"))
        .add_edge(WorkflowEdge("check_approval", "end_rejected", condition="rejected"))
        .add_edge(WorkflowEdge("broadcast", "end_approved"))
    )


def create_direct_broadcast_workflow() -> WorkflowGraph:
    """
    Create a simple direct broadcast workflow (no evaluation).
    
    Flow: Agent generates → Broadcast directly
    """
    return (
        WorkflowGraph("direct_broadcast")
        .add_node(WorkflowNode("start", NodeType.START))
        .add_node(WorkflowNode("generate", NodeType.AGENT, handler="teacher"))
        .add_node(WorkflowNode("broadcast", NodeType.ACTION, handler="broadcast"))
        .add_node(WorkflowNode("end", NodeType.END))
        .add_edge(WorkflowEdge("start", "generate"))
        .add_edge(WorkflowEdge("generate", "broadcast"))
        .add_edge(WorkflowEdge("broadcast", "end"))
    )
