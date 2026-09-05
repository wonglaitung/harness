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
from harness.core.hooks import LifecycleHook, HookResult

agent = AgentHarness()
verification = SelfVerificationHook(
    agent,
    verify_command="pytest -x",
    max_retries=3,
)

class AutoVerifyHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.AFTER_TOOL_EXECUTE]

    async def execute(self, ctx: HookContext) -> HookResult:
        """写文件后自动运行测试"""
        if ctx.tool_name == "write" and ctx.tool_result is not None:
            result = await verification.verify(ctx)
            if not result.passed and ctx.messages is not None:
                ctx.messages.append({
                    "role": "user",
                    "content": f"测试失败，请修复：\n{result.output}"
                })
        return HookResult.continue_()

agent.add_hook(AutoVerifyHook())

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
print(f"Token 使用: 输入 {result.token_usage.input_tokens}, 输出 {result.token_usage.output_tokens}")
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
from pathlib import Path
from harness import AgentHarness

agent = AgentHarness()
# 从指定目录发现技能（自动加载元数据，匹配时注入 system prompt）
agent.load_skills_from_dir(Path(".harness/skills"))

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

# 权限通过 ToolContext.permissions 在工具执行时校验，
# 可在自定义工具中根据 PermissionSet 判断，而非作为 AgentHarness 构造参数
from harness.security.sandbox import PermissionSet, PermissionLevel

permissions = PermissionSet(
    max_permission=PermissionLevel.READ,
    denied_tools={"bash"},
)
```

### 成本控制

```python
from harness import AgentHarness, HarnessConfig, CostControlConfig

agent = AgentHarness(
    config=HarnessConfig(
        max_iterations=30,
        cost_control=CostControlConfig(
            max_tokens_per_session=500000,
            global_daily_budget_usd=5.0,
        ),
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

# 使用 add_response 设置响应（MockHarness 没有 expect/respond API）
mock = MockHarness()
mock.add_response(MockResponse(content="代码质量良好"))
result = await mock.run("分析代码")
assert result.content == "代码质量良好"
```

## 全局记忆

### 配置全局记忆文件

```python
from harness import AgentHarness, HarnessConfig
from pathlib import Path

# 配置全局 MEMORY.md 文件路径
config = HarnessConfig(
    model="claude-sonnet-4-6",
    memory_md_path=Path.home() / ".harness" / "MEMORY.md",
)

agent = AgentHarness(config=config)

# Agent 会自动加载全局记忆到 system prompt
result = await agent.run("帮我重构这段代码")
```

### 全局记忆文件格式

```markdown
# MEMORY.md

## User Profile
- 使用 Windows 操作系统
- 偏好 Python 语言
- 使用 VS Code 编辑器

## Key Decisions
- 2024-01-15: 选择 SQLite 作为会话存储

## Learned Patterns
- 用户喜欢详细的代码示例
- 用户偏好中文回复

## Project Context
- 项目使用 Python 3.11+
- 代码风格遵循 Black 格式化
```

### 即时更新特性

全局记忆文件在每次 `run()` 调用时重新读取，修改后立即生效：

```python
from harness import AgentHarness
from harness.memory.memory_file import MemoryFileManager, MemoryCategory, MemoryEntry, MemorySource
from pathlib import Path

agent = AgentHarness(
    memory_md_path=Path.home() / ".harness" / "MEMORY.md",
)

# 第一次调用 - 加载当前记忆
result1 = await agent.run("分析项目结构")

# 更新记忆文件
manager = MemoryFileManager(Path.home() / ".harness")
manager.add_entry(MemoryEntry(
    category=MemoryCategory.USER_PROFILE,
    content="偏好简洁的代码注释",
    source=MemorySource.USER_INPUT,
))

# 第二次调用 - 自动加载更新后的记忆
result2 = await agent.run("添加函数注释")
```

## Loop Engineering

Loop Engineering 是目标驱动执行范式：用户描述目标，Agent 自主运行直到完成。

### 基础用法：目标驱动执行

```python
import asyncio
from harness import AgentHarness
from harness.loop import GoalStatus

async def main():
    agent = AgentHarness()

    # 用户描述目标，Agent 自主运行直到完成
    result = await agent.run_goal(
        goal="修复 src/ 目录下所有类型错误",
        max_iterations=50,
    )

    if result.status == GoalStatus.ACHIEVED:
        print(f"目标达成！共 {result.total_iterations} 轮迭代")
    elif result.status == GoalStatus.MAX_ITERATIONS:
        print(f"达到最大迭代次数 {result.total_iterations}")
    else:
        print(f"目标未达成: {result.status.value}")

asyncio.run(main())
```

### 自定义验证器

使用自定义函数验证目标是否达成：

```python
import asyncio
from harness import AgentHarness
from harness.loop import GoalStatus

async def check_coverage(result) -> bool:
    """检查测试覆盖率是否达到 80%"""
    proc = await asyncio.create_subprocess_exec(
        "pytest", "--cov", "--cov-report=term",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    # 解析覆盖率报告
    return "TOTAL" in stdout.decode() and "80%" in stdout.decode()

async def main():
    agent = AgentHarness()

    result = await agent.run_goal(
        goal="将测试覆盖率提升到 80%",
        custom_verifier=check_coverage,
        max_iterations=50,
    )

    print(f"状态: {result.status.value}")
    print(f"迭代次数: {result.total_iterations}")

asyncio.run(main())
```

### GoalConfig 完整配置

```python
from harness import AgentHarness
from harness.loop import GoalConfig, GoalStatus

agent = AgentHarness()

config = GoalConfig(
    description="实现用户认证模块",
    success_criteria="所有测试通过，覆盖率 >= 80%",
    workspace_dir="./src/auth",

    # 迭代控制
    max_iterations=50,
    max_context_resets=5,      # 上下文重置次数
    timeout_seconds=3600,      # 1小时超时

    # 成本控制
    max_tokens=500000,
    max_cost_usd=10.0,
)

result = await agent.run_goal(config)
```

### 定时自动化 (Phase 2)

使用 Automation 创建定时任务：

```python
import asyncio
from harness import AgentHarness
from harness.loop import Automation

async def main():
    agent = AgentHarness()

    # Cron 定时任务：每天 9:00 生成日报
    daily_report = Automation(
        name="daily-report",
        schedule="0 9 * * *",
        goal="分析昨日 Git 提交，生成工作日报",
    )

    # 间隔任务：每 5 分钟健康检查
    health_check = Automation(
        name="health-check",
        interval_seconds=300,
        goal="检查系统健康状态，如有异常发送告警",
    )

    # 启动自动化
    await daily_report.start(agent)
    await health_check.start(agent)

    print("自动化任务已启动，按 Ctrl+C 停止")
    try:
        await asyncio.sleep(3600)  # 运行 1 小时
    finally:
        await daily_report.stop()
        await health_check.stop()

asyncio.run(main())
```

### 并行 Worktree 执行 (Phase 3)

在隔离的 worktree 中并行执行多个目标：

```python
import asyncio
from harness import AgentHarness
from harness.loop import WorktreeOrchestrator, WorktreeConfig

async def main():
    agent = AgentHarness()

    orchestrator = WorktreeOrchestrator(agent, workspace_dir=".")

    # 定义并行任务
    tasks = [
        WorktreeConfig(
            name="feature-auth",
            goal="实现用户认证功能",
            base_branch="main",
        ),
        WorktreeConfig(
            name="feature-api",
            goal="实现 REST API 端点",
            base_branch="main",
        ),
        WorktreeConfig(
            name="feature-tests",
            goal="编写集成测试",
            base_branch="main",
        ),
    ]

    # 并行执行
    results = await orchestrator.run_parallel(tasks)

    # 查看结果
    for name, result in results.items():
        print(f"{name}: {result.status}")

    # 合并成功的分支
    for name, result in results.items():
        if result.status == "completed":
            await orchestrator.merge(name)
            print(f"已合并: {name}")

asyncio.run(main())
```

### 指标监控

监控 Goal 执行的详细指标：

```python
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()

result = await agent.run_goal(
    goal="重构数据库访问层",
    max_iterations=30,
)

# 详细指标
print(f"状态: {result.status.value}")
print(f"迭代次数: {result.total_iterations}")
print(f"上下文重置: {result.context_resets}")
print(f"Token 使用: 输入 {result.total_tokens.input_tokens}, 输出 {result.total_tokens.output_tokens}")
print(f"执行时长: {result.duration_seconds:.1f}秒")

# 验证日志
for record in result.verification_log:
    print(f"  第{record.iteration}轮: {record.result.value}")
    if record.reason:
        print(f"    原因: {record.reason}")
```

### 错误处理

处理各种执行状态：

```python
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()
result = await agent.run_goal("复杂任务", max_iterations=10)

match result.status:
    case GoalStatus.ACHIEVED:
        print("目标达成")
    case GoalStatus.TIMEOUT:
        print(f"超时，已运行 {result.duration_seconds}秒")
    case GoalStatus.MAX_ITERATIONS:
        print(f"达到最大迭代次数，建议增加 max_iterations")
    case GoalStatus.MAX_RESETS:
        print("上下文重置次数过多，任务可能过于复杂")
    case GoalStatus.ERROR:
        print(f"执行错误: {result.error}")
    case GoalStatus.VERIFIER_FAULT:
        print("验证器故障，请检查 custom_verifier 实现")
    case GoalStatus.CANCELLED:
        print("用户取消")
```

### 工作流编排

组合多个目标形成工作流：

```python
import asyncio
from harness import AgentHarness
from harness.loop import GoalStatus

async def code_review_workflow(agent: AgentHarness):
    """代码审查工作流"""

    # Step 1: 静态分析
    result1 = await agent.run_goal(
        goal="运行静态分析，找出代码问题",
        max_iterations=10,
    )
    if result1.status != GoalStatus.ACHIEVED:
        return result1

    # Step 2: 修复问题
    result2 = await agent.run_goal(
        goal="修复所有发现的代码问题",
        max_iterations=30,
    )
    if result2.status != GoalStatus.ACHIEVED:
        return result2

    # Step 3: 运行测试
    result3 = await agent.run_goal(
        goal="确保所有测试通过",
        max_iterations=20,
    )

    return result3

async def main():
    agent = AgentHarness()
    result = await code_review_workflow(agent)
    print(f"工作流完成: {result.status.value}")

asyncio.run(main())
```
