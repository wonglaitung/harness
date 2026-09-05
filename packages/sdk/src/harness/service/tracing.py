"""
Tracing middleware for Spring Cloud integration.

Extracts TraceContext from HTTP headers (W3C TraceContext format)
and propagates to OpenTelemetry context.

This enables distributed tracing across Spring Cloud Gateway and
Python Agent Service.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Check if OpenTelemetry is available
try:
    from opentelemetry import context, trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OTEL_AVAILABLE = True
    propagator = TraceContextTextMapPropagator()
except ImportError:
    OTEL_AVAILABLE = False
    context = None
    trace = None
    propagator = None


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and propagate TraceContext from Spring Cloud Gateway.

    Spring Cloud Gateway (Sleuth/Micrometer) uses W3C TraceContext format:
    - traceparent: version-trace-id-parent-id-flags
    - tracestate: vendor-specific key-value pairs

    Example header from Spring Cloud:
        traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

    This middleware:
    1. Extracts trace context from incoming headers
    2. Sets it as current OpenTelemetry context
    3. Allows SDK spans to be linked to Spring Cloud traces
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # If OpenTelemetry is not available, just pass through
        if not OTEL_AVAILABLE:
            response = await call_next(request)
            # Still extract trace ID from header if present
            trace_id = request.headers.get("X-B3-TraceId") or request.headers.get("X-Trace-Id")
            if trace_id:
                response.headers["X-Trace-Id"] = trace_id
            return response

        # Extract trace context from headers
        headers = dict(request.headers)

        # Extract using W3C TraceContext format
        ctx = propagator.extract(headers)

        # Attach context for this request
        token = context.attach(ctx)

        try:
            # Get current span for logging
            span = trace.get_current_span()
            if span and span.is_recording():
                # Add request metadata to span
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute("http.route", request.url.path)

                # Extract user context from Gateway headers (if present)
                user_id = request.headers.get("X-User-Id")
                tenant_id = request.headers.get("X-Tenant-Id")

                if user_id:
                    span.set_attribute("user.id", user_id)
                if tenant_id:
                    span.set_attribute("user.tenant_id", tenant_id)

            # Process request
            response = await call_next(request)

            # Add trace ID to response headers for debugging
            span_context = span.get_span_context() if span else None
            if span_context and span_context.is_valid:
                trace_id = format(span_context.trace_id, "032x")
                response.headers["X-Trace-Id"] = trace_id

            return response

        finally:
            # Detach context
            context.detach(token)


def get_trace_id() -> str | None:
    """
    Get current trace ID from OpenTelemetry context.

    Returns:
        Trace ID in hex format, or None if not in a trace.
    """
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span is None:
        return None

    span_context = span.get_span_context()
    if not span_context or not span_context.is_valid:
        return None

    return format(span_context.trace_id, "032x")


def get_span_id() -> str | None:
    """
    Get current span ID from OpenTelemetry context.

    Returns:
        Span ID in hex format, or None if not in a span.
    """
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span is None:
        return None

    span_context = span.get_span_context()
    if not span_context or not span_context.is_valid:
        return None

    return format(span_context.span_id, "016x")
