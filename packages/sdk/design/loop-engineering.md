# Loop Engineering 设计文档

> **状态**: Phase 1 已实现，Phase 2-5 待开发
> **创建时间**: 2026-06-28
> **最后更新**: 2026-06-28

---

## 背景

**Loop Engineering** 是 2026 年 6 月兴起的新范式，核心思想是：

> 不再逐轮手动提示 AI Agent，而是设计一个自动化循环系统来驱动 Agent

**核心公式**：`Loop = Trigger + Context + Action + Verification + State + Stop rules`

**参考来源**：
- Addy Osmani "Loop Engineering" (2026-06-07)
- Claude Code `/goal` 实现
- Peter Steinberger / Boris Cherny 的相关讨论

---

## 实现状态

| Phase | 组件 | 状态 | 说明 |
|-------|------|------|------|
| **Phase 1** | Goal Verifier | ✅ 已实现 | 目标驱动执行 |
| **Phase 2** | Automations | ✅ 已实现 | 定时触发/调度 |
| **Phase 3** | Worktrees | 📝 设计完成 | 多 Agent 并行隔离 |
| **Phase 4** | Connectors | 📝 设计完成 | 外部系统集成 |
| **Phase 5** | Loop Orchestrator | 📝 设计完成 | 统一编排 API |

---

## Phase 1: Goal Verifier ✅ 已实现

### 目标

实现目标驱动执行（Goal-Driven Execution）：

1. 用户描述目标，Agent 自主运行直到完成
2. 验证器判断目标是否达成
3. 自动重置上下文，防止"上下文焦虑"
4. 成本控制：迭代次数、超时、token 预算

### API 设计

```python
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()

# 基础用法
result = await agent.run_goal(
    goal="将测试覆盖率提升到 80%",
    max_iterations=50,
)

# 简化 API
result = await agent.run_goal("修复所有类型错误")

# 指定工作目录（为 Phase 3 Worktrees 预留）
result = await agent.run_goal(
    goal="修复 lint 错误",
    workspace_dir="/tmp/worktree-feature-a",  # Phase 3: 由 WorktreeManager 传入
)

# 自定义验证函数
def check_coverage(result):
    import subprocess
    r = subprocess.run(["pytest", "--cov"], capture_output=True)
    return "TOTAL.*80%" in r.stdout.decode()

result = await agent.run_goal(
    goal="测试覆盖率达到 80%",
    custom_verifier=check_coverage,
)

# 检查结果
if result.status == GoalStatus.ACHIEVED:
    print("目标达成!")
elif result.status == GoalStatus.VERIFIER_FAULT:
    print(f"验证器故障: {result.error}")
```

### 架构

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

### 类型定义

```python
# loop/types.py

@dataclass
class GoalConfig:
    """Goal configuration."""
    
    # 目标定义
    description: str                    # 目标描述
    success_criteria: str | None = None # 成功标准
    
    # 执行环境（为 Phase 3 Worktrees 预留）
    workspace_dir: str = "."            # 工作目录，Phase 3 可传入 worktree 路径
    
    # 迭代控制
    max_iterations: int = 50
    max_context_resets: int = 5
    timeout_seconds: int = 3600
    
    # 验证配置
    verification_method: str = "llm"    # "llm" | "custom" | "tool"
    custom_verifier: Callable | None = None
    
    # 成本控制
    max_tokens: int | None = None
    max_cost_usd: float | None = None


@dataclass
class GoalResult:
    """Result of goal-driven execution."""
    
    goal: str
    status: GoalStatus
    total_iterations: int
    context_resets: int
    total_tokens: TokenUsage
    duration_seconds: float
    final_response: str
    verification_log: list[VerificationRecord]
    error: str | None = None            # 错误详情


class GoalStatus(Enum):
    ACHIEVED = "achieved"               # 目标达成
    TIMEOUT = "timeout"                 # 超时
    MAX_ITERATIONS = "max_iterations"   # 达到最大迭代
    MAX_RESETS = "max_resets"           # 达到最大重置次数
    ERROR = "error"                     # Agent 执行错误
    VERIFIER_FAULT = "verifier_fault"   # 验证器故障（API 限流、JSON 解析失败等）
    CANCELLED = "cancelled"             # 用户取消
```

### 文件结构

```
packages/sdk/src/harness/loop/
├── __init__.py          # 模块入口
├── types.py             # 类型定义
├── goal.py              # GoalVerifier
└── goal_loop.py         # GoalLoop
```

---

## 设计原则

### GoalVerifier 无状态性

`GoalVerifier` 必须保持**无状态**，像一个纯函数：

```python
# ✅ 正确：无状态验证
class GoalVerifier:
    async def verify(
        self,
        result: LoopResult,
        context: dict | None = None,  # 包含 workspace_dir 等信息
    ) -> VerificationResult:
        # 通过 context 获取工作目录，不内部存储
        workspace = context.get("workspace_dir", ".")
        ...

# ❌ 错误：有状态验证
class GoalVerifier:
    def __init__(self):
        self._current_branch = None  # 不要存储分支状态
        self._workspace = None       # 不要存储路径
```

**原因**：
- 支持并发执行多个 Goal（Phase 3）
- 验证器可被复用于不同 workspace
- 便于测试（无副作用）

### 异步设计考量

`GoalLoop` 可能运行数分钟甚至数小时，需避免阻塞事件循环：

```python
class GoalLoop:
    async def run(self) -> GoalResult:
        while True:
            # ... 执行迭代 ...
            
            # 让出控制权，防止阻塞事件循环
            await asyncio.sleep(0)
            
            # 通过 ProgressCallback 报告进度
            if self._on_progress:
                self._on_progress(ProgressEvent(...))
```

**机制**：
- 每次迭代后 `await asyncio.sleep(0)` 让出控制权
- 使用现有的 `Hooks 系统` 进行事件通知
- 支持通过 `ProgressCallback` 监控长时间运行的任务

### 验证器异步化

`custom_verifier` 应使用异步实现，避免阻塞事件循环：

```python
# ✅ 推荐：异步验证函数
async def check_coverage(result):
    proc = await asyncio.create_subprocess_exec(
        "pytest", "--cov",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return "TOTAL.*80%" in stdout.decode()

# ❌ 避免：同步调用会阻塞整个进程
def check_coverage_sync(result):
    r = subprocess.run(["pytest", "--cov"], capture_output=True)  # 阻塞！
    return "TOTAL.*80%" in r.stdout.decode()
```

### 验证器容错机制

为 `VERIFIER_FAULT` 配置退避重试：

```python
@dataclass
class GoalConfig:
    # ... 其他字段 ...
    
    # 验证器容错配置
    verifier_max_retries: int = 3           # 最大重试次数
    verifier_retry_delay: float = 1.0       # 初始重试延迟（秒）
    verifier_retry_backoff: float = 2.0     # 退避倍数
```

**重试策略**：
- LLM API 限流 → 指数退避重试
- JSON 解析失败 → 直接失败（不重试，返回 `VERIFIER_FAULT`）
- 网络超时 → 重试

---

## RalphLoopHook 重构方案

### 现有问题

- 验证逻辑简单（关键词检测）
- 与 Hook 系统耦合
- 缺少成本控制

### 推荐方案

将 `RalphLoopHook` 逻辑合并到 `GoalLoop`，保持 API 简洁：

```python
class GoalLoop:
    def __init__(self, agent, config):
        # 内部使用 RalphLoopHook 的上下文重置逻辑
        self._ralph_config = RalphLoopConfig(
            max_loops=config.max_context_resets,
            ...
        )
```

---

## 实施步骤

### Step 1: 创建模块结构 ✅
- [x] 创建 `loop/__init__.py`
- [x] 创建 `loop/types.py`

### Step 2: 实现 GoalVerifier ✅
- [x] 创建 `loop/goal.py`
- [x] 实现 LLM 验证
- [x] 支持自定义验证函数
- [x] 支持同步/异步验证器
- [x] 实现重试机制（指数退避）

### Step 3: 实现 GoalLoop ✅
- [x] 创建 `loop/goal_loop.py`
- [x] 实现迭代控制
- [x] 实现上下文重置
- [x] 实现超时处理
- [x] 实现成本控制

### Step 4: 集成到 AgentHarness ✅
- [x] 添加 `run_goal()` 方法
- [x] 更新 `__init__.py` 导出

### Step 5: 编写测试 ✅
- [x] GoalVerifier 单元测试 (18 tests passing)
- [x] GoalLoop 单元测试 (12 tests passing)
- [x] 集成测试 (6 tests passing)

**总计: 36 个测试通过**

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Token 成本失控 | 高 | `max_tokens` / `max_cost_usd` 限制 |
| 无限循环 | 高 | `max_iterations` / `timeout_seconds` |
| 验证器误判 | 中 | LLM + 自定义验证双重检查 |
| 验证器故障 | 中 | `VERIFIER_FAULT` 状态 + 重试机制 |
| 上下文丢失 | 中 | Snapshot 持久化 |
| 事件循环阻塞 | 低 | 每次迭代 `await asyncio.sleep(0)` |

---

## 后续 Phase

### Phase 2: Automations ✅ 已实现
- `TriggerType`: cron / interval / event 触发
- `TriggerAction`: 触发后动作，映射到 GoalConfig
- `TriggerManager`: 触发器管理器
- `Automation`: 简化 API，整合 Trigger + Goal

详见：`design/phase2-automations.md`

### Phase 3: Worktrees 📝 设计完成
- `WorktreeManager`: git worktree 生命周期管理
- `ParallelGoalExecutor`: 并行 Goal 执行器
- `WorktreeOrchestrator`: 顶层 API
- 支持并行执行多个 Goal，每个在隔离的 git worktree 中

详见：`design/phase3-worktrees.md`

### Phase 4: Connectors 📝 设计完成
- `Connector` 基类和标准化事件
- WebhookConnector: HTTP webhook 接收
- SlackConnector: Slack 消息收发
- GitHubConnector: GitHub App 集成
- ConnectorManager: 统一管理
- OutputChannel: 输出路由

详见：`design/phase4-connectors.md`

### Phase 5: Loop Orchestrator 📝 设计完成
- `WorkflowEngine`: 多步骤工作流执行
- `TeamOrchestrator`: 多 Agent 协作编排
- `LoopOrchestrator`: 统一 API 入口
- `MonitorService`: 可观测性

详见：`design/phase5-orchestrator.md`
