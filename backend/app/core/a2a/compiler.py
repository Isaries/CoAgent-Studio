"""
WorkflowCompiler – Translates a Workflow JSON graph into an
executable LangGraph StateGraph.

This is the heart of the dynamic multi-agent engine.  It reads the
``graph_data`` dict (persisted in the DB / sent from the frontend canvas)
and builds a compiled LangGraph that can be invoked with ``ainvoke``.

Design choices
--------------
* Each **agent node** is backed by ``AgentCore.run()`` – no hard-coded
  TeacherAgent / StudentAgent classes required.
* Each **router node** evaluates a simple expression against the current
  state and returns the next edge label.
* Each **action node** performs a side-effect (broadcast, tool call, etc.).
* The compiler injects a **CycleLimiter** guard so workflows cannot loop
  infinitely (defaults to 50 iterations).
"""

from __future__ import annotations

import operator
import structlog
from typing import Annotated, Any, Dict, List, Optional, Sequence
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.core.a2a.models import A2AMessage, MessageType
from app.models.workflow import WorkflowEdgeType, WorkflowNodeType

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Shared state that flows through the graph
# ---------------------------------------------------------------------------

class MultiAgentState(dict):
    """
    State dict passed between LangGraph nodes.

    Keys (all optional with defaults):
        messages:           Accumulated A2A messages (append-only).
        current_proposal:   Latest text proposal from an agent.
        evaluation_result:  Latest boolean evaluation result.
        shared_memory:      Scratch-pad for arbitrary inter-agent data.
        _cycle_count:       Internal counter for the cycle limiter.
        _active_node_id:    ID of the currently executing node (for tracing).
    """
    pass


def _default_state() -> MultiAgentState:
    return MultiAgentState(
        messages=[],
        current_proposal=None,
        evaluation_result=None,
        shared_memory={},
        _cycle_count=0,
        _active_node_id=None,
    )


# ---------------------------------------------------------------------------
# WorkflowCompiler
# ---------------------------------------------------------------------------

class WorkflowCompiler:
    """
    Compiles a ``graph_data`` JSON dict into a runnable LangGraph.

    Usage::

        compiler = WorkflowCompiler()
        compiled = compiler.compile(graph_data, agent_registry)
        result = await compiled.ainvoke(initial_state, config=...)
    """

    MAX_CYCLES = 50  # safety net

    def __init__(self, max_cycles: int = MAX_CYCLES):
        self._max_cycles = max_cycles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(
        self,
        graph_data: Dict[str, Any],
        agent_registry: Dict[str, Any],
        *,
        action_registry: Optional[Dict[str, Any]] = None,
        checkpointer: Any = None,
    ) -> Any:
        """
        Build and compile a LangGraph ``StateGraph``.

        Parameters
        ----------
        graph_data:
            The ``Workflow.graph_data`` JSON with ``nodes`` and ``edges``.
        agent_registry:
            Mapping from ``AgentConfig.id`` (str) → ``AgentCore`` instance.
        action_registry:
            Optional mapping from action name → async callable.
        checkpointer:
            LangGraph persistence backend (e.g. ``PostgresSaver``).

        Returns
        -------
        A compiled LangGraph ready for ``ainvoke`` / ``astream``.
        """
        nodes: List[dict] = graph_data.get("nodes", [])
        edges: List[dict] = graph_data.get("edges", [])
        action_registry = action_registry or {}

        builder = StateGraph(dict)  # type: ignore

        # Phase 1 – Register nodes ------------------------------------------
        start_node_id: Optional[str] = None
        end_node_ids: List[str] = []

        for node in nodes:
            nid = node["id"]
            ntype = node.get("type", "agent")

            if ntype == WorkflowNodeType.START:
                start_node_id = nid
                builder.add_node(nid, self._make_passthrough(nid))

            elif ntype == WorkflowNodeType.END:
                end_node_ids.append(nid)
                # END nodes map to LangGraph's sentinel
                # We add a thin wrapper so we can record the trace event
                builder.add_node(nid, self._make_end_node(nid))

            elif ntype == WorkflowNodeType.AGENT:
                agent_id = node.get("config", {}).get("agent_id")
                agent = agent_registry.get(str(agent_id)) if agent_id else None
                builder.add_node(nid, self._make_agent_node(nid, agent, node, self._max_cycles))

            elif ntype == WorkflowNodeType.ROUTER:
                # Routers are handled via conditional edges (see Phase 2)
                builder.add_node(nid, self._make_router_node(nid, node, self._max_cycles))

            elif ntype == WorkflowNodeType.ACTION:
                action_name = node.get("config", {}).get("action_type", "broadcast")
                handler = action_registry.get(action_name)
                builder.add_node(nid, self._make_action_node(nid, handler, node))

            elif ntype == WorkflowNodeType.MERGE:
                builder.add_node(nid, self._make_passthrough(nid))

            elif ntype == WorkflowNodeType.TOOL:
                builder.add_node(nid, self._make_tool_node(nid, node))

            else:
                logger.warning("workflow_compiler_unknown_node_type", nid=nid, ntype=ntype)
                builder.add_node(nid, self._make_passthrough(nid))

        # Phase 2 – Register edges ------------------------------------------
        # Group edges by source to detect conditional routing
        edges_by_source: Dict[str, List[dict]] = {}
        for edge in edges:
            src = edge["source"]
            edges_by_source.setdefault(src, []).append(edge)

        for src, src_edges in edges_by_source.items():
            src_node = self._find_node(nodes, src)
            src_type = src_node.get("type") if src_node else None

            if src_type == WorkflowNodeType.ROUTER:
                # Conditional branching: each edge has a "condition" label
                path_map: dict = {}
                for e in src_edges:
                    condition_label = e.get("condition", e.get("type", "default"))
                    path_map[condition_label] = e["target"]
                # Ensure there is always an "exceeded" fallback for the
                # global cycle guard.  Map it to the first END node if
                # the workflow didn't explicitly define one.
                if "exceeded" not in path_map and end_node_ids:
                    path_map["exceeded"] = end_node_ids[0]
                builder.add_conditional_edges(src, self._make_route_fn(src), path_map)  # type: ignore
            else:
                # Simple sequential edges
                if len(src_edges) == 1:
                    target = src_edges[0]["target"]
                    target_node = self._find_node(nodes, target)
                    if target_node and target_node.get("type") == WorkflowNodeType.END:
                        builder.add_edge(src, target)
                    else:
                        builder.add_edge(src, target)
                else:
                    # Multiple outgoing edges from non-router → fan-out
                    # For simplicity, take the first edge as default
                    for e in src_edges:
                        builder.add_edge(src, e["target"])

        # Set entry point
        if start_node_id:
            builder.set_entry_point(start_node_id)
        elif nodes:
            builder.set_entry_point(nodes[0]["id"])

        # Set finish points
        for eid in end_node_ids:
            builder.set_finish_point(eid)

        # Compile
        compile_kwargs = {}
        if checkpointer:
            compile_kwargs["checkpointer"] = checkpointer
        # LangGraph recursion_limit is per-superstep; give headroom for
        # routers / passthroughs that don't bump _cycle_count.
        compile_kwargs["recursion_limit"] = self._max_cycles * 3

        compiled = builder.compile(**compile_kwargs)
        logger.info(
            "workflow_compiled",
            node_count=len(nodes),
            edge_count=len(edges),
        )
        return compiled

    # ------------------------------------------------------------------
    # Node factory methods
    # ------------------------------------------------------------------

    @staticmethod
    def _make_passthrough(node_id: str):
        """A no-op node that just passes state through (START, MERGE)."""
        async def _passthrough(state: dict) -> dict:
            return {"_active_node_id": node_id}
        return _passthrough

    @staticmethod
    def _make_end_node(node_id: str):
        """Terminal node – marks the run as complete."""
        async def _end(state: dict) -> dict:
            return {"_active_node_id": node_id}
        return _end

    @staticmethod
    def _make_agent_node(node_id: str, agent, node_config: dict, max_cycles: int = 50):
        """
        Create a LangGraph node backed by an ``AgentCore`` instance.

        The node reads ``state["messages"]`` for context, calls the LLM,
        and writes the response back into the state.

        Returns a partial update dict — never mutates ``state`` in-place.
        """
        async def _agent(state: dict) -> dict:
            updates: dict = {"_active_node_id": node_id}

            cycle_count = state.get("_cycle_count", 0)

            # Global cycle guard — terminate if limit exceeded
            if cycle_count >= max_cycles:
                logger.warning(
                    "workflow_cycle_limit_exceeded",
                    node_id=node_id,
                    cycle_count=cycle_count,
                    max_cycles=max_cycles,
                )
                term_msg = {
                    "type": MessageType.PROPOSAL.value,
                    "sender_id": node_id,
                    "content": f"[System] Cycle limit ({max_cycles}) exceeded. Workflow terminated.",
                }
                updates["messages"] = list(state.get("messages", [])) + [term_msg]
                updates["_cycle_count"] = cycle_count + 1
                return updates

            if agent is None:
                logger.warning("workflow_agent_node_no_agent", node_id=node_id)
                return updates

            # Build prompt from message history (read-only access to state)
            messages = state.get("messages", [])
            context_lines = []
            for m in messages[-10:]:
                if isinstance(m, dict):
                    sender = m.get("sender_id", "unknown")
                    content = m.get("content", "")
                else:
                    sender = getattr(m, "sender_id", "unknown")
                    content = getattr(m, "content", "")
                context_lines.append(f"{sender}: {content}")

            context = "\n".join(context_lines)
            prompt = f"Chat History:\n{context}\n\nRespond based on your role."

            response = await agent.run(prompt)

            # Determine the edge type from configuration
            edge_behavior = node_config.get("config", {}).get("output_behavior", "proposal")

            if edge_behavior == "proposal":
                updates["current_proposal"] = str(response)
            elif edge_behavior == "evaluation":
                approved = "YES" in str(response).upper()
                updates["evaluation_result"] = approved

            # Always append to message log (copy, don't mutate)
            new_msg = {
                "type": MessageType.PROPOSAL.value,
                "sender_id": node_id,
                "content": str(response),
            }
            updates["messages"] = list(state.get("messages", [])) + [new_msg]

            # Cycle limiter
            updates["_cycle_count"] = cycle_count + 1

            logger.info("workflow_agent_executed", node_id=node_id)
            return updates

        return _agent

    @staticmethod
    def _make_router_node(node_id: str, node_config: dict, max_cycles: int = 50):
        """
        Router node – evaluates a condition and stores the result.
        The actual branching is handled by ``add_conditional_edges``.

        Returns a partial update dict — never mutates ``state`` in-place.
        Includes a global cycle guard: if ``_cycle_count >= max_cycles``,
        forces ``_route_result = "exceeded"`` regardless of condition type.
        """
        async def _router(state: dict) -> dict:
            updates: dict = {"_active_node_id": node_id}

            # Global cycle guard — override any condition
            cycle_count = state.get("_cycle_count", 0)
            if cycle_count >= max_cycles:
                logger.warning(
                    "workflow_router_cycle_limit_forced",
                    node_id=node_id,
                    cycle_count=cycle_count,
                    max_cycles=max_cycles,
                )
                updates["_route_result"] = "exceeded"
                return updates

            condition_type = node_config.get("config", {}).get("condition", "is_approved")

            if condition_type == "is_approved":
                result = state.get("evaluation_result")
                updates["_route_result"] = "approved" if result else "rejected"

            elif condition_type == "cycle_limit":
                max_cfg = node_config.get("config", {}).get("max_cycles", 50)
                updates["_route_result"] = "exceeded" if cycle_count >= max_cfg else "continue"

            else:
                updates["_route_result"] = "default"

            return updates
        return _router

    @staticmethod
    def _make_route_fn(node_id: str):
        """Return a callable that extracts the route result from state."""
        def _route(state: dict) -> str:
            return state.get("_route_result", "default")
        return _route

    @staticmethod
    def _make_action_node(node_id: str, handler, node_config: dict):
        """Action node – performs side effects (broadcast, tool calls).

        Returns a partial update dict. The handler receives state for
        reading but the node itself only updates ``_active_node_id``.
        """
        async def _action(state: dict) -> dict:
            if handler:
                await handler(state)
            else:
                logger.warning("workflow_action_no_handler", node_id=node_id)
            return {"_active_node_id": node_id}
        return _action

    @staticmethod
    def _make_tool_node(node_id: str, node_config: dict):
        """Tool node – invokes an external tool."""
        async def _tool(state: dict) -> dict:
            tool_name = node_config.get("config", {}).get("tool_name", "unknown")
            logger.info("workflow_tool_node", node_id=node_id, tool=tool_name)
            # Tool execution will be implemented when tool registry is ready
            return {"_active_node_id": node_id}
        return _tool

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_node(nodes: List[dict], node_id: str) -> Optional[dict]:
        """Find a node dict by ID."""
        for n in nodes:
            if n["id"] == node_id:
                return n
        return None
