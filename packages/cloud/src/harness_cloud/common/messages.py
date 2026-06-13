"""
WebSocket message protocol definitions.

This module defines all message types and data structures used for
communication between Frontend, Gateway, and Container Agent.

Reference: packages/cloud/docs/05-messages.md
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    # Client → Server (request types)
    AUTH = "auth"  # Authentication with API credentials
    RUN_REQUEST = "run_request"
    INTERRUPT = "interrupt"
    PING = "ping"  # Heartbeat request

    # Server → Client (response types)
    ACK = "ack"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    RUN_RESULT = "run_result"
    STREAM_CHUNK = "stream_chunk"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    PONG = "pong"  # Heartbeat response


class MessageEnvelope(BaseModel):
    """
    Message wrapper for all WebSocket messages.

    All messages follow this envelope format for consistency.
    """

    type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None


# =============================================================================
# Request Types
# =============================================================================


class AuthRequest(BaseModel):
    """
    Authentication request with API credentials.

    Sent once after WebSocket connection. Subsequent run_request
    messages will use the cached credentials.

    Required fields:
    - api_key: API key for the LLM provider

    Optional fields:
    - provider: "anthropic" (default) or "openai"
    - base_url: Custom API endpoint (for OpenAI-compatible APIs)
    - model: Default model to use
    """

    api_key: str
    provider: str = "anthropic"
    base_url: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    max_iterations: int = 10
    temperature: float = 1.0
    system_prompt: str = ""
    tool_result_role: str = "tool"

    def merge_with_request(self, request: "RunRequest") -> "MergedRequest":
        """
        Merge auth config with run request (request can override).

        Args:
            request: Run request with optional overrides

        Returns:
            MergedRequest with final configuration
        """
        return MergedRequest(
            prompt=request.prompt,
            session_id=request.session_id,
            api_key=self.api_key,
            provider=self.provider,
            base_url=self.base_url,
            model=request.model or self.model,
            max_iterations=request.max_iterations or self.max_iterations,
            temperature=request.temperature if request.temperature is not None else self.temperature,
            system_prompt=request.system_prompt or self.system_prompt,
            tool_result_role=self.tool_result_role,
        )


class MergedRequest(BaseModel):
    """
    Merged request combining auth config and run request.

    Used internally by SDKBridge to execute with final configuration.
    """

    prompt: str
    session_id: Optional[str] = None
    api_key: str
    provider: str = "anthropic"
    base_url: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    max_iterations: int = 10
    temperature: float = 1.0
    system_prompt: str = ""
    tool_result_role: str = "tool"


class RunRequest(BaseModel):
    """
    Execution request from client.

    Requires prior authentication via auth message.
    Only prompt and optional session_id are needed.
    """

    prompt: str
    session_id: Optional[str] = None
    # Optional overrides (if not set, uses auth config)
    model: Optional[str] = None
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None


class InterruptRequest(BaseModel):
    """Request to interrupt current execution."""

    pass


# =============================================================================
# Response Types
# =============================================================================


class AuthSuccess(BaseModel):
    """Successful authentication response."""

    provider: str
    model: str


class AuthFailed(BaseModel):
    """Failed authentication response."""

    error: str
    error_code: str  # "INVALID_API_KEY", "UNSUPPORTED_PROVIDER", etc.


class AckResponse(BaseModel):
    """Acknowledgment response."""

    session_id: Optional[str] = None


class RunResult(BaseModel):
    """
    Final execution result.

    Sent when the agent loop completes (successfully, interrupted, or error).
    """

    status: str  # "completed" | "interrupted" | "error"
    content: str
    iterations: int = 0
    token_usage: dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0})
    error: Optional[str] = None


class StreamChunk(BaseModel):
    """Streaming text chunk from LLM response."""

    content: str


class ToolCallEvent(BaseModel):
    """Tool call started event."""

    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(BaseModel):
    """Tool execution result event."""

    tool_name: str
    success: bool
    result: str
    error: Optional[str] = None


class ProgressEventData(BaseModel):
    """Progress event data."""

    event_type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(BaseModel):
    """Error event."""

    error: str
    error_code: Optional[str] = None


class InterruptedResponse(BaseModel):
    """Execution interrupted response."""

    pass


# =============================================================================
# Helper Functions
# =============================================================================


def create_message(msg_type: MessageType, payload: dict[str, Any] | BaseModel) -> dict[str, Any]:
    """
    Create a message dictionary ready for JSON serialization.

    Args:
        msg_type: Message type
        payload: Message payload (dict or Pydantic model)

    Returns:
        Dictionary ready for JSON serialization
    """
    if isinstance(payload, BaseModel):
        payload_dict = payload.model_dump()
    else:
        payload_dict = payload

    return {
        "type": msg_type.value,
        "payload": payload_dict,
    }
