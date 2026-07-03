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

```python
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()

# 基础用法
result = await agent.run_goal("修复所有类型错误")

# 检查结果
if result.status == GoalStatus.ACHIEVED:
    print(f"目标达成，共 {result.total_iterations} 轮迭代")
```

### GoalConfig 配置

```python
from harness.loop import GoalConfig

config = GoalConfig(
    description="将测试覆盖率提升到 80%",  # 目标描述
    session_id="my-session-123",            # 会话 ID（用于对话连续性，可选）
    success_criteria="测试覆盖率报告显示 >= 80%",  # 成功标准（可选）
    workspace_dir=".",                       # 工作目录
    
    # 迭代控制
    max_iterations=50,                       # 最大迭代次数
    max_context_resets=5,                    # 最大上下文重置次数
    timeout_seconds=3600,                    # 超时时间（秒）
    
    # 验证配置
    custom_verifier=None,                    # 自定义验证函数
    
    # 成本控制
    max_tokens=None,                         # 最大 token 数
    max_cost_usd=None,                       # 最大成本（美元）
)

result = await agent.run_goal(config)
```

### 会话连续性

默认情况下，每次调用 `run_goal()` 会创建新的会话。如果需要在多轮目标执行之间保持对话上下文，可以指定 `session_id`：

```python
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()

# 第一轮目标执行
result1 = await agent.run_goal(
    goal="分析代码库结构",
    session_id="my-project-session",  # 指定会话 ID
)

# 第二轮目标执行（会记住第一轮的上下文）
result2 = await agent.run_goal(
    goal="根据分析结果生成文档",
    session_id="my-project-session",  # 使用相同的会话 ID
)
```

**适用场景**：
- 多阶段任务：前一个目标的执行结果需要传递给后续目标
- 上下文保持：在长时间任务中保持对话历史
- 任务续接：恢复中断的任务执行

**注意**：上下文重置（`max_context_resets`）会创建新的会话 ID 以防止 token 溢出，此时历史消息会被精简。

### 自定义验证器

```python
import asyncio
from harness import AgentHarness
from harness.loop import GoalStatus

agent = AgentHarness()

# 异步验证函数
async def check_coverage(result):
    """检查测试覆盖率是否达到 80%"""
    proc = await asyncio.create_subprocess_exec(
        "pytest", "--cov", "--cov-report=term",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return "TOTAL.*80%" in stdout.decode()

result = await agent.run_goal(
    goal="测试覆盖率达到 80%",
    custom_verifier=check_coverage,
    max_iterations=50,
)

if result.status == GoalStatus.ACHIEVED:
    print("目标达成!")
```

### 工具验证（Tool Verification）

工具验证提供客观、确定性的目标验证方式，通过运行测试、Lint、类型检查等命令来验证目标是否达成。

#### 基础用法

```python
from harness import AgentHarness
from harness.loop import GoalConfig, GoalStatus, VerificationMethod
from harness.loop.tool_verification import ToolVerificationConfig

agent = AgentHarness()

# Python 项目验证配置
config = ToolVerificationConfig(
    commands=[
        ("pytest", "pytest", "tests/", "-v"),
        ("mypy", "mypy", "src/"),
        ("ruff", "ruff", "check", "src/"),
    ],
    working_directory=".",
    timeout_seconds=300,
)

result = await agent.run_goal(
    goal=GoalConfig(
        description="修复所有类型错误",
        verification_method=VerificationMethod.TOOL,
        tool_verification_config=config,
    ),
)

if result.status == GoalStatus.ACHIEVED:
    print("所有验证通过!")
```

#### 预设配置

SDK 提供常用项目的预设验证配置：

```python
from harness.loop.tool_verification import ToolVerificationConfig

# Python 项目（pytest + mypy + ruff）
python_config = ToolVerificationConfig.python_defaults()

# Python 项目（自定义路径）
python_config = ToolVerificationConfig.python_project(
    test_path="tests/",
    src_path="src/",
)

# Java/Gradle 项目
gradle_config = ToolVerificationConfig.gradle_defaults()

# Java/Maven 项目
maven_config = ToolVerificationConfig.maven_defaults()

# Node.js/npm 项目
npm_config = ToolVerificationConfig.npm_defaults()
```

#### 自定义命令

```python
from harness.loop.tool_verification import ToolVerificationConfig, VerificationCommand

config = ToolVerificationConfig(
    commands=[
        VerificationCommand(
            name="unit-tests",
            command=["pytest", "tests/unit/", "-v"],
        ),
        VerificationCommand(
            name="integration-tests",
            command=["pytest", "tests/integration/", "-v"],
        ),
        VerificationCommand(
            name="type-check",
            command=["mypy", "src/"],
        ),
    ],
    working_directory="./project",
    timeout_seconds=600,  # 10 分钟
    fail_fast=True,       # 第一个失败就停止
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `commands` | `list[VerificationCommand]` | 必填 | 验证命令列表 |
| `working_directory` | `str` | `"."` | 命令执行目录 |
| `timeout_seconds` | `int` | `300` | 每个命令的超时时间 |
| `fail_fast` | `bool` | `True` | 是否在第一个失败时停止 |
| `continue_on_warning` | `bool` | `False` | 警告时是否继续 |

#### 验证结果

工具验证的结果会包含在 `GoalResult.verification_log` 中：

```python
result = await agent.run_goal(...)

for record in result.verification_log:
    print(f"迭代 {record.iteration}:")
    print(f"  方法: {record.method}")  # VerificationMethod.TOOL
    print(f"  结果: {'通过' if record.achieved else '失败'}")
    print(f"  原因: {record.reasoning}")
```

#### 使用场景

| 场景 | 推荐验证方式 |
|------|------------|
| 修复类型错误 | `VerificationMethod.TOOL` + mypy |
| 提高测试覆盖率 | `VerificationMethod.TOOL` + pytest --cov |
| 代码重构 | `VerificationMethod.TOOL` + pytest + ruff |
| 功能开发 | `VerificationMethod.TOOL` + pytest |
| 文档生成 | `VerificationMethod.LLM` 或自定义验证器 |

### GoalStatus 状态

```python
from harness.loop import GoalStatus

class GoalStatus(Enum):
    ACHIEVED = "achieved"               # 目标达成
    TIMEOUT = "timeout"                 # 超时
    MAX_ITERATIONS = "max_iterations"   # 达到最大迭代
    MAX_RESETS = "max_resets"           # 达到最大重置次数
    ERROR = "error"                     # Agent 执行错误
    VERIFIER_FAULT = "verifier_fault"   # 验证器故障
    CANCELLED = "cancelled"             # 用户取消
```

### GoalResult 结果

```python
@dataclass
class GoalResult:
    goal: str                           # 目标描述
    status: GoalStatus                  # 执行状态
    total_iterations: int               # 总迭代次数
    context_resets: int                 # 上下文重置次数
    total_tokens: TokenUsage            # Token 使用量
    duration_seconds: float             # 执行时长
    final_response: str                 # 最终响应
    verification_log: list[VerificationRecord]  # 验证日志
    error: str | None = None            # 错误详情
```

---

## 设计原则

### GoalVerifier 无状态性

`GoalVerifier` 是无状态的，所有上下文通过参数传递：

```python
# ✅ 正确：无状态验证
async def verify(result: LoopResult, context: dict | None = None) -> VerificationResult:
    workspace = context.get("workspace_dir", ".")
    # 通过 context 获取信息，不内部存储

# ❌ 错误：有状态验证
class MyVerifier:
    def __init__(self):
        self._workspace = None  # 不要存储状态
```

**原因**：
- 支持并发执行多个 Goal
- 验证器可被复用于不同 workspace
- 便于测试（无副作用）

### 异步设计

`GoalLoop` 可能运行数分钟甚至数小时，需避免阻塞事件循环：

```python
async def run(self) -> GoalResult:
    while True:
        # ... 执行迭代 ...
        
        # 让出控制权，防止阻塞事件循环
        await asyncio.sleep(0)
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

```
packages/sdk/src/harness/loop/
├── __init__.py              # 模块入口
├── types.py                 # 类型定义 (GoalConfig, GoalResult, GoalStatus, VerificationMethod)
├── goal.py                  # GoalVerifier
├── goal_loop.py             # GoalLoop
└── tool_verification.py     # ToolVerificationConfig, 工具验证
```

---

## 后续 Phase

### Phase 2: Automations（定时调度）✅ 已实现

让 Agent 根据时间、事件自动触发执行。

```python
from harness.loop import Automation
import asyncio

async def main():
    # 定时任务（cron 表达式）
    automation = Automation(
        name="daily-report",
        schedule="0 9 * * *",  # 每天 9:00
        goal="生成每日报告并发送到 Slack",
        skills=["report-generation"],
    )

    # 间隔任务
    health_check = Automation(
        name="health-check",
        interval_seconds=300,  # 每 5 分钟
        goal="检查系统健康状态",
    )

    # 启动
    from harness import AgentHarness
    agent = AgentHarness()

    await automation.start(agent)
    await health_check.start(agent)

    # 运行一段时间
    await asyncio.sleep(3600)

    # 停止
    await automation.stop()
    await health_check.stop()

asyncio.run(main())
```

**核心组件**：
- `CronTrigger` - cron 表达式定时触发
- `IntervalTrigger` - 固定间隔触发
- `TriggerManager` - 管理多个触发器
- `Automation` - 简化 API

详见 [06-triggers.md](./06-triggers.md)。

### Phase 3: Worktrees（并行隔离）✅ 已实现

支持并行执行多个 Goal，每个在独立工作目录。

```python
from harness.loop import WorktreeOrchestrator, WorktreeConfig

orchestrator = WorktreeOrchestrator(agent, ".")

results = await orchestrator.run_parallel([
    WorktreeConfig(name="feature-a", goal="实现功能 A"),
    WorktreeConfig(name="feature-b", goal="实现功能 B"),
])

# 合并成功的分支
for name, result in results.items():
    if result.status == "completed":
        await orchestrator.merge(name)
```

详见 [11-worktrees.md](./11-worktrees.md)。

### Phase 4: Connectors（外部集成）✅ 已实现

让 Agent 与外部系统集成。

```python
from harness.connectors import (
    ConnectorManager,
    SlackConnector,
    GitHubConnector,
)

manager = ConnectorManager(trigger_manager)

# Slack 集成
slack = SlackConnector(config=SlackConfig(bot_token="xoxb-..."))
manager.register_connector(slack)

# GitHub 集成
github = GitHubConnector(config=GitHubConfig(app_id="123", private_key="..."))
manager.register_connector(github)

await manager.start()
```

详见 [12-connectors.md](./12-connectors.md)。

### Phase 5: Loop Orchestrator（统一编排）✅ 已实现

整合所有组件的统一 API。

```python
from harness.orchestrator import (
    LoopOrchestrator,
    WorkflowConfig,
    WorkflowStep,
)

orchestrator = LoopOrchestrator(agent)

# 创建工作流
workflow = WorkflowConfig(
    name="code-review",
    steps=[
        WorkflowStep(name="analyze", goal="分析代码"),
        WorkflowStep(name="review", goal="代码审查", depends_on=["analyze"]),
    ],
)

result = await orchestrator.run_workflow("code-review")
```

详见 [13-orchestrator.md](./13-orchestrator.md)。

---

## 参考

- [设计文档](../design/loop-engineering.md)
- [06-trigger-system.md](./06-trigger-system.md) - Trigger System 详细设计
- [11-worktrees.md](./11-worktrees.md) - Worktrees 并行隔离执行
- [12-connectors.md](./12-connectors.md) - Connectors 外部系统集成
- [13-orchestrator.md](./13-orchestrator.md) - Orchestrator 工作流编排
