"""治理块数据模型与解析。

治理块（governance block）是技能的**授权书**：声明这个 Agent 由谁负责、
允许做什么、按什么步骤做、超限怎么办。它随技能 frontmatter 同源存放，
在启动时编译成 `PolicySnapshot`（见 `harness.governance.policy`）。

本模块只做**结构化解析**——把 YAML frontmatter 变成数据类，不做语义校验
（校验在 `harness.governance.validation`，29 条规则），也不做运行时求值。

设计约束（来自设计稿 §6.2 / §6.3）：
- 未知字段必须被拒绝，而不是静默忽略——否则拼写错误会造成绕过
- 表达式只允许受限子集（见 `harness.governance.expression`）
- 产出（outputs）全为字符串，比较须写 `== 'true'`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 能力分级（§6.3 规则 1）
CAPABILITIES = ("read", "write", "payment", "destructive")

# 完成条件取值（§6.3 规则 10）
COMPLETE_MODES = ("all", "any")

# 产出来源（§6.3 规则 3）
OUTPUT_SOURCES = ("metadata", "content_json")

# 步骤结论（GHA 语义，§8.3）
STEP_OUTCOMES = ("success", "failure", "cancelled", "skipped")


class GovernanceError(Exception):
    """治理块解析或校验失败。

    strict 模式下任何 GovernanceError 都导致治理块不生效（fail-closed）。
    """


@dataclass(frozen=True)
class ToolOutput:
    """工具产出的一个事实。

    事实是条件判断的唯一合法来源（§8.2）——分支的判据必须来自工具产出，
    不能来自模型判断。
    """

    name: str
    source: str = "metadata"
    path: str = ""


@dataclass(frozen=True)
class ToolSpec:
    """治理块中一个工具的契约声明。"""

    name: str
    capability: str
    idempotent: bool
    outputs: tuple[ToolOutput, ...] = ()
    # 自研工具在代码里声明的约束（§6.4）；治理块中的 MCP 工具没有此项
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepSpec:
    """步骤链中的一个步骤。"""

    id: str
    tools: tuple[str, ...]
    complete: str = "all"  # all | any | <tool_name>
    requires: tuple[str, ...] = ()  # 前驱 step id（§8.1 的 requires）
    condition: str | None = None  # if 表达式原文（未求值）
    timeout_minutes: int | None = None
    continue_on_error: bool = False


@dataclass(frozen=True)
class WorkflowSpec:
    """步骤链。"""

    steps: tuple[StepSpec, ...] = ()
    shared_tools: tuple[str, ...] = ()

    def step_by_id(self, step_id: str) -> StepSpec | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


@dataclass(frozen=True)
class Limits:
    """治理限额（§9.1）。"""

    max_tool_calls_per_run: int = 50
    max_calls_per_minute: int = 20
    max_tokens_per_run: int = 200_000
    approval_timeout_seconds: int = 300
    signal_thresholds: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceBlock:
    """一个技能的治理块。

    字段分两类（§6.2「字段强制等级」）：
    - **执行期强制**：网关在运行路径上消费
    - **仅登记备查**：只供事后追溯，不影响放行/阻断
    """

    agent_id: str
    version: str
    approved_by: str
    business_intent: str
    owners_accountable: str
    owners_technical: str
    tools: tuple[ToolSpec, ...]
    limits: Limits
    material: bool = False
    workflow: WorkflowSpec = field(default_factory=WorkflowSpec)
    allowed_paths: tuple[str, ...] = ()
    allowed_hosts: tuple[str, ...] = ()
    approval_required_for: tuple[str, ...] = ()
    intervention_kill_switch: str = "file"
    intervention_fallback: str = ""

    def tool_by_name(self, name: str) -> ToolSpec | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    @property
    def tool_names(self) -> set[str]:
        return {t.name for t in self.tools}


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

# 治理块允许的顶层字段（§6.3 规则 6：未知字段拒绝）
_ALLOWED_TOP = {
    "agent_id",
    "version",
    "approved_by",
    "business_intint",  # 占位，实际见下
    "owners",
    "material",
    "tools",
    "workflow",
    "allowed_paths",
    "allowed_hosts",
    "limits",
    "approval_required_for",
    "intervention",
}
_ALLOWED_TOP.discard("business_intint")
_ALLOWED_TOP.add("business_intent")

_ALLOWED_TOOL = {"name", "capability", "idempotent", "outputs", "constraints"}
_ALLOWED_OUTPUT = {"name", "from", "path"}
_ALLOWED_STEP = {
    "id",
    "tools",
    "complete",
    "requires",
    "if",
    "timeout-minutes",
    "continue-on-error",
}
_ALLOWED_WORKFLOW = {"steps", "shared_tools"}
_ALLOWED_LIMITS = {
    "max_tool_calls_per_run",
    "max_calls_per_minute",
    "max_tokens_per_run",
    "approval_timeout_seconds",
    "signal_thresholds",
}
_ALLOWED_OWNERS = {"accountable", "technical"}
_ALLOWED_INTERVENTION = {"kill_switch", "fallback"}


def _reject_unknown(data: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise GovernanceError(
            f"{where} 含未知字段 {unknown}；只允许 {sorted(allowed)}"
        )


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise GovernanceError(f"{where} 缺少必填字段 `{key}`")
    return data[key]


def _as_str(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise GovernanceError(f"{where} 必须是字符串，实际是 {type(value).__name__}")
    return value


def _as_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise GovernanceError(f"{where} 必须是布尔值，实际是 {type(value).__name__}")
    return value


def _as_str_tuple(value: Any, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise GovernanceError(f"{where} 必须是字符串列表")
    return tuple(value)


def parse_tool_output(raw: Any, where: str) -> ToolOutput:
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_OUTPUT, where)
    name = _as_str(_require(raw, "name", where), f"{where}.name")
    source = raw.get("from", "metadata")
    if source not in OUTPUT_SOURCES:
        raise GovernanceError(
            f"{where}.from 只能是 {list(OUTPUT_SOURCES)}，实际是 {source!r}"
        )
    path = raw.get("path", "")
    if not isinstance(path, str):
        raise GovernanceError(f"{where}.path 必须是字符串")
    return ToolOutput(name=name, source=source, path=path)


def parse_tool_spec(raw: Any, where: str) -> ToolSpec:
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_TOOL, where)
    name = _as_str(_require(raw, "name", where), f"{where}.name")
    capability = _as_str(_require(raw, "capability", where), f"{where}.capability")
    if capability not in CAPABILITIES:
        raise GovernanceError(
            f"{where}.capability 只能是 {list(CAPABILITIES)}，实际是 {capability!r}"
        )
    idempotent = _as_bool(_require(raw, "idempotent", where), f"{where}.idempotent")
    outputs_raw = raw.get("outputs", [])
    if not isinstance(outputs_raw, list):
        raise GovernanceError(f"{where}.outputs 必须是列表")
    outputs = tuple(
        parse_tool_output(o, f"{where}.outputs[{i}]") for i, o in enumerate(outputs_raw)
    )
    constraints = raw.get("constraints", {}) or {}
    if not isinstance(constraints, dict):
        raise GovernanceError(f"{where}.constraints 必须是对象")
    return ToolSpec(
        name=name,
        capability=capability,
        idempotent=idempotent,
        outputs=outputs,
        constraints=constraints,
    )


def parse_step_spec(raw: Any, where: str) -> StepSpec:
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_STEP, where)
    step_id = _as_str(_require(raw, "id", where), f"{where}.id")
    tools = _as_str_tuple(raw.get("tools"), f"{where}.tools")
    if not tools:
        raise GovernanceError(f"{where}.tools 至少要绑定一个工具")
    complete = raw.get("complete", "all")
    if not isinstance(complete, str):
        raise GovernanceError(f"{where}.complete 必须是字符串")
    requires = _as_str_tuple(raw.get("requires"), f"{where}.requires")
    condition = raw.get("if")
    if condition is not None and not isinstance(condition, str):
        raise GovernanceError(f"{where}.if 必须是字符串")
    timeout = raw.get("timeout-minutes")
    if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
        raise GovernanceError(f"{where}.timeout-minutes 必须是正整数")
    continue_on_error = raw.get("continue-on-error", False)
    if not isinstance(continue_on_error, bool):
        raise GovernanceError(f"{where}.continue-on-error 必须是布尔值")
    return StepSpec(
        id=step_id,
        tools=tools,
        complete=complete,
        requires=requires,
        condition=condition,
        timeout_minutes=timeout,
        continue_on_error=continue_on_error,
    )


def parse_workflow(raw: Any, where: str) -> WorkflowSpec:
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_WORKFLOW, where)
    steps_raw = raw.get("steps", [])
    if not isinstance(steps_raw, list):
        raise GovernanceError(f"{where}.steps 必须是列表")
    steps = tuple(
        parse_step_spec(s, f"{where}.steps[{i}]") for i, s in enumerate(steps_raw)
    )
    shared = _as_str_tuple(raw.get("shared_tools"), f"{where}.shared_tools")
    return WorkflowSpec(steps=steps, shared_tools=shared)


def parse_limits(raw: Any, where: str) -> Limits:
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_LIMITS, where)
    thresholds = raw.get("signal_thresholds", {}) or {}
    if not isinstance(thresholds, dict):
        raise GovernanceError(f"{where}.signal_thresholds 必须是对象")
    for name, value in thresholds.items():
        if not isinstance(value, int) or value < 0:
            raise GovernanceError(f"{where}.signal_thresholds.{name} 必须是非负整数")
    defaults = Limits()
    return Limits(
        max_tool_calls_per_run=int(
            raw.get("max_tool_calls_per_run", defaults.max_tool_calls_per_run)
        ),
        max_calls_per_minute=int(
            raw.get("max_calls_per_minute", defaults.max_calls_per_minute)
        ),
        max_tokens_per_run=int(
            raw.get("max_tokens_per_run", defaults.max_tokens_per_run)
        ),
        approval_timeout_seconds=int(
            raw.get("approval_timeout_seconds", defaults.approval_timeout_seconds)
        ),
        signal_thresholds=dict(thresholds),
    )


def parse_governance_block(raw: Any, where: str = "governance") -> GovernanceBlock:
    """把 frontmatter 的 `governance` 段解析成 `GovernanceBlock`。

    只做结构与类型解析；跨字段语义（子集关系、引用闭合等）在
    `harness.governance.validation` 中校验。
    """
    if not isinstance(raw, dict):
        raise GovernanceError(f"{where} 必须是对象")
    _reject_unknown(raw, _ALLOWED_TOP, where)

    owners_raw = raw.get("owners", {})
    if not isinstance(owners_raw, dict):
        raise GovernanceError(f"{where}.owners 必须是对象")
    _reject_unknown(owners_raw, _ALLOWED_OWNERS, f"{where}.owners")

    tools_raw = _require(raw, "tools", where)
    if not isinstance(tools_raw, list) or not tools_raw:
        raise GovernanceError(f"{where}.tools 必须是非空列表")
    tools = tuple(
        parse_tool_spec(t, f"{where}.tools[{i}]") for i, t in enumerate(tools_raw)
    )

    intervention = raw.get("intervention", {}) or {}
    if not isinstance(intervention, dict):
        raise GovernanceError(f"{where}.intervention 必须是对象")
    _reject_unknown(intervention, _ALLOWED_INTERVENTION, f"{where}.intervention")

    material = raw.get("material", False)
    if not isinstance(material, bool):
        raise GovernanceError(f"{where}.material 必须是布尔值")

    return GovernanceBlock(
        agent_id=_as_str(_require(raw, "agent_id", where), f"{where}.agent_id"),
        version=_as_str(_require(raw, "version", where), f"{where}.version"),
        approved_by=_as_str(
            _require(raw, "approved_by", where), f"{where}.approved_by"
        ),
        business_intent=_as_str(
            _require(raw, "business_intent", where), f"{where}.business_intent"
        ),
        owners_accountable=_as_str(
            _require(owners_raw, "accountable", f"{where}.owners"),
            f"{where}.owners.accountable",
        ),
        owners_technical=_as_str(
            _require(owners_raw, "technical", f"{where}.owners"),
            f"{where}.owners.technical",
        ),
        tools=tools,
        limits=parse_limits(_require(raw, "limits", where), f"{where}.limits"),
        material=material,
        workflow=parse_workflow(raw.get("workflow", {}) or {}, f"{where}.workflow"),
        allowed_paths=_as_str_tuple(raw.get("allowed_paths"), f"{where}.allowed_paths"),
        allowed_hosts=_as_str_tuple(raw.get("allowed_hosts"), f"{where}.allowed_hosts"),
        approval_required_for=_as_str_tuple(
            raw.get("approval_required_for"), f"{where}.approval_required_for"
        ),
        intervention_kill_switch=str(
            intervention.get("kill_switch", "file")
        ),
        intervention_fallback=str(intervention.get("fallback", "")),
    )
