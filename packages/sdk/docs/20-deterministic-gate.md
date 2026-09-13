# Deterministic Gate 确定性闸门

> LLM 只产出候选内容，确定性代码 100% 裁决是否交付。

---

## 1. 概述

LLM 输出有三类固有风险：

| 风险 | 例子 | 传统方案 |
|---|---|---|
| **格式缺陷** | 空内容、代码围栏未闭合 | 人工 review |
| **事实无溯源** | "营收增长 25%"但数据源里没有 | RAG + 人工核对 |
| **逻辑不一致** | 数字求和不对、自相矛盾 | 单元测试（但 LLM 输出不是代码） |

确定性闸门用**纯代码**对这三个维度逐一校验，无需 LLM 参与。

**核心原则**：LLM 永远不决定"能不能发"，只有代码说了算。

---

## 2. 三层验证架构

```
LLM 输出候选内容
       │
       ▼
┌─────────────────────────────────────────┐
│  Layer 1: FormatValidator (格式校验)     │
│  - 空内容? → ERROR                      │
│  - 代码围栏未闭合? → WARNING            │
│  - 模型校验失败? → ERROR                │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Layer 2: FactGrounder (事实溯源)        │
│  - 提取事实声明 (数字、日期、百分比)      │
│  - 双通道溯源:                           │
│    Channel A: 工具调用记录自动采集        │
│    Channel B: 手动传入 sources           │
│  - 无源声明 → ERROR (可配置为 WARNING)   │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Layer 3: LogicReconciler (逻辑校验)     │
│  - 用户自定义规则 (函数或声明式)          │
│  - 规则失败 → WARNING (不阻断)           │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Reconciler (交付前调和)                  │
│  - 交叉核验所有声明 vs 溯源              │
│  - 无溯源声明 → 替换为 [已隔离:无溯源]   │
│  - 全部失败 → 隔离整个内容               │
└─────────────────────────────────────────┘
       │
       ▼
   交付内容 (redacted)
```

### 2.1 FormatValidator

校验输出格式完整性：

| 检查项 | 严重级别 | 说明 |
|---|---|---|
| 空内容 / 纯空白 | ERROR `fmt:empty` | 交付内容为空 |
| 代码围栏 ``` 奇数个 | WARNING `fmt:code-fence` | 围栏未闭合 |
| Pydantic 模型校验失败 | ERROR `fmt:model` | 结构化输出不符合 schema |

### 2.2 FactGrounder

事实溯源是 Gate 的核心能力。提取内容中的事实声明，校验是否有数据源支撑。

**声明提取规则**（正则匹配）：
- 数字 + 单位：`25%`、`1.2 万元`、`300 kg`、`USD 5000`
- 日期：`2024-01-15`、`2024/03/20`、`2024年Q1`
- 季度标签：`Q1 2024`、`FY2024`

**文本归一化**（防混淆）：
- NFKC 全角→半角（`２５％` → `25%`）
- 去除数字内空格（`1 2 3` → `123`）
- HTML 实体解码（`&#37;` → `%`）

**双通道溯源**：

| Channel | 来源 | 自动/手动 |
|---|---|---|
| A | 工具调用记录（`read()`、`bash()` 等） | 自动采集 |
| B | `sources=` 参数手动传入 | 手动 |

**溯源匹配**：声明作为 needle 在 sources 中做 haystack 搜索（最长 40 字符子串），匹配即视为有源。

### 2.3 LogicReconciler

执行用户自定义的业务规则。规则是纯函数 `(content, sources) -> list[GateFinding]`。

规则失败不会阻断 Gate（try/except 包裹），而是产生 WARNING `logic:rule-N-error`。

### 2.4 Reconciler

交付前的最后一道防线：

1. 交叉核验所有事实声明 vs 溯源集合
2. 无溯源声明 → 替换为 `[已隔离:无溯源]`
3. 如果全部内容不可交付 → 硬隔离：`[内容未通过确定性闸门，已隔离，不交付原始内容]`

---

## 3. 声明式规则

无需写代码，用 JSON/YAML 定义业务规则。

### 3.1 四种规则类型

| Kind | 说明 | 参数 |
|---|---|---|
| `numeric_sum` | A ≈ B₁ + B₂ + ... (容差内) | `left`, `rights`, `tolerance` |
| `equality` | A == B | `left`, `right` |
| `range` | min ≤ field ≤ max | `field`, `min`, `max` |
| `regex_present` | 内容匹配正则 | `pattern` |

### 3.2 JSON 示例

```json
[
  {
    "kind": "numeric_sum",
    "id": "revenue-check",
    "left": "营收合计",
    "rights": ["产品收入", "服务收入"],
    "tolerance": 0.01,
    "severity": "error",
    "message": "营收合计应等于产品收入+服务收入"
  },
  {
    "kind": "equality",
    "id": "headcount-check",
    "left": "员工总数",
    "right": "在职人数",
    "severity": "warning"
  },
  {
    "kind": "range",
    "id": "growth-range",
    "field": "增长率",
    "min": -50,
    "max": 200,
    "severity": "error",
    "message": "增长率应在合理范围内"
  },
  {
    "kind": "regex_present",
    "id": "disclaimer-required",
    "pattern": "免责声明|风险提示",
    "severity": "warning",
    "message": "交付内容应包含免责声明"
  }
]
```

### 3.3 加载方式

```python
from harness import AgentHarness, GateConfig

# JSON 文件
agent = AgentHarness(
    model="gpt-4o",
    gate=GateConfig(rules_path="rules.json"),
)

# 也可以混合使用声明式 + Python 函数
from harness.gate import GateFinding, GateSeverity

def my_rule(content: str, sources: list[str]) -> list[GateFinding]:
    if "机密" in content and not sources:
        return [GateFinding(id="custom:secret", type="logic", severity=GateSeverity.ERROR, message="机密内容必须有溯源")]
    return []

agent = AgentHarness(
    model="gpt-4o",
    gate=GateConfig(
        rules_path="rules.json",
        rules=[my_rule],
    ),
)
```

**值提取**：先尝试 JSON 解析内容，再回退到带标签的数字提取（如"资产总计 1234"提取 1234）。

---

## 4. 事实溯源机制

### 4.1 双通道工作流

```
Channel A (自动采集)                    Channel B (手动传入)
┌──────────────────┐                   ┌──────────────────┐
│ 工具调用记录自动  │                   │ sources=[        │
│ 采集为溯源:       │                   │   "Q1_report.pdf"│
│ ["read(file1)",  │                   │   "db_query.sql" │
│  "bash(grep)"]   │                   │ ]                │
└──────────────────┘                   └──────────────────┘
         │                                      │
         └──────────────┬───────────────────────┘
                        ▼
              FactGrounder 双通道校验
              ┌────────────────────────┐
              │ "营收增长 25%"         │
              │  → 源文件中有 "25%"?   │
              │  → YES → 通过          │
              │  → NO  → WARNING       │
              └────────────────────────┘
```

### 4.2 代码示例

```python
from harness import AgentHarness

agent = AgentHarness(model="gpt-4o", strict=True)

# Channel A 自动生效 — 工具调用记录自动作为溯源
result = agent.run("读取 Q1_report.xlsx 并总结关键数据")

# Channel B 手动传入 — 通过 sources 参数
result = agent.run(
    "根据以下数据生成分析报告",
    sources=["Q1_report.xlsx", "database_export.csv"],
)

# 查看溯源报告
print(result.reconciliation_report)
# {
#   "checked_claims": 12,
#   "sourced_claims": 10,
#   "unsourced_claims": 2,
#   "source_count": 2
# }
```

---

## 5. 交付强制机制

### 5.1 三种交付路径

| Gate 结果 | 交付行为 |
|---|---|
| `passed=True` | 原文交付（无溯源声明被标记但不阻断） |
| `passed=False` + 有可隔离内容 | 红线隔离后交付（`[已隔离:无溯源]`） |
| `passed=False` + 全部不可交付 | 硬隔离：`[内容未通过确定性闸门，已隔离，不交付原始内容]` |

### 5.2 关键字段

```python
result = agent.run("分析财报")

result.gate_verdict            # GateVerdict (passed, findings, ...)
result.delivered_content        # 经 redact 后的安全内容
result.final_response           # 同 delivered_content
result.reconciliation_report    # 溯源核验报告
```

**注意**：`final_response` 和 `delivered_content` 始终是 Gate 调和后的内容，原始 LLM 输出不会直接交付。

---

## 6. 治理率指标

### 6.1 三个核心比率

| 指标 | 公式 | 含义 | 健康值 |
|---|---|---|---|
| **隔离率** `isolation_rate` | `blocked / checks` | 多少比例的输出被阻断/隔离了 | 越低越好（但不能为 0） |
| **溯源覆盖率** `coverage_rate` | `sourced_claims / total_claims` | 多少比例的事实声明有来源支撑 | 越高越好 |
| **事实锚定率** `grounding_rate` | `1 - (unsourced_claims / total_claims)` | 与覆盖率互补，视角相反 | 越高越好 |

### 6.2 实际含义

```
Agent 跑了 100 次，产出 500 条事实声明:

checks:          100          # 总调用次数
passed:           92          # 通过 Gate 的次数
blocked:           8          # 被隔离的次数

total_claims:    500          # 总事实声明数
sourced_claims:  460          # 有溯源支撑的声明
unsourced_claims: 40          # 无溯源的声明

isolation_rate:  0.08         # 8% 的输出被隔离
coverage_rate:   0.92         # 92% 的声明有来源
grounding_rate:  0.92         # 同上
```

**解读**：
- `isolation_rate=8%` — 有 8 次输出因格式/事实/逻辑问题被拦截，合理范围
- `coverage_rate=92%` — LLM 说的数字里，92% 能从数据源找到依据
- `unsourced_claims=40` — 40 条"编造"的声明被标记隔离

### 6.3 实时查询

```python
agent = AgentHarness(model="gpt-4o", strict=True)

# ... 跑多次任务 ...

snapshot = agent.gate_metrics.snapshot()
print(snapshot)
# {
#   "checks": 150,
#   "passed": 142,
#   "blocked": 8,
#   "isolation_rate": 0.053,
#   "coverage_rate": 0.92,
#   "grounding_rate": 0.92,
#   "findings_by_type": {"format": 2, "fact": 5, "logic": 1},
#   "findings_by_severity": {"warning": 6, "error": 2},
#   "total_claims": 500,
#   "sourced_claims": 460,
#   "unsourced_claims": 40
# }
```

### 6.4 告警规则

```python
snapshot = agent.gate_metrics.snapshot()

# 隔离率过高 → Agent 质量下降，可能需要调 prompt
if snapshot["isolation_rate"] > 0.15:
    print("⚠️ 隔离率 > 15%，检查 Agent 输出质量")

# 溯源率过低 → 数据源不全或 Agent 在编造
if snapshot["coverage_rate"] < 0.8:
    print("⚠️ 溯源率 < 80%，Agent 可能在编造数据")

# 全量通过 → 可能 Gate 没生效
if snapshot["checks"] > 0 and snapshot["blocked"] == 0:
    print("ℹ️ 零隔离，确认 Gate 是否正常工作")
```

### 6.5 OTel 仪表盘集成

```python
from opentelemetry import metrics
from harness.gate.metrics import GateMetrics

meter = metrics.get_meter("harness")
gate = GateMetrics()
gate.configure_otel(meter)

# 指标自动导出:
# harness.gate.checks          (Counter)
# harness.gate.blocked         (Counter)
# harness.gate.isolation_rate  (ObservableGauge)
# harness.gate.coverage_rate   (ObservableGauge)
# harness.gate.claims_total    (Counter)
# harness.gate.claims_sourced  (Counter)
# harness.gate.claims_unsourced (Counter)
```

### 6.6 与传统 APM 的区别

| 传统监控 | 治理率指标 | 区别 |
|---|---|---|
| QPS、延迟、错误率 | isolation_rate | 传统看"系统是否健康"，治理看"AI 输出是否可信" |
| 无 | coverage_rate | 传统不关心"数据从哪来"，治理强制溯源 |
| 无 | grounding_rate | 传统不区分"编造 vs 真实"，治理区分 |

**一句话总结**：治理率指标回答的是 **"Agent 给用户看的东西，有多少是靠谱的"**——这是传统 APM 无法回答的问题。

---

## 7. 配置参考

### GateConfig 参数

```python
@dataclass
class GateConfig:
    enable: bool = True                   # 是否启用 Gate
    block_on_unsourced: bool = True       # 无溯源声明 → ERROR (否则 WARNING)
    min_content_len: int = 200            # 低于此长度跳过事实校验
    rules: list[GateRule] | None = None   # Python 函数规则
    rule_specs: list[dict] | None = None  # 声明式规则 (dict)
    rules_path: str | None = None         # 规则文件路径 (JSON/YAML)
```

### strict 模式

```python
# strict=True 自动启用 Gate + 全部安全治理
agent = AgentHarness(model="gpt-4o", strict=True)

# 等价于手动配置:
agent = AgentHarness(
    model="gpt-4o",
    gate=GateConfig(enable=True, block_on_unsourced=True),
    security=SecurityConfig(...),
    cost_control=CostControlConfig(...),
)
```

> **生产环境推荐 `strict=True`**。`strict=False`（默认）适用于开发调试。

---

## 8. 与同类产品对比

| 维度 | Harness Deterministic Gate | OPA (Open Policy Agent) | Guardrails AI | LangChain |
|---|---|---|---|---|
| **定位** | LLM 输出校验 | API/Infra 策略 | LLM 输出校验 | 通用框架 |
| **执行方式** | 100% 确定性代码 | 100% 确定性代码 | LLM + 规则混合 | LLM + 规则混合 |
| **事实溯源** | ✅ 双通道 | ❌ | ⚠️ 需配置 | ❌ |
| **交付隔离** | ✅ 自动 redact | ❌ (仅 deny) | ❌ | ❌ |
| **声明式规则** | ✅ JSON/YAML | ✅ Rego | ⚠️ 有限 | ❌ |
| **内置于 Agent** | ✅ (strict 模式) | ❌ (外部 sidecar) | ❌ (需手动接入) | ❌ (需手动接入) |
| **可观测性** | ✅ 治理率指标 | ✅ (通过 Prometheus) | ⚠️ 基础 | ❌ |

**独特优势**：
1. **事实溯源**是独有能力——其他框架只做格式校验，不做"这个数字从哪来"的核验
2. **交付隔离**（而非 deny）——不是拒绝整个请求，而是标记并隔离无源声明，保留有源内容
3. **内置于 Agent**——`strict=True` 一行代码启用，无需外部 sidecar
