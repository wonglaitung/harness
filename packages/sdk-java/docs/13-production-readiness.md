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

```python
from harness import AgentHarness, HarnessConfig

agent = AgentHarness(
    config=HarnessConfig(
        max_cost_per_run=5.0,      # 单次运行最多 $5
        max_tokens_per_run=500000, # 单次运行最多 500K tokens
        max_iterations=50,         # 最多 50 步
    ),
)
```

### 3. 安全配置

```python
from harness import AgentHarness, HarnessConfig
from harness.security.sandbox import PermissionSet, PermissionLevel

agent = AgentHarness(
    config=HarnessConfig(
        sandbox_enabled=True,
        bash_timeout=60000,
        bash_blacklist=["rm -rf /", "sudo", "mkfs"],
    ),
    permissions=PermissionSet(
        max_permission=PermissionLevel.EXECUTE,
        denied_tools={"bash"},  # 按需禁用
    ),
)
```

### 4. 记忆管理

```python
agent = AgentHarness(
    memory_dir="/secure/harness/memory",  # 指定安全目录
    vector_store=True,                     # 启用向量检索
)
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

```python
from harness import AgentHarness
from harness.core.hooks import HookPoint, HookContext

agent = AgentHarness()

cost_tracker = {"total": 0.0}

@agent.hook(HookPoint.AFTER_LLM_CALL)
async def track_cost(ctx: HookContext):
    if ctx.response and ctx.response.usage:
        input_cost = ctx.response.usage.input_tokens * 0.000003
        output_cost = ctx.response.usage.output_tokens * 0.000015
        cost_tracker["total"] += input_cost + output_cost
    return ctx

result = await agent.run("分析代码")
print(f"本次运行成本: ${cost_tracker['total']:.4f}")
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
