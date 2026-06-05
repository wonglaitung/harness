"""
Circuit breaker for detecting and preventing infinite loops.

Simple, scalable approach following Bitter Lesson principles:
- Simple rules over complex heuristics
- Trust the model to self-correct
- Only intervene on obvious problems (same tool + same args repeated)
"""

from __future__ import annotations

from collections import Counter
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
class CircuitBreakerConfig:
    """Configuration for circuit breaker.

    Following Bitter Lesson: keep it simple, trust the model.
    """
    # Same tool + args threshold
    # Only trigger when calling same tool with same arguments repeatedly
    # This is the simplest, most reliable detection
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

    Simple approach:
    - Detect when same tool is called with same arguments repeatedly
    - Detect when too many errors occur in a short time

    We don't try to be "smart" about detecting complex patterns.
    Trust the model (via system prompt) to know when to stop.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED

        # Track tool:args combination (simple and effective)
        self._tool_args_counter: Counter[str] = Counter()

        # Track errors
        self._error_times: list[datetime] = []

        # Track half-open state
        self._open_time: datetime | None = None
        self._half_open_calls = 0

        # Track why circuit opened
        self._open_reason: str | None = None

    def record_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """
        Record a tool call for pattern detection.

        Simple: just count tool:args combinations.
        """
        args_key = self._make_args_key(tool_name, arguments)
        self._tool_args_counter[args_key] += 1

        # Check if we should open circuit
        self._check_patterns()

    def _make_args_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Create a hashable key for tool + args combination."""
        args_hash = self._hashable_args(arguments)
        return f"{tool_name}:{args_hash}"

    def record_error(self, error: Exception | None = None) -> None:
        """Record an error during tool execution."""
        self._error_times.append(datetime.now())

        # Clean old errors outside window
        cutoff = datetime.now() - timedelta(seconds=self.config.error_window_seconds)
        self._error_times = [t for t in self._error_times if t > cutoff]

        # Check if error threshold reached
        if len(self._error_times) >= self.config.error_threshold:
            self._open_reason = (
                f"{len(self._error_times)} errors in last "
                f"{self.config.error_window_seconds} seconds"
            )
            self._open()

    def record_success(self) -> None:
        """Record a successful tool execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._close()

    def is_open(self) -> bool:
        """Check if circuit is open (should block calls)."""
        if self._state == CircuitState.CLOSED:
            return False

        if self._state == CircuitState.OPEN:
            if self._open_time:
                elapsed = (datetime.now() - self._open_time).total_seconds()
                if elapsed >= self.config.recovery_timeout_seconds:
                    self._half_open()
                    return False
            return True

        if self._half_open_calls >= self.config.half_open_max_calls:
            return True

        return False

    def get_reason(self) -> str | None:
        """Get the reason why circuit is open."""
        if self._state == CircuitState.CLOSED:
            return None
        return self._open_reason or "Circuit breaker is open"

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._close()
        self._tool_args_counter.clear()
        self._error_times.clear()
        self._open_reason = None

    def _check_patterns(self) -> None:
        """Check for problematic patterns - keep it simple."""
        # Only check: same tool + same args repeated
        for args_key, count in self._tool_args_counter.items():
            if count >= self.config.same_args_threshold:
                tool_name = args_key.split(":", 1)[0]
                self._open_reason = (
                    f"Tool '{tool_name}' with same arguments called {count} times "
                    f"(threshold: {self.config.same_args_threshold})"
                )
                self._open()
                return

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
            "recent_errors": len(self._error_times),
            "tool_args_counter": dict(self._tool_args_counter.most_common(5)),
        }
