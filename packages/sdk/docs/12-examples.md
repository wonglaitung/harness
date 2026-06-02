# 12 - 示例代码

## 概述

本文档提供 Harness SDK 的完整使用示例，涵盖从基础用法到高级功能的各种场景。

## 基础用法

### 最简 Agent

```python
import asyncio
from harness import AgentHarness

async def main():
    agent = AgentHarness()
    result = await agent.run("你好，请介绍一下你自己")
    print(result.content)

asyncio.run(main())
```

### 使用 OpenAI 模型

```python
from harness import AgentHarness

agent = AgentHarness(
    api_key="sk-...",
    model="gpt-4o",
    provider="openai",
)

result = await agent.run("分析这段代码的性能问题")
```

### 使用第三方 OpenAI 兼容 API

```python
from harness import AgentHarness

agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",
    api_key="your-api-key",
    model="your-model-name",
    # provider 自动检测为 openai（因为不是 claude-* 前缀）
)

result = await agent.run("翻译以下文本为英文")
```

### 流式输出

```python
from harness import AgentHarness

agent = AgentHarness()

async for chunk in agent.stream("写一篇关于 AI 的短文"):
    print(chunk, end="", flush=True)
```

### 从配置文件创建

```python
from harness import AgentHarness

agent = AgentHarness.from_config("harness.yaml")
result = await agent.run("检查项目状态")
```

## 自定义工具

### 装饰器注册

```python
from harness import AgentHarness

agent = AgentHarness()

@agent.tool(description="获取天气信息")
def get_weather(city: str) -> str:
    """获取指定城市的天气"""
    # 实际实现调用天气 API
    return f"{city}: 晴天, 25°C"

@agent.tool(
    description="发送邮件",
    permission_level="network",
)
async def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件"""
    # 实际实现调用邮件 API
    return f"邮件已发送至 {to}"

result = await agent.run("查一下北京天气，然后发邮件给 team@example.com 通知他们")
```

### 继承 Tool 类

```python
from harness import AgentHarness
from harness.tools.base import Tool, ToolResult, ToolContext, PermissionLevel

class DatabaseTool(Tool):
    @property
    def name(self) -> str:
        return "db_query"

    @property
    def description(self) -> str:
        return "执行数据库查询"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL 查询"},
                "database": {"type": "string", "description": "数据库名"},
            },
            "required": ["query"],
        }

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.DANGEROUS

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            result = await execute_sql(args.get("database", "default"), args["query"])
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(output="", error=str(e))

agent = AgentHarness()
agent.register_tool(DatabaseTool())
```

## Lifecycle Hooks

### 请求审批

```python
from harness import AgentHarness
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

agent = AgentHarness()

class ApprovalHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.BEFORE_TOOL_EXECUTE]
    
    async def execute(self, ctx: HookContext) -> HookResult:
        """危险操作需要用户确认"""
        if ctx.tool_name in ("bash", "write"):
            command = ctx.tool_args.get("command", "") if ctx.tool_name == "bash" else str(ctx.tool_args)
            print(f"⚠️ Agent 想要执行 {ctx.tool_name}: {command}")
            confirm = input("允许？(y/n): ")
            if confirm.lower() != "y":
                return HookResult.abort("用户拒绝了操作")
        return HookResult.continue_()

agent.add_hook(ApprovalHook())
result = await agent.run("删除临时文件")
```

### 日志记录

```python
import logging
from harness import AgentHarness
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

logger = logging.getLogger("harness")
agent = AgentHarness()

class LoggingHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.AFTER_LLM_CALL, HookPoint.AFTER_TOOL_EXECUTE]
    
    async def execute(self, ctx: HookContext) -> HookResult:
        if ctx.hook_point == HookPoint.AFTER_LLM_CALL and ctx.llm_response:
            logger.info(f"LLM 调用: {ctx.llm_response.usage.input_tokens} 输入 tokens, {ctx.llm_response.usage.output_tokens} 输出 tokens")
        elif ctx.hook_point == HookPoint.AFTER_TOOL_EXECUTE and ctx.tool_result:
            logger.info(f"工具 {ctx.tool_name}: {len(ctx.tool_result.output)} 字符")
        return HookResult.continue_()

agent.add_hook(LoggingHook())
```

### 阻止过早退出

```python
from harness import AgentHarness
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

agent = AgentHarness()

class PreventEarlyExitHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.ON_EXIT_ATTEMPT]
    
    async def execute(self, ctx: HookContext) -> HookResult:
        """如果任务未完成，阻止 Agent 草率退出"""
        if ctx.messages and "完成" not in ctx.messages[-1].get("content", ""):
            # 注入消息让 Agent 继续工作
            return HookResult.inject_message({
                "role": "user",
                "content": "请继续完成任务，不要提前结束。"
            })
        return HookResult.continue_()

agent.add_hook(PreventEarlyExitHook())
```

## 自验证

```python
from harness import AgentHarness
from harness.core.hooks import HookPoint
from harness.core.self_verification import SelfVerificationHook

agent = AgentHarness()
verification = SelfVerificationHook(
    agent,
    verify_command="pytest -x",
    max_retries=3,
)

@agent.hook(HookPoint.AFTER_TOOL_EXECUTE)
async def auto_verify(ctx: HookContext):
    """写文件后自动运行测试"""
    if ctx.tool_call and ctx.tool_call.get("name") == "write":
        result = await verification.verify(ctx)
        if not result.passed:
            ctx.messages.append({
                "role": "user",
                "content": f"测试失败，请修复：\n{result.output}"
            })
    return ctx

result = await agent.run("实现一个计算器类并确保测试通过")
```

## Ralph Loop（长任务）

```python
from harness import AgentHarness
from harness.core.ralph_loop import RalphLoop

agent = AgentHarness()

# 使用 Ralph Loop 执行长任务
ralph = RalphLoop(
    agent,
    max_iterations=100,
    summary_interval=10,
    compression_threshold=80000,
)

result = await ralph.run("重构整个认证模块，添加 OAuth2 支持，确保所有测试通过")
print(f"完成步数: {result.iterations}")
print(f"总成本: ${result.total_cost:.4f}")
```

## Sub-Agent

```python
import asyncio
from harness import AgentHarness
from harness.core.subagent import SubAgentManager

agent = AgentHarness()
sub_agent = SubAgentManager(agent)

# 并行执行多个子任务
results = await asyncio.gather(
    sub_agent.create("分析代码质量", tools=["read", "grep"]),
    sub_agent.create("检查安全漏洞", tools=["read", "grep"]),
    sub_agent.create("生成 API 文档", tools=["read", "write"]),
)

for r in results:
    print(f"任务: {r.task}")
    print(f"成功: {r.success}")
    print(f"结果: {r.content[:100]}...")
```

## 技能系统

### 使用技能

```python
from harness import AgentHarness

agent = AgentHarness(skill_dirs=[".harness/skills"])

# 指定技能
result = await agent.run("审查这段代码", skills=["code-review"])

# 自动选择技能
result = await agent.run("检查安全漏洞")
```

### 创建技能文件

```markdown
---
name: code-review
description: Review code for issues and improvements
tools: [read, grep, glob]
priority: 10
---

# Code Review Skill

You are an expert code reviewer. Your task is to:
1. Read the code files carefully
2. Identify bugs, security issues, and performance problems
3. Provide actionable suggestions with specific fixes

## Guidelines
- Focus on correctness first, then performance
- Always check for security vulnerabilities
- Provide concrete fix suggestions, not just complaints
- Rate severity: Critical / Warning / Info
```

## MCP 集成

### 使用 MCP 服务器

```python
from harness import AgentHarness, MCPManager, MCPServerConfig

agent = AgentHarness()

# 创建 MCP 管理器
mcp_manager = MCPManager(tool_registry=agent._tool_registry)

# 添加 MCP 服务器
github_config = MCPServerConfig(
    name="github",
    transport="stdio",
    command="mcp-github",
    env={"GITHUB_TOKEN": "your-token-here"},
)
mcp_manager.add_server(github_config)

slack_config = MCPServerConfig(
    name="slack",
    transport="stdio",
    command="mcp-slack",
    args=["--token", "$SLACK_TOKEN"],
    env={"SLACK_TOKEN": "your-slack-token"},
)
mcp_manager.add_server(slack_config)

# 连接所有服务器
await mcp_manager.connect_all()

result = await agent.run("查看最近的 GitHub issue 并在 Slack 通知团队")
```

### 自定义 LLM 客户端

```python
from harness import AgentHarness
from harness.llm.base import LLMClient, LLMResponse, TokenUsage

class MyCustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-custom-model"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # 实现自定义 LLM 调用
        response_text = await my_api_call(messages, tools, system)
        return LLMResponse(
            content=response_text,
            tool_calls=None,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
            stop_reason="end_turn",
        )

agent = AgentHarness(llm_client=MyCustomLLM())
result = await agent.run("你好")
```

## 触发器

### Cron 触发

```python
from harness import AgentHarness
from harness.triggers.cron import CronTrigger

agent = AgentHarness()

# 每天 9:00 生成日报
cron = CronTrigger(
    name="daily-report",
    schedule="0 9 * * *",
    task="生成昨日工作日报，包括完成的任务和待处理的事项",
)

agent.triggers.register(cron)
await agent.triggers.start_all()
```

### Webhook 触发

```python
from harness import AgentHarness
from harness.triggers.webhook import WebhookTrigger

agent = AgentHarness()

github = WebhookTrigger(
    name="github-pr",
    path="/webhook/github",
    task="审查 PR #{event.pull_request.number}",
    skills=["code-review"],
)

agent.triggers.register(github)
```

## 安全配置

### 最小权限

```python
from harness import AgentHarness
from harness.security.sandbox import PermissionSet, PermissionLevel

agent = AgentHarness(
    permissions=PermissionSet(
        max_permission=PermissionLevel.READ,
        denied_tools={"bash"},
    ),
)
```

### 成本控制

```python
from harness import AgentHarness, HarnessConfig

agent = AgentHarness(
    config=HarnessConfig(
        max_cost_per_run=5.0,
        max_tokens_per_run=500000,
        max_iterations=30,
    ),
)
```

## FastAPI 集成

```python
from fastapi import FastAPI
from harness import AgentHarness

app = FastAPI()
agent = AgentHarness()

@app.post("/ai")
async def ai_endpoint(message: str):
    result = await agent.run(message)
    return {"response": result.content}

@app.post("/ai/stream")
async def ai_stream_endpoint(message: str):
    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)
    return {"response": "".join(chunks)}
```

## 测试

```python
from harness.testing import MockHarness, MockResponse

# 简单 mock
mock = MockHarness(responses=[
    MockResponse(content="分析完成"),
])
result = await mock.run("分析代码")
assert result.content == "分析完成"

# 期望-响应模式
mock = MockHarness()
mock.expect("分析代码").respond("代码质量良好")
result = await mock.run("分析代码")
assert result.content == "代码质量良好"
```
