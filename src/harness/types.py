"""
Core type definitions for Harness SDK.

These types form the foundation of the agent loop, tool system, and memory management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


# =============================================================================
# Progress Events - 进度事件类型
# =============================================================================

class ProgressEventType(Enum):
    """Progress event types for tracking agent execution."""
    LOOP_START = "loop_start"            # Agent 循环开始
    LOOP_END = "loop_end"                # Agent 循环结束
    STATE_CHANGE = "state_change"        # 状态变化
    TOOL_CALL = "tool_call"              # 工具调用开始
    TOOL_RESULT = "tool_result"          # 工具调用结果
    LLM_CALL = "llm_call"                # LLM 调用开始
    LLM_RESPONSE = "llm_response"        # LLM 响应接收
    ITERATION = "iteration"              # 迭代计数
    ERROR = "error"                      # 错误发生


@dataclass
class ProgressEvent:
    """
    Progress event for tracking agent execution.

    Attributes:
        type: Event type
        message: Human-readable message
        timestamp: When the event occurred
        data: Additional event data (tool name, arguments, timing, etc.)
        duration_ms: Duration in milliseconds (for timed events)
    """
    type: ProgressEventType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        duration = f" ({self.duration_ms:.0f}ms)" if self.duration_ms else ""
        return f"[{ts}] {self.type.value}: {self.message}{duration}"


# Progress callback type
ProgressCallback = Callable[[ProgressEvent], None]


# =============================================================================
# Loop State - 循环状态
# =============================================================================

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


# =============================================================================
# Cost Control - 成本控制
# =============================================================================

class BudgetExceededError(Exception):
    """Raised when session budget is exceeded."""

    def __init__(self, message: str, usage: "TokenUsage | None" = None, limit: int = 0):
        super().__init__(message)
        self.usage = usage
        self.limit = limit


@dataclass
class CostConfig:
    """
    Cost control configuration.

    Implements multi-level budget management to prevent runaway costs.

    Attributes:
        max_tokens_per_session: Maximum tokens allowed per session
        max_tool_calls_per_session: Maximum tool calls per session
        max_iterations_per_request: Maximum iterations per request
        warning_threshold: Ratio at which to emit warning (0.0-1.0)
        action_on_exceed: Action when budget exceeded: "stop", "compress", "warn"
    """
    max_tokens_per_session: int = 1_000_000
    max_tool_calls_per_session: int = 500
    max_iterations_per_request: int = 20
    warning_threshold: float = 0.8
    action_on_exceed: str = "stop"  # stop | compress | warn

    def __post_init__(self):
        if self.action_on_exceed not in ("stop", "compress", "warn"):
            raise ValueError(f"Invalid action_on_exceed: {self.action_on_exceed}")


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    tool_calls: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def check_budget(self, config: CostConfig) -> tuple[bool, str | None]:
        """
        Check if usage exceeds budget.

        Args:
            config: Cost configuration

        Returns:
            Tuple of (is_within_budget, warning_message)
        """
        if self.total_tokens > config.max_tokens_per_session:
            return False, f"Token limit exceeded: {self.total_tokens}/{config.max_tokens_per_session}"

        if self.tool_calls > config.max_tool_calls_per_session:
            return False, f"Tool call limit exceeded: {self.tool_calls}/{config.max_tool_calls_per_session}"

        # Check warning threshold
        usage_ratio = self.total_tokens / config.max_tokens_per_session
        if usage_ratio >= config.warning_threshold:
            return True, f"Budget warning: {usage_ratio:.0%} of session budget used"

        return True, None


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
