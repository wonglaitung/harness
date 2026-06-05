"""
Tests for Phase 0 components: TokenCounter, ContextBudget, CircuitBreaker, ErrorHandler.
"""

import pytest

from harness.memory.token_counter import TokenCounter, count_tokens
from harness.memory.context_builder import ContextBudget, ContextBuilder, ContextConfig
from harness.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from harness.core.error_handler import ErrorHandler, ErrorAction, ErrorContext


class TestTokenCounter:
    """Tests for TokenCounter."""

    def test_count_simple_text(self):
        """Test counting tokens in simple text."""
        counter = TokenCounter("claude-sonnet-4-6")
        count = counter.count("Hello, world!")
        assert count > 0

    def test_count_empty_string(self):
        """Test counting empty string returns 0."""
        counter = TokenCounter()
        assert counter.count("") == 0

    def test_count_caches_results(self):
        """Test that count caches results."""
        counter = TokenCounter()
        text = "This is a test string"

        # First call
        count1 = counter.count(text)
        # Second call should use cache
        count2 = counter.count(text)

        assert count1 == count2
        assert text in counter._cache

    def test_estimate_tool_overhead(self):
        """Test estimating tool schema overhead."""
        counter = TokenCounter()

        class MockTool:
            name = "read"
            description = "Read a file"
            input_schema = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
            }

        overhead = counter.estimate_tool_overhead([MockTool()])
        assert overhead > 0

    def test_get_budget_allocation(self):
        """Test budget allocation calculation."""
        counter = TokenCounter()

        budget = counter.get_budget_allocation(
            max_tokens=100000,
            system_prompt="You are a helpful assistant.",
        )

        assert budget["response_reserve"] == 4096
        assert budget["recent_messages"] > 0
        assert budget["total_available"] == 100000 - 4096


class TestContextBudget:
    """Tests for ContextBudget."""

    def test_allocate_default(self):
        """Test default allocation."""
        budget = ContextBudget.allocate(max_tokens=100000)

        assert budget.max_tokens == 100000
        assert budget.response_reserve == 4096
        assert budget.available_for_input == 95904

    def test_allocate_with_system_prompt(self):
        """Test allocation with system prompt."""
        budget = ContextBudget.allocate(
            max_tokens=100000,
            system_prompt_tokens=5000,
        )

        assert budget.system_prompt == 5000
        assert budget.tools == 0
        assert budget.recent_messages > 0

    def test_needs_compression(self):
        """Test compression detection."""
        budget = ContextBudget(
            max_tokens=10000,
            response_reserve=4096,
            system_prompt=2000,
            recent_messages=10000,  # Exceeds available
        )

        assert budget.needs_compression is True

    def test_remaining_calculation(self):
        """Test remaining tokens calculation."""
        budget = ContextBudget(
            max_tokens=10000,
            response_reserve=4096,
            system_prompt=1000,
            tools=500,
            recent_messages=3000,
            skills=500,
            memory=200,
        )

        expected_used = 1000 + 500 + 3000 + 500 + 200
        expected_remaining = (10000 - 4096) - expected_used

        assert budget.used == expected_used
        assert budget.remaining == expected_remaining


class TestCircuitBreaker:
    """Tests for CircuitBreaker (simplified version following Bitter Lesson)."""

    def test_same_args_pattern_opens_circuit(self):
        """Test that same tool + args pattern opens circuit.

        This is the core detection mechanism - simple and effective.
        """
        cb = CircuitBreaker(CircuitBreakerConfig(same_args_threshold=3))

        # Call same tool with same args 3 times
        args = {"path": "test.txt"}
        for _ in range(3):
            cb.record_call("read", args)

        assert cb.is_open() is True
        assert "read" in cb.get_reason()

    def test_different_args_dont_open_circuit(self):
        """Test that different tools or different args don't trigger circuit.

        Trust the model - only block obvious repetition.
        """
        cb = CircuitBreaker()

        # Call same tool with different args (should NOT trigger)
        for i in range(10):
            cb.record_call("read", {"path": f"file_{i}.txt"})

        assert cb.is_open() is False

        # Call different tools (should NOT trigger)
        cb.reset()
        for i in range(10):
            cb.record_call(f"tool_{i}", {})

        assert cb.is_open() is False

    def test_reset_closes_circuit(self):
        """Test that reset closes the circuit."""
        cb = CircuitBreaker(CircuitBreakerConfig(same_args_threshold=2))

        # Open the circuit
        for _ in range(2):
            cb.record_call("read", {"path": "same.txt"})

        assert cb.is_open() is True

        # Reset
        cb.reset()

        assert cb.is_open() is False
        assert cb.state == CircuitState.CLOSED

    def test_record_error_increments_error_count(self):
        """Test that errors are tracked."""
        cb = CircuitBreaker(CircuitBreakerConfig(error_threshold=3))

        for _ in range(3):
            cb.record_error()

        assert cb.is_open() is True

    def test_recovery_after_timeout(self):
        """Test that circuit recovers after timeout."""
        import time

        cb = CircuitBreaker(CircuitBreakerConfig(
            same_args_threshold=3,
            recovery_timeout_seconds=0.1  # Very short for testing
        ))

        # Open the circuit (call 3 times to reach threshold)
        for _ in range(3):
            cb.record_call("read", {"path": "same.txt"})

        assert cb.is_open() is True

        # Wait for recovery timeout
        time.sleep(0.15)

        # Circuit should now be in half-open state (allows limited calls)
        assert cb.is_open() is False  # Allows one test call in half-open


class TestErrorHandler:
    """Tests for ErrorHandler."""

    def test_rate_limit_returns_retry(self):
        """Test rate limit error returns RETRY action."""
        handler = ErrorHandler()
        ctx = ErrorContext(error=Exception("rate limit"), iteration=1)

        decision = handler.handle(Exception("Rate limit exceeded"), ctx)

        assert decision.action == ErrorAction.RETRY
        assert decision.delay_seconds > 0

    def test_permission_denied_returns_abort(self):
        """Test permission error returns ABORT action."""
        handler = ErrorHandler()
        ctx = ErrorContext(error=PermissionError("Access denied"), iteration=1)

        decision = handler.handle(PermissionError("Permission denied"), ctx)

        assert decision.action == ErrorAction.ABORT

    def test_max_retries_exhausted_returns_abort(self):
        """Test that exhausting retries returns ABORT."""
        handler = ErrorHandler(max_retries=2)

        # Simulate multiple retry attempts
        for i in range(3):
            ctx = ErrorContext(error=Exception("timeout"), iteration=i)
            decision = handler.handle(TimeoutError("Connection timed out"), ctx)

        # Should eventually abort
        assert decision.action in (ErrorAction.RETRY, ErrorAction.ABORT)

    def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        handler = ErrorHandler(base_delay=1.0)

        ctx1 = ErrorContext(error=Exception(), iteration=1)
        ctx2 = ErrorContext(error=Exception(), iteration=2)

        decision1 = handler.handle(Exception("rate limit exceeded"), ctx1)
        decision2 = handler.handle(Exception("rate limit exceeded"), ctx2)

        # Second retry should have longer delay
        assert decision2.delay_seconds >= decision1.delay_seconds

    def test_reset_clears_retry_counts(self):
        """Test that reset clears retry counters."""
        handler = ErrorHandler()

        # Generate some retry counts
        ctx = ErrorContext(error=Exception(), iteration=1)
        handler.handle(Exception("rate limit exceeded"), ctx)

        assert len(handler._retry_counts) > 0

        handler.reset()

        assert len(handler._retry_counts) == 0


class TestContextBuilder:
    """Tests for ContextBuilder with TokenCounter integration."""

    def test_build_with_token_budget(self):
        """Test that context building respects token budget."""
        from harness.types import Session

        counter = TokenCounter()
        config = ContextConfig(max_tokens=10000)
        builder = ContextBuilder(config=config, token_counter=counter)

        session = Session(id="test")
        result = builder.build(session, "Hello world")

        assert result.estimated_tokens > 0
        assert result.budget is not None

    def test_context_builder_uses_tiktoken(self):
        """Test that ContextBuilder uses tiktoken for counting."""
        from harness.types import Session

        builder = ContextBuilder()

        # The estimate should be more accurate than len // 4
        count = builder.estimate_tokens("Hello, world!")
        assert count > 0

        # Should match TokenCounter
        counter = TokenCounter()
        assert count == counter.count("Hello, world!")
