# 13 - Orchestrator 工作流编排

> **状态**: ✅ 已实现
> **设计文档**: [phase5-orchestrator.md](../design/phase5-orchestrator.md)

## 概述

Orchestrator 模块提供**统一的工作流编排 API**，整合 Phase 1-4 的所有组件。

**核心特性**：
- 工作流定义 - 声明式多步骤任务
- 依赖解析 - 自动处理步骤依赖
- 多 Agent 协调 - 支持团队协作模式
- 统一监控 - 执行追踪和指标

## 核心 API

### LoopOrchestrator

```python
from harness import AgentHarness
from harness.orchestrator import (
    LoopOrchestrator,
    WorkflowConfig,
    WorkflowStep,
    TeamConfig,
    AgentRole,
    CoordinationMode,
)

agent = AgentHarness(model="claude-sonnet-4-6")
orchestrator = LoopOrchestrator(agent)

# 创建工作流
workflow = WorkflowConfig(
    name="code-review",
    steps=[
        WorkflowStep(name="analyze", goal="分析代码结构"),
        WorkflowStep(name="lint", goal="运行 lint 检查"),
        WorkflowStep(name="review", goal="代码审查", depends_on=["analyze", "lint"]),
        WorkflowStep(name="report", goal="生成审查报告", depends_on=["review"]),
    ],
)
orchestrator.create_workflow(workflow)

# 执行工作流
result = await orchestrator.run_workflow("code-review")
```

## 工作流配置

### WorkflowStep

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | 必填 | 步骤名称 |
| `goal` | str | 必填 | 目标描述（支持模板变量） |
| `depends_on` | list[str] | [] | 依赖的步骤 |
| `mode` | ExecutionMode | SEQUENTIAL | 执行模式 |
| `condition` | str | None | 条件表达式 |
| `workspace_dir` | str | "." | 工作目录 |
| `max_iterations` | int | 50 | 最大迭代次数 |
| `timeout_seconds` | int | 3600 | 超时时间 |
| `skills` | list[str] | [] | 激活的技能 |
| `exports` | dict[str, str] | {} | 导出的数据 |

### WorkflowConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | 必填 | 工作流名称 |
| `description` | str | "" | 描述 |
| `steps` | list[WorkflowStep] | [] | 步骤列表 |
| `default_mode` | ExecutionMode | SEQUENTIAL | 默认执行模式 |
| `max_parallel_steps` | int | 5 | 最大并行步骤数 |

### WorkflowResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `workflow_name` | str | 工作流名称 |
| `status` | WorkflowStatus | 执行状态 |
| `steps` | dict[str, StepResult] | 各步骤结果 |
| `started_at` | datetime | 开始时间 |
| `completed_at` | datetime | 完成时间 |
| `error` | str | 错误信息 |

## 工作流示例

### 顺序执行

```python
workflow = WorkflowConfig(
    name="deploy",
    steps=[
        WorkflowStep(name="test", goal="运行所有测试"),
        WorkflowStep(name="build", goal="构建应用", depends_on=["test"]),
        WorkflowStep(name="deploy", goal="部署到生产环境", depends_on=["build"]),
    ],
)

result = await orchestrator.run_workflow("deploy")
# test → build → deploy（顺序执行）
```

### 并行执行

```python
workflow = WorkflowConfig(
    name="parallel-analysis",
    steps=[
        WorkflowStep(name="security", goal="安全扫描"),
        WorkflowStep(name="performance", goal="性能分析"),
        WorkflowStep(name="coverage", goal="覆盖率检查"),
        WorkflowStep(name="report", goal="生成报告", depends_on=["security", "performance", "coverage"]),
    ],
    default_mode=ExecutionMode.PARALLEL,
)

result = await orchestrator.run_workflow("parallel-analysis")
# security, performance, coverage 并行执行
# 全部完成后执行 report
```

### 条件执行

```python
workflow = WorkflowConfig(
    name="conditional-deploy",
    steps=[
        WorkflowStep(name="check", goal="检查代码质量"),
        WorkflowStep(
            name="deploy",
            goal="部署到生产环境",
            depends_on=["check"],
            condition="steps['check'].status == StepStatus.SUCCESS",
        ),
    ],
)
```

### 模板变量

```python
workflow = WorkflowConfig(
    name="template-example",
    steps=[
        WorkflowStep(
            name="analyze",
            goal="分析代码并生成报告",
            exports={"report_path": "$.artifacts.report_file"},
        ),
        WorkflowStep(
            name="notify",
            goal="发送报告到 Slack: {{steps.analyze.exports.report_path}}",
            depends_on=["analyze"],
        ),
    ],
)
```

## 多 Agent 协调

### TeamConfig

```python
team = TeamConfig(
    name="dev-team",
    description="开发团队",
    roles=[
        AgentRole(
            name="analyzer",
            description="代码分析专家",
            skills=["code-analysis"],
            max_iterations=10,
        ),
        AgentRole(
            name="developer",
            description="开发工程师",
            skills=["coding", "testing"],
            max_iterations=20,
        ),
        AgentRole(
            name="reviewer",
            description="代码审查员",
            skills=["code-review"],
            max_iterations=5,
        ),
    ],
    coordination_mode=CoordinationMode.SEQUENTIAL,
)
```

### 协调模式

| 模式 | 说明 |
|------|------|
| `SEQUENTIAL` | 顺序执行，每个 Agent 完成后传递给下一个 |
| `BROADCAST` | 广播模式，所有 Agent 同时执行相同任务 |
| `HIERARCHICAL` | 层级模式，协调者分配任务给团队成员 |

### 团队执行示例

```python
# 创建团队
orchestrator.create_team(team)

# 执行团队任务
result = await orchestrator.run_team("dev-team", "实现用户登录功能")

# 查看各 Agent 结果
for role_name, agent_result in result.agent_results.items():
    print(f"{role_name}: {agent_result.status.value}")
```

## 执行状态

### WorkflowStatus

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待执行 |
| `RUNNING` | 执行中 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

### StepStatus

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待执行 |
| `RUNNING` | 执行中 |
| `SUCCESS` | 成功 |
| `FAILED` | 失败 |
| `SKIPPED` | 跳过 |

## 监控

```python
# 获取执行指标
metrics = orchestrator.get_metrics("code-review")
print(f"Total steps: {metrics.total_steps}")
print(f"Completed: {metrics.completed_steps}")
print(f"Failed: {metrics.failed_steps}")
print(f"Duration: {metrics.duration_seconds}s")

# 获取执行日志
logs = orchestrator.get_execution_log("code-review")
for log in logs:
    print(f"[{log.timestamp}] {log.step_name}: {log.event}")
```

## 完整示例

### CI/CD 工作流

```python
import asyncio
from harness import AgentHarness
from harness.orchestrator import (
    LoopOrchestrator,
    WorkflowConfig,
    WorkflowStep,
)

async def main():
    agent = AgentHarness(model="claude-sonnet-4-6")
    orchestrator = LoopOrchestrator(agent)

    # 定义 CI/CD 工作流
    workflow = WorkflowConfig(
        name="cicd",
        description="持续集成和部署流程",
        steps=[
            # 并行检查
            WorkflowStep(name="lint", goal="运行 ruff check 检查代码风格"),
            WorkflowStep(name="typecheck", goal="运行 mypy 类型检查"),
            WorkflowStep(name="test", goal="运行 pytest 测试"),

            # 分析（等待检查完成）
            WorkflowStep(
                name="analyze",
                goal="分析代码质量并生成报告",
                depends_on=["lint", "typecheck", "test"],
            ),

            # 决策
            WorkflowStep(
                name="decision",
                goal="根据分析结果决定是否可以部署",
                depends_on=["analyze"],
                condition="steps['test'].status == StepStatus.SUCCESS",
            ),

            # 部署
            WorkflowStep(
                name="deploy",
                goal="部署到 staging 环境",
                depends_on=["decision"],
            ),

            # 通知
            WorkflowStep(
                name="notify",
                goal="发送部署通知到 Slack",
                depends_on=["deploy"],
            ),
        ],
        max_parallel_steps=3,
    )

    orchestrator.create_workflow(workflow)

    # 执行
    result = await orchestrator.run_workflow("cicd")

    print(f"工作流状态: {result.status.value}")
    print(f"总耗时: {result.duration_seconds:.1f}s")

    # 打印各步骤结果
    for step_name, step_result in result.steps.items():
        status = "✅" if step_result.status.value == "success" else "❌"
        print(f"  {status} {step_name}")

asyncio.run(main())
```

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     LoopOrchestrator                         │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ WorkflowEngine  │  │TeamOrchestrator │                   │
│  │ (工作流执行)     │  │ (多Agent协调)    │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           └──────────┬─────────┘                             │
│                      │                                       │
│              ┌───────┴───────┐                               │
│              │ MonitorService │                               │
│              │ (监控和指标)    │                               │
│              └───────────────┘                               │
└─────────────────────────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    Phase 2:      Phase 3:      Phase 4:
    Triggers      Worktrees     Connectors
```

## 下一步

- [10-loop-engineering.md](./18-loop-engineering.md) - Loop Engineering 总览
- [11-worktrees.md](./19-worktrees.md) - 并行隔离执行
- [12-connectors.md](./20-connectors.md) - 外部系统集成
