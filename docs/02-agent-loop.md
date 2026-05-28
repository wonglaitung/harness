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

@dataclass
class Chunk:
    type: ChunkType
    content: str = ""
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

### 流式输出处理

```python
class StreamingHandler:
    """流式输出处理器"""

    def __init__(self, callbacks: Dict[ChunkType, Callable]):
        self.callbacks = callbacks
        self.buffer = []

    async def handle(self, chunk: Chunk):
        """处理流式 chunk"""
        self.buffer.append(chunk)

        if chunk.type in self.callbacks:
            await self.callbacks[chunk.type](chunk)

    def get_full_content(self) -> str:
        """获取完整内容"""
        return "".join(
            c.content for c in self.buffer
            if c.type == ChunkType.TEXT
        )
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
```

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

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import asyncio

@dataclass
class LoopSnapshot:
    """循环快照（用于恢复）"""
    session_id: str
    messages: List[Message]
    current_iteration: int
    pending_tool_calls: List[ToolCall] = field(default_factory=list)
    last_llm_response: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class InterruptibleAgentLoop:
    """可中断的 Agent 循环"""

    def __init__(self, agent: "AgentHarness"):
        self.agent = agent
        self._current_task: Optional[asyncio.Task] = None
        self._snapshot: Optional[LoopSnapshot] = None

    async def run(
        self,
        prompt: str,
        session_id: str,
        checkpoint_interval: int = 1
    ) -> "LoopResult":
        """可中断执行"""
        self._current_task = asyncio.current_task()
        iteration = 0

        try:
            while True:
                # 保存快照
                if iteration % checkpoint_interval == 0:
                    self._save_snapshot(session_id, iteration)

                result = await self._run_step(prompt, session_id, iteration)

                if result.finished:
                    return result

                iteration += 1

        except asyncio.CancelledError:
            # 保存中断点快照
            await self._save_interrupt_point(session_id, iteration)
            raise

    async def interrupt(self):
        """中断当前执行"""
        if self._current_task:
            self._current_task.cancel()

    async def resume(self, session_id: str) -> "LoopResult":
        """从快照恢复执行"""
        snapshot = await self.agent.memory.load_checkpoint(session_id)
        if not snapshot:
            raise ValueError(f"No checkpoint found for session {session_id}")

        return await self.run(
            prompt="",
            session_id=session_id,
            start_iteration=snapshot.current_iteration
        )
```

---

## OpenTelemetry 集成

原生集成 OpenTelemetry，导出标准 Span，兼容 Langfuse、Datadog、Jaeger 等观测平台。

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# 初始化 OTel
resource = Resource.create({"service.name": "harness-agent"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("harness.agent")


class ObservableAgentLoop:
    """可观测的 Agent 循环"""

    async def run(self, prompt: str, session_id: str) -> LoopResult:
        """执行循环（带 OTel 埋点）"""
        with tracer.start_as_current_span(
            "agent_loop.run",
            attributes={
                "session.id": session_id,
                "prompt.length": len(prompt)
            }
        ) as span:

            # 1. 构建上下文
            with tracer.start_as_current_span("context.build") as ctx_span:
                context = await self._build_context(session_id)
                ctx_span.set_attribute("context.token_count", context.token_count)
                ctx_span.set_attribute("context.message_count", len(context.messages))

            # 2. LLM 调用
            with tracer.start_as_current_span("llm.call") as llm_span:
                llm_span.set_attribute("llm.model", self.llm.model)
                response = await self.llm.call(context)
                llm_span.set_attribute("llm.input_tokens", response.usage.input_tokens)
                llm_span.set_attribute("llm.output_tokens", response.usage.output_tokens)

            # 3. 工具执行
            if response.tool_calls:
                with tracer.start_as_current_span("tools.execute") as tools_span:
                    tools_span.set_attribute("tools.count", len(response.tool_calls))
                    results = await self._execute_tools(response.tool_calls)

            return result
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
