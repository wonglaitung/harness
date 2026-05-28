"""
OpenTelemetry integration for Harness SDK.

Provides observability support for tracing agent execution.
Compatible with Jaeger, Datadog, Langfuse, and other OTel-compatible backends.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from harness.types import ProgressEvent, ProgressEventType

if TYPE_CHECKING:
    from harness.types import Session, TokenUsage

logger = logging.getLogger(__name__)

# Check if OpenTelemetry is available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Span, Status, StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    Span = Any
    Status = Any
    StatusCode = Any


@dataclass
class ObservabilityConfig:
    """Configuration for OpenTelemetry integration."""

    service_name: str = "harness-agent"
    service_version: str = "0.1.0"
    enabled: bool = True
    export_console: bool = False  # Export to console for debugging
    export_otlp: bool = False  # Export to OTLP endpoint
    otlp_endpoint: str = "http://localhost:4317"  # OTLP gRPC endpoint
    sample_rate: float = 1.0  # 1.0 = sample all traces


class ObservabilityManager:
    """
    Manages OpenTelemetry configuration and tracer provider.

    This is the main entry point for enabling observability in Harness.

    Example:
        >>> # Enable with console export (debugging)
        >>> manager = ObservabilityManager(config=ObservabilityConfig(
        ...     export_console=True
        ... ))
        >>> manager.setup()

        >>> # Enable with OTLP export (production)
        >>> manager = ObservabilityManager(config=ObservabilityConfig(
        ...     export_otlp=True,
        ...     otlp_endpoint="http://jaeger:4317"
        ... ))
        >>> manager.setup()
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        self.config = config or ObservabilityConfig()
        self._tracer_provider: Any = None
        self._tracer: Any = None
        self._setup_complete = False

    @property
    def is_enabled(self) -> bool:
        """Check if observability is enabled and available."""
        return self.config.enabled and OTEL_AVAILABLE

    @property
    def tracer(self) -> Any:
        """Get the tracer instance."""
        if not self.is_enabled:
            return None
        if self._tracer is None:
            self._tracer = trace.get_tracer(
                "harness.agent",
                self.config.service_version,
            )
        return self._tracer

    def setup(self) -> bool:
        """
        Set up OpenTelemetry tracing.

        Returns:
            True if setup was successful, False otherwise
        """
        if not self.is_enabled:
            logger.debug("OpenTelemetry is disabled or not available")
            return False

        if self._setup_complete:
            return True

        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
            })

            # Create tracer provider
            self._tracer_provider = TracerProvider(resource=resource)

            # Add exporters
            if self.config.export_console:
                console_exporter = ConsoleSpanExporter()
                self._tracer_provider.add_span_processor(
                    BatchSpanProcessor(console_exporter)
                )

            if self.config.export_otlp:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                        OTLPSpanExporter,
                    )

                    otlp_exporter = OTLPSpanExporter(
                        endpoint=self.config.otlp_endpoint
                    )
                    self._tracer_provider.add_span_processor(
                        BatchSpanProcessor(otlp_exporter)
                    )
                except ImportError:
                    logger.warning(
                        "OTLP exporter not available. "
                        "Install with: pip install opentelemetry-exporter-otlp"
                    )

            # Set global tracer provider
            trace.set_tracer_provider(self._tracer_provider)

            self._setup_complete = True
            logger.info(
                f"OpenTelemetry initialized: service={self.config.service_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the tracer provider."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
            self._setup_complete = False


# Global manager instance
_global_manager: ObservabilityManager | None = None


def get_observability_manager() -> ObservabilityManager:
    """Get the global observability manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ObservabilityManager()
    return _global_manager


def setup_observability(config: ObservabilityConfig | None = None) -> bool:
    """
    Set up global OpenTelemetry tracing.

    Args:
        config: Optional configuration. Uses defaults if not provided.

    Returns:
        True if setup was successful
    """
    global _global_manager
    _global_manager = ObservabilityManager(config)
    return _global_manager.setup()


def get_tracer() -> Any:
    """Get the global tracer."""
    return get_observability_manager().tracer


class SpanBuilder:
    """
    Builder for creating spans with attributes.

    Provides a fluent interface for adding attributes and events to spans.

    Example:
        >>> with SpanBuilder("agent_loop.run") as span:
        ...     span.set_attr("session.id", session_id)
        ...     span.set_attr("prompt.length", len(prompt))
        ...     # ... do work ...
    """

    def __init__(self, name: str, parent: Span | None = None):
        self.name = name
        self.parent = parent
        self._span: Span | None = None
        self._start_time: float | None = None

    def __enter__(self) -> "SpanBuilder":
        tracer = get_tracer()
        if tracer is None:
            return self

        self._start_time = time.time()

        if self.parent:
            # Use parent context
            ctx = trace.set_span_in_context(self.parent)
            self._span = tracer.start_as_current_span(
                self.name,
                context=ctx,
            )
        else:
            self._span = tracer.start_as_current_span(self.name)

        self._span.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._span is None:
            return

        if exc_type is not None:
            self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self._span.record_exception(exc_val)

        self._span.__exit__(exc_type, exc_val, exc_tb)

    def set_attr(self, key: str, value: Any) -> "SpanBuilder":
        """Set an attribute on the span."""
        if self._span:
            self._span.set_attribute(key, value)
        return self

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> "SpanBuilder":
        """Add an event to the span."""
        if self._span:
            self._span.add_event(name, attributes or {})
        return self

    @property
    def span(self) -> Span | None:
        """Get the underlying span."""
        return self._span


@contextmanager
def traced_operation(
    name: str,
    attributes: dict[str, Any] | None = None,
    parent: Span | None = None,
):
    """
    Context manager for tracing an operation.

    Example:
        >>> with traced_operation("llm.call", {"model": "claude-sonnet-4-6"}):
        ...     response = await llm.call(...)
    """
    builder = SpanBuilder(name, parent)
    with builder as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attr(key, value)
        yield span


def trace_progress_event(event: ProgressEvent, span: Span | None = None) -> None:
    """
    Record a progress event as a span event.

    Args:
        event: The progress event to record
        span: Optional parent span. Uses current span if not provided.
    """
    tracer = get_tracer()
    if tracer is None:
        return

    # Create event attributes
    attributes = {
        "event.type": event.type.value,
        "event.message": event.message,
    }

    if event.duration_ms is not None:
        attributes["event.duration_ms"] = event.duration_ms

    if event.data:
        # Add data attributes (flatten simple values)
        for key, value in event.data.items():
            if isinstance(value, (str, int, float, bool)):
                attributes[f"event.{key}"] = value

    if span:
        span.add_event(f"progress.{event.type.value}", attributes)


def create_session_span(session: "Session", parent: Span | None = None) -> SpanBuilder:
    """
    Create a span for a session.

    Args:
        session: The session to create a span for
        parent: Optional parent span

    Returns:
        SpanBuilder for the session span
    """
    return SpanBuilder(
        f"session.{session.id[:8]}",
        parent=parent,
    )


def record_token_usage(usage: "TokenUsage", span: Span | None = None) -> None:
    """
    Record token usage as span attributes.

    Args:
        usage: Token usage to record
        span: Optional span to record on. Uses current span if not provided.
    """
    if span is None:
        return

    span.set_attr("tokens.input", usage.input_tokens)
    span.set_attr("tokens.output", usage.output_tokens)
    span.set_attr("tokens.total", usage.total_tokens)

    if usage.cache_read_tokens > 0:
        span.set_attr("tokens.cache_read", usage.cache_read_tokens)

    if usage.cache_write_tokens > 0:
        span.set_attr("tokens.cache_write", usage.cache_write_tokens)

    if usage.tool_calls > 0:
        span.set_attr("tokens.tool_calls", usage.tool_calls)


# Convenience function to check if tracing is active
def is_tracing() -> bool:
    """Check if OpenTelemetry tracing is active."""
    return OTEL_AVAILABLE and get_tracer() is not None
