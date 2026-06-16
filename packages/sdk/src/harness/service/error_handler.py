"""
Unified error handling for Spring Cloud integration.

Provides standardized error response format compatible with
Spring Cloud's global exception handling.

Error Response Format:
    {
        "errorCode": "AGENT_400_001",
        "errorMessage": "Invalid input parameter",
        "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
        "timestamp": "2026-06-16T10:30:00Z"
    }
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """
    Standard error codes for Agent Service.

    Format: AGENT_{HTTP_STATUS}_{SEQUENCE}

    This matches Spring Cloud's error code convention.
    """

    # Client errors (4xx)
    INVALID_INPUT = "AGENT_400_001"
    UNAUTHORIZED = "AGENT_401_001"
    FORBIDDEN = "AGENT_403_001"
    NOT_FOUND = "AGENT_404_001"
    TIMEOUT = "AGENT_408_001"
    RATE_LIMITED = "AGENT_429_001"

    # Server errors (5xx)
    INTERNAL_ERROR = "AGENT_500_001"
    LLM_ERROR = "AGENT_502_001"
    TOOL_ERROR = "AGENT_502_002"
    GATEWAY_TIMEOUT = "AGENT_504_001"

    # Business errors
    BUDGET_EXCEEDED = "AGENT_400_002"
    ITERATION_LIMIT = "AGENT_400_003"
    STUCK_DETECTED = "AGENT_400_004"


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Compatible with Spring Cloud's global exception handling.

    Attributes:
        errorCode: Error code for programmatic handling
        errorMessage: Human-readable error message
        traceId: Distributed trace ID for debugging
        timestamp: ISO 8601 timestamp
    """

    errorCode: str
    errorMessage: str
    traceId: str | None = None
    timestamp: str

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


def create_error_response(
    error_code: ErrorCode | str,
    message: str,
    trace_id: str | None = None,
    **extra: Any,
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        error_code: Error code (enum or string)
        message: Human-readable error message
        trace_id: Distributed trace ID (from X-Trace-Id header)
        **extra: Additional context (logged but not in response)

    Returns:
        ErrorResponse instance
    """
    code = error_code.value if isinstance(error_code, ErrorCode) else error_code

    return ErrorResponse(
        errorCode=code,
        errorMessage=message,
        traceId=trace_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# =============================================================================
# Custom Exceptions
# =============================================================================


class AgentServiceError(Exception):
    """Base exception for Agent Service."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class BudgetExceededError(AgentServiceError):
    """Raised when budget is exceeded."""

    def __init__(self, message: str = "Budget exceeded"):
        super().__init__(message, ErrorCode.BUDGET_EXCEEDED)


class IterationLimitError(AgentServiceError):
    """Raised when iteration limit is reached."""

    def __init__(self, iterations: int):
        super().__init__(
            f"Iteration limit reached: {iterations}",
            ErrorCode.ITERATION_LIMIT,
        )


class StuckDetectedError(AgentServiceError):
    """Raised when agent is stuck in a loop."""

    def __init__(self, reason: str = "Agent stuck detected"):
        super().__init__(reason, ErrorCode.STUCK_DETECTED)


class LLMError(AgentServiceError):
    """Raised when LLM call fails."""

    def __init__(self, message: str = "LLM service error"):
        super().__init__(message, ErrorCode.LLM_ERROR)


class ToolExecutionError(AgentServiceError):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, error: str):
        super().__init__(
            f"Tool '{tool_name}' failed: {error}",
            ErrorCode.TOOL_ERROR,
        )
