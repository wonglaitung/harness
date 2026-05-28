"""
Core type definitions for Harness SDK.

These types form the foundation of the agent loop, tool system, and memory management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LoopState(Enum):
    """Agent loop state machine states."""
    IDLE = "idle"                    # 空闲，等待输入
    BUILDING_CONTEXT = "building"    # 构建上下文
    CALLING_LLM = "calling"          # 调用 LLM
    PARSING_RESPONSE = "parsing"     # 解析响应
    EXECUTING_TOOLS = "executing"    # 执行工具
    COMPLETED = "completed"          # 完成
    ERROR = "error"                  # 错误状态
    INTERRUPTED = "interrupted"      # 被中断


class StopReason(Enum):
    """LLM response stop reason."""
    END_TURN = "end_turn"            # 正常结束
    TOOL_USE = "tool_use"            # 需要工具调用
    MAX_TOKENS = "max_tokens"        # 达到最大 token
    STOP_SEQUENCE = "stop_sequence"  # 遇到停止序列


class MessageRole(Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in the conversation."""
    role: str
    content: str | list[dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message after initialization."""
        if self.role not in ("system", "user", "assistant", "tool"):
            raise ValueError(f"Invalid message role: {self.role}")

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for LLM call."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class ToolCall:
    """A tool call request from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "type": "tool_use",
            "id": self.id,
            "name": self.name,
            "input": self.arguments,
        }


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_call_id: str
    success: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for LLM."""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_call_id,
            "content": self.content if self.success else f"Error: {self.error}",
            "is_error": not self.success,
        }


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw_response: dict[str, Any] | None = None

    @property
    def is_tool_use(self) -> bool:
        """Check if response requires tool use."""
        return self.stop_reason == StopReason.TOOL_USE and len(self.tool_calls) > 0

    @property
    def is_complete(self) -> bool:
        """Check if response is complete (no more tools needed)."""
        return self.stop_reason in (
            StopReason.END_TURN,
            StopReason.MAX_TOKENS,
            StopReason.STOP_SEQUENCE,
        )


@dataclass
class Session:
    """A conversation session."""
    id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def clear_messages(self) -> None:
        """Clear all messages in the session."""
        self.messages.clear()
        self.updated_at = datetime.now()

    def get_last_n_messages(self, n: int) -> list[Message]:
        """Get the last N messages."""
        return self.messages[-n:] if n > 0 else []


@dataclass
class LoopResult:
    """Result from agent loop execution."""
    status: LoopState
    session: Session
    messages: list[Message] = field(default_factory=list)
    final_response: str | None = None
    iterations: int = 0
    error: str | None = None
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    @property
    def is_success(self) -> bool:
        """Check if loop completed successfully."""
        return self.status == LoopState.COMPLETED

    @property
    def content(self) -> str:
        """Get the final response content."""
        return self.final_response or ""
