"""
Cost Controller for managing session budgets.

Prevents runaway costs by enforcing token and tool call limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.types import CostConfig, ProgressEventType, TokenUsage

if TYPE_CHECKING:
    from harness.types import ProgressCallback, ProgressEvent

logger = logging.getLogger(__name__)


@dataclass
class BudgetStatus:
    """Current budget status."""
    is_within_budget: bool
    usage: TokenUsage
    config: CostConfig
    warning_message: str | None = None
    should_compress: bool = False
    usage_ratio: float = 0.0

    @property
    def is_warning(self) -> bool:
        """Check if in warning state."""
        return self.warning_message is not None and self.is_within_budget

    @property
    def remaining_tokens(self) -> int:
        """Tokens remaining in budget."""
        return max(0, self.config.max_tokens_per_session - self.usage.total_tokens)

    @property
    def remaining_tool_calls(self) -> int:
        """Tool calls remaining in budget."""
        return max(0, self.config.max_tool_calls_per_session - self.usage.tool_calls)


class CostController:
    """
    Controller for managing session-level budgets.

    Enforces limits on:
    - Total tokens per session
    - Tool calls per session
    - Iterations per request

    Emits warnings at configurable threshold (default 80%).

    Example:
        >>> config = CostConfig(max_tokens_per_session=100_000)
        >>> controller = CostController(config)
        >>>
        >>> # Check before operation
        >>> status = controller.check(usage)
        >>> if not status.is_within_budget:
        ...     raise BudgetExceededError(status.warning_message)
    """

    def __init__(
        self,
        config: CostConfig | None = None,
        on_progress: "ProgressCallback | None" = None,
    ):
        self.config = config or CostConfig()
        self._on_progress = on_progress
        self._session_usage: dict[str, TokenUsage] = {}
        self._request_iterations: dict[str, int] = {}

    def check(self, usage: TokenUsage, session_id: str | None = None) -> BudgetStatus:
        """
        Check if usage is within budget.

        Args:
            usage: Current token usage
            session_id: Optional session ID for tracking

        Returns:
            BudgetStatus with check results
        """
        is_within, warning = usage.check_budget(self.config)
        usage_ratio = usage.total_tokens / self.config.max_tokens_per_session

        should_compress = False
        if not is_within and self.config.action_on_exceed == "compress":
            should_compress = True
            is_within = True  # Allow to continue with compression

        status = BudgetStatus(
            is_within_budget=is_within,
            usage=usage,
            config=self.config,
            warning_message=warning,
            should_compress=should_compress,
            usage_ratio=usage_ratio,
        )

        # Emit progress event for warnings
        if warning and self._on_progress:
            from harness.types import ProgressEvent
            event_type = ProgressEventType.ERROR if not is_within else ProgressEventType.STATE_CHANGE
            self._on_progress(ProgressEvent(
                type=event_type,
                message=warning,
                data={
                    "usage_ratio": usage_ratio,
                    "total_tokens": usage.total_tokens,
                    "limit": self.config.max_tokens_per_session,
                },
            ))

        return status

    def check_iteration(self, iteration: int, session_id: str | None = None) -> bool:
        """
        Check if iteration count is within limit.

        Args:
            iteration: Current iteration number
            session_id: Optional session ID

        Returns:
            True if within limit
        """
        if iteration >= self.config.max_iterations_per_request:
            logger.warning(
                f"Iteration limit reached: {iteration}/{self.config.max_iterations_per_request}"
            )
            return False
        return True

    def record_usage(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_call: bool = False,
    ) -> TokenUsage:
        """
        Record usage for a session.

        Args:
            session_id: Session to record for
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
            tool_call: Whether a tool call was made

        Returns:
            Updated TokenUsage for the session
        """
        if session_id not in self._session_usage:
            self._session_usage[session_id] = TokenUsage()

        usage = self._session_usage[session_id]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        if tool_call:
            usage.tool_calls += 1

        return usage

    def get_session_usage(self, session_id: str) -> TokenUsage:
        """
        Get usage for a session.

        Args:
            session_id: Session ID

        Returns:
            TokenUsage for the session (or empty if not tracked)
        """
        return self._session_usage.get(session_id, TokenUsage())

    def reset_session(self, session_id: str) -> None:
        """
        Reset usage tracking for a session.

        Args:
            session_id: Session to reset
        """
        self._session_usage.pop(session_id, None)
        self._request_iterations.pop(session_id, None)

    def should_stop(self, usage: TokenUsage) -> bool:
        """
        Check if execution should stop due to budget.

        Args:
            usage: Current usage

        Returns:
            True if should stop
        """
        status = self.check(usage)
        return not status.is_within_budget and not status.should_compress

    def should_compress(self, usage: TokenUsage) -> bool:
        """
        Check if context should be compressed.

        Args:
            usage: Current usage

        Returns:
            True if compression needed
        """
        status = self.check(usage)
        return status.should_compress

    @property
    def stats(self) -> dict[str, Any]:
        """Get controller statistics."""
        return {
            "config": {
                "max_tokens_per_session": self.config.max_tokens_per_session,
                "max_tool_calls_per_session": self.config.max_tool_calls_per_session,
                "max_iterations_per_request": self.config.max_iterations_per_request,
                "warning_threshold": self.config.warning_threshold,
            },
            "sessions_tracked": len(self._session_usage),
        }
