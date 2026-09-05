"""
Step Budget Controller - Per-task iteration and tool call limits.

Provides fine-grained budget control to prevent runaway agent loops
while allowing legitimate long-running tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BudgetLevel(Enum):
    """
    Budget status levels.

    - NORMAL: Within safe limits
    - WARNING: Approaching limits (warning_threshold)
    - CRITICAL: Near limits (critical_threshold)
    - EXCEEDED: Budget exceeded, action required
    """

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class StepBudgetConfig:
    """
    Configuration for step-based budget control.

    This differs from CostConfig which tracks token usage.
    StepBudget tracks iteration and tool call counts per task.

    Attributes:
        max_iterations_per_task: Maximum iterations allowed per task (default 50)
        max_tool_calls_per_step: Maximum tool calls per single LLM response (default 10)
        max_tool_calls_per_task: Maximum total tool calls per task (default 200)
        warning_threshold: Ratio to trigger warning (default 0.8)
        critical_threshold: Ratio to trigger critical (default 0.95)
        action_on_exceed: Action when budget exceeded (stop | warn | throttle)
        throttle_ratio: Ratio of budget to use when throttling (default 0.5)
    """

    max_iterations_per_task: int = 50
    max_tool_calls_per_step: int = 10
    max_tool_calls_per_task: int = 200
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95
    action_on_exceed: str = "stop"  # stop | warn | throttle
    throttle_ratio: float = 0.5  # When throttling, use this ratio of remaining budget

    def __post_init__(self):
        """Validate configuration."""
        if self.max_iterations_per_task < 1:
            raise ValueError("max_iterations_per_task must be at least 1")
        if self.max_tool_calls_per_step < 1:
            raise ValueError("max_tool_calls_per_step must be at least 1")
        if self.max_tool_calls_per_task < self.max_tool_calls_per_step:
            raise ValueError("max_tool_calls_per_task must be >= max_tool_calls_per_step")
        if not 0 < self.warning_threshold < 1:
            raise ValueError("warning_threshold must be between 0 and 1")
        if not 0 < self.critical_threshold <= 1:
            raise ValueError("critical_threshold must be between 0 and 1")
        if self.warning_threshold >= self.critical_threshold:
            raise ValueError("warning_threshold must be < critical_threshold")
        if self.action_on_exceed not in ("stop", "warn", "throttle"):
            raise ValueError(f"Invalid action_on_exceed: {self.action_on_exceed}")
        if not 0 < self.throttle_ratio <= 1:
            raise ValueError("throttle_ratio must be between 0 and 1")


@dataclass
class StepUsage:
    """
    Current step budget usage.

    Attributes:
        iterations: Number of iterations completed
        tool_calls_total: Total tool calls in this task
        tool_calls_this_step: Tool calls in current step (current LLM response)
        tool_calls_by_tool: Per-tool call counts
        task_start_time: When the task started
        last_step_time: When the last step started
    """

    iterations: int = 0
    tool_calls_total: int = 0
    tool_calls_this_step: int = 0
    tool_calls_by_tool: dict[str, int] = field(default_factory=dict)
    task_start_time: datetime = field(default_factory=datetime.now)
    last_step_time: datetime = field(default_factory=datetime.now)

    def reset_step(self) -> None:
        """Reset step-level counters (after each LLM response)."""
        self.tool_calls_this_step = 0
        self.last_step_time = datetime.now()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "iterations": self.iterations,
            "tool_calls_total": self.tool_calls_total,
            "tool_calls_this_step": self.tool_calls_this_step,
            "tool_calls_by_tool": self.tool_calls_by_tool,
            "task_start_time": self.task_start_time.isoformat(),
            "last_step_time": self.last_step_time.isoformat(),
        }


@dataclass
class BudgetCheckResult:
    """
    Result of a budget check.

    Attributes:
        level: Current budget level
        is_within_budget: True if budget not exceeded
        message: Human-readable status message
        remaining_iterations: Remaining iterations allowed
        remaining_tool_calls: Remaining tool calls allowed
        should_stop: True if execution should stop
        throttle_limit: Optional throttle limit for tool calls
    """

    level: BudgetLevel
    is_within_budget: bool
    message: str
    remaining_iterations: int = 0
    remaining_tool_calls: int = 0
    should_stop: bool = False
    throttle_limit: int | None = None


class StepBudgetController:
    """
    Controller for step-based budget management.

    Features:
    - Per-task iteration limits
    - Per-step tool call limits (prevents LLM from calling too many tools at once)
    - Per-task tool call limits
    - Warning and critical thresholds
    - Throttling support for graceful degradation
    """

    def __init__(self, config: StepBudgetConfig | None = None):
        """Initialize the controller."""
        self.config = config or StepBudgetConfig()
        self._usage = StepUsage()
        self._task_active = False
        self._warned = False  # Track if warning was already emitted

    def start_task(self) -> None:
        """
        Start a new task.

        Resets all counters and marks task as active.
        """
        self._usage = StepUsage()
        self._task_active = True
        self._warned = False
        logger.debug("Step budget: Task started")

    def end_task(self) -> StepUsage:
        """
        End the current task.

        Returns:
            Final usage statistics
        """
        self._task_active = False
        logger.debug(
            f"Step budget: Task ended with {self._usage.iterations} iterations, "
            f"{self._usage.tool_calls_total} tool calls"
        )
        return self._usage

    def advance_iteration(self) -> BudgetCheckResult:
        """
        Advance iteration count and check budget.

        Should be called after each iteration completes.

        Returns:
            BudgetCheckResult with current status
        """
        if not self._task_active:
            logger.warning("Step budget: advance_iteration called without active task")
            return BudgetCheckResult(
                level=BudgetLevel.NORMAL,
                is_within_budget=True,
                message="No active task",
            )

        self._usage.iterations += 1
        self._usage.reset_step()  # Reset step counters for new iteration

        return self._check_budget()

    def record_tool_call(self, tool_name: str) -> BudgetCheckResult:
        """
        Record a tool call and check budget.

        Args:
            tool_name: Name of the tool being called

        Returns:
            BudgetCheckResult with current status
        """
        if not self._task_active:
            logger.warning("Step budget: record_tool_call called without active task")
            return BudgetCheckResult(
                level=BudgetLevel.NORMAL,
                is_within_budget=True,
                message="No active task",
            )

        self._usage.tool_calls_total += 1
        self._usage.tool_calls_this_step += 1

        # Track per-tool calls
        if tool_name not in self._usage.tool_calls_by_tool:
            self._usage.tool_calls_by_tool[tool_name] = 0
        self._usage.tool_calls_by_tool[tool_name] += 1

        return self._check_budget()

    def check_before_tool_call(self, tool_name: str = "") -> BudgetCheckResult:
        """
        Check budget before executing a tool call.

        This is a pre-check that doesn't increment counters.
        Use this to decide whether to proceed with a tool call.

        Args:
            tool_name: Name of the tool to be called (optional, for logging)

        Returns:
            BudgetCheckResult with projection based on current usage
        """
        if not self._task_active:
            logger.warning("Step budget: check_before_tool_call called without active task")
            return BudgetCheckResult(
                level=BudgetLevel.NORMAL,
                is_within_budget=True,
                message="No active task",
            )

        # Project next call
        projected_total = self._usage.tool_calls_total + 1
        projected_step = self._usage.tool_calls_this_step + 1

        logger.info(
            f"Step budget check: tool={tool_name}, "
            f"projected_step={projected_step}/{self.config.max_tool_calls_per_step}, "
            f"projected_total={projected_total}/{self.config.max_tool_calls_per_task}"
        )

        # Check step limit first (more restrictive)
        if projected_step > self.config.max_tool_calls_per_step:
            logger.warning(
                f"Step budget exceeded: {projected_step}/{self.config.max_tool_calls_per_step}"
            )
            return BudgetCheckResult(
                level=BudgetLevel.EXCEEDED,
                is_within_budget=False,
                message=(
                    f"Step tool call limit exceeded: {projected_step}/"
                    f"{self.config.max_tool_calls_per_step}"
                ),
                should_stop=True,
            )

        # Check total limit
        return self._check_budget_projected(projected_total)

    def _check_budget(self) -> BudgetCheckResult:
        """
        Check current budget status.

        Returns:
            BudgetCheckResult with current status
        """
        # Check iteration limit
        iteration_ratio = self._usage.iterations / self.config.max_iterations_per_task
        tool_ratio = self._usage.tool_calls_total / self.config.max_tool_calls_per_task
        step_ratio = self._usage.tool_calls_this_step / self.config.max_tool_calls_per_step

        # Determine level (use the highest ratio)
        max_ratio = max(iteration_ratio, tool_ratio, step_ratio)

        if max_ratio >= 1.0:
            level = BudgetLevel.EXCEEDED
        elif max_ratio >= self.config.critical_threshold:
            level = BudgetLevel.CRITICAL
        elif max_ratio >= self.config.warning_threshold:
            level = BudgetLevel.WARNING
        else:
            level = BudgetLevel.NORMAL

        # Determine action
        remaining_iterations = self.config.max_iterations_per_task - self._usage.iterations
        remaining_tool_calls = self.config.max_tool_calls_per_task - self._usage.tool_calls_total

        should_stop = False
        throttle_limit = None

        if level == BudgetLevel.EXCEEDED:
            if self.config.action_on_exceed == "stop":
                should_stop = True
            elif self.config.action_on_exceed == "throttle":
                throttle_limit = max(1, int(remaining_tool_calls * self.config.throttle_ratio))

        # Generate message
        if level == BudgetLevel.NORMAL:
            message = (
                f"Budget OK: {self._usage.iterations}/{self.config.max_iterations_per_task} "
                f"iterations, {self._usage.tool_calls_total}/"
                f"{self.config.max_tool_calls_per_task} tool calls"
            )
        elif level == BudgetLevel.WARNING:
            message = f"Budget warning: {max_ratio:.0%} used"
        elif level == BudgetLevel.CRITICAL:
            message = f"Budget critical: {max_ratio:.0%} used, consider stopping"
        else:  # EXCEEDED
            message = (
                f"Budget exceeded: iterations={self._usage.iterations}, "
                f"tool_calls={self._usage.tool_calls_total}"
            )

        return BudgetCheckResult(
            level=level,
            is_within_budget=level != BudgetLevel.EXCEEDED
            or self.config.action_on_exceed != "stop",
            message=message,
            remaining_iterations=remaining_iterations,
            remaining_tool_calls=remaining_tool_calls,
            should_stop=should_stop,
            throttle_limit=throttle_limit,
        )

    def _check_budget_projected(self, projected_tool_calls: int) -> BudgetCheckResult:
        """
        Check budget with projected tool calls.

        Args:
            projected_tool_calls: Projected total tool calls

        Returns:
            BudgetCheckResult with projected status
        """
        iteration_ratio = self._usage.iterations / self.config.max_iterations_per_task
        tool_ratio = projected_tool_calls / self.config.max_tool_calls_per_task

        max_ratio = max(iteration_ratio, tool_ratio)

        if max_ratio >= 1.0:
            level = BudgetLevel.EXCEEDED
        elif max_ratio >= self.config.critical_threshold:
            level = BudgetLevel.CRITICAL
        elif max_ratio >= self.config.warning_threshold:
            level = BudgetLevel.WARNING
        else:
            level = BudgetLevel.NORMAL

        remaining_iterations = self.config.max_iterations_per_task - self._usage.iterations
        remaining_tool_calls = self.config.max_tool_calls_per_task - projected_tool_calls

        should_stop = False
        throttle_limit = None

        if level == BudgetLevel.EXCEEDED:
            if self.config.action_on_exceed == "stop":
                should_stop = True
            elif self.config.action_on_exceed == "throttle":
                throttle_limit = max(1, int(remaining_tool_calls * self.config.throttle_ratio))

        message = (
            f"Projected budget: {projected_tool_calls}/"
            f"{self.config.max_tool_calls_per_task} tool calls"
        )

        return BudgetCheckResult(
            level=level,
            is_within_budget=level != BudgetLevel.EXCEEDED
            or self.config.action_on_exceed != "stop",
            message=message,
            remaining_iterations=remaining_iterations,
            remaining_tool_calls=remaining_tool_calls,
            should_stop=should_stop,
            throttle_limit=throttle_limit,
        )

    def get_usage_report(self) -> dict[str, Any]:
        """
        Get detailed usage report.

        Returns:
            Dictionary with usage statistics and budget info
        """
        remaining_iterations = self.config.max_iterations_per_task - self._usage.iterations
        remaining_tool_calls = self.config.max_tool_calls_per_task - self._usage.tool_calls_total

        return {
            "iterations": {
                "used": self._usage.iterations,
                "limit": self.config.max_iterations_per_task,
                "remaining": remaining_iterations,
                "percentage": self._usage.iterations / self.config.max_iterations_per_task * 100,
            },
            "tool_calls": {
                "used": self._usage.tool_calls_total,
                "limit": self.config.max_tool_calls_per_task,
                "remaining": remaining_tool_calls,
                "percentage": self._usage.tool_calls_total
                / self.config.max_tool_calls_per_task
                * 100,
                "this_step": self._usage.tool_calls_this_step,
                "step_limit": self.config.max_tool_calls_per_step,
            },
            "by_tool": self._usage.tool_calls_by_tool,
            "task_active": self._task_active,
            "config": {
                "max_iterations_per_task": self.config.max_iterations_per_task,
                "max_tool_calls_per_step": self.config.max_tool_calls_per_step,
                "max_tool_calls_per_task": self.config.max_tool_calls_per_task,
                "action_on_exceed": self.config.action_on_exceed,
            },
        }

    def get_usage(self) -> StepUsage:
        """
        Get current usage object.

        Returns:
            Current StepUsage
        """
        return self._usage
