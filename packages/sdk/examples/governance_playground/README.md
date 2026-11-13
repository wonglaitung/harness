# 治理手工演练（governance playground）

这是**人工可操作**的治理验证环境：用 Mock LLM 串出工具调用序列，不联网、不依赖
真实模型，跑完能直接看到「放行 / 拒绝 / 审批 / 熔断 / 留痕」的全过程。

自动化断言在 `packages/sdk/tests/{unit,integration}/test_governance*.py`；本目录
只负责**手动演练与演示**，不参与 CI（`pytest` 的 `testpaths` 只含 `tests/`）。

设计依据：`docs/21-hkma-agentic-governance.md`（§7 执行网关、§8 步骤链、
§10 Kill Switch、§11 事件日志、§13.4 CLI）。

## 前置

用仓库虚拟环境的 Python（系统 Python 3.10 可能缺 `tiktoken`）：

```bash
cd packages/sdk
pip install -e .          # 或者直接用 /data/harness/.venv/bin/python
```

## 目录

```
examples/governance_playground/
├── run.py                  # 场景入口
├── skills/
│   ├── report.md           # report-assembler：collect_data → aml_check → draft_report
│   └── payment.md          # payment-agent：disburse（payment 强制审批 + 金额上限）
└── .work/                  # 运行时工作区（已 gitignore）
    ├── .harness/skills/    # 脚本从 skills/ 复制过来
    └── home/               # 隔离的 HOME：审批 / 控制面 / 审计都落这里
```

`run.py` 会在**导入 harness 之前**切换 CWD 与 `HOME`（技能加载器只读
`./.harness/skills` 与 `~/.harness/skills`，且在导入时求值）。因此不会读写你
真实的 `~/.harness`。

## 五个场景

```bash
cd packages/sdk/examples/governance_playground

python run.py happy             # 三步依次执行 → completed
python run.py skip              # 直接出报告（跳步）→ draft 被拒，工具不执行
python run.py constraint        # 金额 9,999,999 → 被业务约束拒绝
python run.py approval          # payment → 阻塞，等待人工审批
AML_NO_OUTPUT=1 python run.py missing_output   # AML 未产出 aml_hit → step failure
```

| 场景 | 系统行为 | 去哪看证据 |
|---|---|---|
| `happy` | 三个工具依次执行，step 依次 `success` | 事件：`tool_call_decision(allow)`、`tool_call_result` |
| `skip` | `报告草稿` 在 `collect_data` 之前调用 → 拒绝 | 事件：`decision=deny`、`rule=步骤游标`、`signal=step_violations` |
| `constraint` | 超过 `max_amount` → 拒绝 | 事件：`reason="amount: 金额超出上限"`（不记实际值） |
| `approval` | 调用阻塞，请求先落盘再等待 | `~/.harness/control/approvals/<run_id>/apr-0000.json` |
| `missing_output` | 声明了 `aml_hit` 却没产出 → step `failure` → 后续不可达 | 事件：`tool_call_result` 的 `outcome=failure` |

## 审批（两个终端）

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

## Kill Switch（两个终端 / 预置状态）

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

## 看留痕

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

## 自己改场景

- **自动 suspend**：在 `skills/report.md` 的 `limits` 里加
  `signal_thresholds: {step_violations: 1}`，再跑 `skip`，然后
  `governance status report-assembler` 会看到 `suspended`。
- **INCOMPLETE**：给末端 step 加 `if:`（使其不成立），末端被 `skipped` 时
  run 结论是 `incomplete`（不是 `completed`）。
- **路径越界**：给工具加 `path` 参数并传 `/etc/passwd`，会被
  `FileInputValidator` / `deny_paths` 拒绝。
- **校验治理块**：

  ```bash
  HOME=$PWD/.work/home python -m harness.cli governance check skills/report.md
  # 把 capability 改成 destroy 再看输出：`file:line 规则 N｜field：message`，退出码 1
  ```

- **改 Mock 序列**：编辑 `run.py` 里 `_build_responses()`；工具桩在 `_make_tools()`。
  新工具必须在 strict 下声明 `capability` 与 `idempotent`，否则注册即被拒。

## 清理

```bash
rm -rf .work
```
