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

```python
from harness import AgentHarness
from harness.loop import WorktreeOrchestrator, WorktreeConfig

agent = AgentHarness(model="claude-sonnet-4-6")
orchestrator = WorktreeOrchestrator(agent, ".")

# 并行执行多个 Goal
results = await orchestrator.run_parallel([
    WorktreeConfig(name="feature-a", goal="实现功能 A"),
    WorktreeConfig(name="feature-b", goal="实现功能 B"),
    WorktreeConfig(name="bugfix-c", goal="修复 Bug C"),
])

# 检查结果
for name, result in results.items():
    print(f"{name}: {result.goal_result.status.value}")
    if result.goal_result.achieved:
        print(f"  Branch: {result.branch_name}")
        print(f"  Iterations: {result.goal_result.total_iterations}")

# 合并成功的分支
for name, result in results.items():
    if result.achieved:
        print(f"{name}: merged successfully")
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

```python
import asyncio
from harness import AgentHarness
from harness.loop import WorktreeOrchestrator, WorktreeConfig

async def main():
    agent = AgentHarness(model="claude-sonnet-4-6")
    orchestrator = WorktreeOrchestrator(agent, ".")

    # 定义并行任务
    tasks = [
        WorktreeConfig(
            name="add-auth",
            goal="实现用户认证功能，包括登录、注册、登出",
            base_branch="main",
        ),
        WorktreeConfig(
            name="add-api",
            goal="实现 REST API 端点，包括 CRUD 操作",
            base_branch="main",
        ),
        WorktreeConfig(
            name="fix-tests",
            goal="修复所有失败的测试用例",
            base_branch="main",
        ),
    ]

    # 并行执行
    print("开始并行执行 3 个任务...")
    results = await orchestrator.run_parallel(tasks)

    # 汇总结果
    achieved = sum(1 for r in results.values() if r.achieved)
    print(f"\n完成: {achieved}/{len(tasks)} 个任务达成目标")

    # 合并所有成功的分支
    merge_result = await orchestrator.merge_successful(results)
    print(f"合并成功: {merge_result.merged}")
    print(f"有冲突: {merge_result.conflicts}")
    print(f"跳过: {merge_result.skipped}")

asyncio.run(main())
```

### 使用自定义验证器

```python
async def verify_tests_pass(result):
    """验证测试通过"""
    proc = await asyncio.create_subprocess_exec(
        "pytest", "tests/",
        stdout=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    return proc.returncode == 0

tasks = [
    WorktreeConfig(
        name="refactor-auth",
        goal="重构认证模块",
        custom_verifier=verify_tests_pass,
    ),
]

results = await orchestrator.run_parallel(tasks)
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

- [10-loop-engineering.md](./10-loop-engineering.md) - Loop Engineering 总览
- [12-connectors.md](./12-connectors.md) - 外部系统集成
