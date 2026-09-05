"""
Core type definitions for Harness SDK.

These types form the foundation of the agent loop, tool system, and memory management.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Progress Events - 进度事件类型
# =============================================================================


class ProgressEventType(Enum):
    """Progress event types for tracking agent execution."""

    LOOP_START = "loop_start"  # Agent 循环开始
    LOOP_END = "loop_end"  # Agent 循环结束
    STATE_CHANGE = "state_change"  # 状态变化
    TOOL_CALL = "tool_call"  # 工具调用开始
    TOOL_RESULT = "tool_result"  # 工具调用结果
    LLM_CALL = "llm_call"  # LLM 调用开始
    LLM_RESPONSE = "llm_response"  # LLM 响应接收
    TEXT_CHUNK = "text_chunk"  # 流式文本块
    ITERATION = "iteration"  # 迭代计数
    ERROR = "error"  # 错误发生
    STREAM_BACKPRESSURE = "stream_backpressure"  # 流式输出背压
    STUCK_DETECTED = "stuck_detected"  # 检测到停滞状态
    ROUTER_DECISION = "router_decision"  # 路由决策（CPU Router）


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

    IDLE = "idle"  # 空闲，等待输入
    BUILDING_CONTEXT = "building"  # 构建上下文
    CALLING_LLM = "calling"  # 调用 LLM
    PARSING_RESPONSE = "parsing"  # 解析响应
    EXECUTING_TOOLS = "executing"  # 执行工具
    COMPLETED = "completed"  # 完成
    ERROR = "error"  # 错误状态
    INTERRUPTED = "interrupted"  # 被中断
    STUCK = "stuck"  # 陷入停滞


class StopReason(Enum):
    """LLM response stop reason."""

    END_TURN = "end_turn"  # 正常结束
    TOOL_USE = "tool_use"  # 需要工具调用
    MAX_TOKENS = "max_tokens"  # 达到最大 token
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
        result = {
            "role": self.role,
            "content": self.content,
        }
        # Include metadata for tool messages (needed for compatibility mode)
        if self.role == "tool" and self.metadata:
            result["metadata"] = self.metadata
        return result


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (for snapshot)."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            arguments=data.get("arguments", {}),
        )


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_call_id: str
    success: bool
    content: str
    error: str | None = None
    tool_name: str | None = None  # Tool name for compatibility mode formatting
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

    def __init__(self, message: str, usage: TokenUsage | None = None, limit: int = 0):
        super().__init__(message)
        self.usage = usage
        self.limit = limit


class UserBudgetExceededError(Exception):
    """Raised when user-level budget is exceeded."""

    def __init__(self, message: str, user_id: str = "", limit: int = 0):
        super().__init__(message)
        self.user_id = user_id
        self.limit = limit


class GlobalBudgetExceededError(Exception):
    """Raised when global budget is exceeded."""

    def __init__(self, message: str, current_cost: float = 0, budget: float = 0):
        super().__init__(message)
        self.current_cost = current_cost
        self.budget = budget


class DocumentTooLargeError(Exception):
    """Raised when document size exceeds the configured limit."""

    def __init__(self, filename: str, size: int, limit: int):
        self.filename = filename
        self.size = size
        self.limit = limit
        message = (
            f"Document '{filename}' ({size / 1024 / 1024:.1f}MB) exceeds limit "
            f"({limit / 1024 / 1024:.1f}MB)"
        )
        super().__init__(message)


@dataclass
class CostConfig:
    """
    Cost control configuration.

    Implements multi-level budget management to prevent runaway costs.

    Session Level:
        max_tokens_per_session: Maximum tokens allowed per session
        max_tool_calls_per_session: Maximum tool calls per session
        max_iterations_per_request: Maximum iterations per request

    User Level:
        daily_token_limit: Maximum tokens per user per day
        hourly_request_limit: Maximum requests per user per hour

    Global Level:
        global_daily_budget_usd: Global daily budget in USD
        auto_throttle: Enable automatic throttling when budget is low
        fallback_model: Model to switch to when budget is tight
        context_reduction_ratio: Ratio to reduce context when budget is tight
    """

    # Session level
    max_tokens_per_session: int = 1_000_000
    max_tool_calls_per_session: int = 500
    max_iterations_per_request: int = 20

    # User level
    daily_token_limit: int = 10_000_000
    hourly_request_limit: int = 100

    # Global level
    global_daily_budget_usd: float = 100.0
    auto_throttle: bool = True
    fallback_model: str = "claude-haiku-4-5"
    context_reduction_ratio: float = 0.5

    # Common settings
    warning_threshold: float = 0.8
    action_on_exceed: str = "stop"  # stop | compress | warn | downgrade

    def __post_init__(self):
        if self.action_on_exceed not in ("stop", "compress", "warn", "downgrade"):
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
            return (
                False,
                f"Token limit exceeded: {self.total_tokens}/{config.max_tokens_per_session}",
            )

        if self.tool_calls > config.max_tool_calls_per_session:
            return (
                False,
                f"Tool call limit exceeded: {self.tool_calls}/{config.max_tool_calls_per_session}",
            )

        # Check warning threshold
        usage_ratio = self.total_tokens / config.max_tokens_per_session
        if usage_ratio >= config.warning_threshold:
            return True, f"Budget warning: {usage_ratio:.0%} of session budget used"

        return True, None


@dataclass
class UserUsage:
    """User-level usage statistics."""

    user_id: str
    daily_tokens: int = 0
    hourly_requests: int = 0
    date: str = ""  # YYYY-MM-DD format
    hour: int = 0  # 0-23

    def check_budget(self, config: CostConfig) -> tuple[bool, str | None]:
        """
        Check if user usage exceeds budget.

        Args:
            config: Cost configuration

        Returns:
            Tuple of (is_within_budget, warning_message)
        """
        if self.daily_tokens > config.daily_token_limit:
            return (
                False,
                f"Daily token limit exceeded: {self.daily_tokens}/{config.daily_token_limit}",
            )

        if self.hourly_requests > config.hourly_request_limit:
            return (
                False,
                f"Hourly request limit exceeded: "
                f"{self.hourly_requests}/{config.hourly_request_limit}",
            )

        # Check warning threshold
        usage_ratio = self.daily_tokens / config.daily_token_limit
        if usage_ratio >= config.warning_threshold:
            return True, f"User budget warning: {usage_ratio:.0%} of daily budget used"

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


# =============================================================================
# Streaming Types - 流式输出类型
# =============================================================================


class ChunkType(Enum):
    """Types of chunks in streaming output."""

    TEXT = "text"  # 文本内容
    TOOL_CALL_START = "tool_start"  # 工具调用开始
    TOOL_CALL_DELTA = "tool_delta"  # 工具调用增量
    TOOL_CALL_END = "tool_end"  # 工具调用结束
    THINKING = "thinking"  # 思考过程（Claude）
    ERROR = "error"  # 错误
    DONE = "done"  # 流结束


@dataclass
class Chunk:
    """
    A chunk of streaming output.

    Attributes:
        type: Chunk type
        content: Text content (for TEXT/THINKING/ERROR)
        tool_call_id: Tool call ID (for TOOL_CALL_* types)
        tool_name: Tool name (for TOOL_CALL_START)
        tool_arguments: Partial arguments (for TOOL_CALL_DELTA)
        metadata: Additional metadata
    """

    type: ChunkType
    content: str = ""
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_text(self) -> bool:
        """Check if this is a text chunk."""
        return self.type == ChunkType.TEXT

    def is_tool_call(self) -> bool:
        """Check if this is a tool call chunk."""
        return self.type in (
            ChunkType.TOOL_CALL_START,
            ChunkType.TOOL_CALL_DELTA,
            ChunkType.TOOL_CALL_END,
        )

    def is_done(self) -> bool:
        """Check if this is the final chunk."""
        return self.type == ChunkType.DONE


# =============================================================================
# Loop Snapshot - 循环快照（用于中断恢复）
# =============================================================================


@dataclass
class LoopSnapshot:
    """
    Snapshot of agent loop state for interruption and recovery.

    Captures all state needed to resume execution after interruption.

    Attributes:
        session_id: Session identifier
        messages: All messages in conversation
        current_iteration: Current iteration number
        pending_tool_calls: Tool calls waiting to be executed
        last_llm_response: Last response from LLM
        created_at: When snapshot was created
    """

    session_id: str
    messages: list[Message] = field(default_factory=list)
    current_iteration: int = 0
    pending_tool_calls: list[ToolCall] = field(default_factory=list)
    last_llm_response: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return {
            "session_id": self.session_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content if isinstance(m.content, str) else str(m.content),
                }
                for m in self.messages
            ],
            "current_iteration": self.current_iteration,
            "pending_tool_calls": [tc.to_dict() for tc in self.pending_tool_calls],
            "last_llm_response": self.last_llm_response,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopSnapshot:
        """Deserialize snapshot from dictionary."""
        return cls(
            session_id=data["session_id"],
            messages=[Message(**m) for m in data.get("messages", [])],
            current_iteration=data.get("current_iteration", 0),
            pending_tool_calls=[
                ToolCall.from_dict(tc) for tc in data.get("pending_tool_calls", [])
            ],
            last_llm_response=data.get("last_llm_response"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
        )


# =============================================================================
# Lifecycle Hooks - 生命周期钩子
# =============================================================================


class HookPoint(Enum):
    """
    Points in the agent loop where hooks can be triggered.

    Hooks allow custom logic to be injected at key points:
    - Before/after LLM calls
    - Before/after tool execution
    - On errors
    - On loop start/end
    - On exit attempts (for Ralph Loop)
    """

    BEFORE_LLM_CALL = "before_llm_call"  # LLM 调用前
    AFTER_LLM_CALL = "after_llm_call"  # LLM 调用后
    BEFORE_TOOL_EXECUTE = "before_tool_execute"  # 工具执行前
    AFTER_TOOL_EXECUTE = "after_tool_execute"  # 工具执行后
    ON_ERROR = "on_error"  # 错误发生时
    ON_LOOP_START = "on_loop_start"  # 循环开始
    ON_LOOP_END = "on_loop_end"  # 循环结束
    ON_EXIT_ATTEMPT = "on_exit_attempt"  # 尝试退出时（Ralph Loop）


class HookAction(Enum):
    """
    Actions a hook can request.

    - CONTINUE: Normal execution continues
    - ABORT: Stop execution immediately
    - RETRY: Retry the current operation
    - INJECT_MESSAGE: Add a message to the context
    - MODIFY_ARGS: Modify tool arguments (before execution)
    - MODIFY_RESULT: Modify tool result (after execution)
    - REINJECT: Clear context and reinject a prompt (for Ralph Loop)
    """

    CONTINUE = "continue"
    ABORT = "abort"
    RETRY = "retry"
    INJECT_MESSAGE = "inject_message"
    MODIFY_ARGS = "modify_args"
    MODIFY_RESULT = "modify_result"
    REINJECT = "reinject"


@dataclass
class HookContext:
    """
    Context passed to hooks during execution.

    Contains all relevant information about the current state
    of the agent loop at the hook point.

    Attributes:
        hook_point: Which hook point triggered this
        session_id: Current session ID
        iteration: Current iteration number
        tool_name: Tool name (for tool hooks)
        tool_args: Tool arguments (for BEFORE_TOOL_EXECUTE)
        tool_result: Tool result (for AFTER_TOOL_EXECUTE)
        llm_response: LLM response (for AFTER_LLM_CALL)
        error: Exception (for ON_ERROR)
        messages: Current messages (optional)
        metadata: Additional context data
    """

    hook_point: HookPoint
    session_id: str
    iteration: int = 0
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: ToolResult | None = None
    llm_response: LLMResponse | None = None
    error: Exception | None = None
    messages: list[Message] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """
    Result returned by a hook.

    Controls what happens after the hook executes.

    Attributes:
        action: What action to take
        modified_args: New arguments (for MODIFY_ARGS)
        modified_result: New result (for MODIFY_RESULT)
        inject_message: Message to add to context (for INJECT_MESSAGE)
        delay_seconds: Delay before retry (for RETRY)
        clear_context: Whether to clear context (for Ralph Loop)
        metadata: Additional data (e.g., abort reason)
    """

    action: HookAction = HookAction.CONTINUE
    modified_args: dict[str, Any] | None = None
    modified_result: ToolResult | None = None
    inject_message: Message | None = None
    delay_seconds: float = 0.0
    clear_context: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def continue_(cls) -> HookResult:
        """Convenience method for continue action."""
        return cls(action=HookAction.CONTINUE)

    @classmethod
    def abort(cls, reason: str = "") -> HookResult:
        """Convenience method for abort action."""
        return cls(action=HookAction.ABORT, metadata={"reason": reason} if reason else {})

    @classmethod
    def inject(cls, message: Message) -> HookResult:
        """Convenience method for inject message action."""
        return cls(action=HookAction.INJECT_MESSAGE, inject_message=message)

    # Alias for consistency
    inject_message = inject

    @classmethod
    def modify_args(cls, args: dict[str, Any]) -> HookResult:
        """Convenience method for modify args action."""
        return cls(action=HookAction.MODIFY_ARGS, modified_args=args)

    @classmethod
    def modify_result(cls, result: ToolResult) -> HookResult:
        """Convenience method for modify result action."""
        return cls(action=HookAction.MODIFY_RESULT, modified_result=result)


# Hook callback type
HookCallback = Callable[[HookContext], HookResult | Coroutine[Any, Any, HookResult]]
