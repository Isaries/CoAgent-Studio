"""
A2A Resilience Patterns.

Provides fault tolerance mechanisms for A2A communication:
- Circuit Breaker: Prevents cascading failures by temporarily blocking requests
- Retry with Exponential Backoff: Automatically retries failed operations
- Timeout handling: Prevents indefinite waits

These patterns are especially important for LLM API calls which can be unreliable.
"""

import asyncio
import structlog
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, ParamSpec

logger = structlog.get_logger()

T = TypeVar("T")
P = ParamSpec("P")


class CircuitState(str, Enum):
    """State of the circuit breaker."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, reject all requests immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""
    
    def __init__(self, breaker_name: str, retry_after: Optional[float] = None):
        self.breaker_name = breaker_name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker '{breaker_name}' is OPEN. Retry after {retry_after}s")


class MaxRetriesExceededError(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Max retries ({attempts}) exceeded. Last error: {last_error}")


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.
    
    Prevents cascading failures by tracking error rates and temporarily
    blocking requests when a service appears unhealthy.
    
    States:
    - CLOSED: Normal operation. Errors are counted.
    - OPEN: Service is down. All requests rejected immediately.
    - HALF_OPEN: Testing recovery. One request allowed through.
    
    Transitions:
    - CLOSED → OPEN: When failure_count >= failure_threshold
    - OPEN → HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN → CLOSED: If test request succeeds
    - HALF_OPEN → OPEN: If test request fails
    
    Example:
        breaker = CircuitBreaker("llm_api")
        
        if not breaker.can_execute():
            raise CircuitOpenError(breaker.name)
        
        try:
            result = await call_llm()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            raise
    """
    name: str
    failure_threshold: int = 5  # Errors before opening
    recovery_timeout: float = 30.0  # Seconds before testing recovery
    success_threshold: int = 2  # Consecutive successes to close
    
    # Internal state (not init params)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _last_state_change: datetime = field(default_factory=datetime.utcnow, init=False)
    
    @property
    def state(self) -> CircuitState:
        """Get current state, accounting for timeout transitions."""
        self._check_state_timeout()
        return self._state
    
    def _check_state_timeout(self) -> None:
        """Check if we should transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
            if elapsed >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.utcnow()
        
        if new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
        
        logger.info(
            "circuit_breaker_state_change",
            name=self.name,
            from_state=old_state.value,
            to_state=new_state.value,
        )
    
    def can_execute(self) -> bool:
        """
        Check if a request can be executed.
        
        Returns:
            True if request should proceed, False if circuit is open
        """
        state = self.state  # Triggers timeout check
        
        if state == CircuitState.CLOSED:
            return True
        
        if state == CircuitState.HALF_OPEN:
            return True  # Allow test request
        
        # OPEN
        return False
    
    def record_success(self) -> None:
        """Record a successful operation."""
        state = self.state
        
        if state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                self._failure_count = 0
        elif state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        state = self.state
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            failure_count=self._failure_count,
            threshold=self.failure_threshold,
        )
        
        if state == CircuitState.HALF_OPEN:
            # Test failed, back to OPEN
            self._transition_to(CircuitState.OPEN)
        elif state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def get_retry_after(self) -> Optional[float]:
        """Get seconds until circuit might close (for OPEN state)."""
        if self._state != CircuitState.OPEN or not self._last_failure_time:
            return None
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        remaining = self.recovery_timeout - elapsed
        return max(0, remaining)
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info("circuit_breaker_reset", name=self.name)


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Circuit breakers are shared globally by name, allowing multiple
    call sites to share the same failure tracking.
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _circuit_breakers[name]


def reset_all_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    for breaker in _circuit_breakers.values():
        breaker.reset()


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    **kwargs,
) -> Any:
    """
    Execute a function with exponential backoff retry.
    
    Args:
        func: Async function to execute
        max_attempts: Maximum number of attempts (including first)
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay cap (seconds)
        exponential_base: Multiplier for exponential growth
        retryable_exceptions: Tuple of exception types to retry
        
    Returns:
        Result of successful function call
        
    Raises:
        MaxRetriesExceededError: If all attempts fail
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_error = e
            
            if attempt >= max_attempts:
                logger.error(
                    "retry_exhausted",
                    func=func.__name__,
                    attempts=attempt,
                    error=str(e),
                )
                raise MaxRetriesExceededError(attempt, e)
            
            # Calculate delay with exponential backoff
            delay = min(
                base_delay * (exponential_base ** (attempt - 1)),
                max_delay,
            )
            
            logger.warning(
                "retry_attempt",
                func=func.__name__,
                attempt=attempt,
                max_attempts=max_attempts,
                delay=delay,
                error=str(e),
            )
            
            await asyncio.sleep(delay)
    
    # Should never reach here, but for type safety
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry state")


def with_resilience(
    breaker_name: str = "default",
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator combining Circuit Breaker and Retry with Exponential Backoff.
    
    This is the recommended way to protect LLM API calls.
    
    Example:
        @with_resilience(
            breaker_name="gemini_api",
            max_retries=3,
            failure_threshold=5,
        )
        async def call_gemini(prompt: str) -> str:
            return await gemini_client.generate(prompt)
    
    Args:
        breaker_name: Name for the circuit breaker (shared across calls)
        max_retries: Number of retry attempts
        base_delay: Initial retry delay
        max_delay: Maximum retry delay
        failure_threshold: Errors before circuit opens
        recovery_timeout: Seconds before testing recovery
        retryable_exceptions: Exception types that trigger retry
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        breaker = get_circuit_breaker(
            breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check circuit breaker first
            if not breaker.can_execute():
                retry_after = breaker.get_retry_after()
                raise CircuitOpenError(breaker_name, retry_after)

            async def attempt():
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result

            # Execute with retries — only retryable exceptions trigger retry.
            # Non-retryable exceptions propagate immediately without
            # tripping the circuit breaker.
            try:
                return await retry_with_backoff(
                    attempt,
                    max_attempts=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    retryable_exceptions=retryable_exceptions,
                )
            except MaxRetriesExceededError:
                # Record failure ONCE after all retries exhausted
                breaker.record_failure()
                raise
        
        return wrapper
    return decorator


def with_timeout(seconds: float):
    """
    Decorator to add timeout to async functions.
    
    Example:
        @with_timeout(30.0)
        async def slow_operation():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "operation_timeout",
                    func=func.__name__,
                    timeout=seconds,
                )
                raise
        return wrapper
    return decorator
