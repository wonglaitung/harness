# 11 - Worktrees 并行隔离执行

> **状态**: ✅ 已实现
> **设计文档**: [phase3-worktrees.md](../design/phase3-worktrees.md)

## 概述

Worktrees 模块支持**并行执行多个 Goal**，每个在独立的 git worktree 中运行，互不干扰。

**核心特性**：
- Git worktree 隔离 - 每个 Goal 有独立工作目录
- 并行执行 - 多个 Goal 同时运行
- 分支管理 - 自动创建和清理分支
- 结果合并 - 支持将成功的分支合并回主分支

## 核心 API

### WorktreeOrchestrator

```java
import com.harness.loop.GoalLoop;
import com.harness.loop.worktree.WorktreeOrchestrator;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeResult;
import java.util.List;
import java.util.Map;

GoalLoop.AgentRunner agent = ...;
WorktreeOrchestrator orchestrator = new WorktreeOrchestrator(agent, ".");

// 并行执行多个 Goal
Map<String, WorktreeResult> results = orchestrator.runParallel(List.of(
    WorktreeConfig.builder().name("feature-a").goal("实现功能 A").build(),
    WorktreeConfig.builder().name("feature-b").goal("实现功能 B").build(),
    WorktreeConfig.builder().name("bugfix-c").goal("修复 Bug C").build()
)).join();

// 检查结果
for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
    WorktreeResult result = entry.getValue();
    System.out.println(entry.getKey() + ": " + result.getGoalResult().status().getValue());
    if (result.isAchieved()) {
        System.out.println("  Branch: " + result.getBranchName());
        System.out.println("  Iterations: " + result.getGoalResult().totalIterations());
    }
}

// 合并成功的分支
for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
    if (entry.getValue().isAchieved()) {
        System.out.println(entry.getKey() + ": merged successfully");
    }
}
```

## 配置选项

### WorktreeConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | 必填 | Worktree 名称（也是分支名前缀） |
| `goal` | str | 必填 | 目标描述 |
| `base_branch` | str | "main" | 基于哪个分支创建 |
| `create_branch` | bool | True | 是否创建新分支 |
| `branch_name` | str | None | 自定义分支名（默认使用 name） |
| `max_iterations` | int | 50 | 最大迭代次数 |
| `timeout_seconds` | int | 3600 | 超时时间（秒） |
| `custom_verifier` | Callable | None | 自定义验证函数 |
| `auto_cleanup` | bool | True | 完成后自动删除 worktree |

### WorktreeResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | Worktree 名称 |
| `goal_result` | GoalResult | Goal 执行结果 |
| `worktree_path` | str | 工作目录路径 |
| `branch_name` | str | 分支名 |
| `commits_made` | int | 提交数量 |
| `cleanup_done` | bool | 是否已清理 |

### MergeResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `merged` | list[str] | 成功合并的分支 |
| `conflicts` | list[str] | 有冲突需要手动处理的分支 |
| `skipped` | list[str] | 未达成目标，跳过合并 |
| `error` | str | 合并过程中的错误 |

## 完整示例

### 并行开发多个功能

```java
import com.harness.loop.GoalLoop;
import com.harness.loop.worktree.WorktreeOrchestrator;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeResult;
import com.harness.loop.worktree.MergeResult;
import java.util.List;
import java.util.Map;

public class WorktreeExample {
    public static void main(String[] args) throws Exception {
        GoalLoop.AgentRunner agent = ...;
        WorktreeOrchestrator orchestrator = new WorktreeOrchestrator(agent, ".");

        // 定义并行任务
        List<WorktreeConfig> tasks = List.of(
            WorktreeConfig.builder()
                .name("add-auth")
                .goal("实现用户认证功能，包括登录、注册、登出")
                .baseBranch("main")
                .build(),
            WorktreeConfig.builder()
                .name("add-api")
                .goal("实现 REST API 端点，包括 CRUD 操作")
                .baseBranch("main")
                .build(),
            WorktreeConfig.builder()
                .name("fix-tests")
                .goal("修复所有失败的测试用例")
                .baseBranch("main")
                .build()
        );

        // 并行执行
        System.out.println("开始并行执行 3 个任务...");
        Map<String, WorktreeResult> results = orchestrator.runParallel(tasks).join();

        // 汇总结果
        long achieved = results.values().stream().filter(WorktreeResult::isAchieved).count();
        System.out.println("\n完成: " + achieved + "/" + tasks.size() + " 个任务达成目标");

        // 合并所有成功的分支
        MergeResult mergeResult = orchestrator.mergeSuccessful(results, "main").join();
        System.out.println("合并成功: " + mergeResult.getMerged());
        System.out.println("有冲突: " + mergeResult.getConflicts());
        System.out.println("跳过: " + mergeResult.getSkipped());
    }
}
```

### 使用自定义验证器

```java
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeOrchestrator;
import com.harness.loop.types.GoalResult;
import java.util.List;
import java.util.function.Function;
import java.util.concurrent.CompletableFuture;

// 自定义验证器：验证测试通过
Function<GoalResult, Boolean> verifyTestsPass = result -> {
    try {
        ProcessBuilder pb = new ProcessBuilder("pytest", "tests/");
        pb.redirectErrorStream(true);
        Process process = pb.start();
        int exitCode = process.waitFor();
        return exitCode == 0;
    } catch (Exception e) {
        return false;
    }
};

List<WorktreeConfig> tasks = List.of(
    WorktreeConfig.builder()
        .name("refactor-auth")
        .goal("重构认证模块")
        .customVerifier(verifyTestsPass)
        .build()
);

Map<String, WorktreeResult> results = orchestrator.runParallel(tasks).join();
```

## 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                  WorktreeOrchestrator                        │
│                                                              │
│  run_parallel([config1, config2, config3])                  │
│      │                                                       │
│      ├─► WorktreeManager.create_worktree("feature-a")       │
│      │       └─► git worktree add .worktrees/feature-a      │
│      │                                                       │
│      ├─► ParallelGoalExecutor.spawn_goal()                  │
│      │       └─► GoalLoop.run() in isolated workspace       │
│      │                                                       │
│      └─► asyncio.gather() → parallel execution              │
│                                                              │
│  merge_successful(results)                                   │
│      └─► git merge feature-a → main                         │
│      └─► git worktree remove .worktrees/feature-a           │
└─────────────────────────────────────────────────────────────┘
```

## 注意事项

1. **Git 仓库要求**: Worktrees 功能需要在 git 仓库中使用
2. **分支命名**: 默认使用 `name` 作为分支名，可通过 `branch_name` 自定义
3. **清理策略**: `auto_cleanup=True` 时，执行完成后自动删除 worktree 目录
4. **冲突处理**: 合并时如有冲突，需手动解决后再合并

## 下一步

- [10-loop-engineering.md](./18-loop-engineering.md) - Loop Engineering 总览
- [12-connectors.md](./20-connectors.md) - 外部系统集成
