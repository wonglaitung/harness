"""
Prometheus metrics endpoint for Spring Cloud integration.

Exports metrics in Prometheus format for monitoring Agent execution.
Compatible with Spring Cloud's Prometheus scraper.

Metrics exposed:
- harness_loop_iterations_total: Total loop iterations
- harness_tool_calls_total: Total tool calls by tool name and success status
- harness_llm_tokens_total: Total token usage by type (input/output)
- harness_session_duration_seconds: Session duration in seconds
- harness_llm_call_duration_seconds: LLM call duration
- harness_tool_call_duration_seconds: Tool call duration by tool name
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.types import ProgressEvent, TokenUsage

logger = logging.getLogger(__name__)

# Check if Prometheus client is available
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Any
    Gauge = Any
    Histogram = Any
    CollectorRegistry = Any
    REGISTRY = None


@dataclass
class MetricsConfig:
    """Configuration for Prometheus metrics."""

    enabled: bool = True
    prefix: str = "harness"  # Metric name prefix
    # Histogram buckets (in seconds)
    duration_buckets: tuple[float, ...] = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)


class MetricsCollector:
    """
    Collects and exports Prometheus metrics for Agent execution.

    This collector integrates with AgentHarness to track:
    - Loop iterations
    - Tool calls (success/failure)
    - Token usage
    - Execution duration

    Example:
        >>> collector = MetricsCollector()
        >>> collector.setup()
        >>> # ... agent runs ...
        >>> metrics_data = collector.export()  # Prometheus format
    """

    def __init__(self, config: MetricsConfig | None = None):
        self.config = config or MetricsConfig()
        self._setup_complete = False

        # Metric instances
        self._loop_iterations: Counter | None = None
        self._tool_calls: Counter | None = None
        self._llm_tokens: Counter | None = None
        self._session_duration: Histogram | None = None
        self._llm_duration: Histogram | None = None
        self._tool_duration: Histogram | None = None
        self._active_sessions: Gauge | None = None

    @property
    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled and available."""
        return self.config.enabled and PROMETHEUS_AVAILABLE

    def setup(self) -> bool:
        """
        Set up Prometheus metrics.

        Returns:
            True if setup was successful, False otherwise
        """
        if not self.is_enabled:
            logger.debug("Prometheus metrics are disabled or not available")
            return False

        if self._setup_complete:
            return True

        try:
            prefix = self.config.prefix

            # Loop iterations counter
            self._loop_iterations = Counter(
                f"{prefix}_loop_iterations_total",
                "Total number of agent loop iterations",
            )

            # Tool calls counter (with labels)
            self._tool_calls = Counter(
                f"{prefix}_tool_calls_total",
                "Total number of tool calls",
                ["tool", "success"],
            )

            # Token usage counter (with labels)
            self._llm_tokens = Counter(
                f"{prefix}_llm_tokens_total",
                "Total LLM token usage",
                ["type"],  # input, output, cache_read, cache_write
            )

            # Session duration histogram
            self._session_duration = Histogram(
                f"{prefix}_session_duration_seconds",
                "Session duration in seconds",
                buckets=self.config.duration_buckets,
            )

            # LLM call duration histogram
            self._llm_duration = Histogram(
                f"{prefix}_llm_call_duration_seconds",
                "LLM call duration in seconds",
                buckets=self.config.duration_buckets,
            )

            # Tool call duration histogram (with labels)
            self._tool_duration = Histogram(
                f"{prefix}_tool_call_duration_seconds",
                "Tool call duration in seconds",
                ["tool"],
                buckets=self.config.duration_buckets,
            )

            # Active sessions gauge
            self._active_sessions = Gauge(
                f"{prefix}_active_sessions",
                "Number of currently active sessions",
            )

            self._setup_complete = True
            logger.info(f"Prometheus metrics initialized: prefix={prefix}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}")
            return False

    def export(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Metrics data in Prometheus text format
        """
        if not PROMETHEUS_AVAILABLE:
            return ""

        return generate_latest(REGISTRY)

    def get_content_type(self) -> str:
        """Get the Prometheus content type."""
        if not PROMETHEUS_AVAILABLE:
            return "text/plain"
        return CONTENT_TYPE_LATEST

    # =========================================================================
    # Metric recording methods
    # =========================================================================

    def record_iteration(self) -> None:
        """Record a loop iteration."""
        if self._loop_iterations:
            self._loop_iterations.inc()

    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        duration_seconds: float | None = None,
    ) -> None:
        """
        Record a tool call.

        Args:
            tool_name: Name of the tool
            success: Whether the call succeeded
            duration_seconds: Duration of the call (optional)
        """
        if self._tool_calls:
            self._tool_calls.labels(tool=tool_name, success=str(success)).inc()

        if duration_seconds and self._tool_duration:
            self._tool_duration.labels(tool=tool_name).observe(duration_seconds)

    def record_token_usage(self, usage: TokenUsage) -> None:
        """
        Record token usage.

        Args:
            usage: Token usage information
        """
        if self._llm_tokens:
            self._llm_tokens.labels(type="input").inc(usage.input_tokens)
            self._llm_tokens.labels(type="output").inc(usage.output_tokens)

            if usage.cache_read_tokens > 0:
                self._llm_tokens.labels(type="cache_read").inc(usage.cache_read_tokens)

            if usage.cache_write_tokens > 0:
                self._llm_tokens.labels(type="cache_write").inc(usage.cache_write_tokens)

    def record_llm_call(self, duration_seconds: float) -> None:
        """
        Record an LLM call duration.

        Args:
            duration_seconds: Duration of the LLM call
        """
        if self._llm_duration:
            self._llm_duration.observe(duration_seconds)

    def record_session_duration(self, duration_seconds: float) -> None:
        """
        Record session duration.

        Args:
            duration_seconds: Total session duration
        """
        if self._session_duration:
            self._session_duration.observe(duration_seconds)

    def increment_active_sessions(self) -> None:
        """Increment active sessions count."""
        if self._active_sessions:
            self._active_sessions.inc()

    def decrement_active_sessions(self) -> None:
        """Decrement active sessions count."""
        if self._active_sessions:
            self._active_sessions.dec()

    # =========================================================================
    # Progress event handler
    # =========================================================================

    def create_progress_handler(self) -> Callable[[ProgressEvent], None]:
        """
        Create a progress event handler that records metrics.

        Returns:
            A function that can be passed to AgentHarness.run(on_progress=...)

        Example:
            >>> collector = MetricsCollector()
            >>> collector.setup()
            >>> result = await agent.run(
            ...     prompt="...",
            ...     on_progress=collector.create_progress_handler()
            ... )
        """
        _tool_call_start_times: dict[str, float] = {}
        _llm_call_start_time: float | None = None
        _session_start_time: float | None = None

        def handle_event(event: ProgressEvent) -> None:
            event_type = event.type.value

            if event_type == "loop_start":
                _session_start_time = time.time()
                self.increment_active_sessions()

            elif event_type == "loop_end":
                if _session_start_time:
                    duration = time.time() - _session_start_time
                    self.record_session_duration(duration)
                self.decrement_active_sessions()

            elif event_type == "iteration":
                self.record_iteration()

            elif event_type == "llm_call":
                _llm_call_start_time = time.time()

            elif event_type == "llm_response":
                if _llm_call_start_time:
                    duration = time.time() - _llm_call_start_time
                    self.record_llm_call(duration)
                    _llm_call_start_time = None

                # Record token usage if available
                if event.data and "token_usage" in event.data:
                    from harness.types import TokenUsage

                    usage_data = event.data["token_usage"]
                    if isinstance(usage_data, dict):
                        usage = TokenUsage(
                            input_tokens=usage_data.get("input_tokens", 0),
                            output_tokens=usage_data.get("output_tokens", 0),
                        )
                        self.record_token_usage(usage)

            elif event_type == "tool_call":
                tool_name = event.data.get("tool", "unknown") if event.data else "unknown"
                _tool_call_start_times[tool_name] = time.time()

            elif event_type == "tool_result":
                tool_name = event.data.get("tool", "unknown") if event.data else "unknown"
                success = event.data.get("success", True) if event.data else True

                duration = None
                if tool_name in _tool_call_start_times:
                    duration = time.time() - _tool_call_start_times[tool_name]
                    del _tool_call_start_times[tool_name]

                self.record_tool_call(tool_name, success, duration)

        return handle_event


# Global collector instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def setup_metrics(config: MetricsConfig | None = None) -> bool:
    """
    Set up global Prometheus metrics collection.

    Args:
        config: Optional configuration. Uses defaults if not provided.

    Returns:
        True if setup was successful
    """
    global _global_collector
    _global_collector = MetricsCollector(config)
    return _global_collector.setup()


def export_metrics() -> str:
    """Export metrics in Prometheus format."""
    return get_metrics_collector().export()


# ASGI app for /metrics endpoint
def create_metrics_app() -> Any:
    """
    Create an ASGI app for the /metrics endpoint.

    This can be mounted to a FastAPI app:
        >>> app.mount("/metrics", create_metrics_app())

    Returns:
        ASGI application for Prometheus metrics
    """
    if not PROMETHEUS_AVAILABLE:
        # Return a simple fallback app
        async def fallback_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Prometheus client not available. "
                    b"Install with: pip install prometheus-client",
                }
            )

        return fallback_app

    from prometheus_client import make_asgi_app

    return make_asgi_app(REGISTRY)
