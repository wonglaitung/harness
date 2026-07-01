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
    content: str | None = None              # 文本响应
    tool_calls: list[dict] | None = None    # 工具调用响应
    stop_reason: str = "end_turn"           # 停止原因

    # 使用 tool_calls 模拟 LLM 返回工具调用
    # tool_calls 格式: [{"name": "read", "arguments": {"file_path": "test.py"}}]
```

### 基本使用

```python
from harness.testing import MockHarness, MockResponse

# 简单文本响应
mock = MockHarness(responses=[
    MockResponse(content="分析完成：代码质量良好"),
])

result = await mock.run("分析代码")
assert result.content == "分析完成：代码质量良好"

# 多步工具调用模拟
mock = MockHarness(responses=[
    MockResponse(tool_calls=[{"name": "read", "arguments": {"file_path": "main.py"}}]),
    MockResponse(content="文件已读取并分析完成"),
])

result = await mock.run("读取并分析 main.py")
```

### 期望-响应模式

```python
mock = MockHarness()

# 设置期望和响应
mock.expect("分析代码").respond("分析结果：代码质量良好")
mock.expect("修复 bug").respond("Bug 已修复")

result1 = await mock.run("分析代码")
result2 = await mock.run("修复 bug")

assert result1.content == "分析结果：代码质量良好"
assert result2.content == "Bug 已修复"
```

## 工具测试

### 自定义工具测试

```python
from harness import AgentHarness
from harness.tools.base import Tool, ToolResult, ToolContext

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

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            result = eval(args["expression"])  # 仅用于演示，生产环境不推荐
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(output="", error=str(e))

# 直接测试工具
tool = CalculatorTool()
ctx = ToolContext(working_dir=".", sandbox=None, permissions=None, session_id="test")
result = await tool.execute({"expression": "2 + 2"}, ctx)
assert result.output == "4"
assert not result.is_error
```

### 在 MockHarness 中测试工具

```python
from harness.testing import MockHarness, MockResponse

mock = MockHarness()
mock.register_tool(CalculatorTool())

# 模拟 LLM 调用工具
mock.expect("计算 2+2").respond_with_tool("calculator", {"expression": "2+2"})
```

## 钩子测试

```python
from harness.testing import MockHarness
from harness.core.hooks import HookPoint, HookContext

mock = MockHarness()

# 记录钩子调用
hook_calls = []

@mock.hook(HookPoint.BEFORE_TOOL_EXECUTE)
async def track_tool_calls(ctx: HookContext):
    hook_calls.append(ctx.tool_call)
    return ctx

result = await mock.run("读取文件")
assert len(hook_calls) > 0
```

## 配置测试

```python
from harness import AgentHarness, HarnessConfig

# 测试特定配置
config = HarnessConfig(
    max_iterations=5,
    max_cost_per_run=0.5,
)

agent = AgentHarness(config=config)
assert agent.config.max_iterations == 5
assert agent.config.max_cost_per_run == 0.5
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
    assert len(result.tool_calls) > 0
    assert any(tc.name == "read" for tc in result.tool_calls)
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
@mock.hook(HookPoint.BEFORE_TOOL_EXECUTE)
async def block_dangerous(ctx: HookContext):
    if ctx.tool_call and ctx.tool_call["name"] == "bash":
        return None  # 阻止执行
    return ctx
```

### 4. 测试错误处理

```python
# 模拟工具错误
mock = MockHarness(responses=[
    MockResponse(tool_calls=[{"name": "bash", "arguments": {"command": "invalid"}}]),
    MockResponse(content="命令执行失败，已尝试替代方案"),
])

result = await mock.run("执行无效命令")
assert result.content
```
