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
