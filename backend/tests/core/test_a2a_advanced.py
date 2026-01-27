"""
Tests for A2A Advanced Features (P0-P2).

P0: Structured Payloads
P1: Graph-based Workflow
P2: Resilience Patterns
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from app.core.a2a import (
    # Core
    A2AMessage,
    MessageType,
    # P0: Payloads
    EvaluationRequestPayload,
    EvaluationResultPayload,
    BroadcastPayload,
    validate_payload,
    create_evaluation_request,
    create_evaluation_result,
    # P1: Workflow
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    WorkflowContext,
    NodeType,
    GraphExecutor,
    create_student_teacher_workflow,
    # P2: Resilience
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    MaxRetriesExceededError,
    get_circuit_breaker,
    reset_all_breakers,
    retry_with_backoff,
    with_resilience,
)


# ============================================================
# P0: Structured Payloads Tests
# ============================================================

class TestStructuredPayloads:
    """Tests for Pydantic-based message payloads."""
    
    def test_evaluation_request_payload_creation(self):
        """Test creating an evaluation request payload."""
        payload = EvaluationRequestPayload(
            proposal="Hello, world!",
            context="Previous messages...",
            urgency="high",
        )
        assert payload.proposal == "Hello, world!"
        assert payload.urgency == "high"
    
    def test_evaluation_request_default_urgency(self):
        """Test default urgency is 'normal'."""
        payload = EvaluationRequestPayload(proposal="Test")
        assert payload.urgency == "normal"
    
    def test_evaluation_request_validation_min_length(self):
        """Test that empty proposals are rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EvaluationRequestPayload(proposal="")
    
    def test_evaluation_result_payload(self):
        """Test creating an evaluation result payload."""
        payload = EvaluationResultPayload(
            approved=True,
            proposal="Test proposal",
            score=85.5,
            feedback="Good work!",
        )
        assert payload.approved is True
        assert payload.score == 85.5
    
    def test_evaluation_result_score_validation(self):
        """Test score must be between 0 and 100."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EvaluationResultPayload(
                approved=True,
                proposal="Test",
                score=150,  # Invalid!
            )
    
    def test_validate_payload_string_to_evaluation_request(self):
        """Test automatic string wrapping."""
        result = validate_payload(MessageType.EVALUATION_REQUEST, "Hello")
        assert isinstance(result, EvaluationRequestPayload)
        assert result.proposal == "Hello"
    
    def test_validate_payload_dict(self):
        """Test dict validation."""
        result = validate_payload(
            MessageType.EVALUATION_RESULT,
            {"approved": True, "proposal": "Test"},
        )
        assert isinstance(result, EvaluationResultPayload)
        assert result.approved is True
    
    def test_factory_functions(self):
        """Test factory helper functions."""
        req = create_evaluation_request("My proposal", context="History", urgency="high")
        assert req.proposal == "My proposal"
        assert req.urgency == "high"
        
        res = create_evaluation_result(True, "My proposal", score=90)
        assert res.approved is True
        assert res.score == 90


# ============================================================
# P1: Graph-based Workflow Tests
# ============================================================

class TestWorkflowGraph:
    """Tests for declarative workflow graph."""
    
    def test_create_simple_graph(self):
        """Test creating a basic workflow graph."""
        graph = (
            WorkflowGraph("test")
            .add_node(WorkflowNode("start", NodeType.START))
            .add_node(WorkflowNode("end", NodeType.END))
            .add_edge(WorkflowEdge("start", "end"))
        )
        
        assert graph.name == "test"
        assert graph.start_node == "start"
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
    
    def test_graph_validation(self):
        """Test graph validation catches errors."""
        # Missing start
        graph1 = WorkflowGraph("test").add_node(WorkflowNode("end", NodeType.END))
        errors = graph1.validate()
        assert "No start node defined" in errors
        
        # Missing end
        graph2 = WorkflowGraph("test").add_node(WorkflowNode("start", NodeType.START))
        errors = graph2.validate()
        assert "No END node defined" in errors
    
    def test_get_next_node_unconditional(self):
        """Test finding next node without conditions."""
        graph = (
            WorkflowGraph()
            .add_node(WorkflowNode("a", NodeType.START))
            .add_node(WorkflowNode("b", NodeType.AGENT))
            .add_edge(WorkflowEdge("a", "b"))
        )
        
        assert graph.get_next_node("a") == "b"
    
    def test_get_next_node_conditional(self):
        """Test finding next node with conditions."""
        graph = (
            WorkflowGraph()
            .add_node(WorkflowNode("check", NodeType.CONDITION))
            .add_node(WorkflowNode("yes", NodeType.END))
            .add_node(WorkflowNode("no", NodeType.END))
            .add_edge(WorkflowEdge("check", "yes", condition="approved"))
            .add_edge(WorkflowEdge("check", "no", condition="rejected"))
        )
        
        assert graph.get_next_node("check", "approved") == "yes"
        assert graph.get_next_node("check", "rejected") == "no"
    
    def test_graph_serialization(self):
        """Test graph can be serialized and deserialized."""
        original = create_student_teacher_workflow()
        data = original.to_dict()
        restored = WorkflowGraph.from_dict(data)
        
        assert restored.name == original.name
        assert len(restored.nodes) == len(original.nodes)
        assert len(restored.edges) == len(original.edges)
    
    def test_predefined_student_teacher_workflow(self):
        """Test the predefined workflow is valid."""
        graph = create_student_teacher_workflow()
        errors = graph.validate()
        assert len(errors) == 0


class TestGraphExecutor:
    """Tests for workflow graph execution."""
    
    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """Test executing a minimal workflow."""
        graph = (
            WorkflowGraph("simple")
            .add_node(WorkflowNode("start", NodeType.START))
            .add_node(WorkflowNode("agent", NodeType.AGENT, handler="test_agent"))
            .add_node(WorkflowNode("end", NodeType.END))
            .add_edge(WorkflowEdge("start", "agent"))
            .add_edge(WorkflowEdge("agent", "end"))
        )
        
        executor = GraphExecutor(graph)
        
        # Register mock agent handler
        async def test_agent_handler(ctx: WorkflowContext) -> A2AMessage:
            return A2AMessage(
                type=MessageType.PROPOSAL,
                sender_id="test",
                content="Generated content",
            )
        
        executor.register_agent("test_agent", test_agent_handler)
        
        result = await executor.execute({"input": "test"})
        
        assert result is not None
        assert result.content == "Generated content"
    
    @pytest.mark.asyncio
    async def test_conditional_workflow(self):
        """Test workflow with condition branching."""
        graph = (
            WorkflowGraph("conditional")
            .add_node(WorkflowNode("start", NodeType.START))
            .add_node(WorkflowNode("evaluate", NodeType.AGENT, handler="evaluator"))
            .add_node(WorkflowNode("check", NodeType.CONDITION, handler="is_approved"))
            .add_node(WorkflowNode("end_yes", NodeType.END, config={"status": "approved"}))
            .add_node(WorkflowNode("end_no", NodeType.END, config={"status": "rejected"}))
            .add_edge(WorkflowEdge("start", "evaluate"))
            .add_edge(WorkflowEdge("evaluate", "check"))
            .add_edge(WorkflowEdge("check", "end_yes", condition="approved"))
            .add_edge(WorkflowEdge("check", "end_no", condition="rejected"))
        )
        
        executor = GraphExecutor(graph)
        
        # Mock evaluator that approves
        async def approve_handler(ctx: WorkflowContext) -> A2AMessage:
            return A2AMessage(
                type=MessageType.EVALUATION_RESULT,
                sender_id="teacher",
                content={"approved": True, "proposal": "test"},
            )
        
        executor.register_agent("evaluator", approve_handler)
        
        result = await executor.execute()
        
        assert result is not None
        # Built-in is_approved should route to "approved" path


# ============================================================
# P2: Resilience Patterns Tests
# ============================================================

class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""
    
    def setup_method(self):
        """Reset all breakers before each test."""
        reset_all_breakers()
    
    def test_initial_state_is_closed(self):
        """Test breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute() is True
    
    def test_opens_after_threshold(self):
        """Test breaker opens after enough failures."""
        breaker = CircuitBreaker("test", failure_threshold=3)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.can_execute() is True  # Still below threshold
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False
    
    def test_success_resets_failure_count(self):
        """Test success decrements failure count."""
        breaker = CircuitBreaker("test", failure_threshold=5)
        
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()  # Decrements by 1
        
        # Failure count is now 2, need 3 more to hit threshold of 5
        breaker.record_failure()
        breaker.record_failure()
        assert breaker._state == CircuitState.CLOSED  # 4 < 5, still closed
    
    def test_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        import time
        time.sleep(0.15)
        
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute() is True
    
    def test_half_open_closes_on_success(self):
        """Test HALF_OPEN closes after successful requests."""
        breaker = CircuitBreaker(
            "test", 
            failure_threshold=1, 
            recovery_timeout=60.0,  # Long timeout to prevent auto-transition
            success_threshold=2,
        )
        
        breaker.record_failure()
        assert breaker._state == CircuitState.OPEN  # Use _state to avoid timeout check
        
        # Force to HALF_OPEN
        breaker._transition_to(CircuitState.HALF_OPEN)
        
        breaker.record_success()
        assert breaker._state == CircuitState.HALF_OPEN  # Need 2 successes
        
        breaker.record_success()
        assert breaker._state == CircuitState.CLOSED
    
    def test_half_open_reopens_on_failure(self):
        """Test HALF_OPEN reopens on failure."""
        breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60.0)  # Long timeout
        
        breaker.record_failure()
        breaker._transition_to(CircuitState.HALF_OPEN)
        
        breaker.record_failure()
        assert breaker._state == CircuitState.OPEN  # Use _state to avoid timeout check
    
    def test_get_circuit_breaker_shared(self):
        """Test circuit breakers are shared by name."""
        b1 = get_circuit_breaker("shared")
        b2 = get_circuit_breaker("shared")
        
        assert b1 is b2
        
        b1.record_failure()
        assert b2._failure_count == 1


class TestRetryWithBackoff:
    """Tests for retry with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """Test no retry needed when function succeeds."""
        call_count = 0
        
        async def success():
            nonlocal call_count
            call_count += 1
            return "ok"
        
        result = await retry_with_backoff(success, max_attempts=3)
        
        assert result == "ok"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Test retry occurs on failure."""
        call_count = 0
        
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "ok"
        
        result = await retry_with_backoff(
            fail_then_succeed, 
            max_attempts=3, 
            base_delay=0.01,
        )
        
        assert result == "ok"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        """Test raises MaxRetriesExceededError when all attempts fail."""
        async def always_fail():
            raise ValueError("Always fails")
        
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await retry_with_backoff(
                always_fail, 
                max_attempts=2, 
                base_delay=0.01,
            )
        
        assert exc_info.value.attempts == 2


class TestWithResilienceDecorator:
    """Tests for the combined resilience decorator."""
    
    def setup_method(self):
        reset_all_breakers()
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test decorator allows successful calls."""
        @with_resilience(breaker_name="test_success", max_retries=2)
        async def my_func():
            return "success"
        
        result = await my_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_opens_circuit_on_failures(self):
        """Test decorator opens circuit after repeated failures."""
        call_count = 0
        
        @with_resilience(
            breaker_name="test_open",
            max_retries=1,
            failure_threshold=2,
            base_delay=0.01,
        )
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")
        
        # First call exhausts retries
        with pytest.raises(MaxRetriesExceededError):
            await failing_func()
        
        # Second call exhausts retries and opens circuit
        with pytest.raises(MaxRetriesExceededError):
            await failing_func()
        
        # Third call should be rejected immediately
        with pytest.raises(CircuitOpenError):
            await failing_func()
