# 11 - 测试详解

## 概述

Harness SDK 提供完整的测试支持，包括 MockHarness 用于单元测试、工具模拟和钩子测试。

## MockHarness

MockHarness 是 AgentHarness 的测试替身，无需调用真实 LLM 即可验证 Agent 行为。

```python
from harness.testing import MockHarness, MockResponse

# 创建 MockHarness
mock = MockHarness(responses=[
    MockResponse(content="模拟响应内容"),
])
```

### MockResponse

```python
@dataclass
class MockResponse:
    content: str = ""                          # 文本响应
    tool_calls: list[ToolCall] = field(default_factory=list)  # 工具调用（ToolCall 对象）
    stop_reason: StopReason = StopReason.END_TURN  # 停止原因（StopReason 枚举）
    input_tokens: int = 100                    # 模拟输入 token
    output_tokens: int = 50                     # 模拟输出 token

    # 使用 tool_calls 模拟 LLM 返回工具调用
    # ToolCall 格式: ToolCall(id="1", name="read", arguments={"path": "test.py"})
```

### 基本使用

```python
from harness.testing import MockHarness, MockResponse
from harness.types import ToolCall, StopReason

# 简单文本响应
mock = MockHarness(responses=[
    MockResponse(content="分析完成：代码质量良好"),
])

result = await mock.run("分析代码")
assert result.content == "分析完成：代码质量良好"

# 多步工具调用模拟
mock = MockHarness(responses=[
    MockResponse(
        tool_calls=[ToolCall(id="1", name="read", arguments={"path": "main.py"})],
        stop_reason=StopReason.TOOL_USE,
    ),
    MockResponse(content="文件已读取并分析完成"),
])

# 提供工具调用的模拟结果
mock.add_tool_result("read", "main.py 的内容")

result = await mock.run("读取并分析 main.py")
assert result.content == "文件已读取并分析完成"
```

### 添加响应与工具结果（替代 expect/respond）

MockHarness **没有** `expect()` / `respond()` / `register_tool()` 方法。请使用以下真实 API：

```python
from harness.testing import MockHarness, MockResponse
from harness.types import ToolCall, StopReason

mock = MockHarness()

# 预置多个响应
mock.add_response(MockResponse(content="分析结果：代码质量良好"))
mock.add_response(MockResponse(content="Bug 已修复"))

# 也可以一次性设置（清空已有响应）
mock.set_responses([
    MockResponse(content="分析结果：代码质量良好"),
    MockResponse(content="Bug 已修复"),
])

# 对于工具调用，提供自动工具结果
mock.add_response(MockResponse(
    tool_calls=[ToolCall(id="1", name="bash", arguments={"command": "echo hi"})],
    stop_reason=StopReason.TOOL_USE,
))
mock.add_tool_result("bash", "hi")

result1 = await mock.run("分析代码")
result2 = await mock.run("修复 bug")

assert result1.content == "分析结果：代码质量良好"
assert result2.content == "Bug 已修复"
```

### MockHarness 公开 API

| 方法 | 说明 |
|------|------|
| `add_response(response: MockResponse)` | 追加一个模拟响应 |
| `add_tool_result(tool_name, result)` | 为指定工具名提供自动返回结果 |
| `set_responses(responses)` | 覆盖所有响应并重置索引 |
| `run(prompt, session_id=None, max_iterations=10)` | 运行，返回 `LoopResult` |
| `run_goal(goal, **kwargs)` | 目标模式运行，返回 `GoalResult` |
| `activate_skill(skill_name)` | 激活技能（测试替身，无副作用） |
| `get_recordings()` | 获取录制列表 |
| `save_recording(path)` | 保存录制到文件 |
| `load_recording(path)` | 从文件加载录制并回放 |
| `reset()` | 重置所有状态 |

## 工具测试

### 自定义工具测试

```python
from harness import AgentHarness
from harness.tools.base import Tool, ToolResult, ToolContext
from pathlib import Path

class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "计算数学表达式"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {"type": "string"},
            },
            "required": ["expression"],
        }

    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        try:
            result = eval(arguments["expression"])  # 仅用于演示，生产环境不推荐
            return ToolResult(
                tool_call_id="",
                success=True,
                content=str(result),
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=str(e),
            )

# 直接测试工具
tool = CalculatorTool()
ctx = ToolContext(
    session_id="test",
    working_directory=Path("."),
    permissions=None,  # PermissionSet 实例
)
result = await tool.execute({"expression": "2 + 2"}, ctx)
assert result.content == "4"
assert result.success
```

### 在 MockHarness 中测试工具

MockHarness 不执行真实工具，而是在收到匹配的工具调用时返回通过
`add_tool_result(tool_name, result)` 注册的模拟结果：

```python
from harness.testing import MockHarness, MockResponse
from harness.types import ToolCall, StopReason

mock = MockHarness()

# 模拟 LLM 调用工具，并提供模拟结果
mock.add_response(MockResponse(
    tool_calls=[ToolCall(id="1", name="calculator", arguments={"expression": "2+2"})],
    stop_reason=StopReason.TOOL_USE,
))
mock.add_tool_result("calculator", "4")

result = await mock.run("计算 2+2")
assert result.content == "4"
```

## 钩子测试

`HookContext` 的字段为 `tool_name` / `tool_args` / `tool_result`（**没有** `tool_call` 属性）。
MockHarness 不提供 `hook` 装饰器；钩子通过 `AgentHarness.add_hook()` 注册：

```python
from harness import AgentHarness
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

# 记录钩子调用
hook_calls = []

class TrackToolHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, ctx: HookContext) -> HookResult:
        hook_calls.append(ctx.tool_name)
        return HookResult.continue_()

agent = AgentHarness()
agent.add_hook(TrackToolHook())

result = await agent.run("读取文件")
assert len(hook_calls) > 0  # 记录了被调用的工具名
```

## 配置测试

```python
from harness import AgentHarness, HarnessConfig

# 测试特定配置
config = HarnessConfig(
    max_iterations=5,
    enable_network=False,
)

agent = AgentHarness(config=config)
assert agent.config.max_iterations == 5
assert agent.config.provider == "auto"  # HarnessConfig 默认 provider 为 "auto"
```

## 集成测试

### 使用真实 LLM 的集成测试

```python
import pytest
from harness import AgentHarness

@pytest.fixture
def agent():
    return AgentHarness(
        api_key="test-key",
        model="claude-haiku-4-5",  # 使用便宜模型
    )

@pytest.mark.asyncio
async def test_basic_conversation(agent):
    result = await agent.run("Hello")
    assert result.content
    assert result.iterations >= 1

@pytest.mark.asyncio
async def test_tool_usage(agent):
    result = await agent.run("读取 README.md 的内容")
    # LoopResult 没有 tool_calls 字段；工具调用体现在 messages 中
    tool_messages = [m for m in result.messages if m.role == "tool"]
    assert len(tool_messages) > 0
```

### 端到端测试

```python
@pytest.mark.asyncio
async def test_full_workflow():
    agent = AgentHarness()

    # 添加自定义工具
    @agent.tool(description="获取天气")
    def get_weather(city: str) -> str:
        return f"{city}: 晴天, 25°C"

    result = await agent.run("北京今天天气怎么样？")
    assert "25" in result.content or "晴" in result.content
```

## RecordingHarness（录制与回放）

RecordingHarness 用于录制真实的 LLM 交互，以便后续回放测试。

### Python SDK

```python
from harness import AgentHarness
from harness.testing import RecordingHarness

# 创建 AgentHarness 和录制器
agent = AgentHarness(model="claude-sonnet-4-6")
recorder = RecordingHarness(agent)

# 开始录制
recorder.start_recording("test_session")

# 运行 Agent（所有交互会被录制）
result = await agent.run("读取 README.md 并分析")

# 保存录制
path = recorder.save_recording("my_test_fixture")
print(f"录制已保存到: {path}")

# 获取录制摘要
summary = recorder.get_recording_summary()
print(f"总交互数: {summary['total_interactions']}")
print(f"LLM 请求: {summary['llm_requests']}")
print(f"工具调用: {summary['tool_calls']}")
print(f"Token 使用: 输入 {summary['total_input_tokens']}, 输出 {summary['total_output_tokens']}")
```

### Java SDK

```java
import com.harness.recording.RecordingHarness;
import com.harness.recording.RecordingConfig;
import com.harness.recording.RecordedInteraction;
import com.harness.sdk.AgentHarness;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

// 创建 AgentHarness 和录制器
AgentHarness agent = new AgentHarness(config);
RecordingHarness recorder = new RecordingHarness(agent, new RecordingConfig.Builder()
    .recordingDir(Path.of(".harness_recordings"))
    .autoSave(true)
    .maxRecordingSize(100)
    .build());

// 开始录制
recorder.startRecording("test_session");

// 录制 LLM 请求
recorder.recordLlmRequest(messages, tools, systemPrompt);

// 录制工具结果
recorder.recordToolResult("call_123", "read", "文件内容", true);

// 获取录制摘要
Map<String, Object> summary = recorder.getRecordingSummary();
System.out.println("总交互数: " + summary.get("total_interactions"));

// 获取所有交互
List<RecordedInteraction> interactions = recorder.getInteractions();
for (RecordedInteraction i : interactions) {
    System.out.println(i.getType() + " at " + i.getTimestamp());
}

// 保存录制
Path path = recorder.saveRecording("my_test_fixture");
```

### RecordingConfig 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `recording_dir` | Path | `.harness_recordings` | 录制文件存储目录 |
| `auto_save` | bool | true | 是否自动保存 |
| `include_metadata` | bool | true | 是否包含元数据 |
| `max_recording_size` | int | 100 | 最大交互记录数 |

### 使用场景

1. **创建测试固件**: 从真实交互生成测试数据
2. **调试 Agent 行为**: 分析 Agent 的决策过程
3. **成本分析**: 追踪 Token 使用量
4. **回放测试**: 使用录制数据驱动 MockHarness

## 测试最佳实践

### 1. 使用 MockHarness 进行单元测试

```python
# 单元测试不需要真实 LLM
mock = MockHarness(responses=[MockResponse(content="OK")])
result = await mock.run("test")
assert result.content == "OK"
```

### 2. 隔离外部依赖

```python
# Mock 外部服务 - 使用 MCPManager 模拟
from harness.mcp.manager import MCPManager, MCPServerConfig

mock = MockHarness()

# 如果需要测试 MCP 集成，可以创建 MCPManager 模拟
# 但通常测试中不需要真实 MCP 连接
# 可以直接模拟工具行为
mock.add_tool_result("mcp_github_search_issues", "模拟的 issue 列表")
```

### 3. 测试钩子逻辑

```python
# 测试钩子的拦截行为
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

class BlockBashHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, ctx: HookContext) -> HookResult:
        if ctx.tool_name == "bash":
            return HookResult.abort("blocked")
        return HookResult.continue_()

agent = AgentHarness()
agent.add_hook(BlockBashHook())
```

### 4. 测试错误处理

```python
# 模拟工具错误
from harness.testing import MockHarness, MockResponse
from harness.types import ToolCall, StopReason

mock = MockHarness(responses=[
    MockResponse(
        tool_calls=[ToolCall(id="1", name="bash", arguments={"command": "invalid"})],
        stop_reason=StopReason.TOOL_USE,
    ),
    MockResponse(content="命令执行失败，已尝试替代方案"),
])

# 提供导致错误的工具结果
mock.add_tool_result("bash", "command not found: invalid")

result = await mock.run("执行无效命令")
assert result.content
```
