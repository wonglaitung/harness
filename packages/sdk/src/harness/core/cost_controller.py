"""
Cost Controller for managing session budgets.

Prevents runaway costs by enforcing token and tool call limits.
Supports multi-level budget management: session, user, and global.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.types import (
    CostConfig,
    GlobalBudgetExceededError,
    ProgressEventType,
    TokenUsage,
    UserBudgetExceededError,
    UserUsage,
)

if TYPE_CHECKING:
    from harness.core.cost_storage import CostStorage
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
    should_downgrade: bool = False
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


@dataclass
class UserBudgetStatus:
    """User-level budget status."""
    is_within_budget: bool
    usage: UserUsage
    config: CostConfig
    warning_message: str | None = None
    usage_ratio: float = 0.0


@dataclass
class GlobalBudgetStatus:
    """Global budget status."""
    is_within_budget: bool
    current_cost: float
    budget: float
    warning_message: str | None = None
    should_throttle: bool = False


class CostController:
    """
    Controller for managing multi-level budgets.

    Enforces limits on:
    - Session level: tokens, tool calls, iterations
    - User level: daily tokens, hourly requests
    - Global level: daily budget in USD

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
        storage: "CostStorage | None" = None,
        on_progress: "ProgressCallback | None" = None,
    ):
        self.config = config or CostConfig()
        self._storage = storage
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
        should_downgrade = False

        if not is_within:
            if self.config.action_on_exceed == "compress":
                should_compress = True
                is_within = True
            elif self.config.action_on_exceed == "downgrade":
                should_downgrade = True
                is_within = True

        status = BudgetStatus(
            is_within_budget=is_within,
            usage=usage,
            config=self.config,
            warning_message=warning,
            should_compress=should_compress,
            should_downgrade=should_downgrade,
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

    def check_user_budget(self, user_id: str) -> UserBudgetStatus:
        """
        Check user-level budget.

        Args:
            user_id: User identifier

        Returns:
            UserBudgetStatus with check results
        """
        if not self._storage:
            # No storage configured, skip user-level check
            return UserBudgetStatus(
                is_within_budget=True,
                usage=UserUsage(user_id=user_id),
                config=self.config,
            )

        usage = self._storage.get_user_usage(user_id)
        is_within, warning = usage.check_budget(self.config)
        usage_ratio = usage.daily_tokens / self.config.daily_token_limit if self.config.daily_token_limit > 0 else 0

        return UserBudgetStatus(
            is_within_budget=is_within,
            usage=usage,
            config=self.config,
            warning_message=warning,
            usage_ratio=usage_ratio,
        )

    def check_global_budget(self) -> GlobalBudgetStatus:
        """
        Check global budget.

        Returns:
            GlobalBudgetStatus with check results
        """
        if not self._storage:
            return GlobalBudgetStatus(
                is_within_budget=True,
                current_cost=0,
                budget=self.config.global_daily_budget_usd,
            )

        usage = self._storage.get_global_usage()
        usage_ratio = usage.daily_cost_usd / self.config.global_daily_budget_usd if self.config.global_daily_budget_usd > 0 else 0

        is_within = usage.daily_cost_usd < self.config.global_daily_budget_usd
        should_throttle = (
            self.config.auto_throttle and
            usage_ratio >= 0.8
        )

        warning = None
        if not is_within:
            warning = f"Global budget exceeded: ${usage.daily_cost_usd:.2f}/${self.config.global_daily_budget_usd:.2f}"
        elif should_throttle:
            warning = f"Global budget warning: {usage_ratio:.0%} of daily budget used"

        return GlobalBudgetStatus(
            is_within_budget=is_within,
            current_cost=usage.daily_cost_usd,
            budget=self.config.global_daily_budget_usd,
            warning_message=warning,
            should_throttle=should_throttle,
        )

    def check_all(
        self,
        usage: TokenUsage,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[BudgetStatus, UserBudgetStatus | None, GlobalBudgetStatus | None]:
        """
        Check all budget levels.

        Args:
            usage: Session token usage
            session_id: Session identifier
            user_id: User identifier (optional)

        Returns:
            Tuple of (session_status, user_status, global_status)
        """
        session_status = self.check(usage, session_id)
        user_status = self.check_user_budget(user_id) if user_id else None
        global_status = self.check_global_budget()

        return session_status, user_status, global_status

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
        user_id: str | None = None,
        cost_usd: float = 0.0,
    ) -> TokenUsage:
        """
        Record usage for a session.

        Args:
            session_id: Session to record for
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
            tool_call: Whether a tool call was made
            user_id: Optional user ID for user-level tracking
            cost_usd: Optional cost in USD for global tracking

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

        # Record user-level usage if storage is available
        if self._storage and user_id:
            self._storage.record_user_usage(
                user_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                request=True,
            )

        # Record global usage if storage is available
        if self._storage and cost_usd > 0:
            self._storage.record_global_usage(
                cost_usd=cost_usd,
                tokens=input_tokens + output_tokens,
            )

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

    def should_downgrade(self, usage: TokenUsage) -> bool:
        """
        Check if model should be downgraded.

        Args:
            usage: Current usage

        Returns:
            True if should downgrade
        """
        status = self.check(usage)
        return status.should_downgrade

    def get_fallback_model(self) -> str:
        """Get the fallback model for budget-constrained scenarios."""
        return self.config.fallback_model

    @property
    def stats(self) -> dict[str, Any]:
        """Get controller statistics."""
        return {
            "config": {
                "max_tokens_per_session": self.config.max_tokens_per_session,
                "max_tool_calls_per_session": self.config.max_tool_calls_per_session,
                "max_iterations_per_request": self.config.max_iterations_per_request,
                "daily_token_limit": self.config.daily_token_limit,
                "hourly_request_limit": self.config.hourly_request_limit,
                "global_daily_budget_usd": self.config.global_daily_budget_usd,
                "warning_threshold": self.config.warning_threshold,
            },
            "sessions_tracked": len(self._session_usage),
            "storage_enabled": self._storage is not None,
        }
