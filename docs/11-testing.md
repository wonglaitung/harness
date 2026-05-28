# 11 - 测试策略

## 概述

本文档定义 Harness 项目的测试策略、测试层级和具体实施方案。

## 测试金字塔

```
                    ┌─────────────┐
                    │    E2E      │  端到端测试
                    │   Tests     │  - 完整 Agent 流程
                    └─────────────┘  - 真实 LLM 调用
                          │
                ┌─────────────────────┐
                │   Integration       │  集成测试
                │      Tests          │  - 组件交互
                └─────────────────────┘  - Mock LLM
                          │
        ┌─────────────────────────────────────┐
        │           Unit Tests                │  单元测试
        │                                     │  - 纯函数逻辑
        │                                     │  - 隔离测试
        └─────────────────────────────────────┘
```

## 测试层级

### Level 1: 单元测试

**目标**: 测试独立函数和类的行为

**原则**:
- 纯函数，无外部依赖
- 快速执行（毫秒级）
- 100% 覆盖核心逻辑

**示例**:

```python
# tests/unit/test_context_builder.py

import pytest
from harness.agent.context import ContextBuilder
from harness.memory.types import Message, Session

class TestContextBuilder:

    def test_build_empty_session(self):
        """空会话构建上下文"""
        builder = ContextBuilder(
            system_prompt="You are helpful.",
            max_tokens=4000
        )

        context = builder.build(Session(id="test"))

        assert len(context.messages) == 1
        assert context.messages[0].role == "system"
        assert context.total_tokens < 100

    def test_build_with_messages(self):
        """包含消息的会话"""
        builder = ContextBuilder(
            system_prompt="You are helpful.",
            max_tokens=4000
        )

        session = Session(id="test")
        session.messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        context = builder.build(session)

        assert len(context.messages) == 3  # system + 2 messages
        assert context.messages[1].content == "Hello"

    def test_truncation_when_exceeds_limit(self):
        """超过 Token 限制时截断"""
        builder = ContextBuilder(
            system_prompt="You are helpful.",
            max_tokens=100  # 很小的限制
        )

        session = Session(id="test")
        session.messages = [
            Message(role="user", content="A" * 1000),  # 很长的消息
            Message(role="assistant", content="B" * 1000),
        ]

        context = builder.build(session)

        assert context.total_tokens <= 100
        # 应该保留系统提示
        assert context.messages[0].role == "system"
```

```python
# tests/unit/test_tool_executor.py

import pytest
from unittest.mock import Mock, AsyncMock
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.tools.types import ToolResult

class TestToolExecutor:

    @pytest.fixture
    def registry(self):
        registry = ToolRegistry()

        # 注册测试工具
        @registry.register("echo")
        def echo_tool(message: str) -> str:
            return message

        @registry.register("fail")
        def fail_tool():
            raise ValueError("Intentional failure")

        return registry

    @pytest.fixture
    def executor(self, registry):
        return ToolExecutor(registry)

    @pytest.mark.asyncio
    async def test_execute_single_tool(self, executor):
        """执行单个工具"""
        result = await executor.execute([
            {"name": "echo", "arguments": {"message": "hello"}}
        ])

        assert len(result) == 1
        assert result[0].success
        assert result[0].output == "hello"

    @pytest.mark.asyncio
    async def test_execute_parallel_tools(self, executor):
        """并行执行多个独立工具"""
        import time

        start = time.time()
        results = await executor.execute([
            {"name": "echo", "arguments": {"message": "a"}},
            {"name": "echo", "arguments": {"message": "b"}},
            {"name": "echo", "arguments": {"message": "c"}},
        ])
        elapsed = time.time() - start

        assert len(results) == 3
        # 并行执行应该很快
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_tool_failure_isolated(self, executor):
        """工具失败不影响其他工具"""
        results = await executor.execute([
            {"name": "echo", "arguments": {"message": "success"}},
            {"name": "fail", "arguments": {}},
        ])

        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
        assert "Intentional failure" in results[1].error

    @pytest.mark.asyncio
    async def test_timeout_on_slow_tool(self, executor):
        """慢工具超时"""
        # 注册一个慢工具
        executor.registry.register("slow")(lambda: time.sleep(10))

        with pytest.raises(TimeoutError):
            await executor.execute(
                [{"name": "slow", "arguments": {}}],
                timeout=1.0
            )
```

---

### Level 2: 集成测试

**目标**: 测试组件之间的交互

**原则**:
- 使用 Mock LLM（不调用真实 API）
- 测试数据流和状态转换
- 覆盖主要使用场景

**示例**:

```python
# tests/integration/test_agent_loop.py

import pytest
from unittest.mock import AsyncMock, patch
from harness import AgentHarness
from harness.llm.types import LLMResponse, ToolCall

class TestAgentLoopIntegration:

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = AsyncMock()

        # 模拟多轮对话
        client.call.side_effect = [
            # 第一轮：请求工具调用
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="read_file",
                        arguments={"path": "test.py"}
                    )
                ]
            ),
            # 第二轮：返回结果
            LLMResponse(
                content="I've read the file. It contains a simple function.",
                tool_calls=[]
            )
        ]

        return client

    @pytest.fixture
    def agent(self, mock_llm_client, tmp_path):
        """创建测试 Agent"""
        return AgentHarness(
            model="test-model",
            llm_client=mock_llm_client,
            memory_dir=str(tmp_path / "memory")
        )

    @pytest.mark.asyncio
    async def test_full_agent_loop(self, agent, tmp_path):
        """测试完整 Agent 循环"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        # 注册工具
        @agent.tools.register("read_file")
        def read_file(path: str) -> str:
            return (tmp_path / path).read_text()

        # 运行 Agent
        response = await agent.run_async("Read test.py and explain it")

        # 验证
        assert response.content == "I've read the file. It contains a simple function."
        assert agent.llm_client.call.call_count == 2

    @pytest.mark.asyncio
    async def test_session_persistence(self, agent):
        """测试会话持久化"""
        # 第一次交互
        await agent.run_async("Hello", session_id="test-session")

        # 验证会话被保存
        session = await agent.memory.load_session("test-session")
        assert session is not None
        assert len(session.messages) == 2  ```


user + assistant

        # 新的交互应该能访问历史
        await agent.run_async("What did I say?", session_id="test-session")
        session = await agent.memory.load_session("test-session")
        assert len(session.messages) == 4  # 2 + 2
```

```python
# tests/integration/test_memory_system.py

import pytest
from harness.memory import MemorySystem, SessionStore
from harness.memory.types import Message, Session

class TestMemoryIntegration:

    @pytest.fixture
    def memory_system(self, tmp_path):
        return MemorySystem(
            storage_dir=str(tmp_path),
            window_size=10,
            summary_threshold=20
        )

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, memory_system):
        """测试会话完整生命周期"""
        session_id = "test-session"

        # 创建会话
        session = await memory_system.create_session(session_id)
        assert session.id == session_id

        # 添加消息
        for i in range(15):
            await memory_system.add_message(
                session_id,
                Message(role="user", content=f"Message {i}")
            )
            await memory_system.add_message(
                session_id,
                Message(role="assistant", content=f"Response {i}")
            )

        # 验证滑动窗口
        loaded = await memory_system.load_session(session_id)
        assert len(loaded.messages) <= 10  # 窗口大小

        # 验证摘要生成
        assert loaded.summary is not None

    @pytest.mark.asyncio
    async def test_cross_session_memory(self, memory_system):
        """测试跨会话记忆"""
        # 第一个会话
        await memory_system.add_message(
            "session-1",
            Message(role="user", content="My name is Alice")
        )
        await memory_system.add_message(
            "session-1",
            Message(role="assistant", content="Nice to meet you, Alice!")
        )

        # 提取关键信息到长期记忆
        await memory_system.extract_to_long_term(
            "session-1",
            key="user_name",
            value="Alice"
        )

        # 第二个会话应该能访问
        context = await memory_system.build_context("session-2")
        assert "Alice" in str(context.long_term_memory)
```

---

### Level 3: 端到端测试

**目标**: 测试真实用户场景

**原则**:
- 使用真实 LLM（测试环境）
- 完整功能流程
- 可选执行（避免 CI 成本）

**示例**:

```python
# tests/e2e/test_real_agent.py

import pytest
import os
from harness import AgentHarness, FileTool, ShellTool

# 只在设置了 API Key 时运行
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="No API key available"
)

class TestRealAgent:

    @pytest.fixture
    def agent(self, tmp_path):
        return AgentHarness(
            model="claude-sonnet-4-6",
            tools=[
                FileTool(base_dir=str(tmp_path)),
                ShellTool(sandbox=True)
            ],
            memory_dir=str(tmp_path / "memory")
        )

    @pytest.mark.asyncio
    async def test_code_analysis_task(self, agent, tmp_path):
        """真实代码分析任务"""
        # 创建测试代码
        (tmp_path / "main.py").write_text("""
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total

def apply_discount(total, discount_percent):
    return total * (1 - discount_percent / 100)
        """)

        # 执行任务
        response = await agent.run_async(
            "Analyze main.py and suggest improvements"
        )

        # 验证响应质量
        assert response.content
        assert len(response.content) > 100
        assert "improvement" in response.content.lower() or "suggest" in response.content.lower()

    @pytest.mark.asyncio
    async def test_multi_step_task(self, agent, tmp_path):
        """多步骤任务"""
        response = await agent.run_async(
            "Create a file called 'report.txt' with the current date, "
            "then read it back to confirm it was created correctly."
        )

        # 验证文件创建
        assert (tmp_path / "report.txt").exists()
        content = (tmp_path / "report.txt").read_text()
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_long_conversation(self, agent):
        """长对话测试"""
        session_id = "long-conversation-test"

        topics = [
            "What is Python?",
            "Can you give me an example?",
            "How do I handle errors?",
            "What about async programming?",
            "Summarize what we've discussed."
        ]

        for topic in topics:
            response = await agent.run_async(
                topic,
                session_id=session_id
            )
            assert response.content

        # 验证会话历史
        session = await agent.memory.load_session(session_id)
        assert len(session.messages) >= len(topics) * 2
```

---

## Mock 策略

### Mock LLM

用于不消耗 API 调用的测试：

```python
# tests/conftest.py

import pytest
from unittest.mock import AsyncMock
from harness.llm.types import LLMResponse, TokenUsage

@pytest.fixture
def mock_llm():
    """创建 Mock LLM 客户端"""

    class MockLLMClient:
        def __init__(self):
            self.call_count = 0
            self.responses = []

        def set_responses(self, responses: list[LLMResponse]):
            self.responses = responses

        async def call(self, messages, tools=None, **kwargs):
            self.call_count += 1
            if self.responses:
                return self.responses.pop(0)

            # 默认响应
            return LLMResponse(
                content="This is a mock response.",
                tool_calls=[],
                usage=TokenUsage(input_tokens=10, output_tokens=10)
            )

    return MockLLMClient()
```

### Mock Tools

```python
# tests/fixtures/tools.py

from harness.tools import Tool, ToolResult

class MockFileTool(Tool):
    """Mock 文件工具"""

    name = "mock_file"
    description = "Mock file operations"

    def __init__(self, files: dict[str, str]):
        self.files = files

    async def execute(self, operation: str, path: str, content: str = None):
        if operation == "read":
            return ToolResult(
                success=True,
                output=self.files.get(path, "File not found")
            )
        elif operation == "write":
            self.files[path] = content
            return ToolResult(success=True, output="File written")

        return ToolResult(success=False, error="Unknown operation")
```

---

## 性能测试

### 基准测试

```python
# tests/performance/test_benchmarks.py

import pytest
import time
from harness import AgentHarness

class TestPerformance:

    @pytest.fixture
    def agent(self, tmp_path):
        return AgentHarness(
            model="mock-model",
            memory_dir=str(tmp_path)
        )

    def test_context_build_speed(self, agent, benchmark):
        """上下文构建性能"""
        # 创建大量消息
        session = create_session_with_messages(1000)

        # 基准测试
        result = benchmark(
            agent.context_builder.build,
            session
        )

        # 应该在 100ms 内完成
        assert result.time < 0.1

    def test_memory_load_speed(self, agent, benchmark, tmp_path):
        """记忆加载性能"""
        # 预填充数据
        populate_memory(agent.memory, sessions=100, messages_per_session=50)

        # 基准测试
        result = benchmark(
            agent.memory.load_session,
            "session-50"
        )

        assert result.time < 0.05

    def test_parallel_tool_execution(self, agent, benchmark):
        """并行工具执行"""
        # 注册 10 个工具
        for i in range(10):
            @agent.tools.register(f"tool_{i}")
            def tool():
                time.sleep(0.1)
                return "done"

        # 执行 10 个工具
        calls = [
            {"name": f"tool_{i}", "arguments": {}}
            for i in range(10)
        ]

        result = benchmark(
            agent.tool_executor.execute,
            calls
        )

        # 并行执行应该在 200ms 内（而非串行的 1000ms）
        assert result.time < 0.2
```

### 负载测试

```python
# tests/load/test_concurrent_sessions.py

import pytest
import asyncio
from harness import AgentHarness

class TestConcurrentLoad:

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, tmp_path):
        """并发会话测试"""
        agent = AgentHarness(
            model="mock-model",
            memory_dir=str(tmp_path)
        )

        # 模拟 100 个并发会话
        async def run_session(session_id: int):
            response = await agent.run_async(
                f"Test message {session_id}",
                session_id=f"session-{session_id}"
            )
            return session_id, response

        results = await asyncio.gather(*[
            run_session(i) for i in range(100)
        ])

        # 验证所有会话都成功
        assert len(results) == 100
        for session_id, response in results:
            assert response.content

        # 验证内存使用
        import tracemalloc
        current, peak = tracemalloc.get_traced_memory()
        assert peak < 500 * 1024 * 1024  # 峰值 < 500MB
```

---

## 测试覆盖率目标

| 模块 | 单元测试 | 集成测试 | 覆盖率目标 |
|------|----------|----------|------------|
| Agent Loop | ✅ | ✅ | 90% |
| Tool System | ✅ | ✅ | 85% |
| Memory System | ✅ | ✅ | 85% |
| Skills System | ✅ | ✅ | 80% |
| Triggers | ✅ | ✅ | 80% |
| SDK API | ✅ | ✅ | 90% |
| Infrastructure | ✅ | - | 70% |

---

## CI/CD 集成

### GitHub Actions

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit -v --cov=harness --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run integration tests
        run: pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run E2E tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: pytest tests/e2e -v --tb=short
```

---

## 测试数据管理

### Fixtures 目录结构

```
tests/
├── fixtures/
│   ├── sessions/
│   │   ├── simple_session.json
│   │   └── long_session.json
│   ├── skills/
│   │   ├── test_skill.md
│   │   └── code_review.md
│   └── tools/
│       └── mock_responses.json
├── conftest.py
└── ...
```

### 数据生成器

```python
# tests/factories.py

from factory import Factory, Faker, LazyAttribute
from harness.memory.types import Message, Session

class MessageFactory(Factory):
    class Meta:
        model = Message

    role = Faker('random_element', elements=['user', 'assistant'])
    content = Faker('sentence')
    timestamp = Faker('date_time')

class SessionFactory(Factory):
    class Meta:
        model = Session

    id = Faker('uuid4')
    messages = []

    @classmethod
    def with_messages(cls, count: int = 10, **kwargs):
        messages = [MessageFactory() for _ in range(count)]
        return cls(messages=messages, **kwargs)
```

---

## 测试最佳实践

1. **隔离性**: 每个测试独立，不依赖执行顺序
2. **可重复**: 使用固定种子或确定性数据
3. **清晰命名**: 测试名称描述测试场景
4. **单一职责**: 每个测试只验证一个行为
5. **快速失败**: 使用明确的断言，避免复杂条件
