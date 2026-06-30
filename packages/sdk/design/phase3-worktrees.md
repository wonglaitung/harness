# Phase 3: Worktrees 设计文档

> **状态**: 待实现
> **创建时间**: 2026-06-30
> **最后更新**: 2026-06-30

---

## 背景

Loop Engineering Phase 1-2 已完成：
- Phase 1: Goal Verifier - 目标驱动执行，验证器判断目标是否达成
- Phase 2: Automations - 定时触发/调度系统

Phase 3 Worktrees 的核心需求是：**让多个 Agent 并行执行，每个在隔离的工作目录中运行，互不干扰**。

**设计目标**：
1. 支持 git worktree 风格的隔离执行
2. 多个 Goal 并行运行，各自有独立工作目录
3. 防止文件冲突、分支冲突
4. 支持结果汇总和合并

---

## 现有架构分析

### 关键组件（可复用）

| 组件 | 文件 | 作用 |
|------|------|------|
| `GoalConfig` | `loop/types.py` | 已有 `workspace_dir` 字段，预留用于 worktree |
| `GoalVerifier` | `loop/goal.py` | **无状态设计**，支持并发执行 |
| `GoalLoop` | `loop/goal_loop.py` | 单 Goal 执行循环 |
| `SubAgentManager` | `core/subagent.py` | **已有并行执行框架**，支持 `run_all()` |
| `TriggerManager` | `triggers/manager.py` | 事件队列 + 并发处理模式 |

### 关键发现

1. **GoalVerifier 无状态性**（lessons.md 2026-06-28）：
   - 所有上下文通过 `context` 参数传递
   - 支持并发执行多个 Goal（Phase 3 预留）
   - 便于测试（无副作用）

2. **SubAgentManager 已实现 `run_all()`**：
   - 使用 `asyncio.gather()` 并行执行
   - 支持独立的 AgentHarness 实例
   - 支持工具过滤和继承

3. **GoalConfig 已有 `workspace_dir` 字段**：
   - 设计文档明确标注"Phase 3: 由 WorktreeManager 传入"
   - 无需修改现有类型定义

---

## 技术方案

### 方案概述

复用 SubAgentManager 的并行执行框架，新增 WorktreeManager 管理 git worktree 生命周期。

**架构**：
```
WorktreeOrchestrator
    ├── WorktreeManager (git worktree 生命周期)
    │   ├── create_worktree() → 工作目录路径
    │   ├── cleanup_worktree()
    │   └── list_worktrees()
    │
    └── ParallelGoalExecutor (并行 Goal 执行)
        ├── spawn_goal() → 创建 GoalLoop
        ├── run_all() → asyncio.gather
        └── collect_results()
```

### API 设计

```python
from harness.loop import WorktreeOrchestrator, WorktreeConfig

# 创建 orchestrator
orchestrator = WorktreeOrchestrator(agent)

# 定义多个 Goal
goals = [
    WorktreeConfig(
        name="feature-auth",
        goal="实现用户认证功能",
        base_branch="main",
        create_branch=True,  # 创建新分支 feature-auth
    ),
    WorktreeConfig(
        name="feature-api",
        goal="实现 API 端点",
        base_branch="main",
        create_branch=True,
    ),
]

# 并行执行
results = await orchestrator.run_parallel(goals)

# 检查结果
for name, result in results.items():
    print(f"{name}: {result.goal_result.status.value}")
    if result.goal_result.achieved:
        print(f"  Branch: {result.branch_name}")
        print(f"  Iterations: {result.goal_result.total_iterations}")

# 合并成功的分支（用户手动调用）
await orchestrator.merge_successful(results)
```

### 核心类型定义

```python
# loop/worktree_types.py

@dataclass
class WorktreeConfig:
    """Worktree 配置."""
    
    # Goal 定义
    name: str                    # Worktree 名称（也是分支名前缀）
    goal: str                    # 目标描述
    
    # Git 配置
    base_branch: str = "main"    # 基于哪个分支
    create_branch: bool = True   # 是否创建新分支
    branch_name: str | None = None  # 自定义分支名（默认 name）
    
    # Goal 配置
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None
    
    # 清理配置
    auto_cleanup: bool = True    # 完成后自动删除 worktree


@dataclass  
class WorktreeResult:
    """Worktree 执行结果."""
    
    name: str
    goal_result: GoalResult      # Goal 执行结果
    
    # Git 信息
    worktree_path: str           # 工作目录路径
    branch_name: str             # 分支名
    commits_made: int = 0        # 提交数量
    
    # 状态
    cleanup_done: bool = False   # 是否已清理


@dataclass
class MergeResult:
    """合并操作结果."""
    
    merged: list[str]            # 成功合并的分支
    conflicts: list[str]         # 有冲突需要手动处理的分支
    skipped: list[str]           # 未达成目标，跳过合并
    error: str | None = None     # 合并过程中的错误（如主仓库脏状态）


class WorktreeError(Exception):
    """Worktree 操作异常."""
    pass
```

### WorktreeManager 实现

```python
# loop/worktree_manager.py

class WorktreeManager:
    """Git worktree 生命周期管理."""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self._worktrees: dict[str, str] = {}  # name -> path
    
    async def create_worktree(
        self,
        name: str,
        base_branch: str,
        create_branch: bool = True,
    ) -> tuple[str, str]:
        """
        创建 git worktree.
        
        Returns:
            (worktree_path, branch_name)
        """
        branch_name = f"{name}" if create_branch else base_branch
        
        # 使用 subprocess 异步执行 git 命令
        worktree_path = f"{self.repo_root}/.worktrees/{name}"
        
        cmd = ["git", "worktree", "add"]
        if create_branch:
            cmd.extend(["-b", branch_name])
        cmd.extend([worktree_path, base_branch])
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise WorktreeError(f"Failed to create worktree: {stderr.decode()}")
        
        self._worktrees[name] = worktree_path
        return worktree_path, branch_name
    
    async def cleanup_worktree(self, name: str) -> bool:
        """删除 worktree 和可选的分支."""
        path = self._worktrees.get(name)
        if not path:
            return False
        
        # git worktree remove
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "remove", path, "--force",
            cwd=self.repo_root,
        )
        await proc.wait()
        
        del self._worktrees[name]
        return True
    
    def list_worktrees(self) -> list[str]:
        """列出所有活跃的 worktrees."""
        return list(self._worktrees.keys())
```

### ParallelGoalExecutor 实现

```python
# loop/parallel_executor.py

class ParallelGoalExecutor:
    """并行 Goal 执行器."""
    
    def __init__(
        self,
        agent: AgentHarness,
        worktree_manager: WorktreeManager,
    ):
        self.agent = agent
        self.worktree_manager = worktree_manager
        self._executions: dict[str, GoalLoop] = {}
    
    async def spawn_goal(
        self,
        config: WorktreeConfig,
    ) -> str:
        """
        为 Goal 创建隔离环境并准备执行.
        
        1. 创建 git worktree
        2. 创建 GoalConfig (workspace_dir = worktree_path)
        3. 创建 GoalLoop 实例
        
        Returns:
            Goal name
        """
        # 创建 worktree
        worktree_path, branch_name = await self.worktree_manager.create_worktree(
            name=config.name,
            base_branch=config.base_branch,
            create_branch=config.create_branch,
        )
        
        # 构建 GoalConfig
        goal_config = GoalConfig(
            description=config.goal,
            workspace_dir=worktree_path,  # 隔离的工作目录
            max_iterations=config.max_iterations,
            timeout_seconds=config.timeout_seconds,
            custom_verifier=config.custom_verifier,
        )
        
        # 创建 GoalLoop
        goal_loop = GoalLoop(
            agent=self.agent,
            config=goal_config,
        )
        
        self._executions[config.name] = goal_loop
        return config.name
    
    async def run_all(self) -> dict[str, GoalResult]:
        """
        并行执行所有 Goals.
        
        使用 asyncio.gather() 并发执行。
        """
        tasks = [
            execution.run()
            for execution in self._executions.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            name: result if isinstance(result, GoalResult) else GoalResult(
                goal=self._executions[name].config.description,
                status=GoalStatus.ERROR,
                error=str(result),
            )
            for name, result in zip(self._executions.keys(), results)
        }
```

### WorktreeOrchestrator 实现

```python
# loop/worktree_orchestrator.py

class WorktreeOrchestrator:
    """顶层 API - 整合 Worktree 和并行执行."""
    
    def __init__(
        self,
        agent: AgentHarness,
        repo_root: str = ".",
    ):
        self.agent = agent
        self.worktree_manager = WorktreeManager(repo_root)
        self.executor = ParallelGoalExecutor(agent, self.worktree_manager)
    
    async def run_parallel(
        self,
        configs: list[WorktreeConfig],
    ) -> dict[str, WorktreeResult]:
        """
        并行执行多个 Goals，每个在独立的 worktree 中.
        
        Returns:
            Dict mapping name to WorktreeResult
        """
        # 1. 创建所有 worktrees
        for config in configs:
            await self.executor.spawn_goal(config)
        
        # 2. 并行执行
        goal_results = await self.executor.run_all()
        
        # 3. 构建 WorktreeResult
        results = {}
        for name, goal_result in goal_results.items():
            config = next(c for c in configs if c.name == name)
            worktree_path = self.worktree_manager._worktrees.get(name, "")
            
            results[name] = WorktreeResult(
                name=name,
                goal_result=goal_result,
                worktree_path=worktree_path,
                branch_name=config.name,
            )
        
        # 4. 可选清理
        for config in configs:
            if config.auto_cleanup and results[config.name].goal_result.achieved:
                await self.worktree_manager.cleanup_worktree(config.name)
                results[config.name].cleanup_done = True
        
        return results
    
    async def merge_successful(
        self,
        results: dict[str, WorktreeResult],
        target_branch: str = "main",
    ) -> list[str]:
        """
        合并成功的 Goal 分支到目标分支.
        
        用户手动调用此方法，不会自动执行。
        
        Returns:
            List of successfully merged branch names
        """
        merged = []
        
        for name, result in results.items():
            if not result.goal_result.achieved:
                continue
            
            # 合并分支
            proc = await asyncio.create_subprocess_exec(
                "git", "merge", result.branch_name,
                cwd=self.worktree_manager.repo_root,
            )
            returncode = await proc.wait()
            
            if returncode == 0:
                merged.append(result.branch_name)
        
        return merged
```

---

## 文件结构

```
packages/sdk/src/harness/loop/
├── __init__.py              # 更新导出
├── types.py                 # 已有 GoalConfig 等
├── goal.py                  # 已有 GoalVerifier
├── goal_loop.py             # 已有 GoalLoop
├── automation.py            # 已有 Automation
├── worktree_types.py        # 新增: WorktreeConfig, WorktreeResult
├── worktree_manager.py      # 新增: WorktreeManager
├── parallel_executor.py     # 新增: ParallelGoalExecutor
└── worktree_orchestrator.py # 新增: WorktreeOrchestrator
```

---

## 与现有组件的关系

| 现有组件 | Phase 3 使用方式 |
|---------|-----------------|
| `GoalConfig` | 直接复用，`workspace_dir` 传入 worktree 路径 |
| `GoalVerifier` | 直接复用，无状态设计天然支持并发 |
| `GoalLoop` | 直接复用，每个 worktree 一个实例 |
| `SubAgentManager` | 参考 `run_all()` 模式，不直接使用 |
| `TriggerManager` | 参考 `_process_events()` 模式 |

---

## 设计决策

根据用户反馈，确认以下设计方向：

1. **仅支持 git worktree**：简化实现，不添加非 git 项目的隔离支持
2. **共用一个 agent**：所有 Goals 共用同一个 AgentHarness 实例和配置
3. **用户手动调用合并**：提供 `merge_successful()` 方法，用户自行决定是否调用

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Git worktree 命令失败 | 高 | 异步执行 + 详细错误信息 |
| 并发创建 `index.lock` 冲突 | 高 | `asyncio.Lock()` 串行化创建步骤 |
| 并发冲突（分支名相同） | 高 | 强制使用唯一 name |
| 进程崩溃导致孤儿 worktree | 高 | 初始化时扫描重建状态 |
| Worktree 清理失败 | 中 | `--force` 参数 + 重试 |
| Goal 执行超时 | 中 | 继承 GoalConfig.timeout_seconds |
| 合并时主仓库脏状态 | 中 | 检查 `git status --porcelain` |
| 合并冲突 | 中 | 返回冲突分支列表，用户手动处理 |

---

## 生产级增强措施

### 1. Git 并发锁：`index.lock` 冲突防护

虽然 `git worktree add` 在不同物理目录下工作，但创建瞬间会短暂锁定主仓库索引。
若同时发起 10 个 `create_worktree`，可能触发 `fatal: Unable to create '.../.git/index.lock': File exists`。

**解决方案**：使用 `asyncio.Lock()` 串行化创建步骤（通常只需几十毫秒）：

```python
class WorktreeOrchestrator:
    def __init__(self, agent, repo_root):
        self._create_lock = asyncio.Lock()  # 并发创建锁
        ...
    
    async def run_parallel(self, configs):
        # 创建阶段串行化（避免 index.lock 冲突）
        for config in configs:
            async with self._create_lock:
                await self.executor.spawn_goal(config)
        
        # 执行阶段并发化（真正的高并发）
        goal_results = await self.executor.run_all()
        ...
```

### 2. 孤儿 Worktree 恢复：状态持久化

进程崩溃后，内存中的 `_worktrees` 字典丢失，物理目录成为孤儿。

**解决方案**：初始化时扫描重建状态：

```python
class WorktreeManager:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self._worktrees: dict[str, str] = {}
        self._recover_orphaned_worktrees()
    
    def _recover_orphaned_worktrees(self):
        """从 git worktree list 恢复状态，清理孤儿目录."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        
        # 解析输出，重建 _worktrees 状态
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                path = line.split(" ", 1)[1]
                if ".worktrees/" in path:
                    name = Path(path).name
                    self._worktrees[name] = path
```

### 3. 合并前的脏状态检查

`merge_successful` 在主仓库执行合并，若主仓库处于脏状态（未提交修改），合并会失败。

**解决方案**：合并前检查主仓库状态：

```python
async def merge_successful(self, results, target_branch="main") -> MergeResult:
    """合并成功的 Goal 分支."""
    
    # 检查主仓库脏状态
    proc = await asyncio.create_subprocess_exec(
        "git", "status", "--porcelain",
        cwd=self.repo_root,
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    
    if stdout.decode().strip():
        raise WorktreeError(
            "Main repository has uncommitted changes. "
            "Please commit or stash before merging."
        )
    
    # 执行合并
    merged = []
    conflicts = []
    
    for name, result in results.items():
        if not result.goal_result.achieved:
            continue
        
        proc = await asyncio.create_subprocess_exec(
            "git", "merge", result.branch_name, "--no-edit",
            cwd=self.repo_root,
        )
        returncode = await proc.wait()
        
        if returncode == 0:
            merged.append(result.branch_name)
        else:
            conflicts.append(result.branch_name)
            # 中止失败的合并，保持仓库干净
            await asyncio.create_subprocess_exec(
                "git", "merge", "--abort",
                cwd=self.repo_root,
            ).wait()
    
    return MergeResult(merged=merged, conflicts=conflicts)
```

### 4. 返回详细的合并结果

不再只返回成功列表，而是返回完整的合并状态：

```python
@dataclass
class MergeResult:
    """合并操作结果."""
    merged: list[str]        # 成功合并的分支
    conflicts: list[str]     # 有冲突需要手动处理的分支
    skipped: list[str]       # 未达成目标，跳过合并
    error: str | None = None # 合并过程中的错误
```

---

## 实施步骤

### Step 1: 创建类型定义
- [ ] 创建 `loop/worktree_types.py`
- [ ] 定义 `WorktreeConfig`, `WorktreeResult`, `WorktreeError`

### Step 2: 实现 WorktreeManager
- [ ] 创建 `loop/worktree_manager.py`
- [ ] 实现 `create_worktree()`, `cleanup_worktree()`
- [ ] 异步 git 命令执行
- [ ] 实现 `_recover_orphaned_worktrees()` 孤儿恢复

### Step 3: 实现 ParallelGoalExecutor
- [ ] 创建 `loop/parallel_executor.py`
- [ ] 实现 `spawn_goal()`, `run_all()`
- [ ] 集成 GoalLoop
- [ ] 使用 `return_exceptions=True` 防止单个崩溃影响整体

### Step 4: 实现 WorktreeOrchestrator
- [ ] 创建 `loop/worktree_orchestrator.py`
- [ ] 整合 WorktreeManager + ParallelGoalExecutor
- [ ] 实现 `run_parallel()`, `merge_successful()`
- [ ] 添加 `asyncio.Lock()` 串行化 worktree 创建
- [ ] 实现脏状态检查和冲突分支返回

### Step 5: 编写测试
- [ ] `test_worktree_manager.py` - WorktreeManager 测试
- [ ] `test_parallel_executor.py` - 并行执行测试
- [ ] `test_worktree_integration.py` - 集成测试

### Step 6: 更新文档
- [ ] 更新 `design/loop-engineering.md` Phase 3 状态
- [ ] 添加 API 文档示例

---

## 测试策略

### 单元测试

```python
# tests/test_worktree_manager.py

class TestWorktreeManager:
    """测试 git worktree 管理."""
    
    async def test_create_worktree(self, tmp_path):
        """测试创建 worktree."""
        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=tmp_path)
        subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path)
        
        manager = WorktreeManager(str(tmp_path))
        path, branch = await manager.create_worktree("test", "main")
        
        assert path.endswith("/test")
        assert branch == "test"
        assert Path(path).exists()
    
    async def test_cleanup_worktree(self, tmp_path):
        """测试删除 worktree."""
        manager = WorktreeManager(str(tmp_path))
        await manager.create_worktree("test", "main")
        
        result = await manager.cleanup_worktree("test")
        assert result is True
        assert "test" not in manager.list_worktrees()
```

### 验证方法

1. **运行单元测试**：
   ```bash
   PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/test_worktree*.py -v
   ```

2. **手动验证**：
   ```python
   from harness import AgentHarness
   from harness.loop import WorktreeOrchestrator, WorktreeConfig
   
   agent = AgentHarness()
   orchestrator = WorktreeOrchestrator(agent, ".")
   
   results = await orchestrator.run_parallel([
       WorktreeConfig(name="feature-a", goal="Task A"),
       WorktreeConfig(name="feature-b", goal="Task B"),
   ])
   
   for name, result in results.items():
       print(f"{name}: {result.goal_result.status.value}")
   ```

---

## 后续 Phase 参考

Phase 3 完成后，后续 Phase 可参考：

- **Phase 4: Connectors** - 外部系统集成（Webhook, Slack, GitHub）
- **Phase 5: Loop Orchestrator** - 统一编排（整合所有组件）
