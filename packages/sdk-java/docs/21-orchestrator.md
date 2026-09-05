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

```java
import com.harness.loop.GoalLoop;
import com.harness.orchestrator.WorkflowEngine;
import com.harness.orchestrator.WorkflowConfig;
import com.harness.orchestrator.WorkflowStep;
import com.harness.orchestrator.TeamConfig;
import com.harness.orchestrator.AgentRole;
import com.harness.orchestrator.CoordinationMode;
import com.harness.orchestrator.WorkflowResult;

GoalLoop.AgentRunner agent = ...;
WorkflowEngine engine = new WorkflowEngine();

// 创建工作流
WorkflowConfig workflow = WorkflowConfig.builder()
    .name("code-review")
    .addStep(WorkflowStep.builder()
        .name("analyze")
        .goal("分析代码结构")
        .build())
    .addStep(WorkflowStep.builder()
        .name("lint")
        .goal("运行 lint 检查")
        .build())
    .addStep(WorkflowStep.builder()
        .name("review")
        .goal("代码审查")
        .addDependsOn("analyze")
        .addDependsOn("lint")
        .build())
    .addStep(WorkflowStep.builder()
        .name("report")
        .goal("生成审查报告")
        .addDependsOn("review")
        .build())
    .build();

engine.registerWorkflow(workflow);

// 执行工作流
WorkflowResult result = engine.runWorkflow(workflow, agent).join();
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

```java
WorkflowConfig workflow = WorkflowConfig.builder()
    .name("deploy")
    .addStep(WorkflowStep.builder()
        .name("test")
        .goal("运行所有测试")
        .build())
    .addStep(WorkflowStep.builder()
        .name("build")
        .goal("构建应用")
        .addDependsOn("test")
        .build())
    .addStep(WorkflowStep.builder()
        .name("deploy")
        .goal("部署到生产环境")
        .addDependsOn("build")
        .build())
    .build();

WorkflowResult result = engine.runWorkflow(workflow, agent).join();
// test → build → deploy（顺序执行）
```

### 并行执行

```java
import com.harness.orchestrator.ExecutionMode;

WorkflowConfig workflow = WorkflowConfig.builder()
    .name("parallel-analysis")
    .addStep(WorkflowStep.builder()
        .name("security")
        .goal("安全扫描")
        .build())
    .addStep(WorkflowStep.builder()
        .name("performance")
        .goal("性能分析")
        .build())
    .addStep(WorkflowStep.builder()
        .name("coverage")
        .goal("覆盖率检查")
        .build())
    .addStep(WorkflowStep.builder()
        .name("report")
        .goal("生成报告")
        .addDependsOn("security")
        .addDependsOn("performance")
        .addDependsOn("coverage")
        .build())
    .defaultMode(ExecutionMode.PARALLEL)
    .build();

WorkflowResult result = engine.runWorkflow(workflow, agent).join();
// security, performance, coverage 并行执行
// 全部完成后执行 report
```

### 条件执行

```java
WorkflowConfig workflow = WorkflowConfig.builder()
    .name("conditional-deploy")
    .addStep(WorkflowStep.builder()
        .name("check")
        .goal("检查代码质量")
        .build())
    .addStep(WorkflowStep.builder()
        .name("deploy")
        .goal("部署到生产环境")
        .addDependsOn("check")
        .condition("steps['check'].status == StepStatus.SUCCESS")
        .build())
    .build();
```

### 模板变量

```java
WorkflowConfig workflow = WorkflowConfig.builder()
    .name("template-example")
    .addStep(WorkflowStep.builder()
        .name("analyze")
        .goal("分析代码并生成报告")
        .addExport("report_path", "$.artifacts.report_file")
        .build())
    .addStep(WorkflowStep.builder()
        .name("notify")
        .goal("发送报告到 Slack: {{steps.analyze.exports.report_path}}")
        .addDependsOn("analyze")
        .build())
    .build();
```

## 多 Agent 协调

### TeamConfig

```java
import com.harness.orchestrator.TeamConfig;
import com.harness.orchestrator.AgentRole;
import com.harness.orchestrator.CoordinationMode;

TeamConfig team = TeamConfig.builder()
    .name("dev-team")
    .description("开发团队")
    .addRole(AgentRole.builder()
        .name("analyzer")
        .description("代码分析专家")
        .addSkill("code-analysis")
        .maxIterations(10)
        .build())
    .addRole(AgentRole.builder()
        .name("developer")
        .description("开发工程师")
        .addSkill("coding")
        .addSkill("testing")
        .maxIterations(20)
        .build())
    .addRole(AgentRole.builder()
        .name("reviewer")
        .description("代码审查员")
        .addSkill("code-review")
        .maxIterations(5)
        .build())
    .coordinationMode(CoordinationMode.SEQUENTIAL)
    .build();
```

### 协调模式

| 模式 | 说明 |
|------|------|
| `SEQUENTIAL` | 顺序执行，每个 Agent 完成后传递给下一个 |
| `BROADCAST` | 广播模式，所有 Agent 同时执行相同任务 |
| `HIERARCHICAL` | 层级模式，协调者分配任务给团队成员 |

### 团队执行示例

```java
import com.harness.orchestrator.TeamResult;
import java.util.Map;

// 创建团队
TeamOrchestrator teamOrchestrator = new TeamOrchestrator();
teamOrchestrator.registerTeam(team);

// 执行团队任务
TeamResult result = teamOrchestrator.runTeam("dev-team", "实现用户登录功能", agent).join();

// 查看各 Agent 结果
for (Map.Entry<String, GoalResult> entry : result.getAgentResults().entrySet()) {
    System.out.println(entry.getKey() + ": " + entry.getValue().status().getValue());
}
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

```java
import com.harness.orchestrator.ExecutionMetric;
import com.harness.orchestrator.WorkflowEngine;
import java.util.List;

// 获取执行指标
ExecutionMetric metrics = engine.getMetrics("code-review");
System.out.println("Total steps: " + metrics.getTotalSteps());
System.out.println("Completed: " + metrics.getCompletedSteps());
System.out.println("Failed: " + metrics.getFailedSteps());
System.out.println("Duration: " + metrics.getDurationSeconds() + "s");

// 获取执行日志
List<ExecutionLog> logs = engine.getExecutionLog("code-review");
for (ExecutionLog log : logs) {
    System.out.println("[" + log.getTimestamp() + "] " +
        log.getStepName() + ": " + log.getEvent());
}
```

## 完整示例

### CI/CD 工作流

```java
import com.harness.loop.GoalLoop;
import com.harness.orchestrator.WorkflowEngine;
import com.harness.orchestrator.WorkflowConfig;
import com.harness.orchestrator.WorkflowStep;
import com.harness.orchestrator.WorkflowResult;
import com.harness.orchestrator.StepResult;
import com.harness.orchestrator.StepStatus;
import java.util.Map;

public class CicdExample {
    public static void main(String[] args) throws Exception {
        GoalLoop.AgentRunner agent = ...;
        WorkflowEngine engine = new WorkflowEngine();

        // 定义 CI/CD 工作流
        WorkflowConfig workflow = WorkflowConfig.builder()
            .name("cicd")
            .description("持续集成和部署流程")
            // 并行检查
            .addStep(WorkflowStep.builder()
                .name("lint")
                .goal("运行 ruff check 检查代码风格")
                .build())
            .addStep(WorkflowStep.builder()
                .name("typecheck")
                .goal("运行 mypy 类型检查")
                .build())
            .addStep(WorkflowStep.builder()
                .name("test")
                .goal("运行 pytest 测试")
                .build())
            // 分析（等待检查完成）
            .addStep(WorkflowStep.builder()
                .name("analyze")
                .goal("分析代码质量并生成报告")
                .addDependsOn("lint")
                .addDependsOn("typecheck")
                .addDependsOn("test")
                .build())
            // 决策
            .addStep(WorkflowStep.builder()
                .name("decision")
                .goal("根据分析结果决定是否可以部署")
                .addDependsOn("analyze")
                .condition("steps['test'].status == StepStatus.SUCCESS")
                .build())
            // 部署
            .addStep(WorkflowStep.builder()
                .name("deploy")
                .goal("部署到 staging 环境")
                .addDependsOn("decision")
                .build())
            // 通知
            .addStep(WorkflowStep.builder()
                .name("notify")
                .goal("发送部署通知到 Slack")
                .addDependsOn("deploy")
                .build())
            .maxParallelSteps(3)
            .build();

        engine.registerWorkflow(workflow);

        // 执行
        WorkflowResult result = engine.runWorkflow(workflow, agent).join();

        System.out.println("工作流状态: " + result.getStatus().getValue());
        System.out.printf("总耗时: %.1fs%n", result.getDurationSeconds());

        // 打印各步骤结果
        for (Map.Entry<String, StepResult> entry : result.getSteps().entrySet()) {
            String status = entry.getValue().getStatus() == StepStatus.SUCCESS ? "✓" : "✗";
            System.out.println("  " + status + " " + entry.getKey());
        }
    }
}
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
