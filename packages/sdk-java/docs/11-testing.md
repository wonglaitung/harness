# 11 - 测试详解

## 概述

Harness SDK 提供完整的测试支持，包括 MockHarness 用于单元测试、工具模拟和钩子测试。

## MockHarness

MockHarness 是 AgentHarness 的测试替身，无需调用真实 LLM 即可验证 Agent 行为。

### Java MockHarness

```java
import com.harness.core.MockHarness;
import com.harness.core.MockResponse;

// 创建 MockHarness 并添加预定义响应
MockHarness mock = new MockHarness();
mock.addResponse(MockResponse.text("Hello!"));

// 运行
MockHarness.MockLoopResult result = mock.run("Say hello").join();
assert result.finalResponse().equals("Hello!");
```

### MockResponse

```java
import com.harness.core.MockResponse;
import com.harness.types.ToolCall;
import java.util.Map;

// 文本响应
MockResponse textResponse = MockResponse.text("分析完成");

// 带 token 统计的文本响应
MockResponse textResponse2 = MockResponse.text("OK", 100, 50);

// 工具调用响应
MockResponse toolResponse = MockResponse.toolUse(
    "call_123", "read", Map.of("path", "src/Main.java")
);

// 使用 Builder
MockResponse response = MockResponse.builder()
    .content("分析完成")
    .inputTokens(100)
    .outputTokens(50)
    .build();
```

### 基本使用

```java
import com.harness.core.MockHarness;
import com.harness.core.MockResponse;

// 简单文本响应
MockHarness mock = new MockHarness();
mock.addResponse(MockResponse.text("分析完成：代码质量良好"));
MockHarness.MockLoopResult result = mock.run("分析代码").join();
assert result.finalResponse().equals("分析完成：代码质量良好");

// 多步工具调用模拟
mock.reset();
mock.addResponse(MockResponse.toolUse("call_1", "read", Map.of("path", "main.py")));
mock.addResponse(MockResponse.text("文件已读取并分析完成"));
result = mock.run("读取并分析 main.py").join();
```

### 自动工具结果

```java
MockHarness mock = new MockHarness();

// 为特定工具设置自动返回结果
mock.addToolResult("read", "文件内容...");
mock.addToolResult("grep", "找到 3 个匹配");

// 配合 MockResponse 使用
mock.addResponse(MockResponse.toolUse("call_1", "read", Map.of("path", "test.py")));
mock.addResponse(MockResponse.text("已分析完成"));

MockHarness.MockLoopResult result = mock.run("读取并分析 test.py").join();
```

## 工具测试

### 自定义工具测试

**Java SDK**:

```java
import com.harness.core.Tool;
import com.harness.types.ToolResult;
import com.harness.core.ToolContext;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class CalculatorTool implements Tool {
    @Override
    public String name() { return "calculator"; }

    @Override
    public String description() { return "计算数学表达式"; }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of("expression", Map.of("type", "string")),
            "required", List.of("expression")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        try {
            String expr = (String) args.get("expression");
            // 简单实现：仅用于演示
            return CompletableFuture.completedFuture(
                ToolResult.success(ctx.sessionId(), "4")
            );
        } catch (Exception e) {
            return CompletableFuture.completedFuture(
                ToolResult.failure(ctx.sessionId(), e.getMessage())
            );
        }
    }
}

// 测试工具
CalculatorTool tool = new CalculatorTool();
ToolContext ctx = ToolContext.of(".", "test-session");
ToolResult result = tool.execute(Map.of("expression", "2 + 2"), ctx).join();
assert result.content().equals("4");
assert result.success();
```

### 在 MockHarness 中测试工具

```java
import com.harness.core.MockHarness;
import com.harness.core.MockResponse;
import java.util.Map;

MockHarness mock = new MockHarness();

// 设置工具自动返回
mock.addToolResult("calculator", "4");

// 模拟 LLM 调用工具
mock.addResponse(MockResponse.toolUse("call_1", "calculator", Map.of("expression", "2+2")));
mock.addResponse(MockResponse.text("计算结果是 4"));

MockHarness.MockLoopResult result = mock.run("计算 2+2").join();
assert result.finalResponse().contains("4");
```

## 钩子测试

**Java SDK**:

```java
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

// 自定义钩子用于测试
public class TrackingHook implements LifecycleHook {
    final List<String> hookCalls = new ArrayList<>();

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        hookCalls.add(context.toolName());
        return HookResult.continue_();
    }
}

// 测试钩子
TrackingHook hook = new TrackingHook();
MockHarness mock = new MockHarness();
// 在实际 AgentHarness 中注册 hook 并验证 hookCalls
```

## 配置测试

```java
import com.harness.core.HarnessConfig;

// 测试特定配置
HarnessConfig config = HarnessConfig.builder()
    .maxIterations(5)
    .toolTimeout(60.0)
    .build();

// 验证配置值
assert config.getMaxIterations() == 5;
assert config.getToolTimeout() == 60.0;
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

## 测试最佳实践

### 1. 使用 MockHarness 进行单元测试

```java
// 单元测试不需要真实 LLM
MockHarness mock = new MockHarness();
mock.addResponse(MockResponse.text("OK"));
MockHarness.MockLoopResult result = mock.run("test").join();
assert result.success();
```

### 2. 隔离外部依赖

```java
// 使用 MockHarness 模拟工具行为
MockHarness mock = new MockHarness();

// 直接模拟工具返回
mock.addToolResult("mcp_github_search_issues", "模拟的 issue 列表");
mock.addResponse(MockResponse.toolUse("call_1", "mcp_github_search_issues", Map.of()));
mock.addResponse(MockResponse.text("已获取 issue 列表"));

MockHarness.MockLoopResult result = mock.run("查看 GitHub issues").join();
```

### 3. 测试钩子逻辑

```java
// 测试钩子的拦截行为
public class DangerousToolBlocker implements LifecycleHook {
    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        if ("bash".equals(context.toolName())) {
            return HookResult.abort("Bash blocked in test");
        }
        return HookResult.continue_();
    }
}
```

### 4. 测试错误处理

```java
// 模拟工具错误
MockHarness mock = new MockHarness();
mock.addToolResult("bash", "Command failed: exit code 1");
mock.addResponse(MockResponse.toolUse("call_1", "bash", Map.of("command", "invalid")));
mock.addResponse(MockResponse.text("命令执行失败，已尝试替代方案"));

MockHarness.MockLoopResult result = mock.run("执行无效命令").join();
assert result.finalResponse().contains("失败");
```
