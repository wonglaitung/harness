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
- [12-deployment.md](./12-deployment.md) - 内嵌部署指南
- [13-production-readiness.md](./13-production-readiness.md) - 生产就绪检查
- [14-spring-cloud-integration.md](./14-spring-cloud-integration.md) - Spring Cloud 集成指南

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
