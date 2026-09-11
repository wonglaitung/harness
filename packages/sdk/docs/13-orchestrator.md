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

## 与 Goal_run 的区别

`run_goal` 和 Orchestrator 解决不同的问题：

| 特性 | `run_goal` (GoalLoop) | Orchestrator |
|------|----------------------|--------------|
| **用途** | 单一目标驱动执行 | 多步骤工作流编排 |
| **执行模式** | 迭代直到目标达成 | 按依赖关系调度步骤 |
| **并行性** | 单任务顺序迭代 | 多步骤并行执行 |
| **状态管理** | 单一 GoalResult | 每步骤独立 StepResult |
| **适合场景** | 单一明确目标 | 预定义流水线 |

### 何时使用 run_goal

```python
# 单一目标，让 Agent 自主迭代直到完成
result = await agent.run_goal("修复所有类型错误")
```

适合：
- 单一明确目标（如"修复 bug"、"实现功能"）
- Agent 需要多次迭代探索
- 不需要预定义步骤顺序

### 何时使用 Orchestrator

```python
# 多步骤工作流，步骤间有依赖关系
workflow = WorkflowConfig(
    name="code-review",
    steps=[
        WorkflowStep(name="lint", goal="运行 ruff check"),
        WorkflowStep(name="test", goal="运行 pytest"),
        WorkflowStep(name="review", goal="代码审查", depends_on=["lint", "test"]),
    ],
)
result = await orchestrator.run_workflow("code-review")
```

适合：
- CI/CD 流水线
- 多阶段代码审查
- 需要并行执行多个独立任务
- 多 Agent 协作

**简单原则**：单一目标用 `run_goal`，多步骤有依赖用 Orchestrator。

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

## 确定性闸门抽象层（Deterministic Gate Abstraction）

> **状态**: ✅ 已落地（确定性治理层 M1–M3 已实作，详见「实施路线」与「防翻车清单 A–H 落地状态」）
> **设计稿自检**: 见文末「技术规范符合性自检」小节
> **原则来源**: [AI应用开发通用防翻车原则与检查清单.md](../../convention/AI应用开发通用防翻车原则与检查清单.md)

本项目定位为**单 Agent SDK**；多 Agent 能力须经**抽象层**实现，而非平行重写。核心决策：**两层抽象**——① 确定性安全/问责内核（gate / 共享状态 / 重试 / 人工兜底）落在**单 Agent 内核**，多 Agent 继承；② 编排层（TeamOrchestrator / WorkflowEngine）为架其上的**薄组合层**。

### 设计原则

1. **单 Agent 优先**：先完整单 Agent 内核能力，再多 Agent 经抽象层复用。
2. **LLM 输出不可信**：所有关键决策由确定性代码（deterministic gate）把关，LLM 不参与裁决。
3. **Blackboard 级共享状态**：多 Agent 协作经结构化共享状态（分级 `type/confidence/ttl` + `version+writer_id` + additive/authoritative 写分层 + 乐观并发 CAS + 冲突集显性化），**禁止点对点文本传纸条**。
4. **风险分级治理**：韧性层（熔断/预算/可观测/基础注入校验）始终在线；治理层（C/D/G/H + 完整边界）由统一 `strict` 开关控制。
5. **闭环**：失败 → `RetryPolicy` 局部自愈 → 终止/降级 → `ReviewQueue` 人工兜底。

### 分层架构

```
┌─ 单 Agent 内核 (AgentHarness / agent_loop) ───────────────┐
│  [常开] CircuitBreaker·CostController·OTel·基础注入校验     │
│  [strict] DeterministicGate(格式/事实/逻辑 + 交付对账)      │
│  [strict] SharedStateStore(Blackboard: mem/file/redis/db)  │
│  [strict] ReviewQueue · RetryPolicy · 完整权限沙箱 + PII    │
└───────────────▲ strict 传播 ───────────────────────────────┘
┌─ 编排抽象层 (薄) ──────────────────────────────────────────┐
│  TeamOrchestrator : 组合 AgentHarness，角色最小工具集        │
│  WorkflowEngine    : DAG 调度(含死锁检测)，步骤过同一 gate    │
│  经 SharedStateStore 协作(strict 下强制，替代文本传纸条)     │
└────────────────────────────────────────────────────────────┘
```

### DeterministicGate（确定性闸门）

单 Agent 与多 Agent 共用的一道**交付前**确定性校验管线，100% 代码裁决：

- **三维校验**
  - 格式维：`FormatValidator`（pydantic/dataclass 结构合法性）
  - 事实维：`FactGrounder`（关键结论须带溯源引用）
  - 逻辑维：`LogicReconciler`（跨字段勾稽 / 业务规则）
- **交付前对账** `Reconciliation`：结论 ↔ 可信源字段反向核对，无来源/自相矛盾项删除或标「存疑」，绝不静默交付。

`FactGrounder` 可信源**双通道**：① 工具溯源自动采集（从 `session` 工具调用记录抽取确定性证据）；② 调用时显式 `sources=` 传入。判定取二者并集；冲突以 `sources=` 优先；并集为空 → 结论标存疑/拦截。

### SharedStateStore（Blackboard 级共享状态）

多 Agent 协作的"病例本"，替代 `TeamOrchestrator` 当前的 `final_response` 文本传递：

- 记录模型 `BlackboardItem`：`id / type / content / source_agent / confidence / created_at / base_version / ttl / status`
- 写分层：`additive`（观测/提议，任意 Agent）vs `authoritative`（decision 落定，仅控制层经 verifier）
- 乐观并发：`write_if_version(base_version)` CAS，版本已前进则拒覆盖 / 存为并行提案
- 冲突集显性化：矛盾事实进冲突队列，不静默覆写
- 可插拔后端 `StateBackend`：`memory`(测试) / `file`(worktree 内，开发) / `redis`(生产) / `db`(SQLite/Postgres，生产)；redis/db 作 optional extras（pin 版本，不进核心依赖）

### RetryPolicy 与 ReviewQueue

- `RetryPolicy(max_retries, backoff)`：指数退避 + 上限 + 区分可重试/不可重试错误；用于目标级与 `WorkflowStep.max_retries`（当前 `types.py` 已声明未用）。
- `ReviewQueue`：gate 隔离项入队，人工三选一（确认/修正/豁免），决策写审计日志并沉淀 KB 供复用（G 节）。

### 统一 `strict` 开关

`HarnessConfig.strict: bool = False`：
- `False`（默认）：gate/state/review/retry/PII/全沙箱均 `None`/直通 → **存量应用零迁移**，仅韧性层在线。
- `True`：治理层全开 → 金融级对标防翻车清单 A–H。

风险分级：Low（研究/内部工具）可 `False`；High（金融/监管/安全关键）**必须 `True`**（README/概述须醒目声明，可选部署校验 `HARNESS_REQUIRE_STRICT=1`，详见 [08-security.md](./08-security.md#部署侧强制校验环境变量)）。

### 与现有编排的关系（改造点）

- `TeamOrchestrator._run_sequential/_run_hierarchical`：当前把 `result.final_response` 文本塞入下一 prompt（`team_orchestrator.py:322-380`），改为经 `SharedStateStore` 结构化字段读写；每个子 Agent 结果过同一 `DeterministicGate`（strict 传播）。
- `WorkflowEngine._execute_step`：落实 `WorkflowStep.max_retries` 经 `RetryPolicy`；步骤产物过 gate + 对账；超限升级 `ReviewQueue`。
- `WorktreeOrchestrator`：merge 冲突升级 `ReviewQueue`（保留 abort）。
- `AgentRole` 增 `tools`（角色最小工具集）；`TeamConfig`/`WorkflowStep` 增 `state_store/gate/retry` 引用。

### 实施路线

- **Phase 1（单 Agent 内核）**：新增 `harness/gate/*`、`harness/state/*`、`harness/review/queue.py`；接线 `agent_loop`/`config`/`harness`；`tests/unit/`。
- **Phase 2（多 Agent 抽象）**：改造 `team_orchestrator`/`workflow_engine`/`worktree`/`types`；`tests/` 集成测。Java SDK 同步在 Python 完成后手工开展。

> **三块缝隙已闭合（SDK 侧）**
> 1. **业务规则进自动治理**：`GateConfig.rules`（可调用）/ `rule_specs` / `rules_path`（声明式 `numeric_sum`/`equality`/`range`/`regex_present`）经 `_build_gate` 汇入 `LogicReconciler`——`strict=True` 即跑领域勾稽，无需手驱 `DeterministicGate`。
> 2. **ReviewQueue 持久化桥**：`ReviewQueue(store=SharedStateStore(...))` 同步落盘；`ReviewConfig(backend="file"|"redis"|"db")` 经 `_build_review_queue` 自动接线；`FileBackend` 开 WAL + `busy_timeout` 支持多进程。
> 3. **工具落盘产物（Gap 3，消费方集成）**：auto-gate 只校验 `final_response`，不校验经工具落盘的 spec。消费方应在 `submit_spec` 工具内手动 `gate.check(spec_json)` 并升级 `ReviewQueue`（示例 `examples/spec_submit_governance.py`，接入模式见 [07-sdk-api.md](./07-sdk-api.md#gap-3工具落盘产物的闸门)）。仍属「尽可能用 SDK」。

### 技术规范符合性自检

> 依 `convention/02-安全规约-设计.md` / `03-日志与可观测性.md` / `04-并发·资源·幂等.md` 要求，design 阶段确认。

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·凭证与密钥 | 满足 | 各后端连接串/路径走 `StateConfig`/环境变量，不硬编码 |
| 02-设计·输入校验与防注入 | 满足 | 注入现为硬阻断（`InputValidator(block_injection=True)`，命中即拒绝输入）；工具回传内容亦过 `PromptInjectionDetector` 并清洗后再回灌模型；网络工具走 `PermissionSet` 白名单防 SSRF |
| 02-设计·最小权限 | 满足 | `AgentRole.tools` 角色最小工具集；`PermissionSet` 路径/命令受限 |
| 02-设计·依赖安全 | 部分满足 | redis/db 驱动作 optional extras（pin 版本）；风险：第三方 CVE → 缓解：锁版本+定期审计 |
| 02-设计·输出编码 | 满足 | 既有 guardrails PII 编码；`ResultSanitizer` 已存在 |
| 02-设计·密码学原语 | 满足 | 改造 `team_orchestrator.py:230` 的 `md5` → `sha256`；不引入弱算法 |
| 03-日志·不打敏感信息 | 满足 | gate/state/review 审计日志掩码 PII/密钥，不明文落盘 |
| 03-日志·结构化与级别 | 满足 | 复用 OTel span + 结构化日志，带 trace/run ID 贯穿 |
| 03-日志·适量 | 满足 | 仅关键路径记审计/隔离事件 |
| 04-并发·资源释放 | 满足 | 后端连接/锁用后释放（file=SQLite 连接管理；redis=连接池） |
| 04-并发·避免竞态 | 满足 | `memory`=asyncio.Lock；`file`=SQLite 事务原子；`redis`=原子命令；CAS 防覆盖；临界区不做重 IO |
| 04-并发·写幂等 | 满足 | 写操作幂等（CAS `base_version`），重试安全 |
| 04-并发·重试带退避 | 满足 | `RetryPolicy` 指数退避+上限+区分可/不可重试错误 |

### 防翻车清单 A–H 落地状态

> 依 `convention/AI应用开发通用防翻车原则与检查清单.md` 评估，M1–M3 已补齐。确定性闸门 100% 代码裁决；质量分仅可观测。

| 清单节 | 落地控制 | 代码位置 |
|--------|----------|----------|
| A 确定性裁决 | 双通道溯源 + `DeterministicGate`（Format/Fact/Logic + Reconciler），100% 程序化裁决 | `gate/gate.py`、`gate/reconciliation.py` |
| B 输入边界 | `InputValidator` 注入硬阻断（默认 `block_injection=True`）；工具回传亦过 `PromptInjectionDetector` 并清洗 | `security/validation.py`、`core/agent_loop.py` |
| C 最小权限/沙箱 | 工具调用受 `PermissionSet` 白名单；副作用工具（write/edit/bash）前置闸门前才放行 | `core/agent_loop.py`（`_SIDE_EFFECT_TOOLS`） |
| D 对账 | 双通道溯源；无来源结论在交付内容中强制隔离/标注（`Reconciler.redact`），并记 `recon:unsourced` finding | `gate/gate.py`、`gate/reconciliation.py` |
| E 超时/熔断 | Bash 工具 `start_new_session` + 超时 `os.killpg` 硬杀；LLM 客户端接入 `config.timeout` | `tools/builtins.py`、`llm/openai.py`、`llm/anthropic.py` |
| F 可观测 | `GateMetrics` 累计拦截率/失败分布，复用 `ReviewQueue.pending()` 暴露复核积压，`gate_metrics()` 可查询（注：当前仅内存快照，生产级需接入 OTel 管线；loop 侧效工具前置检查暂不计入指标） | `gate/metrics.py`、`sdk/harness.py` |
| G 复核防绕过 | `ReviewQueue.resolve()` 仅 human 可决 critical（`ERROR` 级发现）；非 critical 需显式 `allow_auto_resolve`；`actor` 为字符串参数、无身份校验，须由 API 层补强 | `review/queue.py` |
| H 状态一致 | redis 后端 Lua 原子 CAS（`write_if_version`）；authoritative 写受 `verifier` 限制（`source_agent=="harness"`，**仅 `strict=True` 时注入**，默认关则不校验）；review 队列经 `_backend.put` 直写（绕开 verifier，因自身 `source_agent=review_queue`） | `sdk/harness.py:582`、`state/__init__.py`、`state/redis_store.py` |

---

## Java SDK 示例

Java SDK 提供完整的 Orchestrator 实现，支持工作流编排和多 Agent 协调。

### WorkflowEngine

```java
import com.harness.orchestrator.WorkflowEngine;
import com.harness.orchestrator.WorkflowConfig;
import com.harness.orchestrator.WorkflowStep;
import com.harness.orchestrator.WorkflowResult;
import com.harness.orchestrator.ExecutionMode;
import com.harness.sdk.AgentHarness;

AgentHarness agent = new AgentHarness(config);
WorkflowEngine engine = new WorkflowEngine(agent);

// 创建工作流
WorkflowConfig workflow = new WorkflowConfig.Builder()
    .name("ci-pipeline")
    .step(new WorkflowStep.Builder()
        .name("lint")
        .goal("运行 ruff check 检查代码风格")
        .build())
    .step(new WorkflowStep.Builder()
        .name("test")
        .goal("运行 pytest 测试")
        .build())
    .step(new WorkflowStep.Builder()
        .name("analyze")
        .goal("分析代码质量并生成报告")
        .dependsOn("lint", "test")
        .build())
    .maxParallelSteps(3)
    .build();

// 执行工作流
WorkflowResult result = engine.execute(workflow).join();

System.out.println("状态: " + result.status());
System.out.println("耗时: " + result.durationSeconds() + "s");
```

### DependencyGraph

```java
import com.harness.orchestrator.DependencyGraph;
import java.util.List;

DependencyGraph graph = new DependencyGraph();

// 添加步骤
graph.addStep("lint", List.of());
graph.addStep("test", List.of());
graph.addStep("analyze", List.of("lint", "test"));

// 获取执行顺序（拓扑排序）
List<List<String>> order = graph.getExecutionOrder();
// [[lint, test], [analyze]] - lint 和 test 可并行，analyze 需等待

// 检测循环依赖
if (graph.hasCycle()) {
    throw new IllegalStateException("工作流包含循环依赖");
}
```

### TeamOrchestrator

```java
import com.harness.orchestrator.TeamOrchestrator;
import com.harness.orchestrator.TeamConfig;
import com.harness.orchestrator.AgentRole;
import com.harness.orchestrator.CoordinationMode;
import com.harness.orchestrator.TeamResult;

TeamConfig team = new TeamConfig.Builder()
    .name("dev-team")
    .description("开发团队")
    .role(new AgentRole.Builder()
        .name("analyzer")
        .description("代码分析专家")
        .skills(List.of("code-analysis"))
        .maxIterations(10)
        .build())
    .role(new AgentRole.Builder()
        .name("developer")
        .description("开发工程师")
        .skills(List.of("coding", "testing"))
        .maxIterations(20)
        .build())
    .coordinationMode(CoordinationMode.SEQUENTIAL)
    .build();

TeamOrchestrator orchestrator = new TeamOrchestrator(agent);
TeamResult result = orchestrator.execute(team, "实现用户登录功能").join();

for (Map.Entry<String, GoalResult> entry : result.agentResults().entrySet()) {
    System.out.println(entry.getKey() + ": " + entry.getValue().status());
}
```

### ExecutionMonitor

```java
import com.harness.orchestrator.ExecutionMonitor;
import com.harness.orchestrator.ExecutionMetric;

ExecutionMonitor monitor = new ExecutionMonitor();

// 记录开始
monitor.recordStart("ci-pipeline");

// 记录步骤完成
monitor.recordStep("ci-pipeline", "lint", StepStatus.SUCCESS, 5.2);
monitor.recordStep("ci-pipeline", "test", StepStatus.SUCCESS, 15.8);

// 获取指标
ExecutionMetric metrics = monitor.getMetrics("ci-pipeline");
System.out.println("总步骤: " + metrics.totalSteps());
System.out.println("完成: " + metrics.completedSteps());
System.out.println("失败: " + metrics.failedSteps());
System.out.println("耗时: " + metrics.durationSeconds() + "s");
```

### WorkflowStatus 枚举

```java
public enum WorkflowStatus {
    PENDING,     // 等待执行
    RUNNING,     // 执行中
    COMPLETED,   // 已完成
    FAILED,      // 失败
    CANCELLED    // 已取消
}
```

### StepStatus 枚举

```java
public enum StepStatus {
    PENDING,    // 等待执行
    RUNNING,    // 执行中
    SUCCESS,    // 成功
    FAILED,     // 失败
    SKIPPED     // 跳过
}
```

## 下一步

- [10-loop-engineering.md](./10-loop-engineering.md) - Loop Engineering 总览
- [11-worktrees.md](./11-worktrees.md) - 并行隔离执行
- [12-connectors.md](./12-connectors.md) - 外部系统集成
- [01-overview.md](./01-overview.md) - 项目概述与架构总览（含风险分级矩阵）
- [08-security.md](./08-security.md) - 安全系统详解（strict 预设与共享状态治理）
- [../../convention/AI应用开发通用防翻车原则与检查清单.md](../../convention/AI应用开发通用防翻车原则与检查清单.md) - 防翻车原则与清单（H 节多 Agent 专属）

---

## 治理層補強記錄（M5-D）：claim 抽取中文邊界修復

> 状态：✅ 已落地（设计稿 + 实现 + 单测）
> 背景：M4 执行中发现 `FactGrounder._CLAIM_PATTERN` 数字前要求 `\b` 词边界，
> 而中文无空格，导致「营收5亿元」整段不被识别为事实性结论，D2/D3 隔离在
> 中文语境下形同虚设（仅「-3亿元」因前面是 `-` 才命中）。

### 修复方案
- `_CLAIM_PATTERN`（`gate/validators.py`）：数字前边界由 `\b` 改为
  `(?<![\dA-Za-z])`（禁止数字/ASCII 字母在数前，但允许 CJK 在数前）；
  数字后由尾 `\b` 改为 `(?!\d)`（禁止数字半截，但允许 CJK/标点在后）。
  补充 `万元` 单位。
- 覆盖验证：CJK 上下文（营收5亿元、5000万元、2024年01月01日、Q1 2024）、
  标识符排除（abc5亿元 不命中）、隔離子串匹配（2024年01月01 核心已隔離）。

### 技术规范符合性自检

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·输入校验与防注入 | 满足 | claim 抽取为确定性正则，无 LLM 参与；边界放宽为纯正则改造，不引入注入面 |
| 02-设计·输出编码 | 满足 | 仍复用 `Reconciler.redact` 的 `[已隔离:无溯源]` 标记，PII 不落盘 |
| 03-日志·不打敏感信息 | 满足 | claim 仅用于溯源比对，审计日志不打印原始结论全文 |
| 03-日志·结构化与级别 | 满足 | 复用既有 gate findings / verdict 结构 |
| 04-并发·资源释放 | 满足 | 纯函数正则，无资源持有 |
| 04-并发·避免竞态 | 满足 | `FactGrounder` 为无状态纯逻辑 |
| 04-并发·写幂等 | 满足 | 抽取为只读，不影响写路径 |
| A 确定性裁决 | 满足 | 中文结论现在进入溯源/隔离流程；仍为 100% 程序化裁决 |
| D 对账 | 满足 | 无来源中文结论现在被强制隔离/标注（修复前漏检） |
| 残余风险 | 部分满足 | 全角数字（２０２４）、数字间插空格（2 0 2 4）、HTML 实体（&#50;024）仍可能绕过抽取——后续可加归一化层（列入 M5 跟进项，非本次范围） |

---

## 治理層補強記錄（M5-C）：BashTool 命令危險度接 LightweightSandbox

> 状态：✅ 已落地（设计稿 + 实现 + 单测）
> 背景：M4 多角度分析中 C 项——`BashTool` 仅有 4 条 `BLOCKED_COMMANDS` +
> `PermissionSet` 放行，对 `curl|bash`、`> /etc/...`、`chmod -R 777`、fork bomb
> 等明显危险命令缺乏覆盖；既有的 `LightweightSandbox`（`security/sandbox.py`）已有
> 更全的拦截规则却未被 BashTool 复用。

### 修复方案
- `tools/builtins.py::BashTool.execute`：在 `BLOCKED_COMMANDS` 与 `PermissionSet`
  检查之后，新增一层 `LightweightSandbox().validate_command(command)` 校验
  （懒导入，避免与 `security` 形成模块级循环依赖）。命中即返回
  `ToolResult(success=False, error="Sandbox blocked command: <reason>")`。
- `security/sandbox.py::LightweightSandbox.DEFAULT_BLOCKED_PATTERNS`：补强
  pipe-to-shell 检测，新增 `| bash` / `|bash` / `| sh` / `|sh`（覆盖 URL 居中时的
  `curl ... | bash` 场景，原 `curl | bash` 子串匹配对带参命令失效）。
- 该层属于「韧性层」，始终开启，与 `strict` 开关无关（命令安全是基线要求）。

### 技术规范符合性自检

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·输入校验与防注入 | 满足 | 危险命令为确定性子串/路径黑名单拦截，无 LLM 参与；懒导入不扩大攻击面 |
| 02-代码·最小权限 | 满足 | 叠加 `BLOCKED_COMMANDS` + `PermissionSet` + Sandbox 三层防御；沙箱拦截优先级最高 |
| 02-代码·命令执行 | 满足 | 仍走既有 `start_new_session` + `killpg` 硬杀路径（E3），与命令校验正交 |
| 03-日志 | 满足 | 仅回传结构化 `error`，不打印命令输出敏感内容 |
| 04-并发·资源释放 | 满足 | 校验为纯函数，失败即返回，不泄漏子进程 |
| 04-并发·避免竞态 | 满足 | 每次调用独立校验，无共享可变状态 |
| C 命令危險度 | 满足 | `curl\|bash`/`wget\|bash`/`> /etc/`/`chmod -R 777`/fork bomb/危险路径现被拦截 |
| 残余风险 | 部分满足 | 拦截基于子串黑名单，变体（如 `cu\rl`、`curl$'\x20'`、base64 管道）仍可绕过；MCP 工具与 `update_core_memory` 写 MEMORY.md 的危險度不在此层（属工具权限治理，列 M5 跟进项） |

---

## 治理層補強記錄（M5-B）：注入檢測語義化（中文/混淆）

> 状态：✅ 已落地（设计稿 + 实现 + 单测）
> 背景：M4 多角度分析中 B 项——`PromptInjectionDetector` 仅英文显形词
>（`ignore previous instructions` 等），中文注入（忽略以上指令、假装你是…）
> 与零宽字符拼接（`ign​ore`）可绕过。

### 修复方案
- `security/validation.py::PromptInjectionDetector.INJECTION_PATTERNS`：新增中文覆盖——
  指令覆盖（忽略/无视/忘掉…指令、限制、规则、安全）、系统提示泄露（显示/你的系统提示…）、
  越狱（假装你是/假设你是/扮演/越狱，以及「现在你是X」仅当 X 指向解除限制/规则/安全）、
  危险指令（删除所有文件/格式化/运行脚本/解密后执行）。
- 新增 `._normalize()`：检测前剔除零宽字符（U+200B/200C/200D/2060/FEFF/00AD），
  同时覆盖 `detect()` 与 `sanitize()`，破解零宽拼接绕过。
- 越狱「现在你是」模式收紧：要求后接 0–10 字内含「限制/规则/安全/约束」等绕過名詞，
  避免把「现在你是我的好朋友」等正常表述误报（已单测验证）。

### 技术规范符合性自检

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·输入校验与防注入 | 满足 | 注入检测为确定性正则 + 零宽归一化，无 LLM 参与；`block_injection=True` 默认硬阻断（B1） |
| 02-代码·防注入 | 满足 | 归一化在 `detect`/`sanitize` 两路径均生效，外部/工具回传内容经此清洗（P1-2） |
| 03-日志 | 满足 | 仅记录命中模式名，不打印原始注入负载全文 |
| 04-并发 | 满足 | 检测器无状态纯函数（除 `custom_patterns`），线程安全 |
| B 注入識別 | 满足 | 中文显形注入 + 零宽混淆现被拦截；英文集补充 developer mode / DAN / decode-and-run |
| 残余风险 | 部分满足 | 仍属关键字启发式：语义等价改写（「请把上面那条规矩忘掉吧」用词偏移）、base64 整段编码、同义隐写仍可绕过；彻底防御需语义级分类器或上下文校验，列 M5 跟进项 |

---

## 治理層補強記錄（M5-F）：gate 指标接入 OTel 导出

> 状态：✅ 已落地（设计稿 + 实现 + 单测）
> 背景：M4 多角度分析中 F 项——`GateMetrics` 仅进程内内存快照，无 OTel / 外部
> 导出；既有的 `core/observability.py` 只配置了 **trace**，`MeterProvider` 缺失。

### 修复方案
- 复用既有 `ObservabilityManager`：新增 `ObservabilityConfig.export_metrics`，在
  `setup()` 内（当 `export_metrics` 为真）追加 `MeterProvider` + `PeriodicExportingMetricReader`
  （console / OTLP gRPC，复用同一 `otlp_endpoint`），并通过 `opentelemetry.metrics.set_meter_provider`
  注册全局 meter；`shutdown()` 一并关闭 meter provider。
- `core/observability.py` 暴露 `get_meter()`（全局），`ObservabilityManager.meter` 属性。
- `gate/metrics.py::GateMetrics`：新增 `configure_otel(meter=None)`，绑定后
  `record()` 向 OTel 计数器 `harness.gate.checks` / `harness.gate.blocked` /
  `harness.gate.findings`（带 `type`/`severity` 属性）推送；未绑定时纯内存。
- `sdk/harness.py`：创建 `GateMetrics` 后调用 `configure_otel()`，自动接上已配置的
  全局 meter（无 OTel 或未开启 `export_metrics` 时为 no-op，零迁移）。
- 依赖经 `pip install harness-sdk[observability]` 可选安装；未安装时 `OTEL_AVAILABLE=False`，
  指标仍内存可用（韧性层），不强制外部依赖。

### 技术规范符合性自检

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·可观测 | 满足 | 拦截率/失败分布/复核积压（F 项三指标）现可经 OTel 导出至 Jaeger/Datadog/Langfuse 等 |
| 02-代码·无强依赖 | 满足 | OTel 懒导入、可选 extra；缺失时内存快照兜底，不影响主流程 |
| 03-日志·不打敏感信息 | 满足 | 导出指标仅计数器与 `type/severity` 枚举属性，不含结论/PII 原文 |
| 03-日志·结构化与级别 | 满足 | OTel 属性为结构化键值；setup 失败仅 `logger.error`，不中断 |
| 04-并发·资源释放 | 满足 | `PeriodicExportingMetricReader` + `shutdown()` 关闭导出器，避免句柄泄漏 |
| 04-并发·线程安全 | 满足 | `record` 为计数器递增 + OTel 原子 `add`，无共享可变结构竞争 |
| F 可观测 | 满足 | gate 指标从「内存快照」升级为可导出；trace 已由既有 `ObservabilityManager` 覆盖 |
| 残余风险 | 部分满足 | 仅 **metric** 导出（计数级），尚未为「取消/硬杀/隔离」单步打 **trace span**；convention 03 要求关键路径带 trace ID，列 M5 跟进项（H 同批可补 span） |

---

## 治理層補強記錄（M5-G）：actor 身份校验 + 升级流接 gate

> 状态：✅ 已落地（设计稿 + 实现 + 单测）
> 背景：M4 多角度分析中 G 项——`ReviewQueue.resolve()` 用 `actor != "human"` 字符串
> 比对，agent 可伪造 `actor="human"` 释放关键隔离项；且 gate 拦截后**没有**自动升级
> 到复核队列的显式路径（升级流断链）。

### 修复方案
- `review/queue.py::ReviewQueue`：
  - 新增 `human_actors: set[str]`（默认 `{"human"}`，保持历史行为）与可选
    `verify_actor: Callable[[str], bool]`。`resolve()` 关键项现在要求
    `actor ∈ human_actors`，且（当配置 `verify_actor` 时）须 `verify_actor(actor)` 为真。
    默认 `{"human"}` 下 G3 守卫不变；高风险部署可把允许集钉成具体身份
    （`{"human:approver-alice"}`），使通用 `human` 伪造被拒。
  - 新增 `escalate_from_verdict(verdict, *, content, source)`：仅当 verdict 含
    ERROR 级 finding（关键隔离）时构造 `ReviewItem` 并 `submit`，返回 item_id；
    仅 warning/info 不升级（返回 `None`）。
- `sdk/harness.py::_apply_gate`：gate 拦截（`not passed`）且复核队列存在时，调用
  `escalate_from_verdict` 自动升级；升级异常被吞掉并 `logger.warning`，绝不中断
  已隔离的交付（升级是旁路副作用）。

### 技术规范符合性自检

| 维度 | 结论 | 说明 / 风险+缓解 |
|------|------|------------------|
| 02-设计·身份/授权 | 满足 | 关键项释放改为「允许集 + 可选运行时校验」，不再信赖裸字符串；默认 `{"human"}` 零迁移 |
| 02-代码·最小授权 | 满足 | 自动化 actor 默认无法释放关键项；非关键项仍需 `allow_auto_resolve` 显式放行 |
| 02-代码·写入幂等/隔离 | 满足 | `escalate_from_verdict` 经既有 `submit` → 持久化路径，与现有机制一致 |
| 03-日志·审计 | 满足 | `resolved_by` 记录真实 actor 串；升级 `logger.info` 含 source/item_id，供审计 |
| 03-日志·不打敏感 | 满足 | 仅记录 finding 枚举/消息与 item_id，不打印结论全文 |
| 04-并发·资源释放 | 满足 | 复用 `ReviewQueue` 既有 `asyncio.Lock` 与 store 同步桥，无新增资源 |
| 04-并发·避免竞态 | 满足 | 升级在 `submit` 临界区外（先判定再 submit），不变更既有锁粒度 |
| G 身份/升级 | 满足 | actor 伪造被允许集挡下；gate→复核升级流接通 |
| 残余风险 | 部分满足 | 默认 `human_actors={"human"}` 仍接受任何 caller 自报 `human`（无真认证后端）；彻底防伪造需接入真实身份提供方并配置 `verify_actor`，列 M5 跟进项；跨进程 actor 校验依赖部署侧 store 一致性 |
