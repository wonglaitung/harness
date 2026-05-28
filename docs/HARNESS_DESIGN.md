# Harness 项目设计文档

> 可内嵌的 AI Agent Harness 框架

## 目录

- [01-overview.md](./01-overview.md) - 项目概述与架构总览
- [02-agent-loop.md](./02-agent-loop.md) - Agent Loop 代理循环引擎
- [03-tool-system.md](./03-tool-system.md) - Tool System 工具系统
- [04-memory-system.md](./04-memory-system.md) - Memory System 记忆系统
- [05-skills-system.md](./05-skills-system.md) - Skills System 技能系统
- [06-triggers.md](./06-triggers.md) - Trigger & Orchestration 触发与编排
- [07-sdk-api.md](./07-sdk-api.md) - SDK 与 API 设计
- [08-security.md](./08-security.md) - 安全设计
- [09-implementation.md](./09-implementation.md) - 实施路线图
- [10-comparison.md](./10-comparison.md) - 与 Hermes/OpenClaw 对比
- [11-testing.md](./11-testing.md) - 测试策略
- [12-decisions.md](./12-decisions.md) - 技术决策与权衡

## 项目定位

构建一个**可内嵌到用户系统**的 AI Agent Harness 框架，让 LLM 从"回答问题的聊天机器人"变成"能自主操作的智能体"。

### 核心理念

```
Agent = Model + Harness
```

- **Model**: 大语言模型（Claude/GPT/本地模型），提供推理能力
- **Harness**: 围绕模型的框架层，提供记忆、工具、触发器、技能

### 与现有方案的区别

| 项目 | 定位 | 部署方式 | 内嵌能力 |
|------|------|----------|----------|
| OpenClaw | 多代理控制平面 | 独立服务 | 有限 |
| Hermes | 自学习个人运行时 | 独立服务 | 有限 |
| **本 Harness** | 可内嵌 SDK | 嵌入用户系统 | **核心设计** |

## 快速预览

### 最简使用示例

```python
from harness import AgentHarness, FileTool, ShellTool

# 创建 Harness 实例
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[FileTool(), ShellTool(sandbox=True)],
    memory_dir="~/.harness/memory"
)

# 同步调用
response = agent.run("分析当前目录的代码结构")

# 流式调用
async for chunk in agent.stream("帮我重构这个函数"):
    print(chunk.content, end="")
```

### 内嵌到现有系统

```python
# 集成到 FastAPI
from fastapi import FastAPI
from harness import AgentHarness

app = FastAPI()
agent = AgentHarness.from_config("harness.yaml")

@app.post("/chat")
async def chat(message: str, session_id: str):
    response = await agent.run_async(message, session_id=session_id)
    return {"response": response.content}

# 集成定时任务
@app.on_event("startup")
async def setup_scheduled_tasks():
    agent.set_trigger(
        CronTrigger("0 9 * * *"),
        lambda: agent.run("生成每日报告")
    )
```

## 设计原则

1. **可内嵌优先**: 设计为库而非服务，可嵌入任何 Python 应用
2. **渐进式复杂度**: 从最简 MVP 开始，逐步增加高级特性
3. **安全默认**: 默认沙箱模式，显式开启危险权限
4. **可观测性**: 内置日志、追踪、指标
5. **可扩展**: 插件式的工具、技能、记忆后端

# 目录

1. [项目概述与架构总览](#1-项目概述与架构总览)
2. [Agent Loop 代理循环引擎](#2-agent-loop-代理循环引擎)
3. [Tool System 工具系统](#3-tool-system-工具系统)
4. [Memory System 记忆系统](#4-memory-system-记忆系统)
5. [Skills System 技能系统](#5-skills-system-技能系统)
6. [Trigger & Orchestration 触发与编排](#6-trigger--orchestration-触发与编排)
7. [SDK 与 API 设计](#7-sdk-与-api-设计)
8. [安全设计](#8-安全设计)
9. [实施路线图](#9-实施路线图)
10. [与 Hermes/OpenClaw 对比](#10-与-hermesopenclaw-对比)
11. [测试策略](#11-测试策略)
12. [技术决策与权衡](#12-技术决策与权衡)

---


# 01 - 项目概述与架构总览

## 项目背景

### 问题陈述

当前 AI 编码工具（Claude Code、Cursor、Copilot 等）大多是独立产品，难以深度集成到用户自己的系统中。用户如果想要：

- 在自己的应用中嵌入 AI Agent 能力
- 自定义工具和技能
- 控制数据流向和存储
- 与现有业务逻辑深度集成

往往需要从零开始构建，或者接受现有产品的限制。

### 解决方案

构建一个**可内嵌的 AI Agent Harness 框架**：

- 以 SDK 形式提供，可嵌入任何 Python 应用
- 模块化设计，可按需组合功能
- 提供完整的工具、记忆、技能系统
- 支持多种 LLM 后端

## 架构总览

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER APPLICATION                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     AGENT HARNESS SDK                       │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                    Agent Loop                         │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │ Input   │→ │ Context │→ │   LLM   │→ │ Output  │  │  │ │
│  │  │  │ Handler │  │ Builder │  │  Call   │  │ Parser  │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  │       ↓            ↓            ↓            ↓       │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │Trigger  │  │ Memory  │  │  Tool   │  │ Action  │  │  │ │
│  │  │  │ Manager │  │ System  │  │ System  │  │ Handler │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                   Skills System                       │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │ │
│  │  │  │  Skill  │  │  Skill  │  │  Skill  │  ...          │  │ │
│  │  │  │ Loader  │  │Registry │  │Injector │               │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                 Infrastructure                        │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │ Config  │  │Logging &│  │  Error  │  │ Metrics │  │  │ │
│  │  │  │ Manager │  │ Tracing │  │ Handler │  │& Stats  │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│         ↓                              ↓                         │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │  LLM PROVIDERS  │          │  MCP SERVERS    │               │
│  │  ┌───────────┐  │          │  ┌───────────┐  │               │
│  │  │ Anthropic │  │          │  │ Filesystem│  │               │
│  │  │   OpenAI  │  │          │  │  GitHub   │  │               │
│  │  │   Local   │  │          │  │  Slack    │  │               │
│  │  └───────────┘  │          │  │  Custom   │  │               │
│  └─────────────────┘          │  └───────────┘  │               │
│                               └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件关系

```
                    ┌─────────────────┐
                    │   Trigger       │
                    │   Manager       │
                    └────────┬────────┘
                             │ 触发执行
                             ↓
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Context │←→→ │   LLM   │←→→ │  Tool   │         │
│  │ Builder │    │  Client │    │Executor │         │
│  └────┬────┘    └────┬────┘    └────┬────┘         │
│       │              │              │               │
│       ↓              ↓              ↓               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Memory  │    │ Skills  │    │ Actions │         │
│  │ System  │    │ System  │    │/Outputs │         │
│  └─────────┘    └─────────┘    └─────────┘         │
└─────────────────────────────────────────────────────┘
```

## 核心概念

### Agent Loop（代理循环）

代理循环是 Harness 的心脏，实现了"代理"行为的核心机制：

```
while not finished:
    1. 接收输入（用户消息/触发器事件）
    2. 构建上下文（从记忆系统加载）
    3. 调用 LLM
    4. 解析响应
    5. 如果需要工具调用 → 执行工具 → 返回结果给 LLM → 继续
    6. 如果完成 → 返回结果
```

关键设计点：
- **流式处理**: 支持 streaming output
- **并行执行**: 多个独立工具调用可并行
- **中断支持**: 允许用户中断执行
- **重试机制**: API 错误自动重试

### Tool System（工具系统）

工具系统让 LLM 能够"动手操作"：

```python
class Tool:
    name: str                    # 工具名称
    description: str             # 工具描述（LLM 可见）
    parameters: JSONSchema       # 参数 Schema
    permission_level: Permission # 权限级别

    def execute(self, params: dict) -> ToolResult:
        """执行工具并返回结果"""
        pass
```

工具类型：
- **内置工具**: File, Shell, Web, Search
- **自定义工具**: 用户注册的 Python 函数
- **MCP 工具**: 通过 Model Context Protocol 连接

### Memory System（记忆系统）

解决 LLM 无状态问题的多层记忆：

```
┌─────────────────────────────────────────┐
│ Layer 1: Working Memory                 │
│ - 当前会话消息                           │
│ - 最近 N 条消息                          │
│ - 当前任务状态                           │
├─────────────────────────────────────────┤
│ Layer 2: Session Memory                 │
│ - 会话摘要                               │
│ - 关键决策记录                           │
│ - 用户偏好                               │
├─────────────────────────────────────────┤
│ Layer 3: Long-term Memory               │
│ - 技能和模式                             │
│ - 项目知识                               │
│ - 历史经验                               │
├─────────────────────────────────────────┤
│ Layer 4: Retrieved Memory               │
│ - 向量检索                               │
│ - 语义搜索                               │
│ - 按需加载                               │
└─────────────────────────────────────────┘
```

### Skills System（技能系统）

技能定义代理的行为边界：

```markdown
---
name: code-review
description: Review code for issues
tools: [Read, Grep, Bash]
---

# Code Review Skill

You are a code reviewer. Your task is to:
1. Read the code files
2. Identify bugs, security issues, performance problems
3. Provide actionable suggestions
```

### Triggers（触发器）

让代理能够自主运行：

| 触发类型 | 说明 | 示例 |
|----------|------|------|
| UserMessage | 用户消息触发 | 用户发送消息 |
| Cron | 定时触发 | 每天 9:00 生成报告 |
| Webhook | 外部事件触发 | GitHub PR 事件 |
| Heartbeat | 周期性心跳 | 每 5 分钟检查状态 |
| FileWatch | 文件变化触发 | 配置文件更新 |

## 数据流

### 请求处理流程

```
用户输入
    │
    ↓
┌─────────────┐
│ Trigger     │ 识别触发源，创建/恢复 Session
│ Manager     │
└─────┬───────┘
      │
      ↓
┌─────────────┐
│ Context     │ 加载记忆、技能、系统提示
│ Builder     │ 构建完整上下文
└─────┬───────┘
      │
      ↓
┌─────────────┐
│ Agent       │ ┌─────────────────────────────┐
│ Loop        │ │         Loop Body           │
│             │ │                             │
│             │ │  ┌───────┐    ┌───────┐    │
│             │ │  │  LLM  │───→│ Parse │    │
│             │ │  │ Call  │    │Output │    │
│             │ │  └───────┘    └───┬───┘    │
│             │ │                    │        │
│             │ │         ┌─────────┴────┐   │
│             │ │         ↓              ↓   │
│             │ │   ┌──────────┐   ┌────────┐│
│             │ │   │Tool Call │   │ Finish ││
│             │ │   │ Execute  │   │        ││
│             │ │   └────┬─────┘   └────────┘│
│             │ │        │                     │
│             │ │        └──────────┐          │
│             │ │                   ↓          │
│             │ │            ┌───────────┐    │
│             │ │            │ Tool      │    │
│             │ │            │ Result    │    │
│             │ │            └─────┬─────┘    │
│             │ │                  │          │
│             │ │                  └──────┐   │
│             │ │                         ↓   │
│             │ │                    Back to  │
│             │ │                    LLM Call │
│             │ └─────────────────────────────┘
└─────┬───────┘
      │
      ↓
┌─────────────┐
│ Memory      │ 保存会话、更新摘要
│ Update      │
└─────┬───────┘
      │
      ↓
┌─────────────┐
│ Output      │ 返回结果给用户/系统
│ Handler     │
└─────────────┘
```

## 模块依赖关系

```
                    ┌─────────────┐
                    │    SDK      │
                    │  (Public)   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ↓                 ↓                 ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Agent Loop  │    │   Skills    │    │  Triggers   │
│             │    │   System    │    │             │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │         ┌────────┴────────┐         │
       │         │                 │         │
       ↓         ↓                 ↓         ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Memory    │    │    Tool     │    │   Config    │
│   System    │    │   System    │    │   Manager   │
└──────┬──────┘    └──────┬──────┘    └─────────────┘
       │                  │
       │         ┌────────┴────────┐
       │         │                 │
       ↓         ↓                 ↓
┌─────────────────────────────────────────┐
│           Infrastructure                 │
│  Logging | Tracing | Metrics | Errors   │
└─────────────────────────────────────────┘
```

## 设计决策记录 (ADR)

### ADR-001: 为什么选择 SDK 而非独立服务？

**决策**: 设计为可内嵌的 Python SDK，而非独立服务。

**原因**:
1. **集成深度**: 用户可以在代码层面调用，无需网络开销
2. **数据控制**: 数据留在用户系统内，无需同步到外部服务
3. **定制灵活**: 用户可以深度定制每个组件
4. **部署简单**: 无需额外部署服务，随应用启动

**权衡**:
- 需要用户提供运行时环境
- 跨语言使用需要额外封装

### ADR-002: 为什么支持多种记忆后端？

**决策**: 支持文件、SQLite、Redis、PostgreSQL 等多种存储后端。

**原因**:
1. **渐进式**: 从单文件开始，逐步支持更复杂的后端
2. **灵活性**: 适应不同规模的部署需求
3. **兼容性**: 可接入用户现有的数据库

### ADR-003: 为什么选择 Python？

**决策**: 使用 Python 作为主要实现语言。

**原因**:
1. **AI 生态**: LLM SDK、向量数据库等库最完善
2. **用户群体**: AI 开发者主要使用 Python
3. **快速迭代**: 便于快速开发和测试

**扩展计划**:
- 后续提供 TypeScript SDK
- 核心 Agent Loop 可考虑 Rust 重写以提升性能

## 参考资源

- [Harness Engineering - Martin Fowler](https://martinfowler.com/articles/harness-engineering.html)
- [OpenClaw Documentation](https://docs.openclaw.ai)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [OpenHarness](https://github.com/HKUDS/OpenHarness)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/tool-use)

---


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

---


# 03 - Tool System 工具系统

## 概述

Tool System 是让 LLM 能够"动手操作"的能力层，定义了 Agent 可以执行的动作和约束。

## 核心设计

### 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                       Tool System                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Registry                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │  │  File   │  │  Shell  │  │   Web   │  │   MCP   │ │   │
│  │  │  Tools  │  │  Tools  │  │  Tools  │  │  Tools  │ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  │              Built-in         Custom       External   │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Permission Manager                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Path      │  │  Command    │  │   Rate      │  │   │
│  │  │   Filter    │  │  Blocklist  │  │   Limiter   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Executor                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Sandbox   │  │   Timeout   │  │   Result    │  │   │
│  │  │  Executor   │  │   Handler   │  │   Parser    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Manager                         │   │
│  │  连接外部 MCP 服务器，自动注册工具                      │   │
│  │  支持: Stdio / HTTP / WebSocket 传输                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Tool 接口设计

### 基础 Tool 类

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import jsonschema

class PermissionLevel(Enum):
    """权限级别"""
    SAFE = "safe"              # 安全操作，无需确认
    MODERATE = "moderate"      # 中等风险，可选确认
    DANGEROUS = "dangerous"    # 危险操作，必须确认
    RESTRICTED = "restricted"  # 受限操作，默认禁用

@dataclass
class ToolSchema:
    """工具 Schema"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    required: List[str] = field(default_factory=list)

    def to_anthropic_format(self) -> dict:
        """转换为 Anthropic 格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }

    def to_openai_format(self) -> dict:
        """转换为 OpenAI 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, content: str, **metadata) -> "ToolResult":
        return cls(success=True, content=content, metadata=metadata)

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(success=False, content="", error=message)

@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]

class Tool(ABC):
    """工具基类"""

    # 子类必须定义
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    required: List[str] = []
    permission_level: PermissionLevel = PermissionLevel.SAFE

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._validate_definition()

    def _validate_definition(self):
        """验证工具定义"""
        if not self.name:
            raise ValueError("Tool must have a name")
        if not self.description:
            raise ValueError("Tool must have a description")

    @property
    def schema(self) -> ToolSchema:
        """获取工具 Schema"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            required=self.required
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            schema = {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
            jsonschema.validate(arguments, schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid arguments: {e.message}")

    @abstractmethod
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        """执行工具"""
        pass

    def should_confirm(self, arguments: Dict[str, Any]) -> bool:
        """是否需要用户确认"""
        if self.permission_level == PermissionLevel.DANGEROUS:
            return True
        if self.permission_level == PermissionLevel.RESTRICTED:
            return True
        return False

    def get_confirmation_message(self, arguments: Dict[str, Any]) -> str:
        """获取确认消息"""
        return f"Execute {self.name} with arguments: {arguments}?"
```

### Tool Context

```python
@dataclass
class ToolContext:
    """工具执行上下文"""
    session_id: str
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    user_id: Optional[str] = None
    permissions: "PermissionSet" = None
    logger: Optional[Logger] = None

    # 回调
    on_progress: Optional[Callable[[str], None]] = None
```

## 内置工具

### 3.1 File Tools

```python
class ReadTool(Tool):
    """读取文件"""

    name = "read"
    description = "Read the contents of a file from the local filesystem."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to read"
        },
        "limit": {
            "type": "integer",
            "description": "Number of lines to read (optional)"
        },
        "offset": {
            "type": "integer",
            "description": "Starting line number (optional)"
        }
    }
    required = ["file_path"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]

        # 权限检查
        if not context.permissions.is_path_allowed(file_path, "read"):
            return ToolResult.error(f"Access denied: {file_path}")

        try:
            with open(file_path, "r") as f:
                if "limit" in arguments or "offset" in arguments:
                    lines = f.readlines()
                    offset = arguments.get("offset", 0)
                    limit = arguments.get("limit", len(lines))
                    content = "".join(lines[offset:offset + limit])
                else:
                    content = f.read()

            return ToolResult.ok(content, path=file_path)

        except FileNotFoundError:
            return ToolResult.error(f"File not found: {file_path}")
        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult.error(f"Error reading file: {e}")


class WriteTool(Tool):
    """写入文件"""

    name = "write"
    description = "Write content to a file on the local filesystem."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to write"
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file"
        }
    }
    required = ["file_path", "content"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]
        content = arguments["content"]

        # 权限检查
        if not context.permissions.is_path_allowed(file_path, "write"):
            return ToolResult.error(f"Write access denied: {file_path}")

        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(content)

            return ToolResult.ok(
                f"Successfully wrote {len(content)} characters to {file_path}",
                path=file_path,
                bytes_written=len(content)
            )

        except Exception as e:
            return ToolResult.error(f"Error writing file: {e}")


class EditTool(Tool):
    """编辑文件"""

    name = "edit"
    description = "Perform exact string replacement in a file."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to edit"
        },
        "old_string": {
            "type": "string",
            "description": "The text to replace"
        },
        "new_string": {
            "type": "string",
            "description": "The text to replace with"
        },
        "replace_all": {
            "type": "boolean",
            "description": "Replace all occurrences (default false)"
        }
    }
    required = ["file_path", "old_string", "new_string"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]
        old_string = arguments["old_string"]
        new_string = arguments["new_string"]
        replace_all = arguments.get("replace_all", False)

        if not context.permissions.is_path_allowed(file_path, "write"):
            return ToolResult.error(f"Write access denied: {file_path}")

        try:
            with open(file_path, "r") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult.error(
                    f"String not found in file: {old_string[:50]}..."
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, "w") as f:
                f.write(new_content)

            return ToolResult.ok(
                f"Successfully edited {file_path}",
                replacements=content.count(old_string) if replace_all else 1
            )

        except Exception as e:
            return ToolResult.error(f"Error editing file: {e}")


class GlobTool(Tool):
    """文件模式匹配"""

    name = "glob"
    description = "Find files matching a glob pattern."
    parameters = {
        "pattern": {
            "type": "string",
            "description": "The glob pattern to match (e.g., **/*.py)"
        },
        "path": {
            "type": "string",
            "description": "The directory to search in (optional)"
        }
    }
    required = ["pattern"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import glob as glob_module

        pattern = arguments["pattern"]
        path = arguments.get("path", context.working_directory)

        matches = glob_module.glob(
            pattern,
            root_dir=path,
            recursive=True
        )

        return ToolResult.ok(
            "\n".join(sorted(matches)),
            count=len(matches)
        )


class GrepTool(Tool):
    """文件内容搜索"""

    name = "grep"
    description = "Search for patterns in file contents using regex."
    parameters = {
        "pattern": {
            "type": "string",
            "description": "The regex pattern to search for"
        },
        "path": {
            "type": "string",
            "description": "The directory to search in (optional)"
        },
        "file_pattern": {
            "type": "string",
            "description": "Glob pattern for files to search (e.g., *.py)"
        },
        "ignore_case": {
            "type": "boolean",
            "description": "Case insensitive search (default false)"
        }
    }
    required = ["pattern"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import re
        from pathlib import Path

        pattern = arguments["pattern"]
        path = Path(arguments.get("path", context.working_directory))
        file_pattern = arguments.get("file_pattern", "*")
        ignore_case = arguments.get("ignore_case", False)

        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        results = []
        for file_path in path.rglob(file_pattern):
            if not file_path.is_file():
                continue
            if not context.permissions.is_path_allowed(str(file_path), "read"):
                continue

            try:
                with open(file_path, "r") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}: {line.rstrip()}")
            except (UnicodeDecodeError, PermissionError):
                continue

        return ToolResult.ok(
            "\n".join(results),
            matches=len(results)
        )
```

### 3.2 Shell Tools

```python
class BashTool(Tool):
    """执行 Shell 命令"""

    name = "bash"
    description = "Execute a shell command and return the output."
    parameters = {
        "command": {
            "type": "string",
            "description": "The command to execute"
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (optional)"
        },
        "cwd": {
            "type": "string",
            "description": "Working directory (optional)"
        }
    }
    required = ["command"]
    permission_level = PermissionLevel.DANGEROUS

    # 危险命令黑名单
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf ~",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sda",
        "chmod -R 777 /",
        "chown -R",
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        command = arguments["command"]
        timeout = arguments.get("timeout", context.timeout)
        cwd = arguments.get("cwd", context.working_directory)

        # 检查危险命令
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult.error(f"Blocked dangerous command: {blocked}")

        # 权限检查
        if not context.permissions.is_command_allowed(command):
            return ToolResult.error(f"Command not allowed: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, **context.environment}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult.error(f"Command timed out after {timeout}s")

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"Exit code {process.returncode}: {error}"
                )

            return ToolResult.ok(
                output,
                exit_code=process.returncode
            )

        except Exception as e:
            return ToolResult.error(f"Error executing command: {e}")
```

### 3.3 Web Tools

```python
class WebSearchTool(Tool):
    """Web 搜索"""

    name = "web_search"
    description = "Search the web for information."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query"
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (default 5)"
        }
    }
    required = ["query"]
    permission_level = PermissionLevel.MODERATE

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.search_engine = config.get("engine", "tavily")

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        query = arguments["query"]
        num_results = arguments.get("num_results", 5)

        # 使用搜索 API
        # 可以接入 Tavily, Serper, Google Custom Search 等
        results = await self._search(query, num_results)

        return ToolResult.ok(
            self._format_results(results),
            query=query,
            count=len(results)
        )


class WebFetchTool(Tool):
    """获取网页内容"""

    name = "web_fetch"
    description = "Fetch and extract content from a URL."
    parameters = {
        "url": {
            "type": "string",
            "description": "The URL to fetch"
        },
        "selector": {
            "type": "string",
            "description": "CSS selector to extract specific content (optional)"
        }
    }
    required = ["url"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import aiohttp
        from bs4 import BeautifulSoup

        url = arguments["url"]
        selector = arguments.get("selector")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        return ToolResult.error(f"HTTP {response.status}")
                    html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()

            if selector:
                content = soup.select(selector)
                text = "\n".join(e.get_text() for e in content)
            else:
                text = soup.get_text(separator="\n", strip=True)

            return ToolResult.ok(text[:10000], url=url)  # 限制长度

        except Exception as e:
            return ToolResult.error(f"Error fetching URL: {e}")
```

## Tool Registry

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

    def register(self, tool: Tool, category: str = "general"):
        """注册工具"""
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool
        self._categories[category].append(tool.name)

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            for tools in self._categories.values():
                if name in tools:
                    tools.remove(name)

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self, category: str = None) -> List[ToolSchema]:
        """列出工具"""
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n].schema for n in names if n in self._tools]
        return [t.schema for t in self._tools.values()]

    def get_schemas_for_llm(self, provider: str = "anthropic") -> List[dict]:
        """获取 LLM 可用的工具 schemas"""
        schemas = []
        for tool in self._tools.values():
            if provider == "anthropic":
                schemas.append(tool.schema.to_anthropic_format())
            elif provider == "openai":
                schemas.append(tool.schema.to_openai_format())
        return schemas

    def register_defaults(self):
        """注册默认工具集"""
        # File tools
        self.register(ReadTool(), category="file")
        self.register(WriteTool(), category="file")
        self.register(EditTool(), category="file")
        self.register(GlobTool(), category="file")
        self.register(GrepTool(), category="file")

        # Shell tools
        self.register(BashTool(), category="shell")

        # Web tools
        self.register(WebSearchTool(), category="web")
        self.register(WebFetchTool(), category="web")
```

## Permission System

```python
@dataclass
class PermissionRule:
    """权限规则"""
    type: str  # "allow" or "deny"
    resource: str  # path pattern, command pattern, etc.
    action: str  # "read", "write", "execute"

@dataclass
class PermissionSet:
    """权限集合"""
    rules: List[PermissionRule] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    default_deny: bool = True

    def is_path_allowed(self, path: str, action: str) -> bool:
        """检查路径权限"""
        from pathlib import Path

        abs_path = Path(path).resolve()

        # 检查黑名单
        for blocked in self.blocked_paths:
            if abs_path.is_relative_to(blocked):
                return False

        # 检查白名单
        if not self.allowed_paths:
            return not self.default_deny

        for allowed in self.allowed_paths:
            if abs_path.is_relative_to(allowed):
                return True

        return not self.default_deny

    def is_command_allowed(self, command: str) -> bool:
        """检查命令权限"""
        # 检查黑名单
        for blocked in self.blocked_commands:
            if blocked in command:
                return False

        # 如果有白名单，检查是否匹配
        if self.allowed_commands:
            for allowed in self.allowed_commands:
                if command.startswith(allowed):
                    return True
            return False

        return True

    @classmethod
    def sandbox(cls, workspace: str) -> "PermissionSet":
        """创建沙箱权限"""
        return cls(
            allowed_paths=[workspace],
            blocked_paths=["/etc", "/root", "~/.ssh"],
            blocked_commands=["rm -rf", "sudo", "chmod"],
            default_deny=True
        )

    @classmethod
    def full_access(cls) -> "PermissionSet":
        """完全访问权限"""
        return cls(
            default_deny=False,
            blocked_commands=["rm -rf /"]
        )
```

## Tool Executor

```python
class ToolExecutor:
    """工具执行器"""

    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionSet,
        default_timeout: float = 30.0,
        sandbox: bool = True
    ):
        self.registry = registry
        self.permissions = permissions
        self.default_timeout = default_timeout
        self.sandbox = sandbox
        self._pending_confirmations: Dict[str, ToolCall] = {}

    async def execute(
        self,
        call: ToolCall,
        context: ToolContext
    ) -> ToolResult:
        """执行工具调用"""

        # 获取工具
        tool = self.registry.get(call.name)
        if not tool:
            return ToolResult.error(f"Unknown tool: {call.name}")

        # 验证参数
        try:
            tool.validate_arguments(call.arguments)
        except ValueError as e:
            return ToolResult.error(str(e))

        # 检查是否需要确认
        if tool.should_confirm(call.arguments):
            # 可以实现确认流程
            confirmed = await self._request_confirmation(tool, call, context)
            if not confirmed:
                return ToolResult.error("User denied the operation")

        # 创建执行上下文
        exec_context = ToolContext(
            session_id=context.session_id,
            working_directory=context.working_directory,
            environment=context.environment,
            timeout=self.default_timeout,
            permissions=self.permissions,
            logger=context.logger
        )

        # 执行工具
        try:
            if self.sandbox:
                result = await self._execute_in_sandbox(tool, call.arguments, exec_context)
            else:
                result = await tool.execute(call.arguments, exec_context)

            return result

        except asyncio.TimeoutError:
            return ToolResult.error(f"Tool execution timed out")
        except Exception as e:
            return ToolResult.error(f"Tool execution error: {e}")

    async def _execute_in_sandbox(
        self,
        tool: Tool,
        arguments: Dict,
        context: ToolContext
    ) -> ToolResult:
        """在沙箱中执行工具"""
        # 可以使用 Docker, gVisor, nsjail 等
        # 这里是一个简化实现
        return await tool.execute(arguments, context)

    async def _request_confirmation(
        self,
        tool: Tool,
        call: ToolCall,
        context: ToolContext
    ) -> bool:
        """请求用户确认"""
        # 实现确认流程
        # 可以通过回调、消息队列等方式
        return True

    async def execute_parallel(
        self,
        calls: List[ToolCall],
        context: ToolContext
    ) -> List[ToolResult]:
        """并行执行多个工具"""
        tasks = [self.execute(call, context) for call in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

## Custom Tools

### 函数装饰器方式

```python
def tool(
    name: str = None,
    description: str = None,
    permission: PermissionLevel = PermissionLevel.SAFE
):
    """将函数注册为工具的装饰器"""

    def decorator(func):
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""

        # 从函数签名推断参数
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls", "context"]:
                continue

            param_type = "string"  # 默认类型
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")

            parameters[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        class FunctionTool(Tool):
            name = tool_name
            description = tool_desc
            parameters = parameters
            required = required
            permission_level = permission

            async def execute(self, arguments, context):
                try:
                    result = func(**arguments)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return ToolResult.ok(str(result))
                except Exception as e:
                    return ToolResult.error(str(e))

        return FunctionTool()

    return decorator


# 使用示例
@tool(description="Get current weather for a city")
async def get_weather(city: str, unit: str = "celsius") -> str:
    """Get weather information"""
    # 调用天气 API
    return f"Weather in {city}: 25°{unit[0].upper()}"


@tool(permission=PermissionLevel.MODERATE)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email"""
    # 发送邮件逻辑
    return f"Email sent to {to}"
```

### 类方式

```python
class DatabaseQueryTool(Tool):
    """数据库查询工具"""

    name = "db_query"
    description = "Execute a SQL query on the database"
    parameters = {
        "query": {
            "type": "string",
            "description": "SQL query to execute"
        },
        "params": {
            "type": "array",
            "description": "Query parameters"
        }
    }
    required = ["query"]
    permission_level = PermissionLevel.DANGEROUS

    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string

    async def execute(self, arguments: Dict, context: ToolContext) -> ToolResult:
        import asyncpg

        query = arguments["query"]
        params = arguments.get("params", [])

        # 只允许 SELECT 语句
        if not query.strip().upper().startswith("SELECT"):
            return ToolResult.error("Only SELECT queries are allowed")

        try:
            conn = await asyncpg.connect(self.connection_string)
            rows = await conn.fetch(query, *params)
            await conn.close()

            return ToolResult.ok(
                json.dumps([dict(r) for r in rows], indent=2),
                row_count=len(rows)
            )
        except Exception as e:
            return ToolResult.error(f"Query error: {e}")
```

## MCP (Model Context Protocol) 支持

MCP 是 Anthropic 提出的开放协议，用于连接 AI 模型与外部工具和资源。Harness 原生支持 MCP，可以将 MCP 服务器的工具无缝集成到工具系统中。

### MCP 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Harness                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Registry                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │   │
│  │  │ Built-in │ │ Custom   │ │     MCP Tools        │ │   │
│  │  │ Tools    │ │ Tools    │ │  (mcp_server_tool)   │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘ │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                               │
│                             ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Manager                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │   │
│  │  │ Transport│ │ Protocol │ │   Server Registry    │ │   │
│  │  │  Layer   │ │  Client  │ │                      │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘ │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                               │
│                             ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Servers                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │   │
│  │  │Filesystem│ │  GitHub  │ │  Slack   │  ...        │   │
│  │  │  Server  │ │  Server  │ │  Server  │             │   │
│  │  └──────────┘ └──────────┘ └──────────┘             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 传输层实现

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
import asyncio
import json

class MCPTransport(ABC):
    """MCP 传输层抽象"""

    @abstractmethod
    async def connect(self):
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def send(self, message: dict) -> None:
        """发送消息"""
        pass

    @abstractmethod
    async def receive(self) -> AsyncIterator[dict]:
        """接收消息流"""
        pass


class StdioTransport(MCPTransport):
    """标准输入输出传输（最常用）"""

    def __init__(self, command: str, args: list = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None

    async def connect(self):
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env}
        )

    async def disconnect(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()

    async def send(self, message: dict) -> None:
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

    async def receive(self) -> AsyncIterator[dict]:
        while True:
            line = await self._process.stdout.readline()
            if not line:
                break
            try:
                yield json.loads(line.decode())
            except json.JSONDecodeError:
                continue


class HTTPTransport(MCPTransport):
    """HTTP/SSE 传输"""

    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        self._session = aiohttp.ClientSession(headers=self.headers)

    async def disconnect(self):
        if self._session:
            await self._session.close()

    async def send(self, message: dict) -> None:
        async with self._session.post(f"{self.url}/message", json=message) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Send failed: {resp.status}")

    async def receive(self) -> AsyncIterator[dict]:
        async with self._session.get(f"{self.url}/sse") as resp:
            async for line in resp.content:
                if line.startswith(b"data: "):
                    yield json.loads(line[6:])
```

### MCP Client 实现

```python
import uuid
from dataclasses import dataclass, field

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class MCPServerInfo:
    """服务器信息"""
    name: str
    version: str
    capabilities: List[str]


class MCPClient:
    """MCP 客户端"""

    def __init__(self, transport: MCPTransport, client_name: str = "harness"):
        self.transport = transport
        self.client_name = client_name
        self._server_info: Optional[MCPServerInfo] = None
        self._tools: List[MCPTool] = []
        self._request_handlers: Dict[str, asyncio.Future] = {}

    async def connect(self) -> MCPServerInfo:
        """连接并初始化"""
        await self.transport.connect()
        asyncio.create_task(self._message_loop())

        # 发送初始化请求
        response = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": self.client_name, "version": "1.0.0"},
            "capabilities": {"tools": {}, "resources": {}}
        })

        self._server_info = MCPServerInfo(
            name=response["serverInfo"]["name"],
            version=response["serverInfo"]["version"],
            capabilities=list(response.get("capabilities", {}).keys())
        )

        # 发送 initialized 通知
        await self._notify("notifications/initialized", {})

        # 获取工具列表
        await self._list_tools()

        return self._server_info

    async def disconnect(self):
        await self.transport.disconnect()

    async def _list_tools(self):
        response = await self._request("tools/list", {})
        self._tools = [
            MCPTool(
                name=tool["name"],
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {})
            )
            for tool in response.get("tools", [])
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用 MCP 工具"""
        response = await self._request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        content = response.get("content", [])
        is_error = response.get("isError", False)

        text_content = "\n".join(
            item.get("text", "")
            for item in content
            if item.get("type") == "text"
        )

        return {"content": text_content, "is_error": is_error}

    async def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._request_handlers[request_id] = future

        await self.transport.send({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        })

        return await future

    async def _notify(self, method: str, params: Dict[str, Any]):
        await self.transport.send({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })

    async def _message_loop(self):
        async for message in self.transport.receive():
            if "id" in message and message["id"] in self._request_handlers:
                future = self._request_handlers.pop(message["id"])
                if "error" in message:
                    future.set_exception(Exception(message["error"]["message"]))
                else:
                    future.set_result(message.get("result", {}))

    @property
    def tools(self) -> List[MCPTool]:
        return self._tools
```

### MCP Manager

```python
@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    transport: str              # "stdio", "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


class MCPManager:
    """MCP 管理器"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._clients: Dict[str, MCPClient] = {}
        self._configs: Dict[str, MCPServerConfig] = {}

    def add_server(self, config: MCPServerConfig):
        """添加 MCP 服务器配置"""
        self._configs[config.name] = config

    async def connect_server(self, name: str) -> MCPClient:
        """连接到指定服务器"""
        if name in self._clients:
            return self._clients[name]

        config = self._configs.get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        # 创建传输层
        if config.transport == "stdio":
            transport = StdioTransport(config.command, config.args, config.env)
        elif config.transport == "http":
            transport = HTTPTransport(config.url)
        else:
            raise ValueError(f"Unknown transport: {config.transport}")

        # 连接
        client = MCPClient(transport)
        await client.connect()

        # 注册工具到 Harness
        for tool in client.tools:
            self._register_mcp_tool(name, tool, client)

        self._clients[name] = client
        return client

    async def connect_all(self):
        """连接所有已启用的服务器"""
        for name, config in self._configs.items():
            if config.enabled:
                try:
                    await self.connect_server(name)
                except Exception as e:
                    print(f"Failed to connect to {name}: {e}")

    async def disconnect_all(self):
        """断开所有连接"""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

    def _register_mcp_tool(self, server_name: str, mcp_tool: MCPTool, client: MCPClient):
        """将 MCP 工具注册到 Harness"""

        class MCPToolWrapper(Tool):
            name = f"mcp_{server_name}_{mcp_tool.name}"
            description = mcp_tool.description
            parameters = mcp_tool.input_schema.get("properties", {})
            required = mcp_tool.input_schema.get("required", [])
            permission_level = PermissionLevel.SAFE

            def __init__(self, mcp_client: MCPClient, original_name: str):
                self._client = mcp_client
                self._original_name = original_name

            async def execute(self, arguments: Dict, context: ToolContext) -> ToolResult:
                try:
                    result = await self._client.call_tool(self._original_name, arguments)
                    if result.get("is_error"):
                        return ToolResult.error(result.get("content", "Unknown error"))
                    return ToolResult.ok(result.get("content", ""))
                except Exception as e:
                    return ToolResult.error(f"MCP tool error: {e}")

        wrapper = MCPToolWrapper(client, mcp_tool.name)
        self.tool_registry.register(wrapper, category="mcp")
```

### MCP 配置文件

#### 配置文件存放位置

```
优先级（高→低）
    │
    ├── 1. ./.agent/mcp.json        # 项目级配置（最高优先级，随项目提交）
    │
    ├── 2. ./.mcp.json              # 项目级配置（备选位置，兼容 Claude Code）
    │
    ├── 3. ~/.harness/mcp.json      # 用户级配置
    │
    └── 4. ~/.claude/mcp.json       # 兼容 Claude Code 全局配置
```

#### 配置文件格式

支持 YAML 和 JSON 两种格式，JSON 格式与 Claude Code 完全兼容：

```json
// .agent/mcp.json (JSON 格式，兼容 Claude Code)
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["/workspace"],
      "env": {}
    },
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "finance-proxy": {
      "command": "python",
      "args": ["/data/bank-services-plugins/prototype/local_proxy/main.py"],
      "env": {
        "REMOTE_MCP_URL": "http://localhost:8001",
        "MCP_REFRESH_TOKEN": "your-token-here"
      }
    }
  }
}
```

```yaml
# .agent/mcp.yaml (YAML 格式)
mcpServers:
  filesystem:
    transport: stdio
    command: mcp-server-filesystem
    args: ["/workspace"]
    enabled: true

  github:
    transport: stdio
    command: mcp-server-github
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
    enabled: true

  custom-api:
    transport: http
    url: https://api.example.com/mcp
    enabled: true
```

#### 项目目录结构示例

```
my-project/
├── .agent/
│   ├── mcp.json              # 项目 MCP 配置
│   ├── skills/               # 项目技能
│   ├── AGENTS.md             # 项目上下文
│   └── config.yaml           # Harness 配置
│
├── .mcp.json                 # 备选 MCP 配置位置
│
└── ...

~/.harness/
├── mcp.json                  # 用户级 MCP 配置
├── skills/                   # 用户技能库
└── memory/                   # 记忆存储
```

### 使用示例

```python
from harness import AgentHarness

# 方式1：自动加载（推荐）
# 自动从 .agent/mcp.json, .mcp.json, ~/.harness/mcp.json 加载
agent = AgentHarness()

# 方式2：指定配置文件
agent = AgentHarness(mcp_config_path="./.agent/mcp.json")

# 方式3：手动添加 MCP 服务器
agent.mcp.add_server(MCPServerConfig(
    name="finance-proxy",
    transport="stdio",
    command="python",
    args=["/data/bank-services-plugins/prototype/local_proxy/main.py"],
    env={
        "REMOTE_MCP_URL": "http://localhost:8001",
        "MCP_REFRESH_TOKEN": "your-token"
    }
))

# 连接所有 MCP 服务器
await agent.mcp.connect_all()

# MCP 工具已自动注册为 mcp_{server}_{tool} 格式
# 例如: mcp_filesystem_read_file, mcp_github_create_issue

result = await agent.run("使用 filesystem 工具读取 config.yaml")
```

### 与 Claude Code 配置兼容

Harness 完全兼容 Claude Code 的 MCP 配置格式，可以直接使用 Claude Code 的配置文件：

```json
// Claude Code 配置格式（完全兼容）
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

## 测试

```python
import pytest

@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register_defaults()
    return registry

@pytest.fixture
def sandbox_permissions():
    return PermissionSet.sandbox("/workspace")

@pytest.mark.asyncio
async def test_read_tool(tool_registry, sandbox_permissions):
    tool = tool_registry.get("read")

    context = ToolContext(
        session_id="test",
        working_directory="/workspace",
        permissions=sandbox_permissions
    )

    # 测试读取文件
    result = await tool.execute({"file_path": "/workspace/test.txt"}, context)
    assert result.success

@pytest.mark.asyncio
async def test_permission_deny():
    permissions = PermissionSet.sandbox("/workspace")
    assert not permissions.is_path_allowed("/etc/passwd", "read")
    assert not permissions.is_command_allowed("rm -rf /")
```

---


# 04 - Memory System 记忆系统

## 概述

Memory System 解决 LLM 无状态问题的上下文管理层，负责会话持久化、上下文构建、记忆压缩和检索。

## 架构设计

### 记忆层级模型

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory System                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 1: Working Memory (Immediate)                  │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Current     │ │ Recent      │ │ Active      │     │   │
│  │ │ Conversation│ │ Messages    │ │ Task State  │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 每次调用必需，不可压缩                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 2: Session Memory (Cross-turn)                 │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Session     │ │ Key         │ │ Working     │     │   │
│  │ │ Summary     │ │ Decisions   │ │ Notes       │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 轻量摘要，关键信息提取                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 3: Long-term Memory (Persistent)               │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Skills &    │ │ Project     │ │ User        │     │   │
│  │ │ Patterns    │ │ Knowledge   │ │ Preferences │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 持久存储，按需加载                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 4: Retrieved Memory (On-demand)                │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │ │ Vector      │ │ Semantic    │ │ Historical  │     │   │
│  │ │ Search      │ │ Lookup      │ │ Context     │     │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │ 特点: 检索式加载，仅加载相关内容                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入
    │
    ↓
┌─────────────────┐
│   Trigger       │
│   Manager       │
└────────┬────────┘
         │ Session ID
         ↓
┌─────────────────────────────────────────────────────┐
│                 Memory Manager                       │
│                                                      │
│  1. Load Session (SessionStore)                     │
│  2. Get Working Memory (last N messages)            │
│  3. Get Session Summary                             │
│  4. Get Skills & Knowledge                          │
│  5. Retrieve Relevant Context                       │
│                                                      │
│  Output: Context object                             │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
              ┌─────────────┐
              │ Context     │
              │ Builder     │
              │             │
              │ - 预算分配   │
              │ - Token 计数 │
              │ - 压缩判断   │
              └─────────────┘
                     │
                     ↓
              ┌─────────────┐
              │   Agent     │
              │   Loop      │
              └─────────────┘
                     │
                     ↓
              ┌─────────────┐
              │ Memory      │
              │ Update      │
              │             │
              │ - 保存消息   │
              │ - 更新摘要   │
              │ - 学习模式   │
              └─────────────┘
```

## 核心组件

### 4.1 Session Management

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

@dataclass
class Message:
    """消息"""
    role: str  # "user", "assistant", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_call_id": self.tool_call_id,
            "metadata": self.metadata
        }

@dataclass
class Session:
    """会话"""
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    working_directory: str = ""
    user_id: Optional[str] = None

    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """获取最近 N 条消息"""
        return self.messages[-n:]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "metadata": self.metadata,
            "working_directory": self.working_directory,
            "user_id": self.user_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data["messages"]],
            summary=data.get("summary"),
            metadata=data.get("metadata", {}),
            working_directory=data.get("working_directory", ""),
            user_id=data.get("user_id")
        )
```

### 4.2 Session Store

```python
from abc import ABC, abstractmethod
import os
import json
from pathlib import Path

class SessionStore(ABC):
    """会话存储抽象"""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """保存会话"""
        pass

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """删除会话"""
        pass

    @abstractmethod
    async def list_sessions(self, user_id: str = None) -> List[str]:
        """列出会话"""
        pass


class FileSessionStore(SessionStore):
    """文件存储实现"""

    def __init__(self, storage_dir: str = "~/.harness/sessions"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    async def save(self, session: Session) -> None:
        """保存会话到文件"""
        path = self._session_path(session.id)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    async def load(self, session_id: str) -> Optional[Session]:
        """从文件加载会话"""
        path = self._session_path(session_id)
        if not path.exists():
            return None

        with open(path, "r") as f:
            data = json.load(f)
            return Session.from_dict(data)

    async def delete(self, session_id: str) -> None:
        """删除会话文件"""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()

    async def list_sessions(self, user_id: str = None) -> List[str]:
        """列出所有会话 ID"""
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            sessions.append(path.stem)
        return sessions


class SQLiteSessionStore(SessionStore):
    """SQLite 存储"""

    def __init__(self, db_path: str = "~/.harness/harness.db"):
        import aiosqlite

        self.db_path = Path(db_path).expanduser()
        self._initialized = False

    async def _init_db(self):
        if self._initialized:
            return

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    user_id TEXT,
                    working_directory TEXT,
                    summary TEXT,
                    metadata TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            await db.commit()

        self._initialized = True

    async def save(self, session: Session) -> None:
        await self._init_db()

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            # 保存会话
            await db.execute("""
                INSERT OR REPLACE INTO sessions
                (id, created_at, updated_at, user_id, working_directory, summary, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.user_id,
                session.working_directory,
                session.summary,
                json.dumps(session.metadata)
            ))

            # 删除旧消息
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session.id,))

            # 保存新消息
            for msg in session.messages:
                await db.execute("""
                    INSERT INTO messages
                    (session_id, role, content, timestamp, tool_calls, tool_call_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.id,
                    msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    json.dumps([tc.to_dict() for tc in msg.tool_calls]),
                    msg.tool_call_id,
                    json.dumps(msg.metadata)
                ))

            await db.commit()

    async def load(self, session_id: str) -> Optional[Session]:
        await self._init_db()

        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            # 加载会话
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            session = Session(
                id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                user_id=row[3],
                working_directory=row[4],
                summary=row[5],
                metadata=json.loads(row[6])
            )

            # 加载消息
            cursor = await db.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,)
            )
            for msg_row in await cursor.fetchall():
                session.messages.append(Message(
                    role=msg_row[1],
                    content=msg_row[2],
                    timestamp=datetime.fromisoformat(msg_row[3]),
                    tool_calls=json.loads(msg_row[4]),
                    tool_call_id=msg_row[5],
                    metadata=json.loads(msg_row[6])
                ))

            return session
```

### 4.3 Context Builder

```python
@dataclass
class ContextBudget:
    """上下文预算"""
    max_tokens: int
    reserved_for_output: int = 4096
    reserved_for_tools: int = 2000

    @property
    def available_for_input(self) -> int:
        return self.max_tokens - self.reserved_for_output - self.reserved_for_tools


@dataclass
class ContextComponents:
    """上下文组件"""
    system_prompt: str = ""
    skills_prompt: str = ""
    recent_messages: List[Message] = field(default_factory=list)
    session_summary: str = ""
    memory_content: str = ""
    retrieved_content: str = ""
    tool_schemas: List[ToolSchema] = field(default_factory=list)


@dataclass
class Context:
    """构建完成的上下文"""
    system_prompt: str
    messages: List[Message]
    tools: List[ToolSchema]
    token_count: int
    components: ContextComponents


class ContextBuilder:
    """上下文构建器"""

    def __init__(
        self,
        token_counter: TokenCounter,
        budget: ContextBudget,
        compression_threshold: float = 0.8
    ):
        self.counter = token_counter
        self.budget = budget
        self.compression_threshold = compression_threshold

    async def build(
        self,
        messages: List[Message],
        session: Session,
        skills: List[Skill] = None,
        tools: List[ToolSchema] = None,
        memory_content: str = ""
    ) -> Context:
        """构建上下文"""

        # 估算各组件 token
        components = ContextComponents(
            recent_messages=messages[-10:],  # 默认保留最近 10 条
            tool_schemas=tools or []
        )

        # 构建系统提示
        components.system_prompt = self._build_system_prompt(session)
        components.skills_prompt = self._build_skills_prompt(skills or [])
        components.session_summary = session.summary or ""

        # 计算当前 token 数
        current_tokens = self._estimate_tokens(components)

        # 检查是否需要压缩
        if current_tokens > self.budget.available_for_input * self.compression_threshold:
            components = await self._compress_context(components)

        # 构建最终上下文
        final_messages = self._build_messages(components)

        return Context(
            system_prompt=self._combine_prompts(components),
            messages=final_messages,
            tools=components.tool_schemas,
            token_count=self.counter.count_messages(final_messages),
            components=components
        )

    def _build_system_prompt(self, session: Session) -> str:
        """构建基础系统提示"""
        return """You are an AI assistant with access to tools.
When you need to perform an action, use the appropriate tool.
Think carefully about which tools to use and provide clear reasoning."""

    def _build_skills_prompt(self, skills: List[Skill]) -> str:
        """构建技能提示"""
        if not skills:
            return ""

        prompts = []
        for skill in skills:
            prompts.append(f"""
## {skill.name}
{skill.content}
""")
        return "\n".join(prompts)

    def _combine_prompts(self, components: ContextComponents) -> str:
        """合并所有提示"""
        parts = [components.system_prompt]

        if components.skills_prompt:
            parts.append("\n# Skills\n" + components.skills_prompt)

        if components.session_summary:
            parts.append("\n# Session Summary\n" + components.session_summary)

        return "\n".join(parts)

    def _build_messages(self, components: ContextComponents) -> List[Message]:
        """构建消息列表"""
        # 可以添加摘要作为系统消息
        messages = []

        if components.session_summary:
            # 在旧消息之前插入摘要
            messages.append(Message(
                role="system",
                content=f"[Previous conversation summary]\n{components.session_summary}"
            ))

        messages.extend(components.recent_messages)

        return messages

    def _estimate_tokens(self, components: ContextComponents) -> int:
        """估算总 token 数"""
        total = 0

        total += self.counter.count(components.system_prompt)
        total += self.counter.count(components.skills_prompt)
        total += self.counter.count(components.session_summary)

        for msg in components.recent_messages:
            total += self.counter.count(msg.content)
            total += 50  # 消息格式开销

        for tool in components.tool_schemas:
            total += 100  # 工具 schema 估算
            total += self.counter.count(json.dumps(tool.parameters)) // 4

        return total

    async def _compress_context(
        self,
        components: ContextComponents
    ) -> ContextComponents:
        """压缩上下文"""

        # 策略 1: 减少最近消息数量
        if len(components.recent_messages) > 5:
            # 摘要旧消息
            old_messages = components.recent_messages[:-5]
            summary = await self._summarize_messages(old_messages)
            components.session_summary = (
                components.session_summary + "\n" + summary
                if components.session_summary
                else summary
            )
            components.recent_messages = components.recent_messages[-5:]

        # 策略 2: 压缩技能提示
        if len(components.skills_prompt) > 1000:
            components.skills_prompt = components.skills_prompt[:1000]

        return components

    async def _summarize_messages(
        self,
        messages: List[Message]
    ) -> str:
        """摘要消息"""
        # 可以使用 LLM 生成摘要，或简单的格式化
        summary_parts = []
        for msg in messages:
            if msg.role == "user":
                summary_parts.append(f"User asked: {msg.content[:100]}")
            elif msg.role == "assistant":
                summary_parts.append(f"Assistant: {msg.content[:100]}")

        return "\n".join(summary_parts)
```

### 4.4 Memory Store

```python
@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    type: str  # "skill", "pattern", "preference", "knowledge"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    relevance_score: float = 0.0


class MemoryStore(ABC):
    """记忆存储抽象"""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """存储记忆"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """检索记忆"""
        pass

    @abstractmethod
    async def get_all(self, type: str = None) -> List[MemoryEntry]:
        """获取所有记忆"""
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> None:
        """删除记忆"""
        pass


class FileMemoryStore(MemoryStore):
    """文件记忆存储"""

    def __init__(self, memory_dir: str = "~/.harness/memory"):
        self.memory_dir = Path(memory_dir).expanduser()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.memory_dir / "index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file) as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def _entry_path(self, entry_id: str) -> Path:
        return self.memory_dir / f"{entry_id}.md"

    async def store(self, entry: MemoryEntry) -> None:
        path = self._entry_path(entry.id)

        # 写入内容
        content = f"""---
id: {entry.id}
type: {entry.type}
created_at: {entry.created_at.isoformat()}
updated_at: {entry.updated_at.isoformat()}
metadata: {json.dumps(entry.metadata)}
---

{entry.content}
"""
        with open(path, "w") as f:
            f.write(content)

        # 更新索引
        self.index[entry.id] = {
            "type": entry.type,
            "path": str(path),
            "created_at": entry.created_at.isoformat()
        }
        self._save_index()

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """简单的关键词检索"""
        results = []

        for entry_id, info in self.index.items():
            if types and info["type"] not in types:
                continue

            path = self._entry_path(entry_id)
            if path.exists():
                content = path.read_text()

                # 简单关键词匹配
                if query.lower() in content.lower():
                    # 解析并返回
                    results.append(self._parse_entry(content))

        return results[:limit]

    def _parse_entry(self, content: str) -> MemoryEntry:
        """解析记忆文件"""
        import yaml

        parts = content.split("---\n")
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2]

            return MemoryEntry(
                id=frontmatter["id"],
                type=frontmatter["type"],
                content=body,
                metadata=frontmatter.get("metadata", {}),
                created_at=datetime.fromisoformat(frontmatter["created_at"]),
                updated_at=datetime.fromisoformat(frontmatter["updated_at"])
            )

        return MemoryEntry(id="unknown", type="unknown", content=content)
```

### 4.5 Vector Retrieval (RAG)

```python
class VectorMemoryStore(MemoryStore):
    """向量检索记忆存储"""

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        vector_db: str = "chroma"
    ):
        self.embedding_model = embedding_model

        # 初始化向量数据库
        if vector_db == "chroma":
            import chromadb
            self.client = chromadb.PersistentClient("~/.harness/vectors")
            self.collection = self.client.get_or_create_collection("memory")

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        # 使用 OpenAI 或本地模型
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        response = await client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def store(self, entry: MemoryEntry) -> None:
        """存储记忆并建立向量索引"""
        embedding = await self._get_embedding(entry.content)

        self.collection.add(
            ids=[entry.id],
            embeddings=[embedding],
            documents=[entry.content],
            metadatas=[{
                "type": entry.type,
                "created_at": entry.created_at.isoformat(),
                **entry.metadata
            }]
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        types: List[str] = None
    ) -> List[MemoryEntry]:
        """向量相似度检索"""
        query_embedding = await self._get_embedding(query)

        where_filter = None
        if types:
            where_filter = {"type": {"$in": types}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter
        )

        entries = []
        for i, doc in enumerate(results["documents"][0]):
            entries.append(MemoryEntry(
                id=results["ids"][0][i],
                type=results["metadatas"][0][i]["type"],
                content=doc,
                metadata=results["metadatas"][0][i],
                relevance_score=1 - results["distances"][0][i]
            ))

        return entries
```

### 4.6 Context Compression

```python
class ContextCompressor:
    """上下文压缩器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def compress_session(
        self,
        session: Session,
        target_tokens: int
    ) -> str:
        """压缩会话为摘要"""

        # 构建所有消息的文本
        all_messages = "\n".join([
            f"{m.role}: {m.content}"
            for m in session.messages
        ])

        prompt = f"""Summarize the following conversation, preserving:
1. Key decisions made
2. Important context established
3. Outstanding tasks or questions
4. User preferences discovered

Conversation:
{all_messages}

Summary (concise, under {target_tokens // 4} words):"""

        response = await self.llm.call(
            Context(
                system_prompt="You are a concise summarizer.",
                messages=[Message(role="user", content=prompt)],
                tools=[]
            )
        )

        return response.message.content

    async def compress_tool_results(
        self,
        results: List[ToolResult],
        max_length: int = 2000
    ) -> str:
        """压缩工具结果"""

        if not results:
            return ""

        # 简单截断或智能摘要
        combined = "\n".join([r.content[:500] for r in results])

        if len(combined) > max_length:
            # 使用 LLM 摘要
            prompt = f"""Summarize these tool results concisely:

{combined}

Summary:"""

            response = await self.llm.call(
                Context(
                    system_prompt="Summarize tool results.",
                    messages=[Message(role="user", content=prompt)],
                    tools=[]
                )
            )
            return response.message.content

        return combined


class AutoCompressor:
    """自动压缩管理器"""

    def __init__(
        self,
        compressor: ContextCompressor,
        threshold_ratio: float = 0.8,
        min_messages_before_compress: int = 20
    ):
        self.compressor = compressor
        self.threshold_ratio = threshold_ratio
        self.min_messages = min_messages_before_compress

    async def should_compress(
        self,
        session: Session,
        current_tokens: int,
        max_tokens: int
    ) -> bool:
        """判断是否需要压缩"""
        if len(session.messages) < self.min_messages:
            return False

        return current_tokens > max_tokens * self.threshold_ratio

    async def auto_compress(
        self,
        session: Session,
        max_tokens: int
    ) -> Session:
        """自动压缩会话"""

        # 保留最近消息，压缩旧消息
        keep_recent = 10
        old_messages = session.messages[:-keep_recent]

        if not old_messages:
            return session

        # 生成摘要
        summary = await self.compressor.compress_session(
            Session(id=session.id, messages=old_messages),
            target_tokens=500
        )

        # 更新会话
        session.summary = (
            session.summary + "\n\n" + summary
            if session.summary
            else summary
        )
        session.messages = session.messages[-keep_recent:]

        return session
```

## Memory Manager

```python
@dataclass
class MemoryConfig:
    """记忆配置"""
    storage_type: str = "file"  # file, sqlite, redis
    storage_path: str = "~/.harness"
    enable_vector_search: bool = False
    embedding_model: str = "text-embedding-3-small"
    max_session_messages: int = 100
    compression_threshold: float = 0.8
    auto_compress: bool = True


class MemoryManager:
    """记忆管理器"""

    def __init__(
        self,
        config: MemoryConfig,
        llm_client: LLMClient = None
    ):
        self.config = config

        # 初始化存储
        if config.storage_type == "file":
            self.session_store = FileSessionStore(
                f"{config.storage_path}/sessions"
            )
            self.memory_store = FileMemoryStore(
                f"{config.storage_path}/memory"
            )
        elif config.storage_type == "sqlite":
            self.session_store = SQLiteSessionStore(
                f"{config.storage_path}/harness.db"
            )
            self.memory_store = FileMemoryStore(
                f"{config.storage_path}/memory"
            )

        # 向量检索
        if config.enable_vector_search:
            self.vector_store = VectorMemoryStore(
                embedding_model=config.embedding_model
            )
        else:
            self.vector_store = None

        # 压缩器
        self.compressor = ContextCompressor(llm_client) if llm_client else None
        self.auto_compressor = AutoCompressor(
            self.compressor,
            threshold_ratio=config.compression_threshold
        ) if self.compressor else None

        # Token 计数器
        self.token_counter = TokenCounter()

        # 上下文构建器
        self.context_builder = ContextBuilder(
            self.token_counter,
            ContextBudget(max_tokens=200000)
        )

    async def create_session(
        self,
        user_id: str = None,
        working_directory: str = ""
    ) -> Session:
        """创建新会话"""
        session_id = self._generate_session_id()

        session = Session(
            id=session_id,
            user_id=user_id,
            working_directory=working_directory
        )

        await self.session_store.save(session)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return await self.session_store.load(session_id)

    async def update_session(self, session: Session) -> None:
        """更新会话"""
        # 检查是否需要压缩
        if self.auto_compressor and self.config.auto_compress:
            current_tokens = self.token_counter.count_messages(session.messages)
            if await self.auto_compressor.should_compress(
                session, current_tokens, 200000
            ):
                session = await self.auto_compressor.auto_compress(session, 200000)

        await self.session_store.save(session)

    async def build_context(
        self,
        session: Session,
        skills: List[Skill] = None,
        tools: List[ToolSchema] = None
    ) -> Context:
        """构建上下文"""
        return await self.context_builder.build(
            messages=session.messages,
            session=session,
            skills=skills,
            tools=tools
        )

    async def store_memory(
        self,
        type: str,
        content: str,
        metadata: Dict = None
    ) -> MemoryEntry:
        """存储记忆"""
        entry_id = self._generate_memory_id()

        entry = MemoryEntry(
            id=entry_id,
            type=type,
            content=content,
            metadata=metadata or {}
        )

        await self.memory_store.store(entry)

        if self.vector_store:
            await self.vector_store.store(entry)

        return entry

    async def retrieve_memory(
        self,
        query: str,
        types: List[str] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """检索记忆"""
        if self.vector_store:
            return await self.vector_store.retrieve(query, limit, types)
        else:
            return await self.memory_store.retrieve(query, limit, types)

    def _generate_session_id(self) -> str:
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"

    def _generate_memory_id(self) -> str:
        import uuid
        return f"memory_{uuid.uuid4().hex[:8]}"
```

## 记忆文件格式

### MEMORY.md 格式

```markdown
# MEMORY.md

This file contains persistent memory that is loaded across sessions.

## User Profile

- Role: Software Developer
- Preferred Language: Python
- Project Context: Building a harness framework

## Key Decisions

- 2026-05-28: Decided to use Python as primary language
- 2026-05-28: Chose SQLite for session storage (simple, embedded)

## Learned Patterns

- User prefers concise responses without trailing summaries
- User wants to see file paths and line numbers in code references

## Active Tasks

- Complete design documentation for harness project
- Implement Agent Loop MVP
```

### Session Summary 格式

```markdown
## Session Summary (2026-05-28)

### Key Actions
1. Created project structure in /data/harness
2. Wrote initial design documents (overview, agent-loop, tool-system)
3. Discussed memory system design

### Important Context
- User wants an embeddable harness SDK (not standalone service)
- Similar to Hermes/OpenClaw but for integration

### Pending
- Need to write remaining design docs (skills, triggers, sdk)
- Need to start implementation after design is complete
```

## 测试

```python
import pytest

@pytest.fixture
async def memory_manager():
    config = MemoryConfig(
        storage_type="file",
        storage_path="/tmp/test_harness"
    )
    return MemoryManager(config)

@pytest.mark.asyncio
async def test_session_lifecycle(memory_manager):
    # 创建会话
    session = await memory_manager.create_session()
    assert session.id.startswith("session_")

    # 添加消息
    session.add_message(Message(role="user", content="Hello"))
    await memory_manager.update_session(session)

    # 加载会话
    loaded = await memory_manager.get_session(session.id)
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"

@pytest.mark.asyncio
async def test_memory_storage(memory_manager):
    # 存储记忆
    entry = await memory_manager.store_memory(
        type="preference",
        content="User prefers Python",
        metadata={"category": "language"}
    )

    # 检索记忆
    results = await memory_manager.retrieve_memory("Python")
    assert len(results) > 0
    assert "Python" in results[0].content
```
---


# 05 - Skills System 技能系统

## 概述

Skills System 定义了代理的行为边界和能力约束，通过结构化的指令文件指导 LLM 如何执行特定任务。

## 设计理念

### 什么是 Skill？

Skill 是一个**结构化、模块化的能力单元**，包含：

- **触发条件**: 何时激活这个技能
- **工具权限**: 可使用的工具集合
- **行为指导**: 具体的执行步骤和规则
- **输出规范**: 预期的输出格式

### Skill vs Prompt 的区别

| 特性 | 传统 Prompt | Skill |
|------|-------------|-------|
| 结构 | 自由文本 | 结构化文件 |
| 持久性 | 单次使用 | 可持久存储 |
| 工具绑定 | 手动指定 | 自动绑定 |
| 可组合性 | 低 | 高（可组合多个 Skill） |
| 可学习性 | 无 | 支持自动生成 |

## Skill 文件格式

### 标准 Skill 格式

```markdown
---
name: code-review
description: Review code changes and provide structured feedback
version: 1.0.0
author: harness-team
triggers:
  keywords:
    - "review"
    - "check code"
    - "code review"
  patterns:
    - "review this"
    - "check my changes"
tools:
  allowed:
    - read
    - grep
    - glob
    - bash
  restricted:
    - write
    - edit
parameters:
  severity_levels:
    type: array
    default: ["critical", "high", "medium", "low"]
  include_suggestions:
    type: boolean
    default: true
---

# Code Review Skill

## Purpose
You are a code reviewer. Your task is to analyze code changes and provide structured, actionable feedback.

## Workflow

1. **Identify Scope**
   - Ask the user which files or changes to review
   - Use `glob` to find relevant files if needed

2. **Read Code**
   - Use `read` to examine each file
   - Focus on changed sections if possible

3. **Analyze**
   Check for:
   - **Bugs**: Logic errors, edge cases, null handling
   - **Security**: Input validation, SQL injection, XSS
   - **Performance**: N+1 queries, unnecessary loops
   - **Style**: Naming conventions, complexity
   - **Architecture**: Module boundaries, dependencies

4. **Provide Feedback**
   Format each issue as:

   ```
   **Severity**: [Critical|High|Medium|Low]
   **Category**: [Bug|Security|Performance|Style|Architecture]
   **File**: path/to/file
   **Line**: line_number
   **Issue**: Description of the problem
   **Suggestion**: How to fix it
   **Code Example**: (optional) Suggested fix snippet
   ```

## Rules

- Never modify code directly (review-only)
- Always provide severity and category
- Include line numbers when possible
- Be specific, not vague
- Prioritize critical issues first

## Examples

### Good Review Output
```json
[
  {
    "severity": "High",
    "category": "Security",
    "file": "src/api/auth.py",
    "line": 45,
    "issue": "Password is logged in debug mode",
    "suggestion": "Remove password from log or disable debug mode"
  }
]
```

### Bad Review Output (avoid)
```
The code looks bad. You should fix it.
```
```

### 简化 Skill 格式

```markdown
---
name: summarize
description: Summarize text or content concisely
---

# Summarize Skill

Summarize the given content in 3-5 bullet points.
Focus on key information, ignore fluff.
Use clear, simple language.
```

## 核心组件

### 5.1 Skill 类定义

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path
import yaml
import re

@dataclass
class SkillTrigger:
    """技能触发器"""
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)  # 触发工具调用

    def matches(self, text: str) -> bool:
        """检查是否匹配触发条件"""
        # 关键词匹配
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True

        # 正则模式匹配
        for pattern in self.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False


@dataclass
class SkillTools:
    """技能工具配置"""
    allowed: List[str] = field(default_factory=list)
    restricted: List[str] = field(default_factory=list)
    default_permission: str = "allow"  # allow, deny, ask

    def is_allowed(self, tool_name: str) -> bool:
        """检查工具是否允许"""
        if tool_name in self.restricted:
            return False
        if not self.allowed:
            return self.default_permission == "allow"
        return tool_name in self.allowed


@dataclass
class SkillParameter:
    """技能参数"""
    name: str
    type: str
    default: Any = None
    description: str = ""
    required: bool = False


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    content: str
    triggers: SkillTrigger = field(default_factory=SkillTrigger)
    tools: SkillTools = field(default_factory=SkillTools)
    parameters: List[SkillParameter] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None

    @classmethod
    def from_file(cls, path: Path) -> "Skill":
        """从文件加载技能"""
        content = path.read_text()

        # 解析 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
            else:
                frontmatter = {}
                body = content
        else:
            frontmatter = {}
            body = content

        # 解析触发器
        triggers_data = frontmatter.get("triggers", {})
        triggers = SkillTrigger(
            keywords=triggers_data.get("keywords", []),
            patterns=triggers_data.get("patterns", []),
            tools=triggers_data.get("tools", [])
        )

        # 解析工具配置
        tools_data = frontmatter.get("tools", {})
        tools = SkillTools(
            allowed=tools_data.get("allowed", []),
            restricted=tools_data.get("restricted", []),
            default_permission=tools_data.get("default_permission", "allow")
        )

        # 解析参数
        parameters = []
        params_data = frontmatter.get("parameters", {})
        for param_name, param_info in params_data.items():
            parameters.append(SkillParameter(
                name=param_name,
                type=param_info.get("type", "string"),
                default=param_info.get("default"),
                description=param_info.get("description", ""),
                required=param_info.get("required", False)
            ))

        return cls(
            name=frontmatter.get("name", path.stem),
            description=frontmatter.get("description", ""),
            content=body,
            triggers=triggers,
            tools=tools,
            parameters=parameters,
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", ""),
            metadata=frontmatter.get("metadata", {}),
            source_path=str(path)
        )

    def to_file(self, path: Path):
        """保存技能到文件"""
        frontmatter = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "triggers": {
                "keywords": self.triggers.keywords,
                "patterns": self.triggers.patterns,
                "tools": self.triggers.tools
            },
            "tools": {
                "allowed": self.tools.allowed,
                "restricted": self.tools.restricted
            },
            "metadata": self.metadata
        }

        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{self.content}"
        path.write_text(content)

    def should_activate(self, user_input: str, context: dict = None) -> bool:
        """判断是否应该激活"""
        return self.triggers.matches(user_input)
```

### 5.2 Skill Registry

```python
class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._active_skills: List[str] = []
        self._skill_dirs: List[Path] = []

    def add_skill_dir(self, directory: Path):
        """添加技能目录"""
        self._skill_dirs.append(directory)
        self._load_from_dir(directory)

    def _load_from_dir(self, directory: Path):
        """从目录加载所有技能"""
        if not directory.exists():
            return

        for skill_file in directory.glob("*.md"):
            skill = Skill.from_file(skill_file)
            self.register(skill)

    def register(self, skill: Skill):
        """注册技能"""
        if skill.name in self._skills:
            # 版本检查
            existing = self._skills[skill.name]
            if skill.version > existing.version:
                self._skills[skill.name] = skill
        else:
            self._skills[skill.name] = skill

    def unregister(self, name: str):
        """注销技能"""
        if name in self._skills:
            del self._skills[name]

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        """列出所有技能"""
        return list(self._skills.values())

    def find_matching_skills(self, user_input: str) -> List[Skill]:
        """查找匹配的技能"""
        matches = []
        for skill in self._skills.values():
            if skill.should_activate(user_input):
                matches.append(skill)
        return matches

    def activate(self, skill_name: str):
        """激活技能"""
        if skill_name in self._skills:
            self._active_skills.append(skill_name)

    def deactivate(self, skill_name: str):
        """关闭技能"""
        if skill_name in self._active_skills:
            self._active_skills.remove(skill_name)

    def get_active_skills(self) -> List[Skill]:
        """获取活跃技能"""
        return [self._skills[name] for name in self._active_skills if name in self._skills]

    def get_allowed_tools(self, tool_name: str) -> bool:
        """检查工具在当前活跃技能中是否允许"""
        for skill in self.get_active_skills():
            if not skill.tools.is_allowed(tool_name):
                return False
        return True

    def reload(self):
        """重新加载所有技能"""
        self._skills.clear()
        for directory in self._skill_dirs:
            self._load_from_dir(directory)
```

### 5.3 Skill Injector

```python
@dataclass
class InjectionConfig:
    """注入配置"""
    max_skills_per_prompt: int = 5
    max_skill_length: int = 2000
    inject_method: str = "append"  # append, prepend, interleaved
    skill_separator: str = "\n\n---\n\n"


class SkillInjector:
    """技能注入器"""

    def __init__(
        self,
        registry: SkillRegistry,
        config: InjectionConfig = None
    ):
        self.registry = registry
        self.config = config or InjectionConfig()

    def inject_skills(
        self,
        system_prompt: str,
        user_input: str,
        context: dict = None
    ) -> str:
        """将技能注入系统提示"""

        # 找到匹配的技能
        matching_skills = self.registry.find_matching_skills(user_input)

        # 加上已经激活的技能
        active_skills = self.registry.get_active_skills()

        # 合并，去重
        all_skills = list(set(matching_skills + active_skills))

        # 限制数量
        all_skills = all_skills[:self.config.max_skills_per_prompt]

        if not all_skills:
            return system_prompt

        # 构建技能提示
        skill_prompts = []
        for skill in all_skills:
            skill_prompt = self._format_skill(skill)
            # 截断过长的技能
            if len(skill_prompt) > self.config.max_skill_length:
                skill_prompt = skill_prompt[:self.config.max_skill_length] + "\n...[truncated]"
            skill_prompts.append(skill_prompt)

        combined_skills = self.config.skill_separator.join(skill_prompts)

        # 根据注入方法组合
        if self.config.inject_method == "append":
            return system_prompt + self.config.skill_separator + combined_skills
        elif self.config.inject_method == "prepend":
            return combined_skills + self.config.skill_separator + system_prompt
        elif self.config.inject_method == "section":
            return f"{system_prompt}\n\n# Active Skills\n\n{combined_skills}"
        else:
            return system_prompt + self.config.skill_separator + combined_skills

    def _format_skill(self, skill: Skill) -> str:
        """格式化单个技能"""
        return f"""## Skill: {skill.name}

{skill.content}

### Available Tools
{', '.join(skill.tools.allowed) if skill.tools.allowed else 'All tools'}
"""

    def get_tool_filter(self) -> Callable[[str], bool]:
        """获取工具过滤器"""
        return lambda tool_name: self.registry.get_allowed_tools(tool_name)
```

### 5.4 Skill Loader

```python
## 技能文件存放位置

### 默认搜索路径

Harness 会自动从以下目录加载 Skill 文件（按优先级排序）：

```
优先级（高→低）
    │
    ├── 1. ./.agent/skills/          # 项目级技能（最高优先级，随项目提交）
    │
    ├── 2. ./skills/                 # 项目级技能（备选位置）
    │
    ├── 3. ~/.harness/skills/        # 用户级技能（个人技能库）
    │
    └── 4. ~/.harness/shared-skills/ # 共享技能（团队共享）
```

### 目录结构示例

```
my-project/
├── .agent/
│   ├── skills/
│   │   ├── code-review.md        # 项目专用代码审查技能
│   │   ├── deploy.md             # 项目部署技能
│   │   └── api-test.md           # API 测试技能
│   └── AGENTS.md                 # 项目上下文说明
│
├── skills/                       # 备选位置
│   └── custom-workflow.md
│
└── ...

~/.harness/
├── skills/                       # 用户个人技能库
│   ├── summarize.md
│   ├── translate.md
│   └── my-helpers/
│       └── data-format.md
│
└── shared-skills/                # 团队共享技能
    └── team-conventions.md
```

### 项目配置文件

在项目根目录创建 `.agent/config.yaml` 进行项目级配置：

```yaml
# .agent/config.yaml
skills:
  directories:
    - ./.agent/skills
    - ./skills
  auto_load: true

mcp:
  config: ./.agent/mcp.json        # MCP 配置文件路径

memory:
  type: file
  path: ./.agent/memory
```

### 使用示例

```python
from harness import AgentHarness

# 方式1：自动加载（推荐）
# 自动加载 .agent/skills/, skills/, ~/.harness/skills/ 中的技能
agent = AgentHarness()

# 方式2：指定配置文件
agent = AgentHarness.from_config("./.agent/config.yaml")

# 方式3：手动加载特定技能
agent = AgentHarness()
agent.load_skill("./.agent/skills/code-review.md")

# 方式4：添加额外技能目录
agent.skills.add_skill_dir(Path("./custom-skills"))
```

### 与 Claude Code 兼容

Harness 的 `.agent/` 目录设计兼容 Claude Code 的项目结构：

```
.agent/
├── AGENTS.md       # Claude Code 项目上下文
├── skills/         # Harness 技能文件
├── mcp.json        # MCP 配置（兼容 Claude Code 格式）
├── config.yaml     # Harness 配置
└── memory/         # 记忆文件
```

    def load_from_path(self, path: str):
        """从指定路径加载"""
        p = Path(path).expanduser()

        if p.is_file() and p.suffix == ".md":
            skill = Skill.from_file(p)
            self.registry.register(skill)
            self.loaded_paths.append(p)
        elif p.is_dir():
            self.registry.add_skill_dir(p)
            self.loaded_paths.append(p)

    def load_from_url(self, url: str):
        """从 URL 加载技能"""
        import aiohttp

        async def _load():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content = await response.text()

            # 临时文件
            temp_path = Path("/tmp") / Path(url).name
            temp_path.write_text(content)

            skill = Skill.from_file(temp_path)
            self.registry.register(skill)

        # 异步加载
        asyncio.create_task(_load())

    def discover_skills(self, directory: Path) -> List[Path]:
        """发现目录中的所有技能文件"""
        skill_files = []

        # 搜索 .md 文件
        for md_file in directory.rglob("*.md"):
            # 检查是否有 skill frontmatter
            content = md_file.read_text()
            if content.startswith("---") and "name:" in content.split("---")[1]:
                skill_files.append(md_file)

        return skill_files
```

### 5.5 Skill Generator (自学习)

```python
@dataclass
class PatternObservation:
    """模式观察"""
    user_inputs: List[str]
    tool_sequences: List[List[ToolCall]]
    outcomes: List[str]
    frequency: int


class SkillGenerator:
    """技能生成器（从重复模式自动生成技能）"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: SkillRegistry,
        observation_window: int = 100
    ):
        self.llm = llm_client
        self.registry = registry
        self.observation_window = observation_window
        self.patterns: Dict[str, PatternObservation] = {}

    def observe(self, session: Session):
        """观察会话中的模式"""
        # 提取用户输入和工具序列
        user_inputs = []
        tool_sequences = []
        current_tools = []

        for msg in session.messages:
            if msg.role == "user":
                if current_tools:
                    tool_sequences.append(current_tools)
                    current_tools = []
                user_inputs.append(msg.content)
            elif msg.role == "assistant" and msg.tool_calls:
                current_tools.extend(msg.tool_calls)

        if len(user_inputs) >= 2 and len(tool_sequences) >= 2:
            # 检查是否有重复模式
            self._analyze_pattern(user_inputs, tool_sequences)

    def _analyze_pattern(
        self,
        inputs: List[str],
        tool_seqs: List[List[ToolCall]]
    ):
        """分析是否有可学习的模式"""

        # 简单模式检测：相似输入 + 相似工具序列
        # 提取关键词
        keywords = self._extract_common_keywords(inputs)

        # 检查工具序列相似性
        common_tools = self._extract_common_tools(tool_seqs)

        if keywords and common_tools:
            pattern_key = f"{keywords}_{common_tools}"
            if pattern_key in self.patterns:
                self.patterns[pattern_key].frequency += 1
            else:
                self.patterns[pattern_key] = PatternObservation(
                    user_inputs=inputs,
                    tool_sequences=tool_seqs,
                    outcomes=[],
                    frequency=1
                )

    def _extract_common_keywords(self, inputs: List[str]) -> List[str]:
        """提取共同关键词"""
        from collections import Counter

        all_words = []
        for input_text in inputs:
            words = input_text.lower().split()
            all_words.extend(words)

        # 高频词
        counter = Counter(all_words)
        return [w for w, c in counter.most_common(5) if c >= 2]

    def _extract_common_tools(self, tool_seqs: List[List[ToolCall]]) -> List[str]:
        """提取共同工具"""
        tool_counts = Counter()
        for seq in tool_seqs:
            for call in seq:
                tool_counts[call.name] += 1

        return [t for t, c in tool_counts.most_common(5) if c >= 2]

    async def generate_skill(self, pattern_key: str) -> Optional[Skill]:
        """从模式生成技能"""

        if self.patterns[pattern_key].frequency < 3:
            # 频率太低，不值得生成技能
            return None

        pattern = self.patterns[pattern_key]

        # 使用 LLM 生成技能描述
        prompt = f"""Generate a skill definition from this observed pattern:

User inputs (similar):
{pattern.user_inputs[:3]}

Tool sequences used:
{[tc.name for tc in pattern.tool_sequences[0]]}

Create a skill YAML frontmatter and content that captures this pattern.
Format as:

---
name: [skill name]
description: [brief description]
triggers:
  keywords: [list of trigger keywords]
tools:
  allowed: [tools used in pattern]
---

[Skill content/instructions]

Output only the skill markdown file content."""

        response = await self.llm.call(
            Context(
                system_prompt="You generate skill definitions from patterns.",
                messages=[Message(role="user", content=prompt)],
                tools=[]
            )
        )

        # 解析生成的技能
        try:
            skill_content = response.message.content

            # 保存到文件
            skill_name = f"auto_{pattern_key.replace('_', '-')}"
            skill_path = Path("~/.harness/skills").expanduser() / f"{skill_name}.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_content)

            # 加载到注册表
            skill = Skill.from_file(skill_path)
            self.registry.register(skill)

            return skill
        except Exception as e:
            print(f"Error generating skill: {e}")
            return None

    async def check_and_generate(self, session: Session):
        """检查模式并生成技能"""
        self.observe(session)

        # 检查是否有高频模式
        for pattern_key, pattern in self.patterns.items():
            if pattern.frequency >= 3:
                skill = await self.generate_skill(pattern_key)
                if skill:
                    # 清除已处理的模式
                    del self.patterns[pattern_key]
                    return skill

        return None
```

## 预置技能库

### 基础技能

```
skills/
├── general/
│   ├── think.md          # 思考和规划
│   ├── summarize.md      # 摘要内容
│   ├── explain.md        # 解释概念
│   └── translate.md      # 翻译
│
├── coding/
│   ├── code-review.md    # 代码审查
│   ├── debug.md          # 调试分析
│   ├── refactor.md       # 重构建议
│   ├── test-gen.md       # 测试生成
│   └── doc-gen.md        # 文档生成
│
├── research/
│   ├── web-search.md     # 网络搜索
│   ├── analyze.md        # 数据分析
│   └── report.md         # 报告生成
│
└── workflow/
│   ├── plan.md           # 任务规划
│   ├── execute.md        # 执行流程
│   ├── review.md         # 结果审查
│   └── iterate.md        # 迭代改进
```

### 内置技能示例

#### think.md

```markdown
---
name: think
description: Think through a problem step by step before acting
triggers:
  keywords:
    - "think"
    - "plan"
    - "analyze"
    - "consider"
tools:
  allowed: []
---

# Think Skill

Before taking any action, think through the problem:

1. **Understand the Request**
   - What is the user asking?
   - What context is available?
   - What constraints exist?

2. **Identify Key Steps**
   - Break down the task into steps
   - Order steps logically
   - Identify dependencies

3. **Consider Alternatives**
   - What are different approaches?
   - What are trade-offs?
   - Which approach is best?

4. **Plan Execution**
   - What tools are needed?
   - What information to gather?
   - What order to execute?

Output your thinking in a structured format before proceeding.
```

#### code-review.md

```markdown
---
name: code-review
description: Review code for bugs, security, and quality issues
triggers:
  keywords:
    - "review"
    - "check code"
    - "analyze code"
  patterns:
    - "review this (file|code)"
    - "check (my|the) (changes|code)"
tools:
  allowed:
    - read
    - grep
    - glob
  restricted:
    - write
    - edit
    - bash
---

# Code Review Skill

## Purpose
Analyze code and provide actionable feedback on quality, security, and correctness.

## Review Categories

### 1. Bugs & Logic Errors
- Incorrect logic
- Edge case handling
- Null/undefined checks
- Race conditions

### 2. Security
- Input validation
- SQL injection
- XSS vulnerabilities
- Authentication/authorization
- Data exposure

### 3. Performance
- N+1 queries
- Unnecessary loops
- Memory leaks
- Blocking operations

### 4. Style & Maintainability
- Naming conventions
- Code complexity
- Documentation
- Duplicate code

### 5. Architecture
- Module boundaries
- Dependency issues
- API design
- Test coverage

## Output Format

For each issue found:

```
**Severity**: Critical|High|Medium|Low
**Category**: Bug|Security|Performance|Style|Architecture
**File**: path/to/file:line_number
**Issue**: [clear description]
**Suggestion**: [how to fix]
**Example**:
  [code snippet if helpful]
```

## Rules

1. Review only - never modify code
2. Always include severity and category
3. Include line numbers when possible
4. Be specific and actionable
5. Prioritize critical issues
```

#### debug.md

```markdown
---
name: debug
description: Debug and diagnose issues in code
triggers:
  keywords:
    - "debug"
    - "fix"
    - "error"
    - "bug"
    - "issue"
  patterns:
    - "(fix|debug) (this|the) (error|bug|issue)"
    - "(why|what) is (wrong|broken|failing)"
tools:
  allowed:
    - read
    - grep
    - glob
    - bash
---

# Debug Skill

## Debugging Workflow

1. **Gather Information**
   - What is the error message?
   - What was expected vs actual behavior?
   - When does it occur?

2. **Locate the Problem**
   - Search for error text in files
   - Find relevant code sections
   - Check recent changes

3. **Analyze**
   - Read the problematic code
   - Trace execution flow
   - Identify root cause

4. **Propose Fix**
   - Explain what's wrong
   - Suggest specific changes
   - Show corrected code

5. **Verify**
   - Check for similar issues elsewhere
   - Consider edge cases
   - Verify fix doesn't break other things

## Output Format

```
## Diagnosis

**Error**: [error message or behavior]
**Location**: file:line
**Root Cause**: [explanation]

## Proposed Fix

**File**: path/to/file
**Change**: [description]
**Code**:
  [corrected code snippet]

## Prevention

[Suggestions to prevent similar issues]
```
```

## Skill 组合

```python
class SkillComposer:
    """技能组合器"""

    def compose(
        self,
        skills: List[Skill],
        composition_type: str = "sequential"
    ) -> Skill:
        """组合多个技能"""

        if composition_type == "sequential":
            # 顺序执行
            combined_content = "# Combined Skill: Sequential Execution\n\n"
            combined_content += "Execute the following skills in order:\n\n"

            for i, skill in enumerate(skills, 1):
                combined_content += f"## Step {i}: {skill.name}\n\n{skill.content}\n\n"

            # 合并工具
            all_allowed = []
            all_restricted = []
            for skill in skills:
                all_allowed.extend(skill.tools.allowed)
                all_restricted.extend(skill.tools.restricted)

            return Skill(
                name=f"combined_{skills[0].name}_sequence",
                description=f"Sequential execution: {', '.join(s.name for s in skills)}",
                content=combined_content,
                tools=SkillTools(
                    allowed=list(set(all_allowed)),
                    restricted=list(set(all_restricted))
                )
            )

        elif composition_type == "parallel":
            # 并行执行
            combined_content = "# Combined Skill: Parallel Analysis\n\n"
            combined_content += "Apply the following perspectives simultaneously:\n\n"

            for skill in skills:
                combined_content += f"## {skill.name}\n\n{skill.content}\n\n"

            return Skill(
                name=f"combined_{skills[0].name}_parallel",
                description=f"Parallel analysis: {', '.join(s.name for s in skills)}",
                content=combined_content
            )

        return None
```

## 测试

```python
@pytest.fixture
def skill_registry():
    registry = SkillRegistry()
    registry.add_skill_dir(Path("tests/fixtures/skills"))
    return registry

def test_skill_loading(skill_registry):
    skill = skill_registry.get("code-review")
    assert skill is not None
    assert skill.name == "code-review"

def test_skill_trigger(skill_registry):
    matches = skill_registry.find_matching_skills("review this code")
    assert len(matches) > 0
    assert any(s.name == "code-review" for s in matches)

def test_skill_tool_filter(skill_registry):
    skill_registry.activate("code-review")

    assert skill_registry.get_allowed_tools("read")
    assert not skill_registry.get_allowed_tools("write")

def test_skill_injection(skill_registry):
    injector = SkillInjector(skill_registry)

    prompt = "You are an AI assistant."
    user_input = "review this code"

    result = injector.inject_skills(prompt, user_input)

    assert "code-review" in result
    assert len(result) > len(prompt)
```
---


# 06 - Trigger & Orchestration 触发与编排

## 概述

Trigger System 让 Agent 能够自主运行，不仅响应用户消息，还能根据时间、事件、状态变化自动触发执行。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Trigger System                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Trigger Sources                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  User       │ │  Cron       │ │  Webhook    │    │   │
│  │  │  Message    │ │  Scheduler  │ │  Handler    │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Heartbeat  │ │  File Watch │ │  Event Bus  │    │   │
│  │  │  Monitor    │ │             │ │             │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Trigger Manager                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Registry   │ │  Priority   │ │  Execution  │    │   │
│  │  │             │ │  Queue      │ │  Scheduler  │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Agent Loop                          │   │
│  │                                                       │   │
│  │  Trigger → Context → LLM → Tools → Result            │   │
│  │                                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Action Handler                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Message    │ │  File       │ │  External   │    │   │
│  │  │  Output     │ │  Update     │ │  API Call   │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 触发类型

### Trigger Type 定义

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import asyncio
import croniter

class TriggerType(Enum):
    USER_MESSAGE = "user_message"      # 用户消息触发
    CRON = "cron"                       # 定时触发
    WEBHOOK = "webhook"                 # HTTP webhook
    HEARTBEAT = "heartbeat"             # 周期性心跳
    FILE_WATCH = "file_watch"           # 文件变化
    EVENT = "event"                     # 事件总线
    CONDITION = "condition"             # 条件触发

@dataclass
class TriggerEvent:
    """触发事件"""
    trigger_type: TriggerType
    trigger_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    priority: int = 0

    @property
    def is_scheduled(self) -> bool:
        return self.trigger_type == TriggerType.CRON

    @property
    def is_external(self) -> bool:
        return self.trigger_type in [TriggerType.WEBHOOK, TriggerType.EVENT]


class Trigger(ABC):
    """触发器基类"""

    trigger_type: TriggerType
    id: str = ""

    @abstractmethod
    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查是否应该触发"""
        pass

    @abstractmethod
    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        """创建触发事件"""
        pass

    @abstractmethod
    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动触发器（对于持续型触发器）"""
        pass

    @abstractmethod
    async def stop(self):
        """停止触发器"""
        pass


@dataclass
class TriggerAction:
    """触发后的动作"""
    agent_prompt: str                    # 发送给 Agent 的提示
    session_id: Optional[str] = None     # 使用哪个会话
    skills_to_activate: List[str] = field(default_factory=list)
    output_channels: List[str] = field(default_factory=list)
    save_result: bool = True
    retry_on_failure: int = 0
```

### 6.1 Cron Trigger

```python
class CronTrigger(Trigger):
    """定时触发器"""

    trigger_type = TriggerType.CRON

    def __init__(
        self,
        schedule: str,          # cron 表达式
        action: TriggerAction,
        timezone: str = "local",
        jitter_seconds: int = 0  # 添加随机延迟避免同时触发
    ):
        self.schedule = schedule
        self.action = action
        self.timezone = timezone
        self.jitter_seconds = jitter_seconds
        self._cron = croniter.croniter(schedule)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查是否到达触发时间"""
        now = datetime.now()
        next_run = self._cron.get_next(datetime)
        return now >= next_run

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id=self.id,
            payload={
                "schedule": self.schedule,
                "action": self.action,
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动定时器"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop(callback))

    async def stop(self):
        """停止定时器"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self, callback: Callable[[TriggerEvent], None]):
        """定时运行循环"""
        while self._running:
            # 计算下次运行时间
            now = datetime.now()
            next_run = self._cron.get_next(datetime)
            wait_seconds = (next_run - now).total_seconds()

            # 添加 jitter
            if self.jitter_seconds > 0:
                import random
                wait_seconds += random.uniform(0, self.jitter_seconds)

            # 等待
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            # 触发
            if self._running:
                try:
                    event = self.create_event()
                    callback(event)
                except Exception as e:
                    print(f"Cron trigger error: {e}")

    def get_next_runs(self, n: int = 5) -> List[datetime]:
        """获取接下来的 N 次运行时间"""
        return [self._cron.get_next(datetime) for _ in range(n)]


# 使用示例
daily_report = CronTrigger(
    schedule="0 9 * * *",      # 每天 9:00
    action=TriggerAction(
        agent_prompt="Generate daily report summarizing yesterday's activities",
        skills_to_activate=["report"],
        output_channels=["email", "slack"]
    )
)

hourly_check = CronTrigger(
    schedule="0 * * * *",      # 每小时
    action=TriggerAction(
        agent_prompt="Check system health and report any issues",
        output_channels=["slack"]
    ),
    jitter_seconds=300         # 添加最多 5 分钟随机延迟
)
```

### 6.2 Webhook Trigger

```python
from fastapi import FastAPI, Request, Response
import hashlib
import hmac

@dataclass
class WebhookConfig:
    """Webhook 配置"""
    endpoint: str              # URL 路径
    secret: Optional[str] = None  # 验证签名
    allowed_sources: List[str] = field(default_factory=list)
    verify_signature: bool = False
    rate_limit: int = 100      # 每分钟限制


class WebhookTrigger(Trigger):
    """HTTP Webhook 触发器"""

    trigger_type = TriggerType.WEBHOOK

    def __init__(
        self,
        config: WebhookConfig,
        action: TriggerAction,
        payload_transform: Callable[[dict], dict] = None
    ):
        self.config = config
        self.action = action
        self.payload_transform = payload_transform
        self._callback: Optional[Callable] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查请求是否有效"""
        request = context.get("request")

        # 检查来源
        if self.config.allowed_sources:
            source = request.headers.get("X-Forwarded-For", "")
            if source not in self.config.allowed_sources:
                return False

        return True

    def verify_signature(self, request: Request, body: bytes) -> bool:
        """验证签名"""
        if not self.config.secret:
            return True

        signature = request.headers.get("X-Signature", "")
        expected = hmac.new(
            self.config.secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.WEBHOOK,
            trigger_id=self.id,
            payload=payload,
            source=payload.get("source", "webhook")
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """注册 webhook endpoint"""
        self._callback = callback

    async def stop(self):
        """注销 webhook"""
        self._callback = None

    async def handle_request(self, request: Request) -> Response:
        """处理 webhook 请求"""
        body = await request.body()

        # 验证签名
        if self.config.verify_signature:
            if not self.verify_signature(request, body):
                return Response(status_code=401, content="Invalid signature")

        # 解析 payload
        try:
            import json
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response(status_code=400, content="Invalid JSON")

        # 转换 payload
        if self.payload_transform:
            payload = self.payload_transform(payload)

        # 创建事件并回调
        event = self.create_event(payload)
        if self._callback:
            self._callback(event)

        return Response(status_code=200, content="OK")


# Webhook Manager
class WebhookManager:
    """管理所有 webhook"""

    def __init__(self, app: FastAPI = None):
        self.app = app or FastAPI()
        self.triggers: Dict[str, WebhookTrigger] = {}

    def register(self, trigger: WebhookTrigger):
        """注册 webhook"""
        self.triggers[trigger.config.endpoint] = trigger

        # 创建路由
        @self.app.post(trigger.config.endpoint)
        async def handle(request: Request):
            return await trigger.handle_request(request)

    def unregister(self, endpoint: str):
        """注销 webhook"""
        if endpoint in self.triggers:
            del self.triggers[endpoint]


# 使用示例
github_pr_webhook = WebhookTrigger(
    config=WebhookConfig(
        endpoint="/webhook/github",
        secret="your-webhook-secret",
        verify_signature=True
    ),
    action=TriggerAction(
        agent_prompt="Review the pull request changes",
        skills_to_activate=["code-review"]
    ),
    payload_transform=lambda p: {
        "pr_number": p.get("number"),
        "repo": p.get("repository", {}).get("full_name"),
        "action": p.get("action")
    }
)
```

### 6.3 Heartbeat Trigger

```python
class HeartbeatTrigger(Trigger):
    """心跳触发器"""

    trigger_type = TriggerType.HEARTBEAT

    def __init__(
        self,
        interval_seconds: int,
        action: TriggerAction,
        check_conditions: Callable[[], bool] = None
    ):
        self.interval = interval_seconds
        self.action = action
        self.check_conditions = check_conditions
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查条件"""
        if self.check_conditions:
            return self.check_conditions()
        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.HEARTBEAT,
            trigger_id=self.id,
            payload={
                "interval": self.interval,
                "timestamp": datetime.now().isoformat(),
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动心跳"""
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop(callback))

    async def stop(self):
        """停止心跳"""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _heartbeat_loop(self, callback: Callable[[TriggerEvent], None]):
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self.interval)

            if self._running and self.should_fire({}):
                event = self.create_event()
                callback(event)
```

### 6.4 File Watch Trigger

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

class FileWatchTrigger(Trigger):
    """文件变化触发器"""

    trigger_type = TriggerType.FILE_WATCH

    def __init__(
        self,
        watch_path: str,
        action: TriggerAction,
        patterns: List[str] = None,      # 只监听特定模式
        ignore_patterns: List[str] = None
    ):
        self.watch_path = watch_path
        self.action = action
        self.patterns = patterns or ["*"]
        self.ignore_patterns = ignore_patterns or []
        self._observer: Optional[Observer] = None
        self._callback: Optional[Callable] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查文件变化是否匹配模式"""
        path = context.get("path", "")
        import fnmatch

        # 检查是否匹配监听模式
        for pattern in self.patterns:
            if fnmatch.fnmatch(path, pattern):
                break
        else:
            return False

        # 检查是否在忽略列表
        for ignore in self.ignore_patterns:
            if fnmatch.fnmatch(path, ignore):
                return False

        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.FILE_WATCH,
            trigger_id=self.id,
            payload={
                "path": payload.get("path"),
                "event_type": payload.get("event_type"),
                **payload
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动文件监听"""
        self._callback = callback
        self._observer = Observer()

        handler = self._create_handler()
        self._observer.schedule(handler, self.watch_path, recursive=True)
        self._observer.start()

    async def stop(self):
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        self._callback = None

    def _create_handler(self) -> FileSystemEventHandler:
        """创建文件事件处理器"""
        class Handler(FileSystemEventHandler):
            def __init__(self, trigger):
                self.trigger = trigger

            def on_modified(self, event):
                if event.is_directory:
                    return

                path = event.src_path
                if self.trigger.should_fire({"path": path}):
                    event_obj = self.trigger.create_event({
                        "path": path,
                        "event_type": "modified"
                    })
                    if self.trigger._callback:
                        self.trigger._callback(event_obj)

        return Handler(self)


# 使用示例
config_watch = FileWatchTrigger(
    watch_path="~/.harness/config",
    action=TriggerAction(
        agent_prompt="Configuration file changed, reload settings",
        skills_to_activate=["config-reload"]
    ),
    patterns=["*.yaml", "*.json"],
    ignore_patterns=["*.bak", "*.tmp"]
)
```

### 6.5 Event Bus Trigger

```python
from collections import defaultdict
import asyncio

class EventBus:
    """事件总线"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """发布事件"""
        self._queue.put_nowait((event_type, payload))

    async def run(self):
        """运行事件处理循环"""
        while True:
            event_type, payload = await self._queue.get()

            for callback in self._subscribers[event_type]:
                try:
                    await callback(payload)
                except Exception as e:
                    print(f"Event handler error: {e}")


class EventBusTrigger(Trigger):
    """事件总线触发器"""

    trigger_type = TriggerType.EVENT

    def __init__(
        self,
        event_type: str,
        action: TriggerAction,
        event_bus: EventBus
    ):
        self.event_type = event_type
        self.action = action
        self.event_bus = event_bus
        self._registered = False

    def should_fire(self, context: Dict[str, Any]) -> bool:
        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.EVENT,
            trigger_id=self.id,
            payload={
                "event_type": self.event_type,
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """订阅事件"""
        def handler(payload):
            event = self.create_event(payload)
            callback(event)

        self.event_bus.subscribe(self.event_type, handler)
        self._registered = True

    async def stop(self):
        """取消订阅"""
        self.event_bus.unsubscribe(self.event_type, None)


# 使用示例
bus = EventBus()

user_login_trigger = EventBusTrigger(
    event_type="user.login",
    action=TriggerAction(
        agent_prompt="New user logged in, send welcome message"
    ),
    event_bus=bus
)

# 发布事件
bus.publish("user.login", {"user_id": "123", "name": "John"})
```

## Trigger Manager

```python
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import asyncio
from datetime import datetime
from queue import PriorityQueue

@dataclass
class TriggerRegistration:
    """触发器注册信息"""
    trigger: Trigger
    action: TriggerAction
    enabled: bool = True
    last_fired: Optional[datetime] = None
    fire_count: int = 0
    error_count: int = 0


class TriggerManager:
    """触发器管理器"""

    def __init__(self, agent_harness: "AgentHarness"):
        self.harness = agent_harness
        self._registrations: Dict[str, TriggerRegistration] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._priority_queue: PriorityQueue = PriorityQueue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

    def register(
        self,
        trigger: Trigger,
        action: TriggerAction,
        enabled: bool = True
    ) -> str:
        """注册触发器"""
        trigger_id = trigger.id or self._generate_id()
        trigger.id = trigger_id

        self._registrations[trigger_id] = TriggerRegistration(
            trigger=trigger,
            action=action,
            enabled=enabled
        )

        return trigger_id

    def unregister(self, trigger_id: str):
        """注销触发器"""
        if trigger_id in self._registrations:
            reg = self._registrations[trigger_id]
            asyncio.create_task(reg.trigger.stop())
            del self._registrations[trigger_id]

    def enable(self, trigger_id: str):
        """启用触发器"""
        if trigger_id in self._registrations:
            self._registrations[trigger_id].enabled = True

    def disable(self, trigger_id: str):
        """禁用触发器"""
        if trigger_id in self._registrations:
            self._registrations[trigger_id].enabled = False

    async def start(self):
        """启动所有触发器"""
        self._running = True

        # 启动事件处理器
        self._processor_task = asyncio.create_task(self._process_events())

        # 启动所有触发器
        for reg in self._registrations.values():
            if reg.enabled:
                await reg.trigger.start(self._enqueue_event)

    async def stop(self):
        """停止所有触发器"""
        self._running = False

        # 停止所有触发器
        for reg in self._registrations.values():
            await reg.trigger.stop()

        # 停止处理器
        if self._processor_task:
            self._processor_task.cancel()

    def _enqueue_event(self, event: TriggerEvent):
        """将事件加入队列"""
        self._event_queue.put_nowait(event)

    async def _process_events(self):
        """处理事件队列"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                await self._handle_event(event)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _handle_event(self, event: TriggerEvent):
        """处理单个事件"""
        trigger_id = event.trigger_id

        if trigger_id not in self._registrations:
            return

        reg = self._registrations[trigger_id]

        if not reg.enabled:
            return

        try:
            # 获取或创建会话
            session_id = reg.action.session_id
            if session_id:
                session = await self.harness.memory.get_session(session_id)
            else:
                session = await self.harness.memory.create_session()

            # 构建提示
            prompt = self._build_prompt(reg.action, event)

            # 激活技能
            for skill_name in reg.action.skills_to_activate:
                self.harness.skills.activate(skill_name)

            # 运行 Agent
            result = await self.harness.run(prompt, session.id)

            # 输出结果
            await self._handle_output(result, reg.action)

            # 更新统计
            reg.last_fired = datetime.now()
            reg.fire_count += 1

        except Exception as e:
            reg.error_count += 1
            print(f"Trigger execution error: {e}")

            # 重试
            if reg.action.retry_on_failure > 0:
                await self._retry(reg, event)

    def _build_prompt(self, action: TriggerAction, event: TriggerEvent) -> str:
        """构建提示"""
        prompt = action.agent_prompt

        # 添加事件上下文
        if event.payload:
            context = "\n\nEvent context:\n"
            for key, value in event.payload.items():
                context += f"- {key}: {value}\n"
            prompt += context

        return prompt

    async def _handle_output(self, result: Any, action: TriggerAction):
        """处理输出"""
        for channel in action.output_channels:
            if channel == "console":
                print(result)
            elif channel == "file":
                # 写入文件
                pass
            elif channel == "slack":
                # 发送到 Slack
                pass
            elif channel == "email":
                # 发送邮件
                pass

    async def _retry(self, reg: TriggerRegistration, event: TriggerEvent):
        """重试触发"""
        for attempt in range(reg.action.retry_on_failure):
            await asyncio.sleep(5 * (attempt + 1))

            try:
                await self._handle_event(event)
                break
            except Exception:
                continue

    def list_triggers(self) -> List[Dict]:
        """列出所有触发器"""
        return [
            {
                "id": trigger_id,
                "type": reg.trigger.trigger_type.value,
                "enabled": reg.enabled,
                "last_fired": reg.last_fired,
                "fire_count": reg.fire_count,
                "error_count": reg.error_count
            }
            for trigger_id, reg in self._registrations.items()
        ]

    def _generate_id(self) -> str:
        import uuid
        return f"trigger_{uuid.uuid4().hex[:8]}"
```

## 多代理编排

```python
@dataclass
class AgentTeam:
    """代理团队"""
    name: str
    agents: Dict[str, "AgentConfig"] = field(default_factory=dict)
    coordinator: str = ""        # 协调者 agent
    communication_bus: str = "internal"


@dataclass
class AgentConfig:
    """代理配置"""
    name: str
    role: str
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    max_iterations: int = 10
    priority: int = 0


class MultiAgentOrchestrator:
    """多代理编排器"""

    def __init__(
        self,
        harness: "AgentHarness",
        event_bus: EventBus
    ):
        self.harness = harness
        self.event_bus = event_bus
        self._teams: Dict[str, AgentTeam] = {}
        self._agent_results: Dict[str, List[Any]] = {}

    def create_team(self, team: AgentTeam) -> str:
        """创建代理团队"""
        team_id = team.name
        self._teams[team_id] = team
        return team_id

    async def dispatch(
        self,
        task: str,
        team_id: str,
        strategy: str = "parallel"
    ) -> Dict[str, Any]:
        """分发任务到团队"""

        team = self._teams.get(team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        if strategy == "parallel":
            # 并行执行所有 agent
            results = await self._parallel_dispatch(task, team)

        elif strategy == "sequential":
            # 顺序执行
            results = await self._sequential_dispatch(task, team)

        elif strategy == "coordinated":
            # 协调执行
            results = await self._coordinated_dispatch(task, team)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        return results

    async def _parallel_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """并行分发"""
        tasks = []
        for agent_name, config in team.agents.items():
            tasks.append(self._run_agent(agent_name, config, task))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: result
            for name, result in zip(team.agents.keys(), results)
        }

    async def _sequential_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """顺序分发"""
        results = {}

        # 按 priority 排序
        sorted_agents = sorted(
            team.agents.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )

        current_task = task
        for agent_name, config in sorted_agents:
            result = await self._run_agent(agent_name, config, current_task)
            results[agent_name] = result

            # 将结果传递给下一个 agent
            if isinstance(result, dict) and "output" in result:
                current_task = f"{task}\n\nPrevious agent output: {result['output']}"

        return results

    async def _coordinated_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """协调分发"""
        results = {}
        coordinator = team.agents.get(team.coordinator)

        if not coordinator:
            return await self._parallel_dispatch(task, team)

        # 协调者分配任务
        allocation = await self._run_agent(
            team.coordinator,
            coordinator,
            f"Coordinate the following task among team members:\n{task}\n\nAvailable agents: {list(team.agents.keys())}"
        )

        # 执行分配的任务
        if isinstance(allocation, dict) and "assignments" in allocation:
            for agent_name, subtask in allocation.get("assignments", {}).items():
                if agent_name in team.agents:
                    result = await self._run_agent(
                        agent_name,
                        team.agents[agent_name],
                        subtask
                    )
                    results[agent_name] = result

        return results

    async def _run_agent(
        self,
        agent_name: str,
        config: AgentConfig,
        task: str
    ) -> Any:
        """运行单个代理"""
        # 创建专用会话
        session = await self.harness.memory.create_session()

        # 激活技能
        for skill_name in config.skills:
            self.harness.skills.activate(skill_name)

        # 运行
        result = await self.harness.run(task, session.id)

        return {
            "agent": agent_name,
            "output": result.final_response.content if hasattr(result, 'final_response') else result,
            "iterations": result.iterations if hasattr(result, 'iterations') else 0
        }

    def broadcast(self, message: str, team_id: str):
        """广播消息到团队"""
        self.event_bus.publish(
            f"team.{team_id}.broadcast",
            {"message": message}
        )
```

## Output Handler

```python
class OutputHandler:
    """输出处理器"""

    def __init__(self):
        self._channels: Dict[str, "OutputChannel"] = {}

    def register_channel(self, name: str, channel: "OutputChannel"):
        """注册输出通道"""
        self._channels[name] = channel

    async def send(self, result: Any, channels: List[str]):
        """发送结果到指定通道"""
        for channel_name in channels:
            if channel_name in self._channels:
                await self._channels[channel_name].send(result)


class OutputChannel(ABC):
    """输出通道抽象"""

    @abstractmethod
    async def send(self, content: Any):
        """发送内容"""
        pass


class ConsoleChannel(OutputChannel):
    """控制台输出"""

    async def send(self, content: Any):
        print(content)


class FileChannel(OutputChannel):
    """文件输出"""

    def __init__(self, file_path: str, mode: str = "a"):
        self.file_path = file_path
        self.mode = mode

    async def send(self, content: Any):
        with open(self.file_path, self.mode) as f:
            f.write(str(content) + "\n")


class SlackChannel(OutputChannel):
    """Slack 输出"""

    def __init__(self, webhook_url: str, channel: str):
        self.webhook_url = webhook_url
        self.channel = channel

    async def send(self, content: Any):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                json={
                    "channel": self.channel,
                    "text": str(content)
                }
            )


class EmailChannel(OutputChannel):
    """邮件输出"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender: str,
        recipients: List[str]
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients

    async def send(self, content: Any):
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = "Harness Agent Output"
        msg.set_content(str(content))

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_server,
            port=self.smtp_port
        )
```

## 测试

```python
@pytest.mark.asyncio
async def test_cron_trigger():
    trigger = CronTrigger(
        schedule="* * * * *",  # 每分钟
        action=TriggerAction(agent_prompt="test")
    )

    events = []
    await trigger.start(lambda e: events.append(e))

    # 等待触发
    await asyncio.sleep(65)

    await trigger.stop()

    assert len(events) >= 1

@pytest.mark.asyncio
async def test_trigger_manager():
    harness = AgentHarness(config)
    manager = TriggerManager(harness)

    trigger = CronTrigger(
        schedule="0 * * * *",
        action=TriggerAction(agent_prompt="test")
    )

    trigger_id = manager.register(trigger, trigger.action)

    assert trigger_id in manager.list_triggers()

    await manager.start()
    await manager.stop()
```
---


# 07 - SDK 与 API 设计

## 概述

Harness SDK 提供简洁的 Python API，让开发者能够轻松地将 AI Agent 能力嵌入到自己的应用中。

## 设计原则

1. **简洁优先**: 核心操作一行代码搞定
2. **渐进式复杂度**: 从简单到高级逐步展开
3. **类型安全**: 完整的类型注解和 IDE 支持
4. **异步优先**: 原生支持异步操作
5. **可扩展**: 易于添加自定义组件

## 快速开始

### 安装

```bash
pip install harness-ai
```

### 最简示例

```python
from harness import AgentHarness

# 创建 agent
agent = AgentHarness()

# 运行
response = await agent.run("分析当前目录的代码结构")
print(response.content)
```

### 完整配置

```python
from harness import AgentHarness, HarnessConfig, ToolConfig

config = HarnessConfig(
    model="claude-sonnet-4-6",
    api_key="your-api-key",
    memory_dir="~/.harness/memory",
    tools=ToolConfig(
        enabled=["read", "write", "bash", "web_search"],
        permission_mode="sandbox"
    )
)

agent = AgentHarness(config)
```

## 核心 API

### AgentHarness 类

```python
from typing import Optional, List, Dict, Any, AsyncIterator, Callable
from dataclasses import dataclass, field

@dataclass
class HarnessConfig:
    """Harness 配置"""

    # LLM 配置
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096

    # 记忆配置
    memory_type: str = "file"          # file, sqlite, redis
    memory_dir: str = "~/.harness"
    max_context_tokens: int = 200000
    auto_compress: bool = True

    # 工具配置
    tools_enabled: List[str] = field(default_factory=lambda: ["all"])
    permission_mode: str = "sandbox"    # sandbox, ask, full

    # 技能配置
    skill_dirs: List[str] = field(default_factory=list)
    auto_load_skills: bool = True

    # 触发器配置
    triggers_enabled: bool = True

    # 调试
    debug: bool = False
    log_level: str = "INFO"


class AgentHarness:
    """Harness 主类"""

    def __init__(
        self,
        config: Optional[HarnessConfig] = None,
        **kwargs
    ):
        """
        初始化 Harness

        Args:
            config: 配置对象，如果为 None 则使用默认配置
            **kwargs: 配置参数，会覆盖 config 中的对应项
        """
        self.config = config or HarnessConfig(**kwargs)
        self._initialize_components()

    def _initialize_components(self):
        """初始化内部组件"""
        # LLM 客户端
        self.llm = self._create_llm_client()

        # 记忆系统
        self.memory = MemoryManager(
            MemoryConfig(
                storage_type=self.config.memory_type,
                storage_path=self.config.memory_dir,
                max_context_tokens=self.config.max_context_tokens,
                auto_compress=self.config.auto_compress
            ),
            llm_client=self.llm
        )

        # 工具系统
        self.tools = ToolRegistry()
        self.tools.register_defaults()
        self._apply_tool_permissions()

        # 技能系统
        self.skills = SkillRegistry()
        self._load_skills()

        # 触发器管理器
        self.triggers = TriggerManager(self)

        # 事件总线
        self.events = EventBus()

    # ==================== 核心方法 ====================

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> "RunResult":
        """
        运行 agent（异步）

        Args:
            prompt: 用户输入
            session_id: 会话 ID，如果为 None 则创建新会话
            **kwargs: 额外参数

        Returns:
            RunResult: 运行结果

        Example:
            result = await agent.run("分析代码", session_id="my-session")
            print(result.content)
        """
        # 获取或创建会话
        if session_id:
            session = await self.memory.get_session(session_id)
            if not session:
                session = await self.memory.create_session(session_id=session_id)
        else:
            session = await self.memory.create_session()

        # 添加用户消息
        session.add_message(Message(role="user", content=prompt))

        # 构建上下文
        context = await self.memory.build_context(
            session=session,
            skills=self.skills.get_active_skills(),
            tools=self.tools.list_tools()
        )

        # 注入技能
        system_prompt = self.skills.injector.inject_skills(
            context.system_prompt,
            prompt
        )

        # 运行代理循环
        result = await self._loop.run(prompt, session)

        # 更新会话
        await self.memory.update_session(session)

        return result

    def run_sync(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> "RunResult":
        """
        运行 agent（同步）

        Args:
            prompt: 用户输入
            session_id: 会话 ID

        Returns:
            RunResult: 运行结果

        Example:
            result = agent.run_sync("分析代码")
        """
        import asyncio
        return asyncio.run(self.run(prompt, session_id, **kwargs))

    async def stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> AsyncIterator["StreamChunk"]:
        """
        流式运行 agent

        Args:
            prompt: 用户输入
            session_id: 会话 ID
            on_chunk: chunk 回调函数

        Yields:
            StreamChunk: 流式输出块

        Example:
            async for chunk in agent.stream("分析代码"):
                print(chunk.content, end="")
        """
        async for chunk in self._loop.stream(prompt, session_id):
            if on_chunk:
                on_chunk(chunk)
            yield chunk

    async def interrupt(self):
        """
        中断当前运行

        Example:
            # 在另一个任务中
            await agent.interrupt()
        """
        self._loop.interrupt()

    # ==================== 工具管理 ====================

    def register_tool(
        self,
        tool: Tool,
        category: str = "custom"
    ):
        """
        注册自定义工具

        Args:
            tool: 工具实例
            category: 工具分类

        Example:
            @agent.tool()
            def my_tool(arg: str) -> str:
                '''My custom tool'''
                return f"Result: {arg}"
        """
        self.tools.register(tool, category)

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission: PermissionLevel = PermissionLevel.SAFE
    ):
        """
        工具装饰器

        Example:
            @agent.tool(description="Get weather info")
            async def weather(city: str) -> str:
                return f"Weather in {city}: sunny"
        """
        def decorator(func):
            tool_instance = create_tool_from_function(
                func,
                name=name,
                description=description,
                permission=permission
            )
            self.register_tool(tool_instance)
            return func
        return decorator

    # ==================== 技能管理 ====================

    def load_skill(self, path: str):
        """
        加载技能文件

        Args:
            path: 技能文件路径

        Example:
            agent.load_skill("skills/code-review.md")
        """
        skill = Skill.from_file(Path(path))
        self.skills.register(skill)

    def activate_skill(self, skill_name: str):
        """
        激活技能

        Args:
            skill_name: 技能名称

        Example:
            agent.activate_skill("code-review")
        """
        self.skills.activate(skill_name)

    def deactivate_skill(self, skill_name: str):
        """
        关闭技能

        Args:
            skill_name: 技能名称
        """
        self.skills.deactivate(skill_name)

    # ==================== 触发器管理 ====================

    def on_schedule(
        self,
        schedule: str,
        prompt: str,
        **kwargs
    ) -> str:
        """
        设置定时触发

        Args:
            schedule: cron 表达式
            prompt: 触发时执行的提示

        Returns:
            trigger_id: 触发器 ID

        Example:
            @agent.on_schedule("0 9 * * *")
            async def morning_report():
                return "Generate daily report"
        """
        trigger = CronTrigger(
            schedule=schedule,
            action=TriggerAction(agent_prompt=prompt, **kwargs)
        )
        return self.triggers.register(trigger, trigger.action)

    def on_webhook(
        self,
        endpoint: str,
        prompt: str,
        **kwargs
    ) -> str:
        """
        设置 webhook 触发

        Args:
            endpoint: webhook 路径
            prompt: 触发时执行的提示

        Returns:
            trigger_id: 触发器 ID

        Example:
            @agent.on_webhook("/github/pr")
            async def handle_pr(payload):
                return f"Review PR #{payload['number']}"
        """
        trigger = WebhookTrigger(
            config=WebhookConfig(endpoint=endpoint),
            action=TriggerAction(agent_prompt=prompt, **kwargs)
        )
        return self.triggers.register(trigger, trigger.action)

    # ==================== 会话管理 ====================

    async def create_session(
        self,
        user_id: Optional[str] = None,
        working_directory: str = ""
    ) -> Session:
        """
        创建新会话

        Returns:
            Session: 会话对象
        """
        return await self.memory.create_session(
            user_id=user_id,
            working_directory=working_directory
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Session: 会话对象，如果不存在返回 None
        """
        return await self.memory.get_session(session_id)

    async def list_sessions(self) -> List[Session]:
        """
        列出所有会话

        Returns:
            List[Session]: 会话列表
        """
        return await self.memory.session_store.list_sessions()

    async def delete_session(self, session_id: str):
        """
        删除会话

        Args:
            session_id: 会话 ID
        """
        await self.memory.session_store.delete(session_id)

    # ==================== 记忆管理 ====================

    async def remember(
        self,
        content: str,
        memory_type: str = "knowledge",
        metadata: Optional[Dict] = None
    ):
        """
        存储记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据

        Example:
            await agent.remember(
                "User prefers Python over JavaScript",
                memory_type="preference"
            )
        """
        await self.memory.store_memory(memory_type, content, metadata)

    async def recall(
        self,
        query: str,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """
        检索记忆

        Args:
            query: 查询字符串
            limit: 返回数量限制

        Returns:
            List[MemoryEntry]: 记忆条目列表

        Example:
            memories = await agent.recall("user preferences")
        """
        return await self.memory.retrieve_memory(query, limit=limit)

    # ==================== 配置 ====================

    @classmethod
    def from_config(cls, config_path: str) -> "AgentHarness":
        """
        从配置文件创建

        Args:
            config_path: 配置文件路径 (YAML 或 JSON)

        Returns:
            AgentHarness: Harness 实例

        Example:
            agent = AgentHarness.from_config("harness.yaml")
        """
        import yaml

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        config = HarnessConfig(**config_data)
        return cls(config)

    @classmethod
    def from_env(cls) -> "AgentHarness":
        """
        从环境变量创建

        Returns:
            AgentHarness: Harness 实例

        环境变量:
            ANTHROPIC_API_KEY or OPENAI_API_KEY
            HARNESS_MODEL
            HARNESS_MEMORY_DIR
            ...
        """
        import os

        config = HarnessConfig(
            model=os.getenv("HARNESS_MODEL", "claude-sonnet-4-6"),
            api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"),
            memory_dir=os.getenv("HARNESS_MEMORY_DIR", "~/.harness"),
            debug=os.getenv("HARNESS_DEBUG", "false").lower() == "true"
        )
        return cls(config)

    # ==================== 生命周期 ====================

    async def start(self):
        """
        启动 Harness（启动触发器等后台服务）
        """
        if self.config.triggers_enabled:
            await self.triggers.start()

        # 启动事件总线
        asyncio.create_task(self.events.run())

    async def stop(self):
        """
        停止 Harness
        """
        await self.triggers.stop()
```

## 返回类型

```python
@dataclass
class RunResult:
    """运行结果"""
    status: LoopState
    content: str
    messages: List[Message]
    iterations: int
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = None
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == LoopState.COMPLETED

    @property
    def was_interrupted(self) -> bool:
        return self.status == LoopState.INTERRUPTED


@dataclass
class StreamChunk:
    """流式输出块"""
    type: ChunkType
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None

    @property
    def is_text(self) -> bool:
        return self.type == ChunkType.TEXT

    @property
    def is_tool_call(self) -> bool:
        return self.type == ChunkType.TOOL_CALL_START
```

## 装饰器 API

```python
# 工具装饰器
@agent.tool(description="Get current weather")
async def get_weather(city: str, unit: str = "celsius") -> str:
    """获取指定城市的天气"""
    return f"Weather in {city}: 25°{unit[0].upper()}"

# 技能装饰器
@agent.skill(
    name="daily-brief",
    triggers=["brief", "summary", "report"]
)
async def daily_brief():
    """生成每日简报"""
    return """Generate a daily brief with:
1. Key activities from yesterday
2. Upcoming tasks
3. Important notifications"""

# 触发器装饰器
@agent.on_schedule("0 9 * * *")
async def morning_brief():
    return "Generate morning brief"

@agent.on_webhook("/slack/events")
async def handle_slack(payload):
    return f"Process Slack event: {payload['type']}"
```

## 上下文管理器

```python
class HarnessContext:
    """上下文管理器"""

    def __init__(self, agent: AgentHarness, session_id: str):
        self.agent = agent
        self.session_id = session_id
        self.session: Optional[Session] = None

    async def __aenter__(self) -> "HarnessContext":
        self.session = await self.agent.get_session(self.session_id)
        if not self.session:
            self.session = await self.agent.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.agent.memory.update_session(self.session)

    async def run(self, prompt: str) -> RunResult:
        return await self.agent.run(prompt, session_id=self.session_id)

    async def stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        async for chunk in self.agent.stream(prompt, self.session_id):
            yield chunk


# 使用示例
async with agent.session("my-session") as ctx:
    result1 = await ctx.run("分析这个文件")
    result2 = await ctx.run("重构它")  # 保持上下文连续
```

## FastAPI 集成

```python
from fastapi import FastAPI
from harness import AgentHarness, HarnessContext

app = FastAPI()
agent = AgentHarness.from_config("harness.yaml")

@app.on_event("startup")
async def startup():
    await agent.start()

@app.on_event("shutdown")
async def shutdown():
    await agent.stop()

@app.post("/chat")
async def chat(message: str, session_id: str = None):
    """聊天接口"""
    result = await agent.run(message, session_id=session_id)
    return {
        "response": result.content,
        "session_id": result.session_id,
        "iterations": result.iterations
    }

@app.post("/chat/stream")
async def chat_stream(message: str, session_id: str = None):
    """流式聊天接口"""
    from fastapi.responses import StreamingResponse

    async def generate():
        async for chunk in agent.stream(message, session_id):
            yield f"data: {chunk.content}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# Webhook 端点
@app.post("/webhook/{trigger_id}")
async def handle_webhook(trigger_id: str, request: Request):
    """Webhook 处理"""
    payload = await request.json()
    # 触发器会自动处理
    return {"status": "ok"}
```

## CLI 工具

```python
# harness/cli.py
import click
import asyncio

@click.group()
def cli():
    """Harness CLI"""
    pass

@cli.command()
@click.argument("prompt")
@click.option("--session", "-s", help="Session ID")
@click.option("--stream", is_flag=True, help="Stream output")
def run(prompt: str, session: str, stream: bool):
    """运行 agent"""
    agent = AgentHarness.from_env()

    if stream:
        async def main():
            async for chunk in agent.stream(prompt, session):
                print(chunk.content, end="", flush=True)
            print()
        asyncio.run(main())
    else:
        result = agent.run_sync(prompt, session)
        print(result.content)

@cli.command()
def sessions():
    """列出所有会话"""
    agent = AgentHarness.from_env()
    for session_id in asyncio.run(agent.list_sessions()):
        print(session_id)

@cli.command()
@click.argument("session_id")
def session(session_id: str):
    """显示会话详情"""
    agent = AgentHarness.from_env()
    session = asyncio.run(agent.get_session(session_id))
    if session:
        print(f"Session: {session.id}")
        print(f"Messages: {len(session.messages)}")
        for msg in session.messages[-5:]:
            print(f"  {msg.role}: {msg.content[:50]}...")

@cli.command()
def skills():
    """列出所有技能"""
    agent = AgentHarness.from_env()
    for skill in agent.skills.list_skills():
        print(f"{skill.name}: {skill.description}")

@cli.command()
def triggers():
    """列出所有触发器"""
    agent = AgentHarness.from_env()
    for trigger in agent.triggers.list_triggers():
        print(f"{trigger['id']}: {trigger['type']} ({'enabled' if trigger['enabled'] else 'disabled'})")

@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000)
def serve(host: str, port: int):
    """启动 HTTP 服务"""
    import uvicorn
    from harness.server import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    cli()
```

## 配置文件格式

```yaml
# harness.yaml

# LLM 配置
model: claude-sonnet-4-6
api_key: ${ANTHROPIC_API_KEY}  # 支持环境变量
temperature: 0.7
max_tokens: 4096

# 记忆配置
memory:
  type: sqlite
  path: ~/.harness/harness.db
  max_context_tokens: 200000
  auto_compress: true
  compression_threshold: 0.8

# 工具配置
tools:
  enabled:
    - read
    - write
    - edit
    - glob
    - grep
    - bash
    - web_search
  permission_mode: sandbox
  sandbox_paths:
    - /workspace
  blocked_commands:
    - rm -rf /
    - sudo

# 技能配置
skills:
  directories:
    - ~/.harness/skills
    - ./skills
  auto_load: true

# 触发器配置
triggers:
  - type: cron
    schedule: "0 9 * * *"
    prompt: "Generate daily report"
    output_channels:
      - console

  - type: webhook
    endpoint: /webhook/github
    prompt: "Process GitHub webhook"
    verify_signature: true

# 日志配置
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ~/.harness/harness.log

# 调试
debug: false
```

## 错误处理

```python
from harness import HarnessError, LLMError, ToolError

try:
    result = await agent.run("分析代码")
except LLMError as e:
    print(f"LLM 错误: {e}")
except ToolError as e:
    print(f"工具错误: {e}")
except HarnessError as e:
    print(f"Harness 错误: {e}")
```

## 测试支持

```python
from harness.testing import MockHarness, MockTool

# 创建 mock harness
agent = MockHarness()

# 设置预期响应
agent.expect("分析代码").respond("代码分析结果...")

# 运行测试
result = await agent.run("分析代码")
assert result.content == "代码分析结果..."
```

---


# 08 - 安全设计

## 概述

安全是 Harness 设计的核心考量。作为可内嵌的 Agent 框架，Harness 需要在提供强大能力的同时，确保系统安全可控。

## 安全架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Layers                          │
│                                                              │
│  Layer 1: 输入验证                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Prompt Injection 检测                              │   │
│  │ • 输入长度限制                                       │   │
│  │ • 恶意模式检测                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 2: 权限控制                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 工具权限管理                                       │   │
│  │ • 路径访问控制                                       │   │
│  │ • 命令执行限制                                       │   │
│  │ • 操作确认机制                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 3: 执行隔离                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 沙箱执行环境                                       │   │
│  │ • 资源限制（CPU/内存/时间）                          │   │
│  │ • 网络隔离                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 4: 审计日志                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 所有操作记录                                       │   │
│  │ • 工具调用追踪                                       │   │
│  │ • 异常检测                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 权限模型

### Permission Level

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Set
from pathlib import Path

class PermissionLevel(Enum):
    """权限级别"""
    SAFE = "safe"              # 安全操作，自动允许
    MODERATE = "moderate"      # 中等风险，可选确认
    DANGEROUS = "dangerous"    # 危险操作，必须确认
    RESTRICTED = "restricted"  # 受限操作，默认禁用

class PermissionMode(Enum):
    """权限模式"""
    FULL = "full"              # 完全访问
    ASK = "ask"                # 询问确认
    SANDBOX = "sandbox"        # 沙箱模式
    READ_ONLY = "read_only"    # 只读模式
```

### PermissionSet

```python
@dataclass
class PermissionSet:
    """权限集合"""

    # 路径权限
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    read_only_paths: List[str] = field(default_factory=list)

    # 命令权限
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    command_whitelist_mode: bool = False  # True = 白名单模式

    # 工具权限
    allowed_tools: Set[str] = field(default_factory=set)
    blocked_tools: Set[str] = field(default_factory=set)

    # 网络权限
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    allow_all_network: bool = True

    # 资源限制
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_execution_time: float = 60.0       # 秒
    max_memory_mb: int = 512               # MB

    # 默认策略
    default_deny: bool = True

    def is_path_allowed(self, path: str, action: str = "read") -> bool:
        """检查路径访问权限"""
        try:
            abs_path = Path(path).resolve()
        except Exception:
            return False

        # 检查黑名单
        for blocked in self.blocked_paths:
            try:
                if abs_path.is_relative_to(Path(blocked).expanduser().resolve()):
                    return False
            except Exception:
                continue

        # 检查只读路径
        if action == "write":
            for read_only in self.read_only_paths:
                try:
                    if abs_path.is_relative_to(Path(read_only).expanduser().resolve()):
                        return False
                except Exception:
                    continue

        # 检查白名单
        if self.allowed_paths:
            for allowed in self.allowed_paths:
                try:
                    if abs_path.is_relative_to(Path(allowed).expanduser().resolve()):
                        return True
                except Exception:
                    continue
            return False

        return not self.default_deny

    def is_command_allowed(self, command: str) -> bool:
        """检查命令执行权限"""
        # 检查黑名单
        for blocked in self.blocked_commands:
            if blocked in command:
                return False

        # 白名单模式
        if self.command_whitelist_mode:
            for allowed in self.allowed_commands:
                if command.strip().startswith(allowed):
                    return True
            return False

        return True

    def is_tool_allowed(self, tool_name: str) -> bool:
        """检查工具使用权限"""
        if tool_name in self.blocked_tools:
            return False
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        return True

    def is_domain_allowed(self, domain: str) -> bool:
        """检查网络域名权限"""
        if domain in self.blocked_domains:
            return False
        if self.allowed_domains and domain not in self.allowed_domains:
            return False
        return self.allow_all_network

    @classmethod
    def sandbox(cls, workspace: str) -> "PermissionSet":
        """创建沙箱权限"""
        return cls(
            allowed_paths=[workspace],
            blocked_paths=[
                "/etc", "/root", "/home",
                "~/.ssh", "~/.gnupg", "~/.config",
                "~/.aws", "~/.env"
            ],
            blocked_commands=[
                "rm -rf", "sudo", "chmod", "chown",
                "mkfs", "dd", "fdisk",
                "curl | bash", "wget | bash",
                "> /dev/", "2>&1"
            ],
            allowed_tools={"read", "write", "edit", "glob", "grep"},
            blocked_tools={"bash"},
            allow_all_network=False,
            default_deny=True,
            max_execution_time=30.0
        )

    @classmethod
    def read_only(cls, workspace: str) -> "PermissionSet":
        """创建只读权限"""
        permissions = cls.sandbox(workspace)
        permissions.read_only_paths = [workspace]
        permissions.allowed_tools = {"read", "glob", "grep"}
        return permissions

    @classmethod
    def full_access(cls) -> "PermissionSet":
        """创建完全访问权限（谨慎使用）"""
        return cls(
            blocked_commands=["rm -rf /", "rm -rf ~"],
            default_deny=False,
            allow_all_network=True
        )
```

## 沙箱执行

### Sandbox Executor

```python
import asyncio
import subprocess
import resource
import os
from typing import Optional, Dict, Any

class SandboxExecutor:
    """沙箱执行器"""

    def __init__(
        self,
        permissions: PermissionSet,
        container_runtime: str = "none"  # none, docker, nsjail
    ):
        self.permissions = permissions
        self.container_runtime = container_runtime

    async def execute_command(
        self,
        command: str,
        cwd: str = None,
        env: Dict[str, str] = None,
        stdin: str = None
    ) -> "ExecutionResult":
        """在沙箱中执行命令"""

        # 权限检查
        if not self.permissions.is_command_allowed(command):
            raise PermissionDeniedError(f"Command not allowed: {command}")

        # 根据运行时选择执行方式
        if self.container_runtime == "docker":
            return await self._execute_docker(command, cwd, env, stdin)
        elif self.container_runtime == "nsjail":
            return await self._execute_nsjail(command, cwd, env, stdin)
        else:
            return await self._execute_native(command, cwd, env, stdin)

    async def _execute_native(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        stdin: str
    ) -> "ExecutionResult":
        """原生执行（有限隔离）"""

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            cwd=cwd,
            env=self._filter_env(env)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin.encode() if stdin else None),
                timeout=self.permissions.max_execution_time
            )

            return ExecutionResult(
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace")
            )

        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Execution timed out after {self.permissions.max_execution_time}s")

    async def _execute_docker(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        stdin: str
    ) -> "ExecutionResult":
        """Docker 容器执行"""

        # 构建 docker 命令
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none" if not self.permissions.allow_all_network else "bridge",
            "--memory", f"{self.permissions.max_memory_mb}m",
            "--cpus", "1",
            "-v", f"{cwd}:/workspace",
            "-w", "/workspace",
        ]

        # 添加环境变量
        for key, value in (env or {}).items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # 使用安全镜像
        docker_cmd.extend(["harness-sandbox:latest", "sh", "-c", command])

        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None
        )

        stdout, stderr = await process.communicate(
            stdin.encode() if stdin else None
        )

        return ExecutionResult(
            exit_code=process.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace")
        )

    def _filter_env(self, env: Dict[str, str] = None) -> Dict[str, str]:
        """过滤环境变量，移除敏感信息"""
        sensitive_vars = {
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "GITHUB_TOKEN", "GITLAB_TOKEN",
            "DATABASE_URL", "DB_PASSWORD"
        }

        filtered = dict(os.environ)
        for var in sensitive_vars:
            filtered.pop(var, None)

        if env:
            filtered.update(env)

        return filtered


@dataclass
class ExecutionResult:
    """执行结果"""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0
```

## 输入验证

### Prompt Injection 检测

```python
import re
from typing import List, Tuple

class PromptInjectionDetector:
    """Prompt 注入检测器"""

    # 常见的注入模式
    INJECTION_PATTERNS = [
        # 角色扮演
        r"ignore (all )?(previous|above) instructions",
        r"disregard (all )?(previous|above) instructions",
        r"forget (all )?(previous|above) instructions",

        # 系统提示泄露
        r"what (is|are) your (system |initial )?instructions",
        r"repeat your (system |initial )?prompt",
        r"show me your (system |initial )?prompt",

        # 越狱尝试
        r"you are now (a|an) \w+",
        r"pretend (to be|you are)",
        r"act as (if|though)",

        # 编码绕过
        r"base64",
        r"rot13",
        r"hex encode",

        # 危险指令
        r"sudo",
        r"chmod",
        r"rm -rf",
        r"delete all",
        r"format disk",
    ]

    def __init__(self, custom_patterns: List[str] = None):
        self.patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.INJECTION_PATTERNS
        ]
        if custom_patterns:
            self.patterns.extend(
                re.compile(p, re.IGNORECASE)
                for p in custom_patterns
            )

    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        检测是否存在注入尝试

        Returns:
            (is_safe, detected_patterns)
        """
        detected = []

        for pattern in self.patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)

        return len(detected) == 0, detected

    def sanitize(self, text: str) -> str:
        """清理可疑内容"""
        # 基本清理：转义特殊字符
        sanitized = text

        # 可以添加更复杂的清理逻辑
        # 注意：清理并不能保证安全，应该结合拒绝策略

        return sanitized


class InputValidator:
    """输入验证器"""

    def __init__(
        self,
        max_length: int = 100000,
        check_injection: bool = True
    ):
        self.max_length = max_length
        self.injection_detector = PromptInjectionDetector() if check_injection else None

    def validate(self, text: str) -> "ValidationResult":
        """验证输入"""
        errors = []
        warnings = []

        # 长度检查
        if len(text) > self.max_length:
            errors.append(f"Input exceeds maximum length ({self.max_length})")

        # 注入检测
        if self.injection_detector:
            is_safe, patterns = self.injection_detector.detect(text)
            if not is_safe:
                warnings.append(f"Potential injection patterns detected: {patterns}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_text=self.injection_detector.sanitize(text) if self.injection_detector else text
        )


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_text: str
```

## 操作确认

```python
from abc import ABC, abstractmethod
from typing import Callable, Optional
import asyncio

class ConfirmationHandler(ABC):
    """确认处理器抽象"""

    @abstractmethod
    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        """请求用户确认"""
        pass


class ConsoleConfirmation(ConfirmationHandler):
    """控制台确认"""

    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        print(f"\n[CONFIRMATION REQUIRED] Risk: {risk_level}")
        print(f"Operation: {operation}")
        print(f"Details: {details}")
        print()

        response = input("Proceed? [y/N]: ")
        return response.lower() == "y"


class CallbackConfirmation(ConfirmationHandler):
    """回调确认"""

    def __init__(self, callback: Callable[[str, Dict, str], bool]):
        self.callback = callback

    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        if asyncio.iscoroutinefunction(self.callback):
            return await self.callback(operation, details, risk_level)
        return self.callback(operation, details, risk_level)


class ConfirmationManager:
    """确认管理器"""

    def __init__(
        self,
        handler: ConfirmationHandler,
        auto_approve_safe: bool = True,
        cache_approvals: bool = False
    ):
        self.handler = handler
        self.auto_approve_safe = auto_approve_safe
        self.cache_approvals = cache_approvals
        self._approval_cache: Dict[str, bool] = {}

    async def check_confirmation(
        self,
        tool: Tool,
        arguments: Dict[str, Any]
    ) -> bool:
        """检查是否需要确认并请求"""

        # 安全操作自动批准
        if self.auto_approve_safe and tool.permission_level == PermissionLevel.SAFE:
            return True

        # 检查缓存
        cache_key = f"{tool.name}:{json.dumps(arguments, sort_keys=True)}"
        if self.cache_approvals and cache_key in self._approval_cache:
            return self._approval_cache[cache_key]

        # 请求确认
        risk_level = tool.permission_level.value
        approved = await self.handler.request_confirmation(
            operation=tool.name,
            details=arguments,
            risk_level=risk_level
        )

        # 缓存结果
        if self.cache_approvals:
            self._approval_cache[cache_key] = approved

        return approved
```

## 审计日志

```python
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

@dataclass
class AuditLogEntry:
    """审计日志条目"""
    timestamp: datetime
    session_id: str
    event_type: str              # tool_call, file_access, command, etc.
    action: str
    resource: str
    arguments: Dict[str, Any]
    result: str                  # success, denied, error
    details: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "event_type": self.event_type,
            "action": self.action,
            "resource": self.resource,
            "arguments": self._sanitize_arguments(self.arguments),
            "result": self.result,
            "details": self.details
        })

    def _sanitize_arguments(self, args: Dict) -> Dict:
        """清理敏感参数"""
        sensitive_keys = {"password", "token", "secret", "key", "credential"}
        sanitized = {}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized


class AuditLogger:
    """审计日志器"""

    def __init__(
        self,
        log_dir: str = "~/.harness/audit",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 30
    ):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self._current_file: Optional[Path] = None

    def log(self, entry: AuditLogEntry):
        """记录审计日志"""
        log_file = self._get_log_file()

        with open(log_file, "a") as f:
            f.write(entry.to_json() + "\n")

    def _get_log_file(self) -> Path:
        """获取当前日志文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit-{today}.log"

        # 检查文件大小
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            # 创建新文件
            index = 1
            while True:
                new_file = self.log_dir / f"audit-{today}-{index}.log"
                if not new_file.exists():
                    log_file = new_file
                    break
                index += 1

        return log_file

    def query(
        self,
        session_id: str = None,
        event_type: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[AuditLogEntry]:
        """查询审计日志"""
        results = []

        for log_file in self.log_dir.glob("audit-*.log"):
            with open(log_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        entry = AuditLogEntry(
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            session_id=data["session_id"],
                            event_type=data["event_type"],
                            action=data["action"],
                            resource=data["resource"],
                            arguments=data["arguments"],
                            result=data["result"],
                            details=data["details"]
                        )

                        # 过滤
                        if session_id and entry.session_id != session_id:
                            continue
                        if event_type and entry.event_type != event_type:
                            continue
                        if start_time and entry.timestamp < start_time:
                            continue
                        if end_time and entry.timestamp > end_time:
                            continue

                        results.append(entry)
                    except Exception:
                        continue

        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def cleanup_old_logs(self):
        """清理过期日志"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit-*.log"):
            try:
                file_date_str = log_file.stem.split("-")[1]
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    log_file.unlink()
            except Exception:
                continue
```

## 安全配置

```python
@dataclass
class SecurityConfig:
    """安全配置"""

    # 权限模式
    permission_mode: PermissionMode = PermissionMode.SANDBOX

    # 路径配置
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/root", "~/.ssh", "~/.aws", "~/.config"
    ])

    # 命令配置
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /", "rm -rf ~", "sudo", "chmod -R 777"
    ])

    # 工具配置
    allowed_tools: List[str] = field(default_factory=list)  # 空 = 全部允许
    blocked_tools: List[str] = field(default_factory=list)

    # 网络配置
    allow_network: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)

    # 执行限制
    max_execution_time: float = 60.0
    max_file_size: int = 10 * 1024 * 1024
    max_memory_mb: int = 512

    # 确认配置
    require_confirmation: bool = True
    auto_approve_safe: bool = True
    cache_approvals: bool = False

    # 输入验证
    max_input_length: int = 100000
    check_prompt_injection: bool = True

    # 审计
    enable_audit_log: bool = True
    audit_log_dir: str = "~/.harness/audit"
    audit_retention_days: int = 30

    # 沙箱
    sandbox_runtime: str = "none"  # none, docker, nsjail

    def to_permission_set(self) -> PermissionSet:
        """转换为权限集合"""
        return PermissionSet(
            allowed_paths=self.allowed_paths,
            blocked_paths=self.blocked_paths,
            blocked_commands=self.blocked_commands,
            allowed_tools=set(self.allowed_tools),
            blocked_tools=set(self.blocked_tools),
            allow_all_network=self.allow_network,
            allowed_domains=self.allowed_domains,
            blocked_domains=self.blocked_domains,
            max_execution_time=self.max_execution_time,
            max_file_size=self.max_file_size,
            max_memory_mb=self.max_memory_mb
        )


# 预设配置
SECURITY_PRESETS = {
    "development": SecurityConfig(
        permission_mode=PermissionMode.ASK,
        require_confirmation=False,
        sandbox_runtime="none"
    ),

    "production": SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        sandbox_runtime="docker",
        require_confirmation=True,
        enable_audit_log=True
    ),

    "readonly": SecurityConfig(
        permission_mode=PermissionMode.READ_ONLY,
        allowed_tools=["read", "glob", "grep"],
        blocked_tools=["write", "edit", "bash"]
    ),

    "isolated": SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        sandbox_runtime="docker",
        allow_network=False,
        allowed_paths=["/workspace"],
        blocked_commands=["rm", "sudo", "chmod"]
    )
}
```

## 安全最佳实践

### 1. 始终使用最小权限原则

```python
# 好：明确限制工作目录
agent = AgentHarness(
    security=SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        allowed_paths=["/workspace/my-project"]
    )
)

# 避免：完全访问权限
agent = AgentHarness(
    security=SecurityConfig(
        permission_mode=PermissionMode.FULL  # 危险！
    )
)
```

### 2. 启用审计日志

```python
agent = AgentHarness(
    security=SecurityConfig(
        enable_audit_log=True,
        audit_log_dir="/var/log/harness"
    )
)
```

### 3. 验证用户输入

```python
validator = InputValidator(check_injection=True)

user_input = get_user_input()
result = validator.validate(user_input)

if not result.valid:
    raise ValueError(result.errors)

if result.warnings:
    log.warning(f"Input warnings: {result.warnings}")
```

### 4. 使用沙箱执行

```python
# 生产环境推荐使用 Docker 沙箱
agent = AgentHarness(
    security=SecurityConfig(
        sandbox_runtime="docker",
        max_execution_time=30.0
    )
)
```

### 5. 定期审查审计日志

```python
# 检查可疑活动
audit = AuditLogger()
suspicious = audit.query(
    event_type="tool_call",
    start_time=datetime.now() - timedelta(days=1)
)

for entry in suspicious:
    if entry.result == "denied":
        alert_security_team(entry)
```
---


# 09 - 实施路线图

## 概述

本文档规划了 Harness 项目的实施路线图，按阶段划分，确保从 MVP 到生产就绪的渐进式开发。

## 项目结构

```
harness/
├── src/
│   └── harness/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent_loop.py
│       │   ├── context.py
│       │   └── result.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── local.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── executor.py
│       │   ├── file.py
│       │   ├── shell.py
│       │   ├── web.py
│       │   └── mcp.py
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── store.py
│       │   ├── context_builder.py
│       │   └── compressor.py
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── skill.py
│       │   ├── registry.py
│       │   ├── loader.py
│       │   └── generator.py
│       ├── triggers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── cron.py
│       │   ├── webhook.py
│       │   └── manager.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── permissions.py
│       │   ├── sandbox.py
│       │   ├── validator.py
│       │   └── audit.py
│       ├── sdk/
│       │   ├── __init__.py
│       │   ├── harness.py
│       │   └── config.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── examples/
├── skills/
│   └── default/
├── pyproject.toml
├── setup.py
└── README.md
```

## Phase 1: MVP 核心功能 (Week 1-3)

### 目标

构建最小可用版本，验证核心架构。

### 任务清单

#### Week 1: Agent Loop & LLM 客户端

| 任务 | 优先级 | 状态 |
|------|--------|------|
| AgentLoop 核心循环实现 | P0 | - |
| 基础状态机 | P0 | - |
| LLMClient 抽象接口 | P0 | - |
| AnthropicClient 实现 | P0 | - |
| OpenAIClient 实现 | P1 | - |
| Token 计数器 | P1 | - |
| 基础错误处理 | P0 | - |
| 单元测试 | P0 | - |

**交付物**:
- `src/harness/core/agent_loop.py`
- `src/harness/llm/`
- `tests/unit/test_agent_loop.py`

#### Week 2: 工具系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Tool 基类定义 | P0 | - |
| ToolRegistry 实现 | P0 | - |
| ToolExecutor 实现 | P0 | - |
| File Tools (Read, Write, Edit) | P0 | - |
| Glob/Grep Tools | P0 | - |
| Bash Tool (基础版) | P1 | - |
| PermissionSet 实现 | P0 | - |
| 工具权限检查 | P0 | - |

**交付物**:
- `src/harness/tools/`
- `tests/unit/test_tools.py`

#### Week 3: 记忆系统基础

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Session 数据结构 | P0 | - |
| FileSessionStore | P0 | - |
| ContextBuilder 基础版 | P0 | - |
| Token 预算管理 | P1 | - |
| 会话持久化 | P0 | - |

**交付物**:
- `src/harness/memory/`
- `tests/unit/test_memory.py`

### MVP 示例代码

```python
from harness import AgentHarness

# 最简使用
agent = AgentHarness(
    model="claude-sonnet-4-6",
    api_key="your-key"
)

# 运行
result = await agent.run("读取 main.py 并分析其结构")
print(result.content)
```

## Phase 2: 增强功能 (Week 4-6)

### 目标

增加高级特性，提升易用性和可靠性。

### 任务清单

#### Week 4: 上下文管理增强

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 上下文压缩器 | P1 | - |
| 会话摘要生成 | P1 | - |
| SQLite 存储 | P1 | - |
| 记忆检索基础 | P2 | - |

#### Week 5: 技能系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Skill 文件格式 | P0 | - |
| SkillRegistry | P0 | - |
| SkillLoader | P0 | - |
| SkillInjector | P0 | - |
| 预置技能库 (5-10个) | P1 | - |

#### Week 6: 安全增强 & Web 工具

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 沙箱执行器 | P0 | - |
| 输入验证器 | P1 | - |
| WebSearch Tool | P1 | - |
| WebFetch Tool | P1 | - |
| 审计日志 | P1 | - |

### Phase 2 示例

```python
# 技能激活
agent = AgentHarness()
agent.load_skill("skills/code-review.md")
agent.activate_skill("code-review")

result = await agent.run("review this code")
```

## Phase 3: 高级特性 (Week 7-10)

### 目标

实现自主运行、多代理协调等高级特性。

### 任务清单

#### Week 7-8: 触发器系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Trigger 基类 | P0 | - |
| CronTrigger | P0 | - |
| WebhookTrigger | P0 | - |
| HeartbeatTrigger | P1 | - |
| FileWatchTrigger | P2 | - |
| TriggerManager | P0 | - |
| OutputHandler | P1 | - |

#### Week 9: 多代理协调

| 任务 | 优先级 | 状态 |
|------|--------|------|
| EventBus | P1 | - |
| AgentTeam | P2 | - |
| MultiAgentOrchestrator | P2 | - |
| 并行/顺序分发 | P2 | - |

#### Week 10: MCP 支持

| 任务 | 优先级 | 状态 |
|------|--------|------|
| MCP 协议实现 | P1 | - |
| MCP Connector | P1 | - |
| MCP Tool 包装 | P1 | - |

### Phase 3 示例

```python
# 定时任务
agent.on_schedule("0 9 * * *", "生成每日报告")

# Webhook
agent.on_webhook("/github/pr", "Review PR changes")

# 启动后台服务
await agent.start()
```

## Phase 4: 生产就绪 (Week 11-12)

### 目标

完善文档、测试、性能优化，确保生产可用。

### 任务清单

#### Week 11: 完善与优化

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 完整类型注解 | P0 | - |
| 文档完善 | P0 | - |
| 性能优化 | P1 | - |
| 错误处理完善 | P0 | - |
| 日志系统 | P1 | - |
| 指标收集 | P2 | - |

#### Week 12: 测试与发布

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 单元测试覆盖 80%+ | P0 | - |
| 集成测试 | P0 | - |
| E2E 测试 | P1 | - |
| CI/CD 配置 | P0 | - |
| PyPI 发布准备 | P0 | - |
| 示例项目 | P1 | - |

### 发布清单

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 文档完整
- [ ] CHANGELOG 更新
- [ ] 版本号确定
- [ ] PyPI 发布
- [ ] GitHub Release

## 技术债务管理

### 已知技术债务

| 项目 | 描述 | 优先级 | 计划处理 |
|------|------|--------|----------|
| 流式输出优化 | 大文件流式处理性能 | P1 | Phase 4 |
| Token 计数精度 | 不同模型的 token 计数 | P2 | Phase 4 |
| 错误恢复 | 更健壮的错误恢复机制 | P1 | Phase 3 |
| 缓存机制 | LLM 响应缓存 | P2 | Phase 3 |

## 依赖管理

### 核心依赖

```toml
[project]
dependencies = [
    "anthropic>=0.18.0",
    "openai>=1.0.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.0.0",
    "croniter>=2.0.0",
    "watchdog>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
vector = [
    "chromadb>=0.4.0",
    "tiktoken>=0.5.0",
]
docker = [
    "docker>=6.0.0",
]
```

## 测试策略

### 测试金字塔

```
        ┌─────────┐
        │   E2E   │  ← 少量，关键流程
        │  Tests  │
        ├─────────┤
        │Integration│ ← 中等，组件交互
        │   Tests   │
        ├───────────┤
        │   Unit    │  ← 大量，函数级别
        │   Tests   │
        └───────────┘
```

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| core/ | 90% |
| llm/ | 85% |
| tools/ | 85% |
| memory/ | 80% |
| skills/ | 80% |
| triggers/ | 75% |
| security/ | 90% |

### CI/CD 流程

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run linting
        run: |
          ruff check src/
          black --check src/
          mypy src/

      - name: Run tests
        run: pytest --cov=src/harness tests/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 发布计划

### 版本规划

| 版本 | 时间 | 内容 |
|------|------|------|
| 0.1.0 | Week 3 | MVP |
| 0.2.0 | Week 6 | 增强功能 |
| 0.3.0 | Week 10 | 高级特性 |
| 1.0.0 | Week 12 | 生产就绪 |

### 版本策略

- **0.x.x**: 开发版本，API 可能变更
- **1.x.x**: 稳定版本，遵循语义化版本
- **主版本号**: 不兼容的 API 变更
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修复

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM API 变更 | 高 | 抽象层隔离，快速适配 |
| 性能瓶颈 | 中 | 性能测试，优化关键路径 |
| 安全漏洞 | 高 | 安全审计，沙箱隔离 |
| 依赖冲突 | 低 | 版本锁定，可选依赖 |

## 后续规划

### v1.1+ 考虑的功能

- TypeScript SDK
- Rust 核心（性能优化）
- 更多 LLM 后端支持
- Web UI Dashboard
- 云端部署方案
- 更多预置技能
- 自学习增强
- 多模态支持
---


# 10 - 与 Hermes/OpenClaw 对比

## 概述

本文档对比 Harness 项目与 Hermes Agent 和 OpenClaw 的设计差异，明确本项目的定位和独特价值。

## 竞品概览

### Hermes Agent

- **开发方**: Nous Research
- **定位**: 自学习个人运行时
- **特点**:
  - 自动从重复模式生成技能
  - 搜索历史对话
  - 多平台接入（Telegram、Discord 等）
  - Web UI Dashboard
- **Stars**: 100,000+ (GitHub)
- **License**: MIT

### OpenClaw

- **开发方**: OpenAI 社区
- **定位**: 多代理控制平面
- **特点**:
  - 持久代理团队
  - 多渠道路由
  - ClawHub 技能市场
  - TaskFlow 工作流
- **Stars**: 极高
- **License**: Open Source

### 本 Harness

- **定位**: 可内嵌 SDK
- **特点**:
  - 嵌入用户系统
  - 最小依赖
  - 完全控制数据
  - 高度定制化

## 详细对比

### 架构对比

| 特性 | Hermes | OpenClaw | 本 Harness |
|------|--------|----------|------------|
| **架构模式** | 独立服务 | 独立服务 | **SDK 库** |
| **部署方式** | 独立进程/容器 | 独立进程/容器 | **嵌入应用** |
| **主要入口** | CLI + Gateway | CLI + Dashboard | **Python API** |
| **运行时** | Python + Gateway | Python + Runtime | **纯 Python** |

```
Hermes/OpenClaw 架构:
┌─────────────────────────────────────────────────────┐
│                   独立服务                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │   CLI     │  │  Gateway  │  │ Dashboard │       │
│  └───────────┘  └───────────┘  └───────────┘       │
│                        ↓                             │
│  ┌───────────────────────────────────────────┐     │
│  │              Agent Runtime                 │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
            ↑ 外部 API调用 ↑

本 Harness 架构:
┌─────────────────────────────────────────────────────┐
│                   用户应用                            │
│  ┌───────────────────────────────────────────┐     │
│  │           业务代码                          │     │
│  │  ┌───────────────────────────────────┐   │     │
│  │  │         Harness SDK (嵌入)          │   │     │
│  │  │  ┌─────────┐ ┌─────────┐          │   │     │
│  │  │  │ Agent   │ │ Memory  │          │   │     │
│  │  │  │ Loop    │ │ System  │          │   │     │
│  │  │  └─────────┘ └─────────┘          │   │     │
│  │  └───────────────────────────────────┘   │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
            无外部依赖，纯代码调用
```

### 功能对比

| 功能类别 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| **代理循环** | ✓ | ✓ | ✓ |
| **工具系统** | ✓ (丰富) | ✓ (丰富) | ✓ (可扩展) |
| **记忆系统** | ✓ (搜索优先) | ✓ (层级丰富) | ✓ (可配置后端) |
| **技能系统** | ✓ (自学习) | ✓ (静态+市场) | ✓ (文件+可扩展) |
| **触发器** | ✓ (cron+gateway) | ✓ (TaskFlow) | ✓ (cron+webhook+事件) |
| **多代理** | 父子模式 | 团队模式 | 支持 (可扩展) |
| **多渠道** | ✓ (22+) | ✓ (原生) | 可扩展 |
| **MCP 支持** | ✓ | ✓ | ✓ |
| **自学习** | ✓ | 部分 | 可选 |
| **市场/生态** | 稀疏 | ClawHub | 用户自建 |
| **Web UI** | ✓ | ✓ | 不含 (用户自建) |

### 内嵌能力对比

| 内嵌场景 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| Python 应用 | 需要外部调用 | 需要外部调用 | **直接 import** |
| FastAPI 集成 | 需要网关 | 需要网关 | **直接集成** |
| Celery 任务 | 需要外部触发 | 需要外部触发 | **直接调用** |
| 数据处理脚本 | 需要外部进程 | 需要外部进程 | **同进程执行** |
| 测试环境 | 需要启动服务 | 需要启动服务 | **Mock 内嵌** |

```python
# Hermes/OpenClaw 使用方式（需要外部服务）
import requests

response = requests.post(
    "http://localhost:8080/chat",
    json={"message": "分析代码"}
)

# 本 Harness 使用方式（直接嵌入）
from harness import AgentHarness

agent = AgentHarness()
result = await agent.run("分析代码")
print(result.content)
```

### 数据控制对比

| 数据类型 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| 会话数据 | Gateway 存储 | Runtime 存储 | **用户控制** |
| 记忆文件 | ~/.hermes | ~/.claw | **可配置路径** |
| 技能文件 | ~/.hermes/skills | ClawHub + local | **用户目录** |
| 日志/审计 | Gateway logs | Runtime logs | **用户控制** |
| API 密钥 | Gateway 管理 | Dashboard 管理 | **用户管理** |

### 性能对比

| 维度 | Hermes | OpenClaw | 本 Harness |
|------|--------|----------|------------|
| **启动延迟** | 需启动服务 | 启动服务 | **零延迟** |
| **调用开销** | HTTP/API | HTTP/API | **函数调用** |
| **资源占用** | 独立进程 | 独立进程 | **共享进程** |
| **并发处理** | Gateway 处理 | Runtime 处理 | **用户控制** |

### 定制化对比

| 定制维度 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| 工具扩展 | Skills + MCP | Skills + MCP | **Python 函数** |
| 记忆后端 | 固定 | 固定 | **可选多种** |
| LLM 后端 | 多种支持 | 多种支持 | **插件式** |
| 触发器类型 | Gateway 定义 | TaskFlow 定义 | **可自定义** |
| 输出通道 | Gateway 路由 | Dashboard 定义 | **用户控制** |
| 权限模型 | Gateway 配置 | Runtime 配置 | **代码级控制** |

## 本 Harness 的独特价值

### 1. 零外部依赖

```python
# 无需启动任何外部服务
agent = AgentHarness()
result = await agent.run("任务")
# 完成，无需任何外部进程
```

### 2. 完全数据控制

```python
# 数据完全在用户控制下
agent = AgentHarness(
    memory_dir="/secure/location",
    audit_log_dir="/compliant/logs"
)
# 数据不经过任何外部系统
```

### 3. 代码级定制

```python
# 可以深度定制每个组件
agent = AgentHarness()

# 自定义工具
@agent.tool()
def my_custom_tool(data: dict) -> str:
    return process_data(data)

# 自定义记忆后端
agent.memory = MyCustomMemoryStore()

# 自定义权限检查
agent.permissions = MyPermissionSet()
```

### 4. 测试友好

```python
# 内嵌测试，无需启动服务
from harness.testing import MockHarness

agent = MockHarness()
agent.expect("分析代码").respond("分析结果")

result = await agent.run("分析代码")
assert result.content == "分析结果"
```

### 5. 部署简单

```python
# 随应用部署，无需额外步骤
# 在现有应用中添加：
from harness import AgentHarness

agent = AgentHarness.from_config("harness.yaml")

# 集成到 FastAPI
@app.post("/ai")
async def ai_endpoint(message: str):
    return await agent.run(message)
```

## 适用场景对比

| 场景 | 推荐 |
|------|------|
| **个人自动化** | Hermes (自学习) |
| **多渠道代理系统** | OpenClaw (多渠道原生) |
| **需要技能市场** | OpenClaw (ClawHub) |
| **嵌入现有应用** | **本 Harness** |
| **数据敏感场景** | **本 Harness** |
| **深度定制需求** | **本 Harness** |
| **测试环境集成** | **本 Harness** |
| **轻量部署** | **本 Harness** |

## 取舍说明

### 本 Harness 的取舍

**选择舍弃的功能**:

1. **Web UI Dashboard**: 用户可自行开发或集成现有 UI
2. **技能市场**: 用户自建技能库更灵活
3. **Gateway 多渠道**: 用户按需集成
4. **自学习**: 可选功能，Phase 3+ 实现

**选择保留的核心**:

1. **Agent Loop**: 核心功能
2. **工具系统**: 必需能力
3. **记忆系统**: 持久化必需
4. **技能系统**: 行为指导必需
5. **触发器**: 自主运行必需
6. **安全系统**: 内嵌必需

### 学习借鉴

**从 Hermes 学习**:

- 自学习机制设计
- 搜索历史对话的检索策略
- 技能生成模式

**从 OpenClaw 学习**:

- TaskFlow 工作流概念
- 持久代理团队设计
- 多代理协调模式

**改进方向**:

- 内嵌优先设计
- 更简洁的 API
- 更灵活的组件替换
- 更完善的安全模型

## 互操作性

### 共享格式

本 Harness 支持与 Hermes/OpenClaw 共享的部分：

```python
# 共享技能文件格式 (.md)
# 可以直接加载 Hermes/OpenClaw 的技能文件
agent.load_skill("hermes_skill.md")

# 共享记忆文件格式 (MEMORY.md)
# 可以读取相同的记忆文件

# 共享 AGENTS.md 格式
# 项目上下文文件兼容
```

### 迁移路径

```python
# 从 Hermes 迁移
# Hermes 的 ~/.hermes/skills 可直接加载
agent = AgentHarness()
agent.skills.add_skill_dir("~/.hermes/skills")

# 从 OpenClaw 迁移
# OpenClaw 的 ClawHub 技能可下载后加载
agent.load_skill("downloaded_from_clawhub.md")
```

## 总结

本 Harness 的定位是 **"可内嵌的 AI Agent SDK"**，而非独立服务：

- **Hermes**: 自学习的个人代理运行时，适合自动化场景
- **OpenClaw**: 多代理控制平面，适合复杂代理系统
- **本 Harness**: 内嵌 SDK，适合集成到用户自己的系统

三者互补而非替代，用户可以根据需求选择：
- 需要独立服务 → Hermes/OpenClaw
- 需要内嵌集成 → 本 Harness
- 可以混合使用 → 共享技能/记忆格式
---


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

---


# 12 - 技术决策与权衡

## 概述

本文档记录 Harness 项目的技术决策、权衡取舍，以及已知限制和应对策略。

## 关键技术决策

### ADR-004: 长会话扩展性设计

**问题**: 会话消息可能持续增长，全量加载会导致内存爆炸。

**决策**: 采用分片存储 + 滑动窗口 + 分层摘要策略。

```
会话存储结构：
┌─────────────────────────────────────────────────────────┐
│ Session                                                 │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Active Window (最近 50 条消息)                   │   │
│  │ - 全量存储在内存                                 │   │
│  │ - 快速访问                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Recent Summaries (摘要层)                        │   │
│  │ - 每 100 条消息生成一个摘要                       │   │
│  │ - 存储在 SQLite，按需加载                        │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Archive (归档层)                                 │   │
│  │ - 原始消息压缩存储                               │   │
│  │ - 仅在需要时解压                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**实现**:

```python
class ScalableSessionStore:
    """可扩展的会话存储"""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_tables()

        # 配置
        self.active_window_size = 50      # 内存中保留的消息数
        self.summary_chunk_size = 100     # 每多少条生成摘要
        self.archive_threshold = 500      # 超过此数量开始归档

    async def get_session(self, session_id: str) -> Session:
        """获取会话，只加载活跃窗口"""
        session = Session(id=session_id)

        # 1. 加载活跃窗口（最近 N 条）
        cursor = self.db.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, self.active_window_size))

        session.messages = [self._row_to_message(row) for row in cursor.fetchall()]
        session.messages.reverse()  # 恢复时间顺序

        # 2. 加载摘要（如果有）
        cursor = self.db.execute("""
            SELECT summary FROM session_summaries
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))

        row = cursor.fetchone()
        if row:
            session.summary = row[0]

        return session

    async def add_message(self, session_id: str, message: Message):
        """添加消息，自动触发压缩"""
        # 写入消息
        self.db.execute("""
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, message.role, message.content, message.timestamp))

        # 检查是否需要生成摘要
        count = self._get_message_count(session_id)
        if count % self.summary_chunk_size == 0:
            await self._generate_summary(session_id)

        # 检查是否需要归档
        if count > self.archive_threshold:
            await self._archive_old_messages(session_id)

        self.db.commit()

    async def _generate_summary(self, session_id: str):
        """生成摘要（异步，不阻塞主流程）"""
        # 获取需要摘要的消息
        messages = await self._get_messages_for_summary(session_id)

        # 使用 LLM 生成摘要
        summary = await self._llm_summarize(messages)

        # 存储摘要
        self.db.execute("""
            INSERT INTO session_summaries (session_id, summary, message_range_start, message_range_end)
            VALUES (?, ?, ?, ?)
        """, (session_id, summary, messages[0].timestamp, messages[-1].timestamp))

    async def _archive_old_messages(self, session_id: str):
        """归档旧消息到压缩存储"""
        # 获取需要归档的消息
        cursor = self.db.execute("""
            SELECT id FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, self.archive_threshold // 2))

        ids_to_archive = [row[0] for row in cursor.fetchall()]

        if ids_to_archive:
            # 压缩并存储到归档表
            await self._compress_and_archive(session_id, ids_to_archive)

            # 从主表删除
            self.db.execute(f"""
                DELETE FROM messages WHERE id IN ({','.join('?' * len(ids_to_archive))})
            """, ids_to_archive)
```

**权衡**:
- ✅ 解决内存问题
- ✅ 支持超长会话
- ⚠️ 摘要可能丢失细节
- ⚠️ 归档消息访问延迟

---

### ADR-005: 成本控制设计

**问题**: 需要全局成本控制，防止 Token 消耗失控。

**决策**: 多层级成本控制体系。

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
    fallback_model: str = "claude-haiku-4-5"  # 便宜的模型
    context_reduction_ratio: float = 0.5      # 减少上下文比例


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

    async def check_global_budget(self) -> bool:
        """检查全局预算"""
        daily_cost = await self.storage.get_daily_cost()

        if daily_cost >= self.config.global_daily_budget_usd:
            if self.config.auto_throttle:
                # 触发自适应降级
                return False
            raise BudgetExceededError("Global daily budget exceeded")

        return True

    async def should_downgrade(self) -> tuple[bool, str]:
        """判断是否应该降级"""
        daily_cost = await self.storage.get_daily_cost()
        budget = self.config.global_daily_budget_usd

        if daily_cost >= budget * 0.8:  # 80% 预算
            return True, self.config.fallback_model

        return False, ""

    async def record_usage(
        self,
        session_id: str,
        user_id: str,
        usage: TokenUsage,
        cost_usd: float
    ):
        """记录使用量"""
        await self.storage.record(
            session_id=session_id,
            user_id=user_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now()
        )


class AdaptiveDegradation:
    """自适应降级"""

    def __init__(self, cost_controller: CostController, llm_registry: dict):
        self.cost = cost_controller
        self.llm_registry = llm_registry

    async def select_model(self, preferred_model: str) -> str:
        """选择合适的模型"""
        should_downgrade, fallback = await self.cost.should_downgrade()

        if should_downgrade:
            return fallback

        return preferred_model

    async def adjust_context_budget(
        self,
        requested_tokens: int
    ) -> int:
        """调整上下文预算"""
        should_downgrade, _ = await self.cost.should_downgrade()

        if should_downgrade:
            return int(requested_tokens * self.cost.config.context_reduction_ratio)

        return requested_tokens
```

**权衡**:
- ✅ 防止成本失控
- ✅ 支持多租户
- ⚠️ 降级可能影响体验
- ⚠️ 需要准确的价格表

---

### ADR-006: Skill 冲突解决

**问题**: 多个 Skill 同时激活可能导致指令冲突。

**决策**: 实现优先级 + 互斥 + 融合策略。

```python
@dataclass
class SkillPriority:
    """技能优先级"""
    skill_name: str
    priority: int = 0           # 数值越高优先级越高
    exclusive: bool = False     # 是否互斥（激活时禁用其他）
    conflicts_with: List[str] = field(default_factory=list)  # 冲突列表


class SkillConflictResolver:
    """技能冲突解决器"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.priorities: Dict[str, SkillPriority] = {}

    def set_priority(self, priority: SkillPriority):
        """设置技能优先级"""
        self.priorities[priority.skill_name] = priority

    def resolve(self, matched_skills: List[Skill], user_input: str) -> List[Skill]:
        """解决冲突，返回最终激活的技能"""

        if not matched_skills:
            return []

        # 1. 检查互斥技能
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)
            if priority and priority.exclusive:
                # 只保留这个互斥技能
                return [skill]

        # 2. 检查冲突对
        result = []
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)

            if priority:
                # 检查是否与已选技能冲突
                has_conflict = any(
                    s.name in priority.conflicts_with
                    for s in result
                )
                if has_conflict:
                    continue

            result.append(skill)

        # 3. 按优先级排序，保留前 N 个
        result.sort(
            key=lambda s: self.priorities.get(s.name, SkillPriority(s.name)).priority,
            reverse=True
        )

        # 最多激活 2 个技能
        return result[:2]

    def merge_prompts(
        self,
        system_prompt: str,
        skills: List[Skill]
    ) -> str:
        """融合多个技能的提示"""
        if not skills:
            return system_prompt

        if len(skills) == 1:
            return f"{system_prompt}\n\n# Active Skill: {skills[0].name}\n\n{skills[0].content}"

        # 多个技能时，按优先级组织
        skill_sections = []
        for i, skill in enumerate(skills, 1):
            skill_sections.append(f"## Skill {i}: {skill.name}\n\n{skill.content}")

        return f"{system_prompt}\n\n# Active Skills\n\n" + "\n\n".join(skill_sections)


# 使用示例
resolver = SkillConflictResolver(registry)

# 设置优先级
resolver.set_priority(SkillPriority(
    skill_name="code-review",
    priority=10,
    exclusive=False,
    conflicts_with=["debug"]  # code-review 和 debug 不兼容
))

resolver.set_priority(SkillPriority(
    skill_name="think",
    priority=100,
    exclusive=True  # think 激活时禁用其他技能
))

# 解决冲突
matched = registry.find_matching_skills("review and debug this code")
final_skills = resolver.resolve(matched, user_input)
```

**权衡**:
- ✅ 解决指令冲突
- ✅ 可配置优先级
- ⚠️ 需要用户配置（或学习）
- ⚠️ 可能遗漏一些技能

---

### ADR-007: 向量检索可选化

**问题**: 向量检索增加复杂度和成本，不一定必要。

**决策**: 向量检索作为可选插件，默认关闭。

```python
@dataclass
class MemoryConfig:
    """记忆配置"""
    storage_type: str = "file"

    # 向量检索（可选）
    enable_vector_search: bool = False  # 默认关闭
    embedding_model: str = "text-embedding-3-small"
    vector_db: str = "chroma"

    # 简单检索（默认）
    enable_keyword_search: bool = True  # 默认开启
```

**启用条件**:
- 会话数 > 1000
- 需要跨会话检索
- 有专门的向量数据库

---

## MVP 范围定义

基于上述分析，MVP 范围如下：

### ✅ MVP 必须有

| 功能 | 说明 |
|------|------|
| Agent Loop | 核心循环 + 并行工具 + 重试 |
| Tool System | 内置工具 + 权限控制 |
| Memory (基础) | File/SQLite 存储 + 滑动窗口 |
| Skills (基础) | 加载 + 激活 + 注入（无冲突解决） |
| 成本控制 | 会话级 Token 限制 |

### ⚠️ MVP 简化版

| 功能 | 简化方案 |
|------|----------|
| 上下文压缩 | 启发式摘要（不用 LLM） |
| 技能激活 | 最多 1 个（无冲突处理） |
| 触发器 | 只支持 Cron |

### ❌ MVP 不做

| 功能 | 延后原因 |
|------|----------|
| 向量检索 | 复杂度高，非核心 |
| 自动学习技能 | 实验性功能 |
| 多代理编排 | 需要先验证单代理 |
| 真正的沙箱 | 依赖外部工具（Docker） |

---

## 性能基准

### 目标指标

| 指标 | MVP 目标 | 生产目标 |
|------|----------|----------|
| 单次请求延迟 | < 5s | < 2s |
| 并发会话数 | 10 | 1000 |
| 会话最大消息数 | 100 | 10000 |
| 内存占用（空闲） | < 100MB | < 50MB |
| 内存占用（运行） | < 500MB | < 200MB |

### 测试场景

1. **短会话测试**: 10 条消息，验证基础流程
2. **长会话测试**: 1000 条消息，验证扩展性
3. **并发测试**: 100 并发请求，验证资源隔离
4. **成本测试**: 1000 次请求，验证成本追踪

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 长会话 OOM | 高 | 高 | 分片存储 + 滑动窗口 |
| 成本超支 | 中 | 高 | 多级预算控制 + 自动降级 |
| Skill 冲突 | 中 | 中 | 优先级 + 互斥机制 |
| 向量检索慢 | 低 | 低 | 默认关闭，按需启用 |

---

## 内嵌 SDK 特有风险（架构评审反馈）

### ADR-008: 多进程/分布式环境状态管理

**问题**: 内嵌 SDK 在多进程环境（Gunicorn 多 Worker、K8s 多副本）下的状态灾难：
- SQLite 多进程并发写入导致 `database is locked`
- Trigger 在每个 Worker 进程中独立启动，导致重复触发
- Session 内存缓存不同步，Webhook 请求可能打到错误的 Worker

**决策**: 引入分布式状态后端 + 分布式锁 + 明确部署约束。

```python
from dataclasses import dataclass
from enum import Enum

class DeploymentMode(Enum):
    SINGLETON = "singleton"      # 单进程，使用 File/SQLite
    DISTRIBUTED = "distributed"  # 多进程，必须使用 Redis/PostgreSQL

@dataclass
class DistributedConfig:
    """分布式配置"""
    mode: DeploymentMode = DeploymentMode.SINGLETON
    
    # 分布式存储（当 mode=DISTRIBUTED 时必需）
    storage_backend: str = "redis"  # redis, postgresql
    storage_url: str = ""
    
    # 分布式锁
    lock_backend: str = "redis"
    lock_ttl_seconds: int = 30
    
    # Trigger 配置
    trigger_leader_election: bool = True  # 启用 Leader 选举，只有 Leader 执行 Trigger


class DistributedTriggerManager:
    """分布式触发器管理器"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        self._lock = None
        self._is_leader = False
        
    async def acquire_leader_lock(self) -> bool:
        """获取 Leader 锁（只有 Leader 执行 Trigger）"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True
            
        # 使用 Redis Redlock
        import redis.asyncio as redis
        client = redis.from_url(self.config.storage_url)
        
        self._lock = client.lock(
            "harness:trigger:leader",
            timeout=self.config.lock_ttl_seconds,
            blocking=False
        )
        
        try:
            self._is_leader = await self._lock.acquire()
            return self._is_leader
        except Exception:
            return False
    
    async def should_execute_trigger(self) -> bool:
        """判断当前实例是否应该执行 Trigger"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True
        return self._is_leader
```

**部署约束文档**:
```
## 部署模式

### 单进程模式（默认）
- 适用于：CLI 工具、脚本、单 Worker 应用
- 存储：File / SQLite
- Trigger：直接在进程内运行

### 多进程模式
- 适用于：FastAPI + Gunicorn、K8s 多副本
- 存储：必须使用 Redis / PostgreSQL
- Trigger：必须启用 Leader 选举，或独立部署 Trigger Worker

### 推荐架构
┌─────────────────────────────────────────────────────┐
│                    K8s Cluster                       │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ API Server  │  │ API Server  │  │ API Server  │ │
│  │ (Worker)    │  │ (Worker)    │  │ (Worker)    │ │
│  │ - 无 Trigger│  │ - 无 Trigger│  │ - 无 Trigger│ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │           Trigger Worker (单副本)            │   │
│  │           - Leader Election                  │   │
│  │           - 执行所有 Cron/Webhook            │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │                  Redis                        │   │
│  │           - Session Store                     │   │
│  │           - Distributed Lock                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**权衡**:
- ✅ 支持生产级部署
- ✅ 避免 Trigger 重复执行
- ⚠️ 增加运维复杂度（需要 Redis）
- ⚠️ 需要额外的 Trigger Worker 部署

---

### ADR-009: MCP 子进程生命周期管理

**问题**: `StdioTransport` 启动的 MCP 子进程在宿主崩溃时变成孤儿/僵尸进程。

**决策**: 实现严格的进程生命周期管理 + 健康检查。

```python
import os
import signal
import atexit
from contextlib import asynccontextmanager
from typing import Optional
import asyncio

class MCPProcessManager:
    """MCP 进程管理器"""
    
    def __init__(self):
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}
        self._setup_cleanup_hooks()
    
    def _setup_cleanup_hooks(self):
        """设置清理钩子"""
        # 正常退出时清理
        atexit.register(self._cleanup_all_sync)
        
        # SIGTERM/SIGINT 时清理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self._cleanup_all_sync()
        sys.exit(0)
    
    def _cleanup_all_sync(self):
        """同步清理所有进程"""
        for name, process in self._processes.items():
            try:
                if process.returncode is None:
                    # 发送 SIGTERM 给整个进程组
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
    
    async def start_process(
        self,
        name: str,
        command: str,
        args: list,
        env: dict
    ) -> asyncio.subprocess.Process:
        """启动进程（创建新进程组）"""
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **env},
            # 创建新进程组，便于批量终止
            start_new_session=True
        )
        
        self._processes[name] = process
        
        # 启动健康检查
        self._health_tasks[name] = asyncio.create_task(
            self._health_check(name, process)
        )
        
        return process
    
    async def _health_check(self, name: str, process: asyncio.subprocess.Process):
        """健康检查任务"""
        while process.returncode is None:
            try:
                # 每 30 秒检查一次
                await asyncio.sleep(30)
                
                # 可以发送 ping 消息检查 MCP 进程健康
                # ...
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 进程异常，尝试重启
                await self._restart_process(name)
                break
    
    async def stop_process(self, name: str):
        """停止指定进程"""
        if name in self._processes:
            process = self._processes[name]
            
            # 取消健康检查
            if name in self._health_tasks:
                self._health_tasks[name].cancel()
            
            # 优雅终止
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            finally:
                del self._processes[name]


@asynccontextmanager
async def mcp_session(name: str, command: str, args: list, env: dict):
    """MCP 会话上下文管理器"""
    manager = MCPProcessManager()
    process = await manager.start_process(name, command, args, env)
    
    try:
        yield process
    finally:
        await manager.stop_process(name)


# 使用示例
async def main():
    async with mcp_session(
        "filesystem",
        "mcp-server-filesystem",
        ["/workspace"],
        {}
    ) as process:
        # 使用 MCP 客户端通信
        pass
    # 退出时自动清理
```

**权衡**:
- ✅ 防止孤儿/僵尸进程
- ✅ 支持优雅关闭和自动重启
- ⚠️ 增加代码复杂度
- ⚠️ Windows 平台信号支持有限

---

### ADR-010: 沙箱执行的轻量化方案

**问题**: Docker 沙箱每次执行延迟高达数秒，且需要 Docker 权限，不适合高频工具调用。

**决策**: MVP 放弃 Docker，采用轻量级隔离 + 严格白名单。

```python
from dataclasses import dataclass
from typing import List, Set
import subprocess
import shutil

@dataclass
class LightweightSandboxConfig:
    """轻量级沙箱配置"""
    # 白名单命令
    allowed_commands: Set[str] = None
    
    # 禁止的命令模式
    blocked_patterns: List[str] = None
    
    # 资源限制
    max_execution_time: float = 30.0
    max_output_size: int = 1_000_000  # 1MB
    
    # 环境隔离
    allowed_env_vars: Set[str] = None
    blocked_env_vars: Set[str] = None

class LightweightSandbox:
    """轻量级沙箱执行器"""
    
    DEFAULT_BLOCKED_PATTERNS = [
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "mkfs",
        "dd if=",
        "> /dev/",
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  # Fork bomb
    ]
    
    def __init__(self, config: LightweightSandboxConfig = None):
        self.config = config or LightweightSandboxConfig()
        self.config.blocked_patterns = (
            self.config.blocked_patterns or self.DEFAULT_BLOCKED_PATTERNS
        )
    
    def validate_command(self, command: str) -> tuple[bool, str]:
        """验证命令安全性"""
        # 1. 检查黑名单
        for pattern in self.config.blocked_patterns:
            if pattern in command:
                return False, f"Blocked pattern: {pattern}"
        
        # 2. 白名单检查（如果配置了）
        if self.config.allowed_commands:
            cmd_base = command.split()[0] if command.split() else ""
            if shutil.which(cmd_base) not in self.config.allowed_commands:
                return False, f"Command not in whitelist: {cmd_base}"
        
        # 3. 危险路径检查
        dangerous_paths = ["/etc", "/root", "/home", "~/.ssh", "~/.aws"]
        for path in dangerous_paths:
            if path in command:
                return False, f"Dangerous path: {path}"
        
        return True, ""
    
    async def execute(
        self,
        command: str,
        cwd: str = None,
        env: dict = None,
        timeout: float = None
    ) -> "SandboxResult":
        """在沙箱中执行命令"""
        
        # 验证命令
        valid, reason = self.validate_command(command)
        if not valid:
            return SandboxResult(success=False, error=reason)
        
        # 构建隔离环境
        clean_env = self._build_clean_env(env)
        
        # 执行（使用 setrlimit 限制资源）
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=clean_env,
                # 资源限制
                preexec_fn=self._set_resource_limits
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.config.max_execution_time
            )
            
            # 输出大小限制
            stdout = stdout[:self.config.max_output_size]
            
            return SandboxResult(
                success=process.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=process.returncode
            )
            
        except asyncio.TimeoutError:
            process.kill()
            return SandboxResult(success=False, error="Timeout")
    
    def _build_clean_env(self, extra_env: dict = None) -> dict:
        """构建干净的环境变量"""
        # 只保留安全的环境变量
        safe_vars = {"PATH", "HOME", "USER", "LANG", "LC_ALL"}
        if self.config.allowed_env_vars:
            safe_vars.update(self.config.allowed_env_vars)
        
        env = {k: v for k, v in os.environ.items() if k in safe_vars}
        
        # 移除敏感变量
        sensitive = {
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN", "DATABASE_URL"
        }
        for var in sensitive:
            env.pop(var, None)
        
        if extra_env:
            env.update(extra_env)
        
        return env
    
    @staticmethod
    def _set_resource_limits():
        """设置进程资源限制"""
        import resource
        
        # 限制 CPU 时间（秒）
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        
        # 限制内存（字节）- 512MB
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        
        # 限制进程数
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
        
        # 禁止创建新文件
        # resource.setrlimit(resource.RLIMIT_NOFILE, (0, 0))
```

**权衡**:
- ✅ 毫秒级执行延迟
- ✅ 无需 Docker 权限
- ✅ 适用于云原生环境
- ⚠️ 隔离强度低于容器
- ⚠️ Windows 平台 `setrlimit` 不可用

---

### ADR-011: Skill 自学习的人机协作机制

**问题**: 自动生成的 Skill 质量不可控，可能污染 System Prompt 或引入安全漏洞。

**决策**: 自学习 Skill 必须进入 Draft 状态，经过人工审核后才能激活。

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime

class SkillStatus(Enum):
    DRAFT = "draft"        # 草稿，等待审核
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 已批准，可激活
    REJECTED = "rejected"  # 已拒绝

@dataclass
class DraftSkill:
    """草稿技能"""
    skill: Skill
    status: SkillStatus = SkillStatus.DRAFT
    created_at: datetime = None
    reviewed_at: datetime = None
    reviewed_by: str = ""
    rejection_reason: str = ""

class SkillReviewManager:
    """技能审核管理器"""
    
    def __init__(
        self,
        draft_dir: str = "~/.harness/skills/drafts",
        approved_dir: str = "~/.harness/skills/approved"
    ):
        self.draft_dir = Path(draft_dir).expanduser()
        self.approved_dir = Path(approved_dir).expanduser()
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
    
    async def submit_for_review(self, skill: Skill) -> str:
        """提交技能审核"""
        draft_id = f"draft_{skill.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存到草稿目录
        draft_path = self.draft_dir / f"{draft_id}.md"
        skill.to_file(draft_path)
        
        # 记录元数据
        meta = {
            "status": SkillStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "skill_name": skill.name
        }
        self._save_meta(draft_path, meta)
        
        return draft_id
    
    def list_pending(self) -> List[DraftSkill]:
        """列出待审核的技能"""
        pending = []
        for draft_file in self.draft_dir.glob("*.md"):
            meta = self._load_meta(draft_file)
            if meta.get("status") == SkillStatus.PENDING.value:
                skill = Skill.from_file(draft_file)
                pending.append(DraftSkill(
                    skill=skill,
                    status=SkillStatus.PENDING,
                    created_at=datetime.fromisoformat(meta.get("created_at"))
                ))
        return pending
    
    async def approve(self, draft_id: str, reviewer: str = "user") -> bool:
        """批准技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False
        
        # 移动到批准目录
        skill = Skill.from_file(draft_path)
        approved_path = self.approved_dir / f"{skill.name}.md"
        skill.to_file(approved_path)
        
        # 更新元数据
        meta = self._load_meta(draft_path)
        meta["status"] = SkillStatus.APPROVED.value
        meta["reviewed_at"] = datetime.now().isoformat()
        meta["reviewed_by"] = reviewer
        self._save_meta(draft_path, meta)
        
        # 删除草稿（或归档）
        draft_path.unlink()
        
        return True
    
    async def reject(self, draft_id: str, reason: str) -> bool:
        """拒绝技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False
        
        meta = self._load_meta(draft_path)
        meta["status"] = SkillStatus.REJECTED.value
        meta["reviewed_at"] = datetime.now().isoformat()
        meta["rejection_reason"] = reason
        self._save_meta(draft_path, meta)
        
        return True


# CLI 命令
# harness skill review --list          # 列出待审核
# harness skill approve <draft_id>      # 批准
# harness skill reject <draft_id> -r "不安全"  # 拒绝
```

**权衡**:
- ✅ 防止低质量 Skill 污染
- ✅ Human-in-the-loop 安全保障
- ⚠️ 增加维护成本
- ⚠️ 需要开发者主动参与审核

---

### ADR-012: 成本控制的熔断机制

**问题**: LLM 可能陷入死循环，消耗完预算后才停止。

**决策**: 增加熔断机制，检测异常模式并强制中断。

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
    # 相同工具调用次数阈值
    same_tool_threshold: int = 5
    
    # 时间窗口（秒）
    time_window: float = 60.0
    
    # 相似参数阈值（0-1）
    similarity_threshold: float = 0.8
    
    # 错误重试阈值
    error_threshold: int = 3
    
    # 冷却时间（秒）
    cooldown_seconds: float = 300.0

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
        
        # 检查是否应该熔断
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
        
        # 获取时间窗口内的调用
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
        """计算参数哈希（用于相似性检测）"""
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

**权衡**:
- ✅ 防止无限循环消耗预算
- ✅ 自动检测异常模式
- ⚠️ 可能误杀正常的长任务
- ⚠️ 需要调优阈值参数

---

## MVP 范围调整（基于架构评审）

### ✂️ MVP 延后/移除的功能

| 功能 | 原计划 | 调整 | 原因 |
|------|--------|------|------|
| 多代理编排 | Phase 3 | v2.0 | 掩盖底层 Bug，需先验证单代理 |
| Skill 自学习 | Phase 2 | 独立插件 `harness-ml` | 不可控行为，实验性功能 |
| Webhook Trigger | MVP | Phase 2 | 应由宿主应用处理，SDK 不绑定路由 |
| FileWatch Trigger | Phase 2 | Phase 3 | 非核心，复杂度高 |

### 🚀 MVP 必须强化的功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 流式输出背压处理 | P0 | 定义 AsyncGenerator 缓冲行为 |
| 中断与恢复 | P0 | 长任务优雅中断 + 状态持久化 |
| Mock 测试工具链 | P0 | pytest 插件，`@pytest.mark.harness_mock` |
| OpenTelemetry 集成 | P1 | 替代自研 LoopTracer |
| 增量 Token 计数 | P1 | 缓存历史 Token，避免重复计算 |

### 调整后的 MVP 范围

| 功能 | 说明 | 状态 |
|------|------|------|
| Agent Loop | 核心循环 + 并行工具 + 重试 + 熔断 | ✅ 必须 |
| Tool System | 内置工具 + 权限控制 + 轻量沙箱 | ✅ 必须 |
| Memory (基础) | File/SQLite + 滑动窗口 | ✅ 必须 |
| Skills (基础) | 加载 + 激活 + 注入（无自学习） | ✅ 必须 |
| 成本控制 | 会话级限制 + 熔断机制 | ✅ 必须 |
| Cron Trigger | 仅 Cron，单进程模式 | ✅ 必须 |
| Mock 测试 | pytest 集成 | ✅ 必须 |
| OpenTelemetry | Span 导出 | ⚠️ 推荐 |

---

