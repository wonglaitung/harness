"""
Monitor Service - Orchestrator monitoring and metrics.

This module provides the MonitorService class for:
- Execution history tracking
- Performance metrics collection
- Error tracking
- Status reporting
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.orchestrator.types import ExecutionMetric, OrchestratorConfig, OrchestratorStatus

if TYPE_CHECKING:
    from harness.orchestrator.core import LoopOrchestrator

logger = logging.getLogger(__name__)


class MonitorService:
    """
    Monitoring service for orchestrator.

    Provides unified observability:
    - Execution history: Track all workflow/team/goal executions
    - Performance metrics: Duration, iterations, tokens
    - Error tracking: Log and analyze failures

    Metrics Retention:
    - Keeps last N metrics in memory (configurable)
    - Older metrics are automatically discarded
    - For persistent storage, integrate with external systems
    """

    def __init__(self, orchestrator: LoopOrchestrator, config: OrchestratorConfig | None = None):
        """
        Initialize monitor service.

        Args:
            orchestrator: Parent LoopOrchestrator instance
            config: Orchestrator configuration
        """
        self.orchestrator = orchestrator
        self.config = config or OrchestratorConfig()
        self._metrics: list[ExecutionMetric] = []
        self._running = False

    async def start(self) -> None:
        """Start the monitor service."""
        self._running = True
        logger.info("Monitor service started")

    async def stop(self) -> None:
        """Stop the monitor service."""
        self._running = False
        logger.info("Monitor service stopped")

    def record(self, metric: ExecutionMetric) -> None:
        """
        Record an execution metric.

        Args:
            metric: Execution metric to record
        """
        self._metrics.append(metric)

        # Trim to retention limit
        if len(self._metrics) > self.config.metrics_retention:
            self._metrics = self._metrics[-self.config.metrics_retention :]

        logger.debug(
            f"Recorded metric: {metric.name} ({metric.type}) - "
            f"status={metric.status}, duration={metric.duration_seconds:.2f}s"
        )

    def record_workflow(
        self,
        name: str,
        status: str,
        duration_seconds: float,
        iterations: int = 0,
        tokens_used: int = 0,
    ) -> None:
        """
        Record a workflow execution.

        Args:
            name: Workflow name
            status: Execution status
            duration_seconds: Execution duration
            iterations: Total iterations
            tokens_used: Total tokens
        """
        self.record(
            ExecutionMetric(
                name=name,
                type="workflow",
                status=status,
                duration_seconds=duration_seconds,
                iterations=iterations,
                tokens_used=tokens_used,
            )
        )

    def record_team(
        self,
        name: str,
        status: str,
        duration_seconds: float,
        iterations: int = 0,
        tokens_used: int = 0,
    ) -> None:
        """
        Record a team execution.

        Args:
            name: Team name
            status: Execution status
            duration_seconds: Execution duration
            iterations: Total iterations
            tokens_used: Total tokens
        """
        self.record(
            ExecutionMetric(
                name=name,
                type="team",
                status=status,
                duration_seconds=duration_seconds,
                iterations=iterations,
                tokens_used=tokens_used,
            )
        )

    def record_goal(
        self,
        name: str,
        status: str,
        duration_seconds: float,
        iterations: int = 0,
        tokens_used: int = 0,
    ) -> None:
        """
        Record a goal execution.

        Args:
            name: Goal name
            status: Execution status
            duration_seconds: Execution duration
            iterations: Total iterations
            tokens_used: Total tokens
        """
        self.record(
            ExecutionMetric(
                name=name,
                type="goal",
                status=status,
                duration_seconds=duration_seconds,
                iterations=iterations,
                tokens_used=tokens_used,
            )
        )

    def get_metrics(
        self,
        limit: int = 100,
        type_filter: str | None = None,
    ) -> list[ExecutionMetric]:
        """
        Get recorded metrics.

        Args:
            limit: Maximum number of metrics to return
            type_filter: Filter by type ("workflow", "team", "goal")

        Returns:
            List of metrics (most recent first)
        """
        metrics = self._metrics

        if type_filter:
            metrics = [m for m in metrics if m.type == type_filter]

        return metrics[-limit:]

    def get_summary(self) -> dict[str, Any]:
        """
        Get execution summary statistics.

        Returns:
            Summary dict with totals and averages
        """
        if not self._metrics:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "total_duration_seconds": 0.0,
                "total_tokens": 0,
                "average_duration": 0.0,
            }

        total_duration = sum(m.duration_seconds for m in self._metrics)
        total_tokens = sum(m.tokens_used for m in self._metrics)
        success_count = sum(1 for m in self._metrics if m.status == "success")

        return {
            "total_executions": len(self._metrics),
            "success_rate": success_count / len(self._metrics),
            "total_duration_seconds": total_duration,
            "total_tokens": total_tokens,
            "average_duration": total_duration / len(self._metrics),
            "by_type": self._get_type_breakdown(),
        }

    def _get_type_breakdown(self) -> dict[str, dict[str, Any]]:
        """Get statistics broken down by type."""
        breakdown = {}

        for metric_type in ["workflow", "team", "goal"]:
            type_metrics = [m for m in self._metrics if m.type == metric_type]
            if type_metrics:
                success_count = sum(1 for m in type_metrics if m.status == "success")
                breakdown[metric_type] = {
                    "count": len(type_metrics),
                    "success_rate": success_count / len(type_metrics),
                    "total_duration": sum(m.duration_seconds for m in type_metrics),
                    "total_tokens": sum(m.tokens_used for m in type_metrics),
                }

        return breakdown

    def get_recent_errors(self, limit: int = 10) -> list[ExecutionMetric]:
        """
        Get recent failed executions.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of failed execution metrics
        """
        failed = [m for m in self._metrics if m.status == "failed"]
        return failed[-limit:]

    def get_slowest(
        self,
        limit: int = 10,
        type_filter: str | None = None,
    ) -> list[ExecutionMetric]:
        """
        Get slowest executions.

        Args:
            limit: Maximum number to return
            type_filter: Filter by type

        Returns:
            List of slowest executions
        """
        metrics = self._metrics
        if type_filter:
            metrics = [m for m in metrics if m.type == type_filter]

        sorted_metrics = sorted(metrics, key=lambda m: m.duration_seconds, reverse=True)
        return sorted_metrics[:limit]

    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()
        logger.info("Metrics cleared")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    @property
    def metric_count(self) -> int:
        """Get number of recorded metrics."""
        return len(self._metrics)
