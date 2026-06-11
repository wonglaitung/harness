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
    RUN_REQUEST = "run_request"
    INTERRUPT = "interrupt"

    # Server → Client (response types)
    ACK = "ack"
    RUN_RESULT = "run_result"
    STREAM_CHUNK = "stream_chunk"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    ERROR = "error"
    INTERRUPTED = "interrupted"


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


class RunRequest(BaseModel):
    """
    Execution request from client.

    Contains all configuration needed to create an AgentHarness instance
    and execute a task.
    """

    prompt: str
    session_id: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    provider: str = "anthropic"
    base_url: Optional[str] = None
    max_iterations: int = 10
    temperature: float = 1.0
    system_prompt: str = ""
    tool_result_role: str = "tool"


class InterruptRequest(BaseModel):
    """Request to interrupt current execution."""

    pass


# =============================================================================
# Response Types
# =============================================================================


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
