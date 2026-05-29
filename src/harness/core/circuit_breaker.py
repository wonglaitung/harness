"""
Circuit breaker for detecting and preventing infinite loops.

Detects repeated tool call patterns to prevent agent from getting stuck.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class ToolCallRecord:
    """Record of a tool call for pattern detection."""
    tool_name: str
    arguments: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    # Same tool call threshold
    same_tool_threshold: int = 5
    same_args_threshold: int = 3

    # Error threshold
    error_threshold: int = 5
    error_window_seconds: int = 60

    # Recovery
    recovery_timeout_seconds: int = 30
    half_open_max_calls: int = 1


class CircuitBreaker:
    """
    Circuit breaker to detect and prevent infinite loops.

    Monitors tool call patterns and opens circuit when:
    - Same tool called too many times in a row
    - Same tool + arguments repeated
    - Too many errors in a short time window

    Example:
        >>> cb = CircuitBreaker()
        >>> for _ in range(6):
        ...     cb.record_call("read", {"path": "same.txt"})
        >>> cb.is_open()
        True
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED

        # Track consecutive same tool calls
        self._last_tool: str | None = None
        self._consecutive_same_tool = 0

        # Track same tool + args pattern
        self._call_history: list[ToolCallRecord] = []
        self._max_history = 100

        # Track errors
        self._error_times: list[datetime] = []

        # Track half-open state
        self._open_time: datetime | None = None
        self._half_open_calls = 0

    def record_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """
        Record a tool call for pattern detection.

        Args:
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool
        """
        # Update consecutive same tool counter
        if tool_name == self._last_tool:
            self._consecutive_same_tool += 1
        else:
            self._consecutive_same_tool = 1
            self._last_tool = tool_name

        # Record in history
        record = ToolCallRecord(tool_name=tool_name, arguments=arguments.copy())
        self._call_history.append(record)

        # Trim history
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history:]

        # Check if we should open circuit
        self._check_patterns()

    def record_error(self, error: Exception | None = None) -> None:
        """
        Record an error during tool execution.

        Args:
            error: The error that occurred
        """
        self._error_times.append(datetime.now())

        # Clean old errors outside window
        cutoff = datetime.now() - timedelta(seconds=self.config.error_window_seconds)
        self._error_times = [t for t in self._error_times if t > cutoff]

        # Check if error threshold reached
        if len(self._error_times) >= self.config.error_threshold:
            self._open()

    def record_success(self) -> None:
        """Record a successful tool execution."""
        if self._state == CircuitState.HALF_OPEN:
            # Successful call in half-open, close circuit
            self._close()

    def is_open(self) -> bool:
        """
        Check if circuit is open (should block calls).

        Returns:
            True if circuit is open and calls should be blocked
        """
        if self._state == CircuitState.CLOSED:
            return False

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if self._open_time:
                elapsed = (datetime.now() - self._open_time).total_seconds()
                if elapsed >= self.config.recovery_timeout_seconds:
                    self._half_open()
                    return False
            return True

        # HALF_OPEN: allow limited calls
        if self._half_open_calls >= self.config.half_open_max_calls:
            return True

        return False

    def get_reason(self) -> str | None:
        """
        Get the reason why circuit is open.

        Returns:
            Human-readable reason or None if circuit is closed
        """
        if self._state == CircuitState.CLOSED:
            return None

        if self._consecutive_same_tool >= self.config.same_tool_threshold:
            return (
                f"Tool '{self._last_tool}' called {self._consecutive_same_tool} times "
                f"(threshold: {self.config.same_tool_threshold})"
            )

        if self._check_same_args_pattern():
            recent = self._call_history[-self.config.same_args_threshold:]
            tool = recent[0].tool_name if recent else "unknown"
            return f"Same tool '{tool}' with same arguments repeated"

        if len(self._error_times) >= self.config.error_threshold:
            return (
                f"{len(self._error_times)} errors in last "
                f"{self.config.error_window_seconds} seconds"
            )

        return "Circuit breaker is open"

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._close()
        self._call_history.clear()
        self._error_times.clear()
        self._last_tool = None
        self._consecutive_same_tool = 0

    def _check_patterns(self) -> None:
        """Check for problematic patterns and open circuit if needed."""
        # Check consecutive same tool calls
        if self._consecutive_same_tool >= self.config.same_tool_threshold:
            self._open()
            return

        # Check same tool + args pattern
        if self._check_same_args_pattern():
            self._open()
            return

    def _check_same_args_pattern(self) -> bool:
        """Check if same tool with same args is repeated."""
        if len(self._call_history) < self.config.same_args_threshold:
            return False

        recent = self._call_history[-self.config.same_args_threshold:]

        # All must be same tool
        tools = [r.tool_name for r in recent]
        if len(set(tools)) > 1:
            return False

        # All must have same arguments
        args_list = [self._hashable_args(r.arguments) for r in recent]
        if len(set(args_list)) > 1:
            return False

        return True

    def _hashable_args(self, args: dict[str, Any]) -> tuple:
        """Convert args dict to hashable tuple for comparison."""
        items = []
        for k, v in sorted(args.items()):
            if isinstance(v, dict):
                v = self._hashable_args(v)
            elif isinstance(v, list):
                v = tuple(v)
            items.append((k, v))
        return tuple(items)

    def _open(self) -> None:
        """Open the circuit."""
        self._state = CircuitState.OPEN
        self._open_time = datetime.now()
        self._half_open_calls = 0

    def _half_open(self) -> None:
        """Move to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0

    def _close(self) -> None:
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._open_time = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self._state.value,
            "consecutive_same_tool": self._consecutive_same_tool,
            "last_tool": self._last_tool,
            "recent_errors": len(self._error_times),
            "call_history_size": len(self._call_history),
        }
