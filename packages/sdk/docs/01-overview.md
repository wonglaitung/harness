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

### Agent Harness 定义

**Agent Harness（智能体框架）** 是包裹在 LLM 外层的完整软件基础设施，用于管理长时间运行的任务。它不是 Agent 本身，而是控制 Agent 如何运行的软件系统。

#### 核心类比

| 组件 | 类比 | 职责 |
|------|------|------|
| **模型 (Model)** | CPU | 提供原始处理能力 |
| **上下文窗口 (Context Window)** | RAM | 有限的易失性工作内存 |
| **Agent Harness** | 操作系统 | 管理上下文、处理启动序列、提供标准驱动 |
| **Agent** | 应用程序 | 运行在 OS 之上的具体业务逻辑 |

### 为什么 Harness 重要？

#### 70% 的性能来自 Harness

研究表明，AI Agent 约 70% 的性能表现来自 Harness 而非模型本身。斯坦福 IRIS Lab 的实验显示：使用自动化 Harness 演化系统 (Meta-Harness) 配合 Claude Opus 4.6，在 SWE-Bench 上达到 76.4%，超越了所有手工设计的系统。

#### 基准测试问题

传统单轮对话基准测试无法衡量模型在长时间任务中的可靠性：

- **静态基准局限**: 模型在静态排行榜上的差距正在缩小
- **耐久性缺失**: 1% 的基准差距无法检测模型在 50 步后是否偏离指令
- **真实需求**: 生产环境需要执行数百次工具调用的可靠性

#### Harness 的核心价值

| 价值点 | 说明 |
|--------|------|
| **验证真实进展** | 基准与用户需求错位，Harness 允许在实际场景中测试 |
| **提升用户体验** | 没有Harness，用户体验可能落后于模型潜力 |
| **支持持续优化** | 稳定的环境创造反馈循环，支持"爬山"式改进 |

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

## Production Harness 组件实现状态

基于行业最佳实践（LangChain、Anthropic、Stanford IRIS Lab），一个生产级 Harness 需要 11 个核心组件。

### 实现状态总览

| 组件 | 状态 | 说明 |
|------|------|------|
| Orchestration Loop | ✅ | ReAct 循环、中断恢复、熔断器 |
| Tools | ✅ | 文件操作、搜索、Bash、Web、MCP |
| Filesystem | ✅ | 通过工具实现，支持权限检查 |
| Bash & Code Execution | ✅ | 沙箱执行、命令黑名单、超时控制 |
| Sandbox | ✅ | LightweightSandbox + SandboxExecutor |
| Memory | ⚠️ | 缺向量检索、MEMORY.md 标准 |
| Context Management | ✅ | ContextBuilder 处理组装 |
| Context Rot Defense | ⚠️ | 缺工具输出卸载、渐进加载 |
| Long-Horizon Execution | ⚠️ | 缺 Lifecycle Hooks、Ralph Loop、自验证钩子、Sub-Agent |
| Error Handling | ✅ | 熔断器、成本控制、卡住检测 |
| Serving Layer | ❌ | SDK 不包含（client 层职责） |

详细实现状态见 [10-comparison.md](./10-comparison.md#production-harness-组件对比)。

### 完全缺失的关键功能

| # | 功能 | 描述 | 影响 | 优先级 |
|---|------|------|------|--------|
| 1 | **Lifecycle Hooks** | 工具执行前后的钩子系统 | 企业定制基础 | P0 |
| 2 | **Ralph Loop** | 拦截提前退出，重置上下文继续长任务 | 长任务保障 | P1 |
| 3 | **工具输出卸载** | 大输出保存到文件，只注入引用 | 上下文预算优化 | P3 |
| 4 | **渐进式技能加载** | 三级加载：Frontmatter → Full → Reference | 上下文效率 | P2 |
| 5 | **自验证钩子** | write-code → run-tests → fix-errors 循环 | 代码质量保障 | P2 |
| 6 | **Sub-Agent 管理** | 创建子代理处理子任务 | 大任务分解 | P1 |
| 7 | **MEMORY.md 标准** | 读写项目根目录的持久记忆文件 | 跨会话记忆 | P2 |
| 8 | **向量检索** | 语义搜索历史对话、技能、文档 | 智能检索 | P2 |
| 9 | **动态系统提示组装** | 根据项目上下文动态调整系统提示 | 项目级约定 | P0 |
| 10 | **步骤预算** | 软限制总步骤数，提前警告 | 成本预警 | P3 |

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
- [The importance of Agent Harness in 2026 - Philschmid](https://www.philschmid.de/agent-harness-2026)
- [The Agent Harness: Why 70% of Performance Lives Outside the Model](https://medium.com/@tentenco/the-agent-harness-why-70-of-your-ai-agents-performance-lives-outside-the-model-5093cfe03df1)
- [OpenClaw Documentation](https://docs.openclaw.ai)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [OpenHarness](https://github.com/HKUDS/OpenHarness)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/tool-use)
- [The Bitter Lesson - Rich Sutton](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
