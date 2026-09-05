# 10 - Loop Engineering 循环工程

> **状态**: ✅ 全部实现
> **创建时间**: 2026-06-28

## 概述

**Loop Engineering** 是 2026 年 6 月兴起的新范式：**不再逐轮手动提示 Agent，而是设计自动化循环系统驱动 Agent**。

**核心公式**：`Loop = Trigger + Context + Action + Verification + State + Stop rules`

### 实现状态

| Phase | 组件 | 状态 | 说明 |
|-------|------|------|------|
| Phase 1 | Goal Verifier | ✅ 已实现 | 目标驱动执行 |
| Phase 2 | Automations | ✅ 已实现 | 定时触发/调度 |
| Phase 3 | Worktrees | ✅ 已实现 | 多 Agent 并行隔离 |
| Phase 4 | Connectors | ✅ 已实现 | 外部系统集成 |
| Phase 5 | Loop Orchestrator | ✅ 已实现 | 多 Agent 协调 |

---

## Phase 1: Goal Verifier

### 概念

**目标驱动执行 (Goal-Driven Execution)**：用户描述目标，Agent 自主运行直到完成。

### 核心 API

```java
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.ToolVerificationConfig;

AgentHarness agent = new AgentHarness(llmClient, config);

// 基础用法
GoalResult result = agent.runGoal("修复所有类型错误").join();

// 检查结果
if (result.status() == GoalStatus.ACHIEVED) {
    System.out.println("目标达成，共 " + result.totalIterations() + " 轮迭代");
}
```

### GoalConfig 配置

```java
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.VerificationMethod;

GoalConfig config = GoalConfig.builder()
    .description("将测试覆盖率提升到 80%")
    .sessionId("my-session-123")
    .successCriteria("测试覆盖率报告显示 >= 80%")
    .workspaceDir(".")

    // 迭代控制
    .maxIterations(50)
    .maxContextResets(5)
    .timeoutSeconds(3600)

    // 验证配置
    .verificationMethod(VerificationMethod.LLM)

    // 成本控制
    .maxTokens(null)
    .maxCostUsd(null)
    .build();

GoalResult result = agent.runGoal(config, null).join();
```

### 会话连续性

默认情况下，每次调用 `run_goal()` 会创建新的会话。如果需要在多轮目标执行之间保持对话上下文，可以指定 `session_id`：

```java
// Java 示例
AgentHarness agent = new AgentHarness(llmClient, config);

// 第一轮目标执行
GoalResult result1 = agent.runGoal(
    "分析代码库结构",
    "my-project-session"  // 指定会话 ID
).join();

// 第二轮目标执行（会记住第一轮的上下文）
GoalResult result2 = agent.runGoal(
    "根据分析结果生成文档",
    "my-project-session"  // 使用相同的会话 ID
).join();
```

**适用场景**：
- 多阶段任务：前一个目标的执行结果需要传递给后续目标
- 上下文保持：在长时间任务中保持对话历史
- 任务续接：恢复中断的任务执行

**注意**：上下文重置（`max_context_resets`）会创建新的会话 ID 以防止 token 溢出，此时历史消息会被精简。

### 自定义验证器

```java
import java.util.concurrent.CompletableFuture;
import com.harness.loop.types.GoalResult;

AgentHarness agent = new AgentHarness(llmClient, config);

// 自定义验证函数
Function<GoalResult, Boolean> checkCoverage = result -> {
    try {
        Process process = new ProcessBuilder("pytest", "--cov", "--cov-report=term")
            .directory(new File("."))
            .start();
        String output = new String(process.getInputStream().readAllBytes());
        return output.contains("TOTAL") && output.contains("80%");
    } catch (Exception e) {
        return false;
    }
};

GoalResult result = agent.runGoal(
    "测试覆盖率达到 80%",
    null,  // sessionId
    null,  // onProgress
    checkCoverage
).join();

if (result.getStatus().isAchieved()) {
    System.out.println("目标达成!");
}
```

### 工具验证（Tool Verification）

工具验证提供客观、确定性的目标验证方式，通过运行测试、Lint、类型检查等命令来验证目标是否达成。

#### 基础用法

```java
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.ToolVerificationConfig;

AgentHarness agent = new AgentHarness(llmClient, config);

// Python 项目验证配置
ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
    .addCommand("pytest", "pytest", "tests/", "-v")
    .addCommand("mypy", "mypy", "src/")
    .addCommand("ruff", "ruff", "check", "src/")
    .build();

GoalConfig goalConfig = GoalConfig.builder()
    .description("修复所有类型错误")
    .verificationMethod(VerificationMethod.TOOL)
    .toolVerificationConfig(toolConfig)
    .build();

GoalResult result = agent.runGoal(goalConfig, null).join();

if (result.getStatus().isAchieved()) {
    System.out.println("所有验证通过!");
}
```

#### 预设配置

SDK 提供常用项目的预设验证配置：

```java
// Python 项目（pytest + mypy + ruff）
ToolVerificationConfig pythonConfig = ToolVerificationConfig.pythonDefaults();

// Python 项目（自定义路径）
ToolVerificationConfig pythonConfig = ToolVerificationConfig.pythonProject("tests/", "src/");

// Java/Gradle 项目
ToolVerificationConfig gradleConfig = ToolVerificationConfig.gradleDefaults();

// Java/Maven 项目
ToolVerificationConfig mavenConfig = ToolVerificationConfig.mavenDefaults();

// Node.js/npm 项目
ToolVerificationConfig npmConfig = ToolVerificationConfig.npmDefaults();
```

#### 自定义命令

```java
ToolVerificationConfig config = ToolVerificationConfig.builder()
    .addCommand("unit-tests", "pytest", "tests/unit/", "-v")
    .addCommand("integration-tests", "pytest", "tests/integration/", "-v")
    .addCommand("type-check", "mypy", "src/")
    .workingDirectory("./project")
    .timeoutSeconds(600)   // 10 分钟
    .failFast(true)        // 第一个失败就停止
    .build();
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `commands` | `List<VerificationCommand>` | 必填 | 验证命令列表 |
| `workingDirectory` | `String` | `"."` | 命令执行目录 |
| `timeoutSeconds` | `int` | `300` | 每个命令的超时时间 |
| `failFast` | `boolean` | `true` | 是否在第一个失败时停止 |
| `continueOnWarning` | `boolean` | `false` | 警告时是否继续 |

#### 验证方法对比

| 验证方法 | 说明 | 使用场景 |
|---------|------|---------|
| `LLM` | 让 LLM 判断目标是否达成 | 主观目标、文档生成、分析任务 |
| `CUSTOM` | 用户提供的验证函数 | 自定义逻辑、外部系统检查 |
| `TOOL` | 运行测试/Lint/类型检查 | 代码修复、测试覆盖率、重构验证 |

### GoalStatus 状态

```java
import com.harness.loop.types.GoalStatus;

public enum GoalStatus {
    ACHIEVED("achieved"),               // 目标达成
    TIMEOUT("timeout"),                 // 超时
    MAX_ITERATIONS("max_iterations"),   // 达到最大迭代
    MAX_RESETS("max_resets"),           // 达到最大重置次数
    ERROR("error"),                     // Agent 执行错误
    VERIFIER_FAULT("verifier_fault"),   // 验证器故障
    CANCELLED("cancelled");             // 用户取消

    private final String value;
    GoalStatus(String value) { this.value = value; }
    public String getValue() { return value; }
}
```

### GoalResult 结果

```java
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationRecord;
import java.util.List;
import java.util.Map;

public class GoalResult {
    private final String goal;                    // 目标描述
    private final GoalStatus status;              // 执行状态
    private final int totalIterations;            // 总迭代次数
    private final int contextResets;              // 上下文重置次数
    private final Map<String, Integer> totalTokens; // Token 使用量
    private final double durationSeconds;         // 执行时长
    private final String finalResponse;           // 最终响应
    private final List<VerificationRecord> verificationLog; // 验证日志
    private final String error;                   // 错误详情

    // Getters
    public String goal() { return goal; }
    public GoalStatus status() { return status; }
    public int totalIterations() { return totalIterations; }
    public int contextResets() { return contextResets; }
    public Map<String, Integer> totalTokens() { return totalTokens; }
    public double durationSeconds() { return durationSeconds; }
    public String finalResponse() { return finalResponse; }
    public List<VerificationRecord> verificationLog() { return verificationLog; }
    public String error() { return error; }
    public boolean achieved() { return status == GoalStatus.ACHIEVED; }
}
```

---

## 设计原则

### GoalVerifier 无状态性

`GoalVerifier` 是无状态的，所有上下文通过参数传递：

```java
// ✅ 正确：无状态验证
import com.harness.loop.types.VerificationResult;
import com.harness.types.LoopResult;
import java.util.Map;

public class MyVerifier {
    public VerificationResult verify(LoopResult result, Map<String, Object> context) {
        String workspace = (String) context.getOrDefault("workspace_dir", ".");
        // 通过 context 获取信息，不内部存储
        return new VerificationResult(/* achieved */, /* details */);
    }
}

// ❌ 错误：有状态验证
public class MyVerifier {
    private String workspace; // 不要存储状态

    public VerificationResult verify(LoopResult result) {
        // 使用内部状态而非参数
        return new VerificationResult(/* ... */);
    }
}
```

**原因**：
- 支持并发执行多个 Goal
- 验证器可被复用于不同 workspace
- 便于测试（无副作用）

### 异步设计

`GoalLoop` 可能运行数分钟甚至数小时，需避免阻塞事件循环：

```java
import com.harness.loop.types.GoalResult;
import java.util.concurrent.CompletableFuture;

public CompletableFuture<GoalResult> run() {
    while (true) {
        // ... 执行迭代 ...

        // 让出控制权，防止阻塞事件循环
        Thread.yield();
    }
}
```

### 验证器容错

为 `VERIFIER_FAULT` 配置退避重试：

- LLM API 限流 → 指数退避重试
- JSON 解析失败 → 直接失败（返回 `VERIFIER_FAULT`）
- 网络超时 → 重试

---

## 内部架构

```
┌─────────────────────────────────────────────────────────────┐
│                      AgentHarness                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   run_goal()                             ││
│  │  1. 创建 GoalConfig                                      ││
│  │  2. 初始化 GoalVerifier                                  ││
│  │  3. 进入 GoalLoop                                        ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    GoalLoop                              ││
│  │  while not goal_achieved:                                ││
│  │      result = await agent.run(prompt)                    ││
│  │      verification = await verifier.verify(result)        ││
│  │      if verification.achieved: break                     ││
│  │      if context_full: reset_context()                    ││
│  │      prompt = generate_continuation(result)              ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   GoalVerifier                           ││
│  │  - LLM 验证：让 LLM 判断目标是否达成                      ││
│  │  - 自定义验证：用户提供的验证函数                         ││
│  │  - 工具验证：运行测试/lint/type check                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 文件结构

**Python SDK**:
```
packages/sdk/src/harness/loop/
├── __init__.py              # 模块入口
├── types.py                 # 类型定义 (GoalConfig, GoalResult, GoalStatus, VerificationMethod)
├── goal.py                  # GoalVerifier
├── goal_loop.py             # GoalLoop
└── tool_verification.py     # ToolVerificationConfig, 工具验证
```

**Java SDK**:
```
packages/sdk-java/harness-sdk-loop/src/main/java/com/harness/loop/
├── GoalLoop.java            # 目标驱动执行循环
├── GoalVerifier.java        # 目标验证器
├── ParallelGoalExecutor.java # 并行目标执行
└── types/
    ├── GoalConfig.java      # 目标配置
    ├── GoalResult.java      # 目标结果
    ├── GoalStatus.java      # 目标状态
    ├── VerificationMethod.java # 验证方法
    ├── ToolVerificationConfig.java # 工具验证配置
    └── VerificationCommand.java    # 验证命令
```

---

## 后续 Phase

### Phase 2: Automations（定时调度）✅ 已实现

让 Agent 根据时间、事件自动触发执行。

```java
import com.harness.loop.automation.Automation;
import com.harness.loop.GoalLoop;
import java.util.concurrent.CompletableFuture;

public class AutomationExample {
    public static void main(String[] args) throws Exception {
        GoalLoop.AgentRunner agent = ...;

        // 定时任务（cron 表达式）
        Automation automation = Automation.builder()
            .name("daily-report")
            .schedule("0 9 * * *")  // 每天 9:00
            .goal("生成每日报告并发送到 Slack")
            .addSkill("report-generation")
            .build();

        // 间隔任务
        Automation healthCheck = Automation.builder()
            .name("health-check")
            .intervalSeconds(300)  // 每 5 分钟
            .goal("检查系统健康状态")
            .build();

        // 启动
        automation.start(agent).join();
        healthCheck.start(agent).join();

        // 运行一段时间
        Thread.sleep(3600_000);

        // 停止
        automation.stop().join();
        healthCheck.stop().join();
    }
}
```

**核心组件**：
- `CronTrigger` - cron 表达式定时触发
- `IntervalTrigger` - 固定间隔触发
- `TriggerManager` - 管理多个触发器
- `Automation` - 简化 API

详见 [06-triggers.md](./17-trigger-system.md)。

### Phase 3: Worktrees（并行隔离）✅ 已实现

支持并行执行多个 Goal，每个在独立工作目录。

```java
import com.harness.loop.worktree.WorktreeOrchestrator;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeResult;
import com.harness.loop.GoalLoop;
import java.util.List;
import java.util.Map;

GoalLoop.AgentRunner agent = ...;
WorktreeOrchestrator orchestrator = new WorktreeOrchestrator(agent, ".");

Map<String, WorktreeResult> results = orchestrator.runParallel(List.of(
    WorktreeConfig.builder().name("feature-a").goal("实现功能 A").build(),
    WorktreeConfig.builder().name("feature-b").goal("实现功能 B").build()
)).join();

// 合并成功的分支
for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
    if (entry.getValue().isAchieved()) {
        orchestrator.mergeSuccessful(results, "main").join();
    }
}
```

详见 [11-worktrees.md](./19-worktrees.md)。

### Phase 4: Connectors（外部集成）✅ 已实现

让 Agent 与外部系统集成。

```java
import com.harness.connectors.ConnectorManager;
import com.harness.connectors.SlackConnector;
import com.harness.connectors.SlackConfig;
import com.harness.connectors.GitHubConnector;
import com.harness.connectors.GitHubConfig;

ConnectorManager manager = new ConnectorManager();

// Slack 集成
SlackConnector slack = new SlackConnector(
    new SlackConfig.Builder()
        .botToken("xoxb-...")
        .build()
);
manager.registerConnector(slack);

// GitHub 集成
GitHubConnector github = new GitHubConnector(
    new GitHubConfig.Builder()
        .appId("123")
        .privateKey("...")
        .build()
);
manager.registerConnector(github);

manager.start().join();
```

详见 [12-connectors.md](./20-connectors.md)。

### Phase 5: Loop Orchestrator（统一编排）✅ 已实现

整合所有组件的统一 API。

```java
import com.harness.orchestrator.WorkflowEngine;
import com.harness.orchestrator.WorkflowConfig;
import com.harness.orchestrator.WorkflowStep;
import com.harness.orchestrator.WorkflowResult;
import com.harness.loop.GoalLoop;

GoalLoop.AgentRunner agent = ...;
WorkflowEngine engine = new WorkflowEngine();

// 创建工作流
WorkflowConfig workflow = WorkflowConfig.builder()
    .name("code-review")
    .addStep(WorkflowStep.builder()
        .name("analyze")
        .goal("分析代码")
        .build())
    .addStep(WorkflowStep.builder()
        .name("review")
        .goal("代码审查")
        .addDependsOn("analyze")
        .build())
    .build();

WorkflowResult result = engine.runWorkflow(workflow, agent).join();
```

详见 [13-orchestrator.md](./21-orchestrator.md)。

---

## 参考

- [设计文档](../design/loop-engineering.md)
- [06-trigger-system.md](./17-trigger-system.md) - Trigger System 详细设计
- [11-worktrees.md](./19-worktrees.md) - Worktrees 并行隔离执行
- [12-connectors.md](./20-connectors.md) - Connectors 外部系统集成
- [13-orchestrator.md](./21-orchestrator.md) - Orchestrator 工作流编排
