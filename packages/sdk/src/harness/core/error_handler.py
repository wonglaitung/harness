"""
Error handling strategy for agent loop.

Provides intelligent error recovery based on error type.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorAction(Enum):
    """Actions to take when an error occurs."""

    RETRY = "retry"  # Retry the operation
    COMPRESS_CONTEXT = "compress"  # Compress context and retry
    ABORT = "abort"  # Stop execution
    SKIP = "skip"  # Skip and continue
    ESCALATE = "escalate"  # Escalate to user


@dataclass
class ErrorContext:
    """Context for error handling decision."""

    error: Exception
    iteration: int
    tool_name: str | None = None
    attempt: int = 1
    context_tokens: int = 0
    max_tokens: int = 200000
    previous_errors: list[Exception] | None = None

    @property
    def is_context_overflow(self) -> bool:
        """Check if error is due to context overflow."""
        return self.context_tokens > self.max_tokens * 0.9


@dataclass
class ErrorDecision:
    """Decision on how to handle an error."""

    action: ErrorAction
    delay_seconds: float = 0.0
    message: str = ""
    metadata: dict[str, Any] | None = None


class ErrorHandler:
    """
    Intelligent error handler with recovery strategies.

    Maps error types to appropriate recovery actions:
    - RateLimitError → RETRY with exponential backoff
    - ContextTooLongError → COMPRESS_CONTEXT
    - PermissionDeniedError → ABORT
    - TimeoutError → RETRY (max 3 times)
    - NetworkError → RETRY with backoff
    - ToolExecutionError → SKIP or RETRY

    Example:
        >>> handler = ErrorHandler()
        >>> decision = handler.handle(error, context)
        >>> if decision.action == ErrorAction.RETRY:
        ...     await asyncio.sleep(decision.delay_seconds)
        ...     # retry the operation
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Track retry attempts per operation
        self._retry_counts: dict[str, int] = {}

    def handle(self, error: Exception, context: ErrorContext) -> ErrorDecision:
        """
        Determine how to handle an error.

        Args:
            error: The exception that occurred
            context: Context about the error situation

        Returns:
            ErrorDecision with action and parameters
        """
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Check for rate limit errors
        if self._is_rate_limit_error(error_type, error_message):
            return self._handle_rate_limit(context)

        # Check for context overflow
        if self._is_context_error(error_type, error_message, context):
            return self._handle_context_overflow(context)

        # Check for permission errors
        if self._is_permission_error(error_type, error_message):
            return self._handle_permission_error(error, context)

        # Check for timeout errors
        if self._is_timeout_error(error_type, error_message):
            return self._handle_timeout(context)

        # Check for network errors
        if self._is_network_error(error_type, error_message):
            return self._handle_network_error(context)

        # Check for tool errors
        if context.tool_name:
            return self._handle_tool_error(error, context)

        # Default: abort on unknown errors
        return ErrorDecision(
            action=ErrorAction.ABORT,
            message=f"Unhandled error type: {error_type}: {error}",
        )

    def _is_rate_limit_error(self, error_type: str, message: str) -> bool:
        """Check if this is a rate limit error."""
        rate_limit_indicators = [
            "ratelimit",
            "rate_limit",
            "429",
            "too many requests",
            "rate limit",
            "quota exceeded",
        ]
        return "rate" in error_type.lower() or any(
            indicator in message for indicator in rate_limit_indicators
        )

    def _is_context_error(
        self,
        error_type: str,
        message: str,
        context: ErrorContext,
    ) -> bool:
        """Check if this is a context length error."""
        context_indicators = [
            "context",
            "token limit",
            "max_tokens",
            "too long",
            "length",
            "context_length_exceeded",
        ]
        return context.is_context_overflow or any(
            indicator in message for indicator in context_indicators
        )

    def _is_permission_error(self, error_type: str, message: str) -> bool:
        """Check if this is a permission denied error."""
        permission_indicators = [
            "permission",
            "forbidden",
            "403",
            "unauthorized",
            "access denied",
            "not allowed",
        ]
        return "permission" in error_type.lower() or any(
            indicator in message for indicator in permission_indicators
        )

    def _is_timeout_error(self, error_type: str, message: str) -> bool:
        """Check if this is a timeout error."""
        timeout_indicators = [
            "timeout",
            "timed out",
            "deadline",
        ]
        return "timeout" in error_type.lower() or any(
            indicator in message for indicator in timeout_indicators
        )

    def _is_network_error(self, error_type: str, message: str) -> bool:
        """Check if this is a network error."""
        network_indicators = [
            "connection",
            "network",
            "socket",
            "dns",
            "refused",
            "unreachable",
        ]
        return any(
            term in error_type.lower() for term in ["connection", "network", "socket"]
        ) or any(indicator in message for indicator in network_indicators)

    def _handle_rate_limit(self, context: ErrorContext) -> ErrorDecision:
        """Handle rate limit errors with exponential backoff."""
        key = f"ratelimit_{context.iteration}"
        attempts = self._retry_counts.get(key, 0)

        if attempts >= self.max_retries:
            return ErrorDecision(
                action=ErrorAction.ABORT,
                message=f"Rate limit persisted after {attempts} retries",
            )

        # Exponential backoff
        delay = min(self.base_delay * (2**attempts), self.max_delay)
        self._retry_counts[key] = attempts + 1

        return ErrorDecision(
            action=ErrorAction.RETRY,
            delay_seconds=delay,
            message=f"Rate limited, waiting {delay:.1f}s before retry (attempt {attempts + 1})",
        )

    def _handle_context_overflow(self, context: ErrorContext) -> ErrorDecision:
        """Handle context length errors."""
        if context.iteration > 3:
            # Already tried compression multiple times
            return ErrorDecision(
                action=ErrorAction.ABORT,
                message="Context overflow persists after compression attempts",
            )

        return ErrorDecision(
            action=ErrorAction.COMPRESS_CONTEXT,
            message="Context too long, attempting compression",
            metadata={"current_tokens": context.context_tokens},
        )

    def _handle_permission_error(
        self,
        error: Exception,
        context: ErrorContext,
    ) -> ErrorDecision:
        """Handle permission denied errors."""
        return ErrorDecision(
            action=ErrorAction.ABORT,
            message=f"Permission denied: {error}",
            metadata={"tool": context.tool_name},
        )

    def _handle_timeout(self, context: ErrorContext) -> ErrorDecision:
        """Handle timeout errors with retry."""
        key = f"timeout_{context.iteration}"
        attempts = self._retry_counts.get(key, 0)

        if attempts >= self.max_retries:
            return ErrorDecision(
                action=ErrorAction.ABORT,
                message=f"Operation timed out after {attempts} retries",
            )

        delay = min(self.base_delay * (2**attempts), self.max_delay)
        self._retry_counts[key] = attempts + 1

        return ErrorDecision(
            action=ErrorAction.RETRY,
            delay_seconds=delay,
            message=f"Timeout, retrying in {delay:.1f}s (attempt {attempts + 1})",
        )

    def _handle_network_error(self, context: ErrorContext) -> ErrorDecision:
        """Handle network errors with retry."""
        key = f"network_{context.iteration}"
        attempts = self._retry_counts.get(key, 0)

        if attempts >= self.max_retries:
            return ErrorDecision(
                action=ErrorAction.ABORT,
                message=f"Network error persisted after {attempts} retries",
            )

        delay = min(self.base_delay * (2**attempts), self.max_delay)
        self._retry_counts[key] = attempts + 1

        return ErrorDecision(
            action=ErrorAction.RETRY,
            delay_seconds=delay,
            message=f"Network error, retrying in {delay:.1f}s (attempt {attempts + 1})",
        )

    def _handle_tool_error(
        self,
        error: Exception,
        context: ErrorContext,
    ) -> ErrorDecision:
        """Handle tool execution errors."""
        error_message = str(error).lower()

        # Some tool errors are recoverable
        if "not found" in error_message or "does not exist" in error_message:
            return ErrorDecision(
                action=ErrorAction.SKIP,
                message=f"Tool {context.tool_name}: resource not found",
                metadata={"error": str(error)},
            )

        if "invalid" in error_message or "invalid argument" in error_message:
            # Bad arguments, don't retry
            return ErrorDecision(
                action=ErrorAction.SKIP,
                message=f"Tool {context.tool_name}: invalid arguments",
                metadata={"error": str(error)},
            )

        # Other tool errors: try once more
        key = f"tool_{context.tool_name}_{context.iteration}"
        attempts = self._retry_counts.get(key, 0)

        if attempts >= 1:
            return ErrorDecision(
                action=ErrorAction.SKIP,
                message=f"Tool {context.tool_name} failed, skipping",
                metadata={"error": str(error)},
            )

        self._retry_counts[key] = attempts + 1
        return ErrorDecision(
            action=ErrorAction.RETRY,
            delay_seconds=self.base_delay,
            message=f"Tool {context.tool_name} failed, retrying",
        )

    def reset(self) -> None:
        """Reset retry counters."""
        self._retry_counts.clear()
