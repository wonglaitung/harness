# 治理手工演练（governance playground）

> **一句话**：用 Mock LLM 串出工具调用序列，不联网、不依赖真实模型，手动观察治理的
> 「放行 / 拒绝 / 审批 / 熔断 / 留痕」全过程。

- **自动化断言**在 `packages/sdk/tests/{unit,integration}/test_governance*.py`；
  本目录只负责**手动演练与演示**，不参与 CI（`pytest` 的 `testpaths` 只含 `tests/`）。
- **设计依据**：`packages/sdk/docs/21-hkma-agentic-governance.md`
  （§7 执行网关、§8 步骤链、§10 Kill Switch、§11 事件日志、§13.4 CLI）。

## 目录

1. [快速开始](#1-快速开始)
2. [理解设置：为什么必须有治理块](#2-理解设置为什么必须有治理块)
3. [五个场景](#3-五个场景)
4. [操作手册：审批 / Kill Switch / 留痕](#4-操作手册审批--kill-switch--留痕)
5. [扩展与排错](#5-扩展与排错)

---

## 1. 快速开始

### 1.1 环境

用仓库虚拟环境的 Python（系统 Python 3.10 可能缺 `tiktoken`）：

```bash
cd packages/sdk
pip install -e .          # 或者直接用 /data/harness/.venv/bin/python
```

装包后会生成 `harness` 命令，可直接运行 `harness governance ...`；不想装包时，
在 `packages/sdk` 目录下用模块方式运行：`PYTHONPATH=src python -m harness.cli governance ...`
（本仓库的 `.venv` 已暴露 `src`，可省略 `PYTHONPATH=src`）。下文统一写
`python -m harness.cli`，两者等价。

### 1.2 跑一次

```bash
cd packages/sdk/examples/governance_playground
python run.py happy
```

预期输出（节选）：

```
治理策略：agent_id=report-assembler tools=['aml_screening:run', ...] steps=['collect_data', 'aml_check', 'draft_report'] material=True
技能文件：skills/report.md

=== 场景：happy ===
  [tool] core_banking_api:read_only
  [tool] aml_screening:run
  [tool] report_writer:draft

run 结论：completed
```

### 1.3 目录结构

```
examples/governance_playground/
├── run.py                  # 场景入口（Mock LLM + 工具桩）
├── skills/                 # 被演练的技能（治理块写在 frontmatter）
│   ├── report.md           # report-assembler：collect_data → aml_check → draft_report
│   └── payment.md          # payment-agent：disburse（payment 强制审批 + 金额上限）
└── .work/                  # 运行时工作区（已 gitignore）
    ├── .harness/skills/    # run.py 从 skills/ 复制过来
    └── home/               # 隔离的 HOME：审批 / 控制面 / 审计都落这里
```

### 1.4 隔离：不会碰你的 `~/.harness`

`run.py` 在**导入 harness 之前**切换 CWD 与 `HOME`（技能加载器只读
`./.harness/skills` 与 `~/.harness/skills`，且在导入时求值）：

```python
# run.py:49 _prepare_workspace()
for source in sorted((BASE / "skills").glob("*.md")):
    shutil.copy2(source, WORK / ".harness" / "skills" / source.name)
os.chdir(WORK)                    # 让 ./.harness/skills 指向 .work
os.environ["HOME"] = str(HOME)    # 隔离家目录
```

所以运行时数据全部落在 `.work/`；同时另一个终端的 CLI 必须带**同一个 HOME**：

```bash
HOME=$PWD/.work/home python -m harness.cli governance status report-assembler
```

---

## 2. 理解设置：为什么必须有治理块

### 2.1 三件事让治理块成为硬门槛

1. **打开开关 + 指定身份**（`run.py:194-199`）

   ```python
   HarnessConfig(
       strict=True,                              # 打开治理
       governance_agent_id=AGENTS[scenario],     # 部署方固定身份
   )
   ```

   - `strict=True` → `_governance_enabled()` 为真（`harness.py:550`）；
   - 缺 `governance_agent_id` → `RuntimeError`（fail-closed）。

2. **让技能被加载器发现**：见 [1.4](#14-隔离不会碰你的-harness) 的
   `_prepare_workspace()`。`DEFAULT_SKILL_PATHS` 在导入时求值
   （`loader.py:21-24`），所以「复制技能 + 切 CWD」必须发生在导入 harness 之前。

3. **技能 frontmatter 的 `governance.agent_id` 与身份一致**

   ```yaml
   governance:
     agent_id: report-assembler   # ← 必须等于 AGENTS[scenario]
     tools: [...]                 # ← 运行期白名单
     workflow: { steps: [...] }   # ← 步骤链
   ```

### 2.2 场景 → 治理身份（`AGENTS` 映射）

`run.py` 用一张字典把「场景名」映射到「治理身份」（`agent_id`）：

```python
# run.py:33-38
AGENTS = {
    "happy": "report-assembler",
    "skip": "report-assembler",
    "missing_output": "report-assembler",
    "constraint": "payment-agent",
    "approval": "payment-agent",
}

scenario = sys.argv[1] if len(sys.argv) > 1 else "happy"
governance_agent_id=AGENTS[scenario]          # run.py:198
```

| 命令 | `scenario` | `AGENTS[scenario]` | 生效的治理块 |
|---|---|---|---|
| `python run.py happy` | `happy` | `report-assembler` | `skills/report.md` |
| `python run.py skip` | `skip` | `report-assembler` | `skills/report.md` |
| `python run.py missing_output` | `missing_output` | `report-assembler` | `skills/report.md` |
| `python run.py constraint` | `constraint` | `payment-agent` | `skills/payment.md` |
| `python run.py approval` | `approval` | `payment-agent` | `skills/payment.md` |

身份不匹配的治理块会被**静默忽略**（不报错、不合并）：跑 `approval` 时身份是
`payment-agent`，`report.md` 的块（`agent_id: report-assembler`）不参与本次装配。
这正是「提示词注入不能改变授权集」的实现方式（§6.4.1）。

> 传未知场景会先被 `SCENARIOS` 校验拦下（`SystemExit`），不会走到 `KeyError`。

### 2.3 装配时机与失败模式

- 构造 `AgentHarness` 时只读 **Level 1 元数据**（frontmatter，含 `governance`），
  不编译；
- 首次 `governance_policy()`（`run.py:206` 显式调用；`run()` 内部也会自动调用，
  `harness.py:1259`）触发 `_build_governance()`：按 `agent_id` 过滤块 → 跑 29 条
  校验（含规则 29：块 `tools` ⊆ 技能 `tools.allowed`）→ 核对工具代码声明 →
  产出 `PolicySnapshot`；
- 运行时把网关注入 `AgentLoop` 与 `ToolExecutor`，每个 run 建 `RunContext`，
  工具调用走 11 步流水线。

| 情况 | 结果 |
|---|---|
| `governance_agent_id` 没写 | `RuntimeError: strict=True 需要指定治理身份` |
| 身份对不上任何块（或块被删） | `治理装配失败 … 没有可用治理块（治理块缺失即拒绝，§4.3）` |
| 块内容不合法（字段/引用/表达式/占位符） | 编译期拒绝，报 `规则 N｜field：message` |
| 工具代码声明与块声明冲突 | 编译期拒绝（`治理声明冲突`） |

想亲手验证（都不用改仓库代码）：

```bash
# a) 把 run.py 的 governance_agent_id 改成 "no-such-agent" → 启动失败
# b) 删掉 skills/report.md 的 governance 块 → 启动失败
# c) 块内容不合法 → 离线检查同款规则
python -m harness.cli governance check skills/report.md
```

### 2.4 一般规则：什么情况下技能必须有治理块

判定口诀：**只要部署打开了治理，就至少需要一份「身份匹配」的治理块；具体到每个
技能，凡是它的工具要被放行的，就必须被某份治理块声明。**

| 配置 | 是否启用治理 |
|---|---|
| `HarnessConfig(strict=True)` | ✅ |
| `HarnessConfig(governance_enabled=True)`（即使 `strict=False`） | ✅（显式覆盖） |
| `HARNESS_STRICT=1` + `HarnessConfig.from_env()` | ✅ |
| `HARNESS_REQUIRE_STRICT=1` 且 `strict=False` | ❌ 启动即报错（强制要求开） |
| 默认（`strict=False`、`governance_enabled` 未设） | ❌ 零迁移，不需要治理块 |

打开之后：

1. 必须指定 `governance_agent_id`；
2. 至少一份**被发现的**技能要带治理块且 `agent_id` 与之一致（否则启动失败）；
3. **工具必须在治理块 `tools` 里声明**（运行期白名单；多份同身份块取交集）。
   没被声明的工具在 strict 下调用会被拒，表现为「工具不可用」。

具体到单个技能：

- **必须有**：它会调用工具，且这些工具要在治理下被放行（通常就是它自己的块）。
- **可以没有**：纯提示词、不调工具的技能；或它的工具已由同 `agent_id` 的另一份
  治理块声明。
- **写了但身份不符**：被静默忽略（见 [2.2](#22-场景--治理身份agents-映射)）。

> **合规层面**：项目规约要求 High 风险 / 金融级场景必须开 `strict`，因此这些场景
> 必须有治理块。需要 payment/destructive 强制审批、步骤链、Kill Switch、事件留痕
> 时也必须开治理，否则这些机制不生效（没有 policy、`control` 不会注入）。

---

## 3. 五个场景

### 3.1 命令

```bash
cd packages/sdk/examples/governance_playground

python run.py happy             # 三步依次执行 → completed
python run.py skip              # 直接出报告（跳步）→ draft 被拒，工具不执行
python run.py constraint        # 金额 9,999,999 → 被业务约束拒绝
python run.py approval          # payment → 阻塞，等待人工审批
AML_NO_OUTPUT=1 python run.py missing_output   # AML 未产出 aml_hit → step failure
```

### 3.2 对照表

| 场景 | 使用的技能 / 治理块 | 系统行为 | 去哪看证据 |
|---|---|---|---|
| `happy` | `skills/report.md`（`report-assembler`） | 三个工具依次执行，step 依次 `success` | 事件：`tool_call_decision(allow)`、`tool_call_result` |
| `skip` | `skills/report.md`（`report-assembler`） | `报告草稿` 在 `collect_data` 之前调用 → 拒绝 | 事件：`decision=deny`、`rule=步骤游标`、`signal=step_violations` |
| `constraint` | `skills/payment.md`（`payment-agent`） | 超过 `max_amount` → 拒绝 | 事件：`reason="amount: 金额超出上限"`（不记实际值） |
| `approval` | `skills/payment.md`（`payment-agent`） | 调用阻塞，请求先落盘再等待 | `.work/home/.harness/control/approvals/<run_id>/apr-0000.json` |
| `missing_output` | `skills/report.md`（`report-assembler`） | 声明了 `aml_hit` 却没产出 → step `failure` → 后续不可达 | 事件：`tool_call_result` 的 `outcome=failure` |

### 3.3 两份技能各自覆盖的治理能力

**`skills/report.md` —— `report-assembler`**（`happy` / `skip` / `missing_output`）

- 步骤链：`collect_data → aml_check → draft_report`，工具归属唯一；
- `aml_screening:run` 声明产出 `aml_hit`（条件判断的唯一合法来源）；
- `report_writer:draft` 为 `idempotent: false`（重入会被拒）；
- 覆盖：正常顺序放行、**跳步拒绝**（`skip`）、**产出缺失判 failure**（`missing_output`）。

**`skills/payment.md` —— `payment-agent`**（`constraint` / `approval`）

- 单步 `disburse` 绑定 `pay:transfer`；
- `capability: payment` → **强制人工审批**（治理块不可关闭，`approval_required_for`
  也为编译期规则 20/25 所需）；
- 业务约束：`amount_field=amount`、`max_amount=1_000_000`；
- 覆盖：**业务参数越界拒绝**（`constraint`）、**运行期审批阻塞/放行**（`approval`）。

> 想同时看到两份技能，跑完任一场景后查看 `.work/.harness/skills/`——`run.py`
> 会把 `skills/*.md` 原样复制过去。

---

## 4. 操作手册：审批 / Kill Switch / 留痕

### 4.1 审批（两个终端）

终端 1 跑起来后会停在等待：

```bash
cd packages/sdk/examples/governance_playground
python run.py approval
```

终端 2（**同一个 HOME**）批准或拒绝：

```bash
cd packages/sdk/examples/governance_playground

HOME=$PWD/.work/home python -m harness.cli governance approve apr-0000 --actor alice
# 或者
HOME=$PWD/.work/home python -m harness.cli governance reject  apr-0000 --actor bob --reason "额度不足"
```

`apr-0000` 里的 `args_hash` 是审批绑定的参数指纹：批准后若参数被改动，审批失效。
请求过期（默认 300 秒）后不可再批准，run 按拒绝处理。

### 4.2 Kill Switch

```bash
cd packages/sdk/examples/governance_playground

# 先停
HOME=$PWD/.work/home python -m harness.cli governance suspend report-assembler --reason "手工测试"
python run.py happy
# run 结论：interrupted；错误：Kill Switch：状态 suspended：手工测试（且未调用 LLM）

# 查看与恢复
HOME=$PWD/.work/home python -m harness.cli governance status report-assembler
HOME=$PWD/.work/home python -m harness.cli governance resume report-assembler --reason "已复核"
```

运行中 suspend 也一样：下一个检查点（LLM 前 / 工具前 / 工具后）即停。

### 4.3 看留痕

```bash
cd packages/sdk/examples/governance_playground

# 事件日志（一次 run 用 run_id 贯穿）
tail -f .work/home/.harness/audit/governance/$(date +%Y%m%d)/*.jsonl

# 只看最近一次 run 的判定
tail -20 .work/home/.harness/audit/governance/$(date +%Y%m%d)/*.jsonl | jq -c 'select(.event|startswith("tool_call"))'

# 待审批请求
find .work/home/.harness/control/approvals -name "*.json" -exec cat {} \;

# 控制面状态（文件不存在 = active；文件损坏 = suspended）
cat .work/home/.harness/control/report-assembler.json
```

一条拒绝事件长这样：

```json
{"event":"tool_call_decision","decision":"deny","reason":"amount: 金额超出上限",
 "step":"disburse","gen_ai.tool.name":"pay:transfer","run_id":"..."}
```

---

## 5. 扩展与排错

### 5.1 自己改场景

- **自动 suspend**：在 `skills/report.md` 的 `limits` 里加
  `signal_thresholds: {step_violations: 1}`，再跑 `skip`，然后
  `governance status report-assembler` 会看到 `suspended`。
- **INCOMPLETE**：给末端 step 加 `if:`（使其不成立），末端被 `skipped` 时
  run 结论是 `incomplete`（不是 `completed`）。
- **路径越界**：给工具加 `path` 参数并传 `/etc/passwd`，会被
  `FileInputValidator` / `deny_paths` 拒绝。
- **校验治理块**：

  ```bash
  python -m harness.cli governance check skills/report.md
  # 把 capability 改成 destroy 再看输出：`file:line 规则 N｜field：message`，退出码 1
  ```

- **改 Mock 序列**：编辑 `run.py` 里 `_build_responses()`；工具桩在 `_make_tools()`。
  新工具必须在 strict 下声明 `capability` 与 `idempotent`，否则注册即被拒。
- **换身份/新增场景**：在 `run.py` 的 `SCENARIOS` / `AGENTS` / `SKILL_FILES` 三张
  表里同步加上，并给对应技能写治理块。

### 5.2 排错速查

| 现象 | 先查什么 |
|---|---|
| 启动即 `治理装配失败 … 没有可用治理块` | `governance_agent_id` 与技能 `governance.agent_id` 是否一致；技能是否在 `.work/.harness/skills/` |
| 工具调用被拒「不在治理块白名单内」 | 工具是否写进治理块 `tools`（多块取交集） |
| 工具注册即被拒 | 工具类是否声明 `capability` / `idempotent` |
| CLI 看不到待审批/控制状态 | CLI 的 `HOME` 是否与运行进程一致（`$PWD/.work/home`） |
| 改了技能却不生效 | `run.py` 每次运行会重新复制技能；确认改的是 `skills/` 而不是 `.work/` |

### 5.3 清理

```bash
rm -rf .work
```
