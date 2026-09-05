# 13 - 生产就绪

## 概述

本文档评估 Harness SDK 的生产就绪程度，列出已实现和待实现的功能，以及部署最佳实践。

## Production Harness 组件状态

基于行业最佳实践（LangChain、Anthropic、Stanford IRIS Lab），一个生产级 Harness 需要 11 个核心组件。

### 组件实现状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **Orchestration Loop** | ✅ | ReAct 循环、中断恢复、熔断器、卡住检测 |
| **Tools** | ✅ | 8 内置工具 (Read/Write/Edit/Glob/Grep/Bash/WebSearch/WebFetch) + MCP |
| **Filesystem** | ✅ | 通过工具实现，支持权限检查 |
| **Bash & Code Execution** | ✅ | 沙箱执行、命令黑名单、超时控制 |
| **Sandbox** | ✅ | LightweightSandbox + SandboxExecutor |
| **Memory** | ✅ | 四层记忆 + 向量检索 + MEMORY.md 标准 + 动态系统提示 |
| **Context Management** | ✅ | ContextBuilder + SystemPromptBuilder 动态组装 |
| **Context Rot Defense** | ✅ | 渐进式技能加载 + 上下文压缩 |
| **Long-Horizon Execution** | ✅ | Lifecycle Hooks + Ralph Loop + 自验证 + Sub-Agent |
| **Error Handling** | ✅ | 熔断器 + 成本控制 + 卡住检测 |
| **Serving Layer** | ✅ | `harness.service` 模块：FastAPI 服务、健康检查、Prometheus 指标、WebSocket |

### 功能实现状态

| # | 功能 | 优先级 | 状态 | 说明 |
|---|------|--------|------|------|
| 1 | **Lifecycle Hooks** | P0 | ✅ | 8 个钩子点，支持拦截、修改、注入 |
| 2 | **动态系统提示组装** | P0 | ✅ | SystemPromptBuilder 多源组装、AGENTS.md 支持 |
| 3 | **Sub-Agent 管理** | P1 | ✅ | 创建子代理处理子任务，支持并行执行 |
| 4 | **Ralph Loop** | P1 | ✅ | 长任务循环，自动摘要 + 压缩，防止上下文焦虑 |
| 5 | **自验证钩子** | P2 | ✅ | write-code → run-tests → fix-errors 循环 |
| 6 | **渐进式技能加载** | P2 | ✅ | 三级加载：Frontmatter → Full → Reference |
| 7 | **MEMORY.md 标准** | P2 | ✅ | 持久记忆文件格式，4 种记忆类型 |
| 8 | **向量检索** | P2 | ✅ | VectorMemoryStore 语义搜索 |
| 9 | **工具输出卸载** | P3 | ⚠️ | 上下文预算优化，待实现 |
| 10 | **步骤预算** | P3 | ⚠️ | 成本预警，待实现 |

## 部署最佳实践

### 1. API 密钥管理

```python
import os
from harness import AgentHarness

# 从环境变量读取
agent = AgentHarness(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    # 或 OpenAI
    # api_key=os.environ.get("OPENAI_API_KEY"),
    # model="gpt-4o",
)
```

### 2. 成本控制

```java
import com.harness.core.HarnessConfig;
import com.harness.core.HarnessConfig.CostControlConfig;

HarnessConfig config = HarnessConfig.builder()
    .maxIterations(50)
    .costControl(CostControlConfig.builder()
        .globalDailyBudgetUsd(5.0)
        .maxTokensPerSession(500000)
        .build())
    .build();
```

### 3. 安全配置

```java
import com.harness.core.HarnessConfig;
import com.harness.core.HarnessConfig.SecurityConfig;

HarnessConfig config = HarnessConfig.builder()
    .security(SecurityConfig.builder()
        .enableSandbox(true)
        .enableInputValidation(true)
        .checkPromptInjection(true)
        .enableAuditLog(true)
        .build())
    .build();
```

### 4. 记忆管理

```java
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .memoryDir("/secure/harness/memory")
    .build();
```

### 5. 集成到 Web 服务

```python
from fastapi import FastAPI
from harness import AgentHarness

app = FastAPI()
agent = AgentHarness.from_config("harness.yaml")

@app.post("/ai")
async def ai_endpoint(message: str):
    result = await agent.run(message)
    return {"response": result.content}
```

## 监控与可观测性

### 成本监控

```java
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;
import java.util.List;

// 自定义钩子追踪成本
public class CostTrackingHook implements LifecycleHook {
    double totalCost = 0.0;

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.AFTER_LLM_CALL);
    }

    @Override
    public HookResult execute(HookContext context) {
        if (context.llmResponse() != null && context.llmResponse().usage() != null) {
            var usage = context.llmResponse().usage();
            double inputCost = usage.inputTokens() * 0.000003;
            double outputCost = usage.outputTokens() * 0.000015;
            totalCost += inputCost + outputCost;
        }
        return HookResult.continue_();
    }
}
```

### 审计日志

```python
# 审计日志自动记录到 .harness/audit/
# 包含所有工具调用、权限检查、错误事件
```

## 可靠性

### 重试策略

| 错误类型 | 策略 |
|----------|------|
| API 限流 (429) | 指数退避重试 |
| 服务器错误 (5xx) | 重试最多 3 次 |
| 超时 | 重试 1 次 |
| 上下文超长 | 自动压缩 |

### 熔断器

```python
# 连续 5 次失败触发熔断
# 可通过 HarnessConfig 配置
```

### 卡住检测

```python
# 检测重复输出和循环工具调用
# 自动注入提醒或中断
```

## 扩展性

### 自定义 LLM 客户端

```python
from harness.llm.base import LLMClient, LLMResponse
from harness import AgentHarness

class CustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "custom-model"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # 自定义实现
        ...

agent = AgentHarness(llm_client=CustomLLM())
```

### 自定义记忆后端

```python
# 使用向量检索
agent = AgentHarness(vector_store=True)

# 自定义记忆目录
agent = AgentHarness(memory_dir="/data/harness/memory")
```

### 自定义工具

```python
@agent.tool(description="自定义功能")
def my_tool(param: str) -> str:
    return f"处理: {param}"
```

## 待实现功能

### P3 - 工具输出卸载

当工具输出占用过多上下文空间时，自动卸载到外部存储，仅在需要时加载。

### P3 - 步骤预算

在执行前预估成本，并在每步检查预算余额，接近超限时发出警告。

## 与行业标准对比

详细对比见 [10-comparison.md](./10-comparison.md#production-harness-组件对比)。

| 组件 | Harness SDK | Claude Code | LangGraph |
|------|-------------|-------------|-----------|
| Orchestration Loop | ✅ | ✅ | ✅ |
| Tools | ✅ 8 内置 + MCP | ✅ 6 类 | ✅ |
| Memory | ✅ 四层 + 向量 + MEMORY.md | ✅ 四层 + MEMORY.md | ✅ 向量 |
| Context Management | ✅ 动态组装 | ✅ 优先级栈 | ✅ |
| Long-Horizon | ✅ Hooks + Ralph + Sub-Agent | ✅ Ralph + 自验证 | ✅ |
| Error Handling | ✅ 熔断 + 成本控制 | ✅ 步骤预算 | ✅ |
| Serving Layer | ✅ harness.service | ✅ CLI + Web + API | ✅ |
