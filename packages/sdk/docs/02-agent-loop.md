# 02 - Agent Loop 代理循环引擎

## 概述

Agent Loop 是 Harness 的心脏，实现了将 LLM 从"单次问答"转变为"持续交互代理"的核心机制。

## 核心循环

### 基础循环模型

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
│                                                              │
│    ┌──────────┐                                              │
│    │  Start   │                                              │
│    └────┬─────┘                                              │
│         │                                                    │
│         ↓                                                    │
│    ┌──────────┐     ┌──────────┐                            │
│    │  Build   │────→│  Call    │                            │
│    │ Context  │     │   LLM    │                            │
│    └──────────┘     └────┬─────┘                            │
│                          │                                  │
│                          ↓                                  │
│                    ┌──────────┐                             │
│                    │  Parse   │                             │
│                    │ Response │                             │
│                    └────┬─────┘                             │
│                          │                                  │
│              ┌───────────┴───────────┐                      │
│              │                       │                      │
│              ↓                       ↓                      │
│        ┌──────────┐           ┌──────────┐                  │
│        │  Tool    │           │  Return  │                  │
│        │  Calls   │           │  Result  │                  │
│        └────┬─────┘           └──────────┘                  │
│             │                                                │
│             ↓                                                │
│       ┌──────────┐                                           │
│       │ Execute  │                                           │
│       │  Tools   │                                           │
│       └────┬─────┘                                           │
│             │                                                │
│             ↓                                                │
│       ┌──────────┐                                           │
│       │  Append  │─────────────────┐                         │
│       │ Results  │                 │                         │
│       └──────────┘                 │                         │
│                                    │                         │
│                                    ↓                         │
│                              Back to Build Context           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 循环状态机

```python
class LoopState(Enum):
    IDLE = "idle"                    # 空闲，等待输入
    BUILDING_CONTEXT = "building"    # 构建上下文
    CALLING_LLM = "calling"          # 调用 LLM
    PARSING_RESPONSE = "parsing"     # 解析响应
    EXECUTING_TOOLS = "executing"    # 执行工具
    COMPLETED = "completed"          # 完成
    ERROR = "error"                  # 错误状态
    INTERRUPTED = "interrupted"      # 被中断
```

## 组件设计

### 2.1 AgentLoop 类

```python
from typing import AsyncIterator, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio

@dataclass
class LoopConfig:
    """Agent Loop 配置"""
    max_iterations: int = 100           # 最大循环次数
    max_tokens_per_call: int = 4096     # 每次调用最大 token
    timeout_per_tool: float = 30.0      # 工具执行超时
    enable_parallel_tools: bool = True  # 并行执行工具
    retry_on_error: int = 3             # 错误重试次数
    retry_delay: float = 1.0            # 重试延迟
    enable_cost_control: bool = True    # 启用成本控制
    cost_config: CostConfig | None = None  # 成本控制配置
    security_config: SecurityConfig | None = None  # 安全配置

class AgentLoop:
    """Agent 循环引擎"""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor,
        context_builder: ContextBuilder,
        config: LoopConfig = None
    ):
        self.llm = llm_client
        self.tools = tool_executor
        self.context = context_builder
        self.config = config or LoopConfig()
        self.state = LoopState.IDLE
        self._interrupt_flag = False

        # 初始化安全组件
        if self.config.security_config:
            sec = self.config.security_config
            self._input_validator = InputValidator(
                max_length=sec.max_input_length,
                check_injection=sec.check_prompt_injection,
            ) if sec.enable_input_validation else None
            self._sanitizer = ResultSanitizer(
                max_length=sec.max_output_length,
            ) if sec.enable_output_sanitization else None
            self._audit_logger = AuditLogger(
                log_dir=sec.audit_log_dir,
                retention_days=sec.audit_retention_days,
            ) if sec.enable_audit_log else None
        else:
            # 默认启用所有安全功能
            self._input_validator = InputValidator()
            self._sanitizer = ResultSanitizer()
            self._audit_logger = AuditLogger()

    async def run(
        self,
        prompt: str,
        session: Session,
        on_chunk: Optional[Callable[[Chunk], None]] = None
    ) -> LoopResult:
        """
        运行代理循环

        Args:
            prompt: 用户输入
            session: 会话对象
            on_chunk: 流式输出回调

        Returns:
            LoopResult: 循环结果
        """
        self.state = LoopState.BUILDING_CONTEXT
        self._interrupt_flag = False

        iteration = 0
        messages = session.messages.copy()
        messages.append(Message(role="user", content=prompt))

        while iteration < self.config.max_iterations:
            # 检查中断
            if self._interrupt_flag:
                self.state = LoopState.INTERRUPTED
                return LoopResult(
                    status=LoopState.INTERRUPTED,
                    messages=messages,
                    iterations=iteration
                )

            # 构建上下文
            self.state = LoopState.BUILDING_CONTEXT
            context = await self.context.build(messages, session)

            # 调用 LLM
            self.state = LoopState.CALLING_LLM
            response = await self._call_llm_with_retry(
                context,
                on_chunk=on_chunk
            )

            # 解析响应
            self.state = LoopState.PARSING_RESPONSE
            messages.append(response.message)

            # 检查是否需要工具调用
            if response.stop_reason == StopReason.TOOL_USE:
                self.state = LoopState.EXECUTING_TOOLS

                # 执行工具
                tool_results = await self._execute_tools(
                    response.tool_calls,
                    session
                )

                # 添加工具结果到消息
                messages.extend(tool_results)
                iteration += 1
                continue

            # 完成
            self.state = LoopState.COMPLETED
            return LoopResult(
                status=LoopState.COMPLETED,
                messages=messages,
                final_response=response.message,
                iterations=iteration
            )

        # 达到最大迭代次数
        return LoopResult(
            status=LoopState.ERROR,
            messages=messages,
            error="Max iterations reached",
            iterations=iteration
        )

    def interrupt(self):
        """中断当前循环"""
        self._interrupt_flag = True

    async def _call_llm_with_retry(
        self,
        context: Context,
        on_chunk: Optional[Callable] = None
    ) -> LLMResponse:
        """带重试的 LLM 调用"""
        last_error = None

        for attempt in range(self.config.retry_on_error):
            try:
                return await self.llm.call(
                    context,
                    stream=on_chunk is not None,
                    on_chunk=on_chunk
                )
            except (RateLimitError, APIError) as e:
                last_error = e
                if attempt < self.config.retry_on_error - 1:
                    await asyncio.sleep(
                        self.config.retry_delay * (2 ** attempt)
                    )

        raise last_error

    async def _execute_tools(
        self,
        tool_calls: List[ToolCall],
        session: Session
    ) -> List[ToolResultMessage]:
        """执行工具调用"""
        if self.config.enable_parallel_tools:
            # 并行执行
            tasks = [
                self.tools.execute(call, session)
                for call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 串行执行
            results = []
            for call in tool_calls:
                result = await self.tools.execute(call, session)
                results.append(result)

        return [
            ToolResultMessage(
                tool_call_id=call.id,
                content=result.content if not isinstance(result, Exception)
                        else f"Error: {result}"
            )
            for call, result in zip(tool_calls, results)
        ]
```

### 2.2 LLM Client 接口

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Callable

class StopReason(Enum):
    END_TURN = "end_turn"        # 正常结束
    TOOL_USE = "tool_use"        # 需要工具调用
    MAX_TOKENS = "max_tokens"    # 达到最大 token
    STOP_SEQUENCE = "stop"       # 遇到停止序列

@dataclass
class LLMResponse:
    """LLM 响应"""
    message: Message
    stop_reason: StopReason
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = None

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

class LLMClient(ABC):
    """LLM 客户端抽象接口"""

    @abstractmethod
    async def call(
        self,
        context: Context,
        stream: bool = False,
        on_chunk: Optional[Callable[[Chunk], None]] = None
    ) -> LLMResponse:
        """调用 LLM"""
        pass

    @abstractmethod
    async def count_tokens(self, messages: List[Message]) -> int:
        """计算 token 数量"""
        pass
```

### 2.3 Anthropic Client 实现

```python
from anthropic import AsyncAnthropic

class AnthropicClient(LLMClient):
    """Anthropic Claude 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def call(
        self,
        context: Context,
        stream: bool = False,
        on_chunk: Optional[Callable] = None
    ) -> LLMResponse:
        """调用 Claude API"""

        # 构建请求
        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": context.system_prompt,
            "messages": self._format_messages(context.messages),
            "tools": self._format_tools(context.tools) if context.tools else None,
        }

        if stream:
            return await self._stream_call(request, on_chunk)
        else:
            return await self._sync_call(request)

    async def _sync_call(self, request: dict) -> LLMResponse:
        """同步调用"""
        response = await self.client.messages.create(**request)

        # 解析响应
        content = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return LLMResponse(
            message=Message(
                role="assistant",
                content="\n".join(content)
            ),
            stop_reason=StopReason(response.stop_reason),
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_read_tokens=getattr(response.usage, 'cache_read_input_tokens', 0),
                cache_write_tokens=getattr(response.usage, 'cache_creation_input_tokens', 0)
            )
        )

    async def _stream_call(
        self,
        request: dict,
        on_chunk: Callable
    ) -> LLMResponse:
        """流式调用"""
        async with self.client.messages.stream(**request) as stream:
            text_content = []
            tool_calls = []
            current_tool = None

            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        chunk = Chunk(
                            type=ChunkType.TEXT,
                            content=event.delta.text
                        )
                        text_content.append(event.delta.text)
                        on_chunk(chunk)

                    elif event.delta.type == "input_json_delta":
                        if current_tool:
                            current_tool.arguments += event.delta.partial_json

                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool = ToolCall(
                            id=event.content_block.id,
                            name=event.content_block.name,
                            arguments=""
                        )
                        tool_calls.append(current_tool)

            # 获取最终响应
            final = await stream.get_final_message()

            return LLMResponse(
                message=Message(
                    role="assistant",
                    content="".join(text_content)
                ),
                stop_reason=StopReason(final.stop_reason),
                tool_calls=tool_calls,
                usage=TokenUsage(
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens
                )
            )

    async def count_tokens(self, messages: List[Message]) -> int:
        """计算 token 数量"""
        # 使用 tiktoken 或 Anthropic 的 token counting API
        pass
```

### 2.4 OpenAI Client 实现

```python
from openai import AsyncOpenAI

class OpenAIClient(LLMClient):
    """OpenAI GPT 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def call(
        self,
        context: Context,
        stream: bool = False,
        on_chunk: Optional[Callable] = None
    ) -> LLMResponse:
        """调用 OpenAI API"""

        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": self._format_messages(context),
            "tools": self._format_tools(context.tools) if context.tools else None,
            "tool_choice": "auto" if context.tools else None,
        }

        if stream:
            return await self._stream_call(request, on_chunk)
        else:
            return await self._sync_call(request)

    def _format_messages(self, context: Context) -> List[dict]:
        """格式化消息为 OpenAI 格式"""
        messages = []

        # 系统消息
        if context.system_prompt:
            messages.append({
                "role": "system",
                "content": context.system_prompt
            })

        # 对话消息
        for msg in context.messages:
            if msg.role == "user":
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                item = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    item["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(item)
            elif msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content
                })

        return messages
```

### 2.5 Response Parser

```python
class ResponseParser:
    """响应解析器"""

    def parse(self, raw_response: Any, provider: str) -> LLMResponse:
        """解析原始响应"""
        parser = self._get_parser(provider)
        return parser(raw_response)

    def _get_parser(self, provider: str) -> Callable:
        parsers = {
            "anthropic": self._parse_anthropic,
            "openai": self._parse_openai,
            "local": self._parse_local,
        }
        return parsers.get(provider, self._parse_generic)
```

## 流式处理

### Chunk 类型

```python
class ChunkType(Enum):
    TEXT = "text"                    # 文本内容
    TOOL_CALL_START = "tool_start"   # 工具调用开始
    TOOL_CALL_DELTA = "tool_delta"   # 工具调用增量
    TOOL_CALL_END = "tool_end"       # 工具调用结束
    THINKING = "thinking"            # 思考过程（Claude）
    ERROR = "error"                  # 错误
    DONE = "done"                    # 流结束

@dataclass
class Chunk:
    type: ChunkType
    content: str = ""
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def is_text(self) -> bool:
        return self.type == ChunkType.TEXT

    def is_tool_call(self) -> bool:
        return self.type in (ChunkType.TOOL_CALL_START, ChunkType.TOOL_CALL_DELTA, ChunkType.TOOL_CALL_END)

    def is_done(self) -> bool:
        return self.type == ChunkType.DONE
```

### 流式输出处理与背压控制

```python
@dataclass
class StreamingConfig:
    """流式处理配置"""
    buffer_size: int = 8192                # 缓冲区大小（chunk 数量）
    backpressure_threshold: float = 0.9    # 背压触发阈值
    pause_on_backpressure: bool = True     # 是否在背压时暂停
    max_pause_duration: float = 5.0        # 最大暂停时间（秒）

@dataclass
class StreamingStats:
    """流式统计信息"""
    chunks_received: int = 0
    chunks_processed: int = 0
    backpressure_events: int = 0
    total_pause_time: float = 0.0
    buffer_high_watermark: int = 0

    @property
    def is_healthy(self) -> bool:
        """检查流式处理是否健康（无过度背压）"""
        return self.backpressure_events < 10


class StreamingHandler:
    """
    流式输出处理器，支持背压控制。

    功能：
    - 缓冲区管理
    - 背压检测与处理
    - 进度事件发射
    - 支持不同 chunk 类型

    Example:
        >>> handler = StreamingHandler(on_progress=my_callback)
        >>> async for chunk in llm.stream(messages):
        ...     await handler.handle(chunk)
        ...     if handler.should_pause:
        ...         await asyncio.sleep(0.1)
        >>> content = handler.get_full_content()
    """

    def __init__(
        self,
        config: StreamingConfig | None = None,
        on_progress: ProgressCallback | None = None,
        on_chunk: Callable[[Chunk], None] | None = None,
    ):
        self.config = config or StreamingConfig()
        self._on_progress = on_progress
        self._on_chunk = on_chunk
        self._buffer: deque[Chunk] = deque(maxlen=self.config.buffer_size)
        self._is_paused = False
        self._stats = StreamingStats()
        self._text_content: list[str] = []
        self._tool_calls: dict[str, dict] = {}

    @property
    def buffer_usage(self) -> float:
        """缓冲区使用率 (0.0-1.0)"""
        return len(self._buffer) / self.config.buffer_size

    @property
    def should_pause(self) -> bool:
        """检查是否应暂停上游（背压检测）"""
        return self._is_paused or self.buffer_usage >= self.config.backpressure_threshold

    async def handle(self, chunk: Chunk) -> None:
        """处理 incoming chunk"""
        self._stats.chunks_received += 1
        self._buffer.append(chunk)

        # 更新高水位
        if len(self._buffer) > self._stats.buffer_high_watermark:
            self._stats.buffer_high_watermark = len(self._buffer)

        # 检测背压
        if self.config.pause_on_backpressure and self.should_pause:
            await self._apply_backpressure()

        # 处理 chunk
        self._process_chunk(chunk)
        if self._on_chunk:
            self._on_chunk(chunk)
        self._stats.chunks_processed += 1

    async def _apply_backpressure(self) -> None:
        """应用背压（暂停并等待缓冲区释放）"""
        self._is_paused = True
        self._stats.backpressure_events += 1

        # 发射进度事件
        if self._on_progress:
            self._on_progress(ProgressEvent(
                type=ProgressEventType.STREAM_BACKPRESSURE,
                message=f"Backpressure applied: buffer at {self.buffer_usage:.0%}",
                data={"buffer_size": len(self._buffer), "usage": self.buffer_usage},
            ))

        # 等待缓冲区释放
        while self.buffer_usage > self.config.backpressure_threshold * 0.5:
            await asyncio.sleep(0.01)

        self._is_paused = False

    def get_full_content(self) -> str:
        """获取完整文本内容"""
        return "".join(self._text_content)

    def get_tool_calls(self) -> list[dict]:
        """获取累积的工具调用"""
        return [{"id": id_, **data} for id_, data in self._tool_calls.items()]

    def clear(self) -> None:
        """清空缓冲区和累积内容"""
        self._buffer.clear()
        self._text_content.clear()
        self._tool_calls.clear()
        self._is_paused = False
```

## 错误处理

### 错误类型

```python
class HarnessError(Exception):
    """Harness 基础错误"""
    pass

class LLMError(HarnessError):
    """LLM 调用错误"""
    pass

class RateLimitError(LLMError):
    """速率限制错误"""
    def __init__(self, retry_after: float = None):
        self.retry_after = retry_after

class ContextTooLongError(LLMError):
    """上下文过长错误"""
    pass

class ToolExecutionError(HarnessError):
    """工具执行错误"""
    pass

class PermissionDeniedError(ToolExecutionError):
    """权限拒绝错误"""
    pass

class TimeoutError(ToolExecutionError):
    """超时错误"""
    pass
```

### 错误处理策略

```python
class ErrorHandler:
    """错误处理器"""

    async def handle(
        self,
        error: Exception,
        context: LoopContext
    ) -> ErrorAction:
        """处理错误并返回动作"""

        if isinstance(error, RateLimitError):
            return ErrorAction(
                type=ActionType.RETRY,
                delay=error.retry_after or 60.0
            )

        if isinstance(error, ContextTooLongError):
            return ErrorAction(
                type=ActionType.COMPRESS_CONTEXT,
                target_tokens=context.max_tokens * 0.7
            )

        if isinstance(error, PermissionDeniedError):
            return ErrorAction(
                type=ActionType.ABORT,
                message=f"Permission denied: {error}"
            )

        if isinstance(error, TimeoutError):
            return ErrorAction(
                type=ActionType.RETRY,
                delay=5.0,
                max_retries=3
            )

        # 未知错误
        return ErrorAction(
            type=ActionType.ABORT,
            message=str(error)
        )
```

## Stuck Detection & Adaptive Feedback

Agent Loop 是纯前向循环——调用 LLM、执行工具、继续。当工具连续失败或返回空结果时，Agent 会空转直到 `max_iterations`，浪费 token 而无进展。

Stuck Detection 用纯规则检测停滞状态，通过向上下文注入反馈提示，利用 LLM 自身的反思能力改换策略。零额外 API 调用，零独立模块。

### 设计原则

| 原则 | 说明 |
|------|------|
| 规则层检测 | 不调用 LLM 评估，用纯规则判断是否卡住 |
| 反馈注入 | 不新建评估器/策略适配器，往上下文加一条提示让 LLM 自行调整 |
| 最小实现 | 先覆盖 80% 场景，收集真实数据后再扩展规则 |
| 有界重试 | 反馈最多注入 2 次，之后直接终止 |

### 检测规则

```python
def _is_stuck(self, session: Session, iteration: int) -> bool:
    """
    检测 Agent 是否陷入停滞状态。

    使用绝对计数（非比例）检测最近工具结果的失败模式：
    - 连续 N 条空结果：工具执行成功但无实质输出
    - 连续 N 条错误结果：工具连续失败

    Args:
        session: 当前会话
        iteration: 当前迭代次数

    Returns:
        True 表示检测到停滞
    """
    if iteration < self.config.stuck_min_iterations:
        return False

    recent = session.messages[-6:]  # 最近 3 轮
    tool_msgs = [m for m in recent if m.role == "tool"]

    if len(tool_msgs) < self.config.stuck_consecutive_failures:
        return False

    n = self.config.stuck_consecutive_failures

    # 规则1：连续空结果（完全为空，而非仅短内容）
    empty_count = sum(1 for m in tool_msgs[-n:] if not m.content.strip())
    if empty_count >= n:
        return True

    # 规则2：连续错误结果
    error_count = sum(1 for m in tool_msgs[-n:] if m.content.startswith("Error:"))
    if error_count >= n:
        return True

    return False
```

### 反馈注入

当检测到停滞时，向 session 注入一条提示消息。下一轮 `context.build()` 会自然包含此提示，LLM 在后续调用中可据此调整策略。

反馈分两轮，内容不同：
- **第 1 次**：温和提示，建议换方法
- **第 2 次**：更强硬，包含错误模式分析，要求 LLM 承认困难或根本改变策略

```python
# 在 AgentLoop._run_impl() 的循环中，工具执行之后
if self._is_stuck(session, iteration):
    if self._stuck_feedback_count < self.config.max_stuck_feedbacks:
        self._stuck_feedback_count += 1
        feedback = self._generate_stuck_feedback(self._stuck_feedback_count, session)
        session.add_message(Message(
            role="user",
            content=feedback,
            metadata={"type": "stuck_feedback", "injected": True},
        ))
        self._emit_progress(...)
    else:
        # 反馈已用尽，终止循环
        self.state = LoopState.STUCK
        return LoopResult(
            status=LoopState.STUCK,
            session=session,
            iterations=iteration,
            error="Agent stuck: repeated failures after feedback attempts",
            token_usage=total_usage,
        )
```

### 自适应反馈生成

```python
def _generate_stuck_feedback(self, feedback_count: int, session: Session) -> str:
    """根据反馈次数生成差异化反馈"""
    if feedback_count == 1:
        return (
            "[循环检测] 最近几步操作无进展（工具返回空结果或错误）。\n"
            "请尝试：\n"
            "1. 使用不同的工具或方法\n"
            "2. 调整参数或搜索策略\n"
            "3. 重新评估当前问题是否可解决"
        )
    else:
        error_summary = self._summarize_recent_errors(session)
        return (
            "[循环检测 - 最后机会] 已尝试调整但仍无进展。\n"
            f"观察到的问题：{error_summary}\n"
            "\n请立即：\n"
            "1. 承认无法继续并说明遇到的困难，或\n"
            "2. 采用完全不同的方法（根本性改变策略）"
        )

def _summarize_recent_errors(self, session: Session) -> str:
    """提取最近工具结果的错误模式摘要"""
    recent = session.messages[-6:]
    tool_msgs = [m for m in recent if m.role == "tool"]
    parts = []
    empty = sum(1 for m in tool_msgs if not m.content.strip())
    errors = sum(1 for m in tool_msgs if m.content.startswith("Error:"))
    if empty:
        parts.append(f"空结果 {empty} 次")
    if errors:
        parts.append(f"错误 {errors} 次")
    return " | ".join(parts) if parts else "工具调用无进展"
```

### 配置

```python
@dataclass
class LoopConfig:
    # ... 其他配置 ...

    # Stuck Detection
    max_stuck_feedbacks: int = 2   # 最大反馈注入次数
    stuck_min_iterations: int = 3  # 开始检测的最小迭代次数
    stuck_consecutive_failures: int = 3  # 连续空/错误结果触发数
```

### 与现有机制的关系

| 机制 | 职责 | 重复？ |
|------|------|--------|
| CircuitBreaker | 检测**相同工具**重复调用，熔断 | 不重复——CB 检测工具级循环，Stuck 检测结果级停滞 |
| ErrorHandler | 处理 LLM 调用异常（重试/降级） | 不重复——EH 处理网络/API 错误，Stuck 处理逻辑停滞 |
| CostController | 控制预算不超限 | 不重复——成本控制是硬限制，Stuck 是效率优化 |

CircuitBreaker 和 Stuck Detection 的区别：

```
CircuitBreaker 检测: read_file(path="a") → read_file(path="a") → read_file(path="a") (同一调用重复)
Stuck Detection 检测: read_file(成功但空) → grep(成功但空) → search(错误) (不同工具，但整体无进展)
```

### 进度事件

Stuck Detection 新增一个进度事件场景：

```python
# 检测到停滞时
ProgressEventType.STATE_CHANGE  # message: "Stuck state detected at iteration N"
ProgressEventType.ERROR         # message: "Agent stuck: repeated failures after feedback attempts" (反馈用尽时)
```

不需要新增事件类型，复用 `STATE_CHANGE` 和 `ERROR` 即可。

### 扩展路径

当前最小实现只覆盖"工具结果空/错误"场景。后续根据真实数据可扩展：

| 扩展方向 | 触发条件 | 优先级 |
|---------|---------|--------|
| 重复内容检测 | LLM 连续返回相似文本 | 收集数据后评估 |
| 上下文膨胀检测 | 消息增长但无新实质信息 | 收集数据后评估 |
| 自适应反馈 | 根据失败类型定制反馈内容 | 当前通用反馈够用 |

**不加的场景**：用 LLM 评估每轮输出质量——成本翻倍、延迟翻倍，ROI 不合算。

---

## 性能优化

### Token 计数与预估

```python
class TokenCounter:
    """Token 计数器"""

    def __init__(self, model: str):
        self.model = model
        self._encoder = self._get_encoder()

    def count(self, text: str) -> int:
        """计算文本的 token 数"""
        return len(self._encoder.encode(text))

    def count_messages(self, messages: List[Message]) -> int:
        """计算消息列表的 token 数"""
        total = 0
        for msg in messages:
            total += self.count(msg.content)
            total += 4  # 消息格式开销
        return total

    def estimate_tool_overhead(self, tools: List[Tool]) -> int:
        """估算工具 Schema 的 token 开销"""
        # 每个 tool 的 schema 大约 50-200 tokens
        return sum(
            100 + len(json.dumps(t.parameters)) // 4
            for t in tools
        )
```

### 上下文预算管理

```python
@dataclass
class ContextBudget:
    """上下文预算"""
    max_tokens: int
    reserved_for_output: int = 4096

    @property
    def available_for_input(self) -> int:
        return self.max_tokens - self.reserved_for_output

    def allocate(self, components: Dict[str, int]) -> Dict[str, int]:
        """分配预算给各组件"""
        total_requested = sum(components.values())

        if total_requested <= self.available_for_input:
            return components

        # 需要压缩，按优先级分配
        priority_order = [
            "system_prompt",    # 最高优先级
            "recent_messages",
            "skills",
            "memory",
            "retrieved"         # 最低优先级
        ]

        allocated = {}
        remaining = self.available_for_input

        for component in priority_order:
            if component in components:
                take = min(components[component], remaining)
                allocated[component] = take
                remaining -= take

        return allocated
```

## 进度事件系统

Agent Loop 内置进度事件追踪功能，用于监控执行过程，支持 UI 展示、日志记录、调试等场景。

### 事件类型

```python
class ProgressEventType(Enum):
    """进度事件类型"""
    LOOP_START = "loop_start"            # Agent 循环开始
    LOOP_END = "loop_end"                # Agent 循环结束
    STATE_CHANGE = "state_change"        # 状态变化
    TOOL_CALL = "tool_call"              # 工具调用开始
    TOOL_RESULT = "tool_result"          # 工具调用结果
    LLM_CALL = "llm_call"                # LLM 调用开始
    LLM_RESPONSE = "llm_response"        # LLM 响应接收
    ITERATION = "iteration"              # 迭代计数
    ERROR = "error"                      # 错误发生
```

### 事件数据结构

```python
@dataclass
class ProgressEvent:
    """
    进度事件
    
    Attributes:
        type: 事件类型
        message: 人类可读的消息
        timestamp: 事件发生时间
        data: 附加数据（工具名称、参数、计时等）
        duration_ms: 持续时间（毫秒），用于计时事件
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
```

### 使用示例

```python
from harness import AgentHarness
from harness.types import ProgressEvent, ProgressEventType

# 定义进度回调
def on_progress(event: ProgressEvent):
    if event.type == ProgressEventType.LOOP_START:
        print(f"🚀 开始执行: {event.message}")
    elif event.type == ProgressEventType.LLM_CALL:
        print(f"🤖 调用 LLM...")
    elif event.type == ProgressEventType.LLM_RESPONSE:
        print(f"✅ LLM 响应 ({event.duration_ms:.0f}ms)")
    elif event.type == ProgressEventType.TOOL_CALL:
        print(f"🔧 工具调用: {event.data.get('tool_name')}")
    elif event.type == ProgressEventType.TOOL_RESULT:
        print(f"📋 工具结果: {event.message}")
    elif event.type == ProgressEventType.LOOP_END:
        print(f"🏁 执行完成: {event.message}")

# 创建 agent 并设置进度回调
agent = AgentHarness(model="claude-sonnet-4-6")
agent.set_progress_callback(on_progress)

# 运行
result = await agent.run("分析当前目录的代码结构")
```

### 配置选项

```python
@dataclass
class LoopConfig:
    # ... 其他配置 ...
    enable_progress: bool = True  # 启用进度事件（默认启用）
```

### 事件流示例

```
[14:30:01] loop_start: 开始处理用户请求
[14:30:01] llm_call: 调用 claude-sonnet-4-6
[14:30:03] llm_response: 收到响应 (2100ms)
[14:30:03] tool_call: read_file
[14:30:03] tool_result: 成功读取文件 (50ms)
[14:30:03] iteration: 第 1 次迭代
[14:30:03] llm_call: 调用 claude-sonnet-4-6
[14:30:05] llm_response: 收到响应 (1800ms)
[14:30:05] loop_end: 完成，共 2 次迭代
```

### 典型应用场景

1. **CLI 进度条**: 在命令行界面显示执行进度
2. **Web UI 更新**: 通过 WebSocket 推送进度到前端
3. **日志记录**: 记录详细的执行过程用于调试
4. **性能分析**: 统计各阶段耗时，优化性能瓶颈

### 进度格式化器

Harness 提供内置的进度格式化器，简化进度输出的配置：

```python
from harness import AgentHarness, create_progress_handler, ProgressFormatter

# 方式 1: 使用 verbose=True（最简单）
result = await agent.run("任务", verbose=True)

# 方式 2: 使用 create_progress_handler 创建处理器
handler = create_progress_handler(format_style="emoji")  # 可选: simple, detailed, colored, emoji
result = await agent.run("任务", on_progress=handler)

# 方式 3: 使用 ProgressFormatter 自定义输出
def my_handler(event):
    print(ProgressFormatter.colored(event))

result = await agent.run("任务", on_progress=my_handler)
```

#### 格式化风格对比

| 风格 | 输出示例 | 适用场景 |
|-----|---------|---------|
| `simple` | `[tool_call] Executing: read` | 日志文件 |
| `detailed` | `[2026-05-28 14:32:01] tool_call: Executing: read (50ms) \| {"tool": "read"}` | 调试 |
| `colored` | `[14:32:01] <span style="color:yellow">Executing: read</span> (50ms)` | 终端（ANSI 支持） |
| `emoji` | `[14:32:01] 🔧 Executing: read (50ms)` | 用户界面 |

#### create_progress_handler 参数

```python
def create_progress_handler(
    format_style: str = "emoji",  # simple, detailed, colored, emoji
    quiet: bool = False,          # True 则静默，不输出
) -> Callable[[ProgressEvent], None]:
    """创建进度处理器"""
```

---

## 监控与可观测性

### 循环指标

```python
@dataclass
class LoopMetrics:
    """循环指标"""
    iterations: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    total_tool_time: float = 0.0
    total_llm_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_time(self) -> float:
        return self.total_llm_time + self.total_tool_time
```

### 追踪

```python
class LoopTracer:
    """循环追踪器"""

    def __init__(self):
        self.spans: List[Span] = []

    def start_span(self, name: str, parent: Span = None) -> Span:
        """开始一个 span"""
        span = Span(
            name=name,
            start_time=time.time(),
            parent=parent
        )
        self.spans.append(span)
        return span

    def end_span(self, span: Span, **attributes):
        """结束 span"""
        span.end_time = time.time()
        span.attributes.update(attributes)

    def export(self) -> dict:
        """导出追踪数据"""
        return {
            "spans": [
                {
                    "name": s.name,
                    "duration": s.end_time - s.start_time,
                    "attributes": s.attributes
                }
                for s in self.spans
            ]
        }
```

## 测试策略

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_agent_loop_basic():
    """测试基本循环"""
    # Mock LLM
    llm = AsyncMock(spec=LLMClient)
    llm.call.return_value = LLMResponse(
        message=Message(role="assistant", content="Hello!"),
        stop_reason=StopReason.END_TURN
    )

    # 创建循环
    loop = AgentLoop(
        llm_client=llm,
        tool_executor=MagicMock(),
        context_builder=MagicMock()
    )

    # 运行
    result = await loop.run("Hi", session=Session())

    assert result.status == LoopState.COMPLETED
    assert "Hello!" in result.final_response.content

@pytest.mark.asyncio
async def test_agent_loop_tool_call():
    """测试工具调用"""
    # Mock LLM 返回工具调用
    llm = AsyncMock(spec=LLMClient)
    llm.call.side_effect = [
        LLMResponse(
            message=Message(role="assistant", content=""),
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[ToolCall(id="1", name="read_file", arguments={"path": "test.txt"})]
        ),
        LLMResponse(
            message=Message(role="assistant", content="File content: ..."),
            stop_reason=StopReason.END_TURN
        )
    ]

    # Mock 工具执行
    tool_executor = AsyncMock()
    tool_executor.execute.return_value = ToolResult(content="file content")

    # 运行
    loop = AgentLoop(llm, tool_executor, MagicMock())
    result = await loop.run("Read the file", session=Session())

    assert result.status == LoopState.COMPLETED
    assert result.iterations == 1
```

### 集成测试

```python
@pytest.mark.integration
async def test_agent_loop_with_real_llm():
    """使用真实 LLM 的集成测试"""
    client = AnthropicClient(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model="claude-sonnet-4-6"
    )

    loop = AgentLoop(
        llm_client=client,
        tool_executor=ToolExecutor(tools=[EchoTool()]),
        context_builder=ContextBuilder()
    )

    result = await loop.run("Say hello", session=Session())

    assert result.status == LoopState.COMPLETED
    assert len(result.final_response.content) > 0
```

---

## 成本控制

### 多层级成本控制体系

需要全局成本控制，防止 Token 消耗失控。

```
┌─────────────────────────────────────────────────────────┐
│                    Cost Control                          │
│                                                          │
│  Level 1: 会话级限制                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ max_tokens_per_session: 1,000,000              │    │
│  │ max_tool_calls_per_session: 500                │    │
│  │ max_iterations_per_request: 20                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 2: 用户级限制                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ daily_token_limit: 10,000,000                  │    │
│  │ hourly_request_limit: 100                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 3: 全局限制                                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │ global_daily_budget: $100                       │    │
│  │ auto_throttle: true                             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Level 4: 自适应降级                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 当预算不足时：                                   │    │
│  │ - 切换到更便宜的模型                            │    │
│  │ - 减少上下文长度                                │    │
│  │ - 拒绝非关键请求                                │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**实现**:

```python
@dataclass
class CostConfig:
    """成本配置"""
    # 会话级
    max_tokens_per_session: int = 1_000_000
    max_tool_calls_per_session: int = 500
    max_iterations_per_request: int = 20

    # 用户级
    daily_token_limit: int = 10_000_000
    hourly_request_limit: int = 100

    # 全局
    global_daily_budget_usd: float = 100.0
    auto_throttle: bool = True

    # 自适应降级
    fallback_model: str = "claude-haiku-4-5"
    context_reduction_ratio: float = 0.5


class CostController:
    """成本控制器"""

    def __init__(self, config: CostConfig, storage: "CostStorage"):
        self.config = config
        self.storage = storage

    async def check_session_budget(self, session_id: str) -> bool:
        """检查会话预算"""
        usage = await self.storage.get_session_usage(session_id)

        if usage.total_tokens >= self.config.max_tokens_per_session:
            raise BudgetExceededError(
                f"Session token limit reached: {usage.total_tokens}/{self.config.max_tokens_per_session}"
            )

        if usage.tool_calls >= self.config.max_tool_calls_per_session:
            raise BudgetExceededError("Session tool call limit reached")

        return True

    async def check_user_budget(self, user_id: str) -> bool:
        """检查用户预算"""
        daily_usage = await self.storage.get_daily_user_usage(user_id)

        if daily_usage.tokens >= self.config.daily_token_limit:
            raise BudgetExceededError("Daily token limit reached")

        hourly_requests = await self.storage.get_hourly_request_count(user_id)
        if hourly_requests >= self.config.hourly_request_limit:
            raise RateLimitError("Hourly request limit reached")

        return True

    async def should_downgrade(self) -> tuple[bool, str]:
        """判断是否应该降级"""
        daily_cost = await self.storage.get_daily_cost()
        budget = self.config.global_daily_budget_usd

        if daily_cost >= budget * 0.8:  # 80% 预算
            return True, self.config.fallback_model

        return False, ""


### CostStorage 存储接口

CostController 依赖 CostStorage 接口来持久化用户级和全局级的使用数据。提供两种实现：

```python
from harness.core import CostStorage, InMemoryCostStorage, SQLiteCostStorage
from harness.types import UserUsage

# 抽象接口
class CostStorage(ABC):
    """成本存储抽象基类"""

    @abstractmethod
    def get_user_usage(self, user_id: str) -> UserUsage:
        """获取用户使用量"""
        pass

    @abstractmethod
    def record_user_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request: bool = False,
    ) -> UserUsage:
        """记录用户使用"""
        pass

    @abstractmethod
    def get_global_usage(self) -> GlobalUsage:
        """获取全局使用量"""
        pass

    @abstractmethod
    def reset_daily(self) -> None:
        """重置每日计数器"""
        pass


# 内存实现 - 适合单进程应用
storage = InMemoryCostStorage()
usage = storage.record_user_usage("user-123", input_tokens=1000, output_tokens=500)
print(usage.daily_tokens)  # 1500

# SQLite 实现 - 适合多进程/生产环境
storage = SQLiteCostStorage("~/.harness/costs.db")
usage = storage.get_user_usage("user-123")
```

**选择建议**:
- 开发/测试: `InMemoryCostStorage` (数据重启后丢失)
- 生产环境: `SQLiteCostStorage` (持久化存储)

---

### 熔断机制

LLM 可能陷入死循环，消耗完预算后才停止。需要熔断机制检测异常模式并强制中断。

```python
from dataclasses import dataclass, field
from collections import deque
from typing import Deque
import time

@dataclass
class LoopPattern:
    """循环模式记录"""
    tool_name: str
    arguments_hash: str
    timestamp: float

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    same_tool_threshold: int = 5      # 相同工具调用次数阈值
    time_window: float = 60.0         # 时间窗口（秒）
    error_threshold: int = 3          # 错误重试阈值
    cooldown_seconds: float = 300.0   # 冷却时间（秒）

class CircuitBreaker:
    """熔断器"""

    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self._call_history: Deque[LoopPattern] = deque(maxlen=100)
        self._error_count = 0
        self._last_trip_time: float = 0
        self._tripped = False

    def record_call(self, tool_name: str, arguments: dict):
        """记录工具调用"""
        args_hash = self._hash_arguments(arguments)
        self._call_history.append(LoopPattern(
            tool_name=tool_name,
            arguments_hash=args_hash,
            timestamp=time.time()
        ))

        if self._should_trip():
            self._trip()

    def record_error(self):
        """记录错误"""
        self._error_count += 1
        if self._error_count >= self.config.error_threshold:
            self._trip()

    def _should_trip(self) -> bool:
        """判断是否应该熔断"""
        if len(self._call_history) < self.config.same_tool_threshold:
            return False

        now = time.time()
        recent = [
            p for p in self._call_history
            if now - p.timestamp < self.config.time_window
        ]

        if len(recent) < self.config.same_tool_threshold:
            return False

        # 检查相同工具的重复调用
        tool_counts = {}
        for pattern in recent:
            key = f"{pattern.tool_name}:{pattern.arguments_hash}"
            tool_counts[key] = tool_counts.get(key, 0) + 1

            if tool_counts[key] >= self.config.same_tool_threshold:
                return True

        return False

    def _trip(self):
        """触发熔断"""
        self._tripped = True
        self._last_trip_time = time.time()

    def is_open(self) -> bool:
        """熔断器是否打开（阻止执行）"""
        if not self._tripped:
            return False

        # 检查冷却时间
        if time.time() - self._last_trip_time > self.config.cooldown_seconds:
            self._reset()
            return False

        return True

    def _reset(self):
        """重置熔断器"""
        self._tripped = False
        self._error_count = 0
        self._call_history.clear()

    @staticmethod
    def _hash_arguments(arguments: dict) -> str:
        """计算参数哈希"""
        import json
        import hashlib
        return hashlib.md5(
            json.dumps(arguments, sort_keys=True).encode()
        ).hexdigest()[:16]


class CircuitBreakerError(Exception):
    """熔断错误"""
    def __init__(self, message: str, stats: dict):
        super().__init__(message)
        self.stats = stats
```

---

## 流式中断与恢复

`interrupt()` 无法中断正在进行的 LLM HTTP 请求或长耗时工具执行。需要实现网络级中断 + 状态快照恢复。

### LoopSnapshot 快照结构

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class LoopSnapshot:
    """
    循环快照，用于中断恢复。

    捕获执行状态，支持从中断点恢复执行。

    Attributes:
        session_id: 会话标识符
        messages: 对话中的所有消息
        current_iteration: 当前迭代次数
        pending_tool_calls: 待执行的工具调用
        last_llm_response: 最后的 LLM 响应
        created_at: 快照创建时间
    """
    session_id: str
    messages: list[Message] = field(default_factory=list)
    current_iteration: int = 0
    pending_tool_calls: list[ToolCall] = field(default_factory=list)
    last_llm_response: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """序列化快照为字典"""
        return {
            "session_id": self.session_id,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "current_iteration": self.current_iteration,
            "pending_tool_calls": [tc.to_dict() for tc in self.pending_tool_calls],
            "last_llm_response": self.last_llm_response,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopSnapshot":
        """从字典反序列化快照"""
        return cls(
            session_id=data["session_id"],
            messages=[Message(**m) for m in data.get("messages", [])],
            current_iteration=data.get("current_iteration", 0),
            pending_tool_calls=[ToolCall.from_dict(tc) for tc in data.get("pending_tool_calls", [])],
            last_llm_response=data.get("last_llm_response"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )
```

### AgentLoop 中断恢复方法

```python
class AgentLoop:
    """Agent 循环引擎"""

    def interrupt(self) -> None:
        """中断当前循环"""
        self._interrupt_flag = True

    def create_snapshot(
        self,
        session: Session,
        iteration: int = 0,
        pending_tool_calls: list[ToolCall] | None = None,
        last_llm_response: str | None = None,
    ) -> LoopSnapshot:
        """
        创建当前循环状态的快照。

        Args:
            session: 当前会话
            iteration: 当前迭代次数
            pending_tool_calls: 待执行的工具调用
            last_llm_response: 最后的 LLM 响应

        Returns:
            LoopSnapshot 捕获当前状态
        """
        return LoopSnapshot(
            session_id=session.id,
            messages=session.messages.copy(),
            current_iteration=iteration,
            pending_tool_calls=pending_tool_calls or [],
            last_llm_response=last_llm_response,
        )

    async def resume_from_snapshot(
        self,
        snapshot: LoopSnapshot,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """
        从快照恢复执行。

        Args:
            snapshot: 要恢复的快照
            tools: 可用的工具定义
            on_chunk: 流式回调
            on_progress: 进度回调

        Returns:
            LoopResult 恢复后的执行结果
        """
        # 从快照恢复会话
        session = Session(
            id=snapshot.session_id,
            messages=snapshot.messages.copy(),
        )

        self._on_progress = on_progress
        self._loop_start_time = time.time()
        self._interrupt_flag = False

        # 发射恢复事件
        self._emit_progress(
            ProgressEventType.STATE_CHANGE,
            f"Resuming from snapshot at iteration {snapshot.current_iteration}",
            {"snapshot_created_at": snapshot.created_at.isoformat()},
        )

        # 执行待处理的工具调用
        if snapshot.pending_tool_calls:
            tool_results = await self._execute_tools(
                snapshot.pending_tool_calls,
                session,
            )
            for result in tool_results:
                session.add_message(Message(
                    role="tool",
                    content=result.content,
                    metadata={"tool_call_id": result.tool_call_id},
                ))

        # 继续循环
        iteration = snapshot.current_iteration + 1
        # ... 继续正常循环逻辑
```

### 使用示例

```python
from harness import AgentHarness
from harness.types import LoopSnapshot

agent = AgentHarness(model="claude-sonnet-4-6")

# 执行任务
result = await agent.run("Complex task")

# 如果需要中断
agent._loop.interrupt()

# 创建快照保存状态
snapshot = agent._loop.create_snapshot(
    session=result.session,
    iteration=result.iterations,
)

# 保存快照到文件
import json
with open("checkpoint.json", "w") as f:
    json.dump(snapshot.to_dict(), f)

# 后续从快照恢复
with open("checkpoint.json") as f:
    data = json.load(f)
    snapshot = LoopSnapshot.from_dict(data)

result = await agent._loop.resume_from_snapshot(snapshot)
```

---

## Lifecycle Hooks (待实现) - P0 优先级

Lifecycle Hooks 是最基础的缺失功能，所有其他高级功能（Ralph Loop、自验证）都依赖它。

### 问题场景

当前无法在工具执行前后插入自定义逻辑：
- 无法拦截危险工具调用
- 无法在代码修改后自动运行测试
- 无法记录详细审计日志
- 无法实现自定义重试逻辑

### 钩子系统设计

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

class HookPoint(Enum):
    """钩子触发点"""
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"
    BEFORE_TOOL_EXECUTE = "before_tool_execute"
    AFTER_TOOL_EXECUTE = "after_tool_execute"
    ON_ERROR = "on_error"
    ON_LOOP_START = "on_loop_start"
    ON_LOOP_END = "on_loop_end"
    ON_EXIT_ATTEMPT = "on_exit_attempt"  # Ralph Loop 使用

@dataclass
class HookContext:
    """钩子上下文"""
    hook_point: HookPoint
    session_id: str
    iteration: int
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: ToolResult | None = None
    llm_response: LLMResponse | None = None
    error: Exception | None = None
    messages: list[Message] | None = None
    metadata: dict = None

@dataclass
class HookResult:
    """钩子返回结果"""
    action: str  # "continue", "abort", "retry", "inject_message", "modify_args"
    modified_args: dict | None = None
    modified_result: ToolResult | None = None
    inject_message: Message | None = None
    delay_seconds: float = 0

class LifecycleHook:
    """生命周期钩子基类"""

    @property
    def hook_points(self) -> list[HookPoint]:
        """订阅的钩子点"""
        return []

    async def execute(self, context: HookContext) -> HookResult:
        """执行钩子逻辑"""
        return HookResult(action="continue")

# 注册钩子
agent = AgentHarness()
agent.add_hook(MyCustomHook(), points=[HookPoint.BEFORE_TOOL_EXECUTE])
```

### AgentLoop 集成

```python
class AgentLoop:
    def __init__(self, ...):
        self._hooks: dict[HookPoint, list[LifecycleHook]] = defaultdict(list)

    def add_hook(self, hook: LifecycleHook, points: list[HookPoint] | None = None):
        """注册钩子"""
        points = points or hook.hook_points
        for point in points:
            self._hooks[point].append(hook)

    async def _execute_with_hooks(self, tool_call: ToolCall, context: ToolContext) -> ToolResult:
        """带钩子的工具执行"""
        # Before hook
        for hook in self._hooks[HookPoint.BEFORE_TOOL_EXECUTE]:
            result = await hook.execute(HookContext(
                hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
                tool_name=tool_call.name,
                tool_args=tool_call.arguments,
            ))
            if result.action == "abort":
                return ToolResult(success=False, error="Aborted by hook")
            if result.action == "modify_args":
                tool_call.arguments = result.modified_args

        # Execute tool
        tool_result = await self.tools.execute(tool_call, context)

        # After hook
        for hook in self._hooks[HookPoint.AFTER_TOOL_EXECUTE]:
            result = await hook.execute(HookContext(
                hook_point=HookPoint.AFTER_TOOL_EXECUTE,
                tool_name=tool_call.name,
                tool_result=tool_result,
            ))
            if result.action == "inject_message":
                # 注入消息到上下文
                session.add_message(result.inject_message)
            if result.action == "modify_result":
                tool_result = result.modified_result

        return tool_result
```

---

## 工具输出卸载 (待实现) - P3 优先级

当工具返回大量输出时，直接注入上下文会快速消耗 token 预算。工具输出卸载通过将大输出保存到文件，只注入引用来解决这个问题。

### 问题场景

```
工具: Grep "function" in src/ (500+ 匹配)
输出: 15,000 tokens
结果: 单次工具调用消耗 7.5% 的 200k 上下文
```

### 卸载机制

```python
class ToolOutputOffloader:
    """工具输出卸载器"""

    def __init__(self, threshold_tokens: int = 1000):
        self.threshold = threshold_tokens
        self.offload_dir = Path(".harness/offloads")

    def should_offload(self, result: ToolResult) -> bool:
        """判断是否需要卸载"""
        return result.token_count > self.threshold

    def offload(self, result: ToolResult) -> str:
        """卸载到文件，返回引用路径"""
        offload_id = str(uuid.uuid4())[:8]
        offload_path = self.offload_dir / f"{offload_id}.txt"
        offload_path.write_text(result.content)

        # 返回截断内容 + 文件引用
        preview = result.content[:500]
        return f"{preview}\n\n... [输出已卸载到 {offload_path}，完整内容 {result.token_count} tokens]"
```

### 配置示例

```python
from harness import AgentHarness
from harness.core import ToolOutputOffloader

agent = AgentHarness()
agent.tool_executor.offloader = ToolOutputOffloader(
    threshold_tokens=2000,  # 超过 2000 tokens 则卸载
    offload_dir=".harness/offloads"
)
```

---

## Ralph Loop 模式 (待实现) - P1 优先级

当 Agent 在长时间任务中接近上下文限制时，会产生"上下文焦虑"——提前结束任务。Ralph Loop 通过拦截退出并重置上下文来解决此问题。

### 问题场景

```
任务: 重构整个代码库 (预计需要 50+ 步)
上下文: 开始时 0 tokens，20 步后 80,000 tokens
结果: 模型在第 25 步声称"任务完成"，实际只做了 50%
```

### Ralph Loop 机制

```python
class RalphLoopHook(LifecycleHook):
    """Ralph Loop 钩子"""

    @property
    def hook_points(self) -> list[HookPoint]:
        return [HookPoint.ON_EXIT_ATTEMPT]

    async def execute(self, context: HookContext) -> HookResult:
        """拦截提前退出"""
        if not self._is_task_complete(context):
            # 保存当前状态到文件系统
            self._save_progress(context)

            # 在干净上下文中重新注入提示
            return HookResult(
                action="inject_message",
                inject_message=Message(
                    role="user",
                    content=self._build_continuation_prompt(context)
                ),
                metadata={"clear_context": True}  # 重置上下文
            )

        return HookResult(action="continue")
```

### 使用示例

```python
from harness import AgentHarness
from harness.hooks import RalphLoopHook

agent = AgentHarness(model="claude-sonnet-4-6")
agent.add_hook(RalphLoopHook())

# 长任务会自动循环直到真正完成
result = await agent.run("重构整个代码库，更新所有 API 调用")
```

---

## 自验证钩子 (待实现) - P2 优先级

实现 write-code → run-tests → fix-errors 循环。

```python
class SelfVerificationHook(LifecycleHook):
    """自验证钩子"""

    def __init__(self, test_command: str = "pytest"):
        self.test_command = test_command

    @property
    def hook_points(self) -> list[HookPoint]:
        return [HookPoint.AFTER_TOOL_EXECUTE]

    async def execute(self, context: HookContext) -> HookResult:
        """代码修改后自动运行测试"""
        if context.tool_name in ("write", "edit"):
            # 运行测试
            test_result = await self._run_tests(context)

            if not test_result.success:
                # 测试失败，将错误注入上下文让 LLM 修复
                return HookResult(
                    action="inject_message",
                    inject_message=Message(
                        role="user",
                        content=f"测试失败，请修复：\n{test_result.output}"
                    )
                )

        return HookResult(action="continue")
```

---

## Sub-Agent 管理 (待实现) - P1 优先级

当任务过大需要分解时，主 Agent 可以创建子代理处理子任务。

### 问题场景

```
任务: 分析整个代码库并生成架构文档
步骤:
  1. 分析 src/core 目录 → 需要 10+ 步
  2. 分析 src/tools 目录 → 需要 10+ 步
  3. 汇总生成文档

问题: 主 Agent 上下文会被单个目录分析占满，无法保持全局视图
```

### Sub-Agent 架构

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class SubAgentConfig:
    """子代理配置"""
    name: str                           # 子代理名称
    task: str                           # 子任务描述
    tools: list[str] | None = None      # 可用工具（None = 继承父代理）
    max_iterations: int = 20            # 子代理最大迭代
    inherit_context: bool = False       # 是否继承父代理上下文
    report_format: Literal["summary", "full", "structured"] = "summary"

class SubAgentManager:
    """子代理管理器"""

    def __init__(self, parent_agent: AgentHarness):
        self.parent = parent_agent
        self._sub_agents: dict[str, AgentHarness] = {}

    async def spawn(self, config: SubAgentConfig) -> str:
        """创建子代理"""
        sub_agent = AgentHarness(
            model=self.parent.model,
            tools=config.tools or self.parent.tools,
            max_iterations=config.max_iterations,
        )
        self._sub_agents[config.name] = sub_agent
        return config.name

    async def run(self, name: str, input: str) -> SubAgentResult:
        """运行子代理"""
        sub_agent = self._sub_agents.get(name)
        result = await sub_agent.run(input)
        return SubAgentResult(
            name=name,
            success=result.status == LoopState.COMPLETED,
            summary=result.final_response[:500],
        )

    async def collect_all(self) -> dict[str, SubAgentResult]:
        """收集所有子代理结果"""
        results = {}
        for name in self._sub_agents:
            results[name] = await self.get_result(name)
        return results
```

---

## MEMORY.md 标准 (待实现) - P2 优先级

Claude Code 使用 MEMORY.md 文件存储持久记忆，Harness 应支持读写此标准格式。

### MEMORY.md 格式

```markdown
# MEMORY.md

## User Profile
- Role: Software Developer
- Preferred Language: Python

## Key Decisions
- 2026-05-28: 选择 SQLite 作为会话存储（原因：零配置、跨平台）

## Learned Patterns
- 用户偏好简洁响应，无尾部总结
- 避免在 QThread 中创建 asyncio event loop
```

### 实现设计

```python
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

class MemoryFileManager:
    """MEMORY.md 文件管理器"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.memory_file = self.project_root / "MEMORY.md"

    def load(self) -> dict[str, list[str]]:
        """加载 MEMORY.md 内容"""
        if not self.memory_file.exists():
            return {}
        return self._parse_sections(self.memory_file.read_text())

    def save(self, sections: dict[str, list[str]]) -> None:
        """保存到 MEMORY.md"""
        self.memory_file.write_text(self._build_content(sections))

    def add_entry(self, category: str, content: str) -> None:
        """添加新记忆条目"""
        sections = self.load()
        if category not in sections:
            sections[category] = []
        sections[category].append(f"- {content}")
        self.save(sections)
```

---

## 动态系统提示组装 (待实现) - P0 优先级

根据项目上下文动态调整系统提示，支持 AGENTS.md 标准。

### 问题场景

当前系统提示是静态的，无法根据：
- 项目类型（Python/JavaScript/Rust）
- 框架特性（Django/FastAPI/React）
- 团队规范（代码风格、测试框架）
- 项目结构（Monorepo/Microservice）

自动调整行为。

### AGENTS.md 标准

类似 Claude Code 的 CLAUDE.md 和 Cursor 的 .cursorrules：

```markdown
# AGENTS.md

## Project Context
- Type: Python Monorepo
- Framework: FastAPI + PyQt6
- Test Framework: pytest
- Package Manager: uv

## Code Style
- Use type hints for all public functions
- Prefer composition over inheritance
- Keep functions under 50 lines

## Testing Requirements
- Run pytest after any code modification
- Minimum 80% coverage for new modules

## Deployment
- Build: uv build
- Test: uv run pytest
- Release: uv publish
```

### 实现设计

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ProjectContext:
    """项目上下文"""
    project_type: str
    framework: str | None
    test_command: str | None
    build_command: str | None
    code_style_rules: list[str]
    custom_instructions: list[str]

class DynamicSystemPromptBuilder:
    """动态系统提示构建器"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.agents_file = self.project_root / "AGENTS.md"

    def build(self, base_prompt: str) -> str:
        """构建动态系统提示"""
        if not self.agents_file.exists():
            return base_prompt

        context = self._parse_agents_md(self.agents_file.read_text())

        # 组装系统提示
        parts = [base_prompt]

        if context.project_type:
            parts.append(f"\n## Project Context\n- Type: {context.project_type}")
            if context.framework:
                parts.append(f"- Framework: {context.framework}")

        if context.code_style_rules:
            parts.append("\n## Code Style Guidelines")
            parts.extend(f"- {rule}" for rule in context.code_style_rules)

        if context.test_command:
            parts.append(f"\n## Testing\nAfter code modifications, run: `{context.test_command}`")

        return "\n".join(parts)

    def _parse_agents_md(self, content: str) -> ProjectContext:
        """解析 AGENTS.md"""
        # 解析各章节...
        return ProjectContext(...)
```

### ContextBuilder 集成

```python
class ContextBuilder:
    def build(self, session: Session, ...) -> BuiltContext:
        # 动态组装系统提示
        prompt_builder = DynamicSystemPromptBuilder()
        system_prompt = prompt_builder.build(self.config.base_system_prompt)

        # 继续构建上下文...
```

---

## 步骤预算 (待实现) - P3 优先级

软限制总步骤数，提前警告（与 max_iterations 硬限制不同）。

### 与 max_iterations 的区别

| 特性 | max_iterations | 步骤预算 |
|------|----------------|----------|
| 类型 | 硬限制 | 软限制 |
| 行为 | 强制终止 | 警告提示 |
| 目的 | 防止无限循环 | 成本预警 |
| 时机 | 达到时终止 | 80%时警告 |

### 实现设计

```python
@dataclass
class StepBudgetConfig:
    """步骤预算配置"""
    warning_threshold: int = 40   # 警告阈值
    max_iterations: int = 50      # 最大迭代（硬限制）
    warning_message: str = "Approaching step limit, consider wrapping up."

class StepBudgetController:
    """步骤预算控制器"""

    def __init__(self, config: StepBudgetConfig):
        self.config = config

    def check(self, current_iteration: int) -> StepBudgetStatus:
        """检查步骤预算状态"""
        if current_iteration >= self.config.max_iterations:
            return StepBudgetStatus(
                action="abort",
                reason="Max iterations reached"
            )

        if current_iteration >= self.config.warning_threshold:
            return StepBudgetStatus(
                action="warn",
                reason=self.config.warning_message,
                remaining=self.config.max_iterations - current_iteration
            )

        return StepBudgetStatus(action="continue")

# AgentLoop 集成
async def run(self, ...):
    step_budget = StepBudgetController(config.step_budget)

    while iteration < self.config.max_iterations:
        budget_status = step_budget.check(iteration)

        if budget_status.action == "warn":
            # 注入警告消息
            session.add_message(Message(
                role="system",
                content=f"[警告] {budget_status.reason} (剩余 {budget_status.remaining} 步)"
            ))

        # 继续循环...
```

---

## OpenTelemetry 集成

原生集成 OpenTelemetry，导出标准 Span，兼容 Langfuse、Datadog、Jaeger 等观测平台。

### ObservabilityManager

Harness 提供封装好的 ObservabilityManager，简化 OpenTelemetry 初始化：

```python
from harness import ObservabilityManager, ObservabilityConfig, setup_observability

# 方式 1: 使用便捷函数
setup_observability(ObservabilityConfig(
    service_name="my-agent",
    export_console=True,  # 调试时输出到控制台
))

# 方式 2: 使用 Manager 类
manager = ObservabilityManager(config=ObservabilityConfig(
    service_name="my-agent",
    export_otlp=True,
    otlp_endpoint="http://jaeger:4317",  # OTLP gRPC 端点
))
manager.setup()
```

### 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| service_name | str | "harness-agent" | 服务名称 |
| service_version | str | "0.1.0" | 服务版本 |
| enabled | bool | True | 是否启用 |
| export_console | bool | False | 输出到控制台（调试） |
| export_otlp | bool | False | 导出到 OTLP 端点 |
| otlp_endpoint | str | "http://localhost:4317" | OTLP gRPC 端点 |
| sample_rate | float | 1.0 | 采样率 (1.0 = 全部) |

### SpanBuilder 使用

使用 SpanBuilder 进行链路追踪：

```python
from harness import SpanBuilder, traced_operation

# 方式 1: 使用上下文管理器
with traced_operation("llm.call", {"model": "claude-sonnet-4-6"}) as span:
    response = await llm.call(messages)
    span.set_attr("tokens.input", response.usage.input_tokens)

# 方式 2: 使用 SpanBuilder
with SpanBuilder("agent_loop.run") as span:
    span.set_attr("session.id", session_id)
    span.set_attr("prompt.length", len(prompt))
    # ... 执行任务 ...
    span.add_event("tool.called", {"tool": "read_file"})
```

### 与 Agent 集成

```python
from harness import AgentHarness, ObservabilityConfig, setup_observability

# 初始化可观测性
setup_observability(ObservabilityConfig(
    service_name="production-agent",
    export_otlp=True,
    otlp_endpoint="http://jaeger:4317",
))

# 创建 Agent
agent = AgentHarness(model="claude-sonnet-4-6")

# 运行 - 自动生成 Span
result = await agent.run("Analyze this code")
```

**导出的 Span 结构**:
```
agent_loop.run (session_id=xxx, prompt.length=100)
├── context.build (token_count=5000, message_count=10)
├── llm.call (model=claude-sonnet-4-6, input_tokens=5000, output_tokens=500)
├── tools.execute (count=2, names=["read", "grep"])
│   ├── tools.read (success=true, duration=0.1s)
│   └── tools.grep (success=true, duration=0.2s)
└── memory.save (success=true)
```

### 依赖安装

```bash
# 基础 OpenTelemetry
pip install "harness-ai[observability]"

# 或手动安装
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-otlp  # OTLP 导出
```
