"""治理块校验：29 条规则，strict 下 fail-closed。

规则的编号与设计稿 §6.3 一一对应，**编号是稳定契约**——错误信息里的
`rule N` 直接对应设计稿与 §16.1 可追溯性矩阵。改动规则集时必须同步
矩阵（`tests/unit/test_governance_doc_consistency.py` 会校验矩阵与规则的
一一对应）。

三条校验类别：
- **结构**：字段存在、类型正确、取值在枚举内
- **表达式**：GHA 安全子集（规则 14-19）
- **治理**：跨字段的业务约束（规则 20-29）
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from harness.governance.expression import (
    FORBIDDEN_CONTEXT_ROOTS,
    FORBIDDEN_FUNCTIONS,
    ExpressionError,
    is_wrapped,
    parse_expression,
)
from harness.governance.schema import (
    COMPLETE_MODES,
    GovernanceBlock,
    ToolSpec,
)

# 占位符字面量（规则 26）
PLACEHOLDERS = ("TODO", "TBD", "FIXME", "XXX")

# 必填串字段（规则 26 覆盖）
_PLACEHOLDER_FIELDS = (
    "approved_by",
    "business_intent",
    "owners_accountable",
    "owners_technical",
)

# 强制审批的能力（规则 20 / §6.3）
FORCE_APPROVAL_CAPABILITIES = ("payment", "destructive")


@dataclass(frozen=True)
class ValidationError:
    """一条校验错误。"""

    rule: int
    field: str
    message: str

    def __str__(self) -> str:
        return f"规则 {self.rule}｜{self.field}：{self.message}"


@dataclass(frozen=True)
class ValidationResult:
    """校验结果。`ok` 为 False 时治理块不生效。"""

    errors: tuple[ValidationError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def messages(self) -> list[str]:
        return [str(e) for e in self.errors]


class _Collector:
    def __init__(self) -> None:
        self._errors: list[ValidationError] = []

    def add(self, rule: int, field: str, message: str) -> None:
        self._errors.append(ValidationError(rule, field, message))

    def result(self) -> ValidationResult:
        return ValidationResult(tuple(self._errors))


def _has_placeholder(value: str) -> bool:
    upper = value.strip().upper()
    if upper in PLACEHOLDERS:
        return True
    return upper.startswith("TODO")


def _validate_outputs(tools: tuple[ToolSpec, ...], c: _Collector) -> None:
    """规则 3：产出名称全局唯一、from 取值合法、path 非空。"""
    seen: set[str] = set()
    for tool in tools:
        for output in tool.outputs:
            if output.name in seen:
                c.add(
                    3,
                    f"tools[{tool.name}].outputs.{output.name}",
                    f"产出名 `{output.name}` 重复（产出名须全局唯一）",
                )
            seen.add(output.name)
            if not output.path:
                c.add(
                    3,
                    f"tools[{tool.name}].outputs.{output.name}.path",
                    "path 不得为空",
                )


def _validate_workflow(
    block: GovernanceBlock, c: _Collector
) -> None:
    """规则 8-13、23-28：步骤链结构与引用闭合。"""
    workflow = block.workflow
    step_ids: list[str] = []
    for step in workflow.steps:
        if step.id in step_ids:
            c.add(8, f"workflow.steps.{step.id}", f"step id `{step.id}` 重复")
        step_ids.append(step.id)

    whitelist = block.tool_names

    for step in workflow.steps:
        # 规则 8：step 至少绑一工具（解析期已保证，这里兜底）
        if not step.tools:
            c.add(8, f"workflow.steps.{step.id}.tools", "step 至少要绑定一个工具")

        # 规则 9：工具归属唯一
        for tool_name in step.tools:
            if tool_name in workflow.shared_tools:
                c.add(
                    9,
                    f"workflow.steps.{step.id}.tools",
                    f"工具 `{tool_name}` 同时出现在 step 与 shared_tools",
                )

        # 规则 10：complete 取值合法
        if step.complete not in COMPLETE_MODES and step.complete not in whitelist:
            c.add(
                10,
                f"workflow.steps.{step.id}.complete",
                f"complete 只能是 {list(COMPLETE_MODES)} 或某个已声明工具名，"
                f"实际是 `{step.complete}`",
            )

        # 规则 12/13：if 引用的 step 必须更早且已声明
        if step.condition:
            # 规则 15（安全子集）先于规则 14（语法）：禁止上下文不是语法问题
            _check_expression_safety(step.condition, step.id, c)
            try:
                parse_expression(step.condition)
            except ExpressionError as exc:
                c.add(
                    14,
                    f"workflow.steps.{step.id}.if",
                    f"表达式解析失败：{exc}",
                )
            else:
                if not is_wrapped(step.condition):
                    c.add(
                        17,
                        f"workflow.steps.{step.id}.if",
                        "表达式必须被 `${{ ... }}` 完整包裹",
                    )

    # 规则 12：requires 引用的 step 必须已声明且在本 step 之前
    for index, step in enumerate(workflow.steps):
        for required in step.requires:
            if required not in step_ids:
                c.add(
                    12,
                    f"workflow.steps.{step.id}.requires",
                    f"引用了未声明的 step `{required}`",
                )
            elif step_ids.index(required) >= index:
                c.add(
                    12,
                    f"workflow.steps.{step.id}.requires",
                    f"`{required}` 必须声明在本 step 之前",
                )

    # 规则 27/28：引用闭合
    for step in workflow.steps:
        for tool_name in step.tools:
            if tool_name not in whitelist:
                c.add(
                    27,
                    f"workflow.steps.{step.id}.tools",
                    f"工具 `{tool_name}` 不在治理块 tools 白名单内",
                )
    for tool_name in sorted(whitelist):
        in_step = any(tool_name in s.tools for s in workflow.steps)
        if not in_step and tool_name not in workflow.shared_tools:
            c.add(
                28,
                f"tools.{tool_name}",
                f"工具 `{tool_name}` 既不属于任何 step，也不在 shared_tools 中",
            )

    # 规则 21/22：治理专有组合约束
    for step in workflow.steps:
        if step.complete == "any":
            for tool_name in step.tools:
                spec = block.tool_by_name(tool_name)
                if spec is not None and spec.capability == "destructive":
                    c.add(
                        21,
                        f"workflow.steps.{step.id}",
                        f"`complete: any` 的 step 不得包含 destructive 工具 "
                        f"`{tool_name}`（可绕过其审批关卡）",
                    )
    for tool_name in workflow.shared_tools:
        spec = block.tool_by_name(tool_name)
        if spec is not None and not spec.idempotent:
            c.add(
                22,
                f"workflow.shared_tools.{tool_name}",
                f"非幂等工具 `{tool_name}` 不得放入 shared_tools"
                f"（共享工具可在任意 step 调用 → 非幂等副作用面不可控）",
            )



def _check_expression_safety(
    expression: str, step_id: str, c: _Collector
) -> None:
    """规则 15/18：禁止危险上下文与函数；裸 `!` 开头须加引号。"""
    text = expression.strip()
    for root in FORBIDDEN_CONTEXT_ROOTS:
        if re_search_context(text, root):
            c.add(
                15,
                f"workflow.steps.{step_id}.if",
                f"禁止使用上下文 `{root}`",
            )
    for fn in FORBIDDEN_FUNCTIONS:
        if f"{fn}(" in text:
            c.add(
                15,
                f"workflow.steps.{step_id}.if",
                f"禁止使用函数 `{fn}`（读文件系统＝能力泄漏）",
            )
    # 规则 18：裸 `!` 开头（YAML 会当成标签）
    inner = text[3:-2].strip() if is_wrapped(text) else text
    if inner.startswith("!"):
        c.add(
            18,
            f"workflow.steps.{step_id}.if",
            "`if` 以 `!` 开头必须加引号（否则 YAML 解析失败）",
        )


def re_search_context(text: str, root: str) -> bool:
    """在表达式文本中查找上下文根。

    只匹配**根位置**用法（``secrets.X`` / ``hashFiles(...)``），
    避免把 ``steps.a.outputs.github`` 这类合法路径里的同名子串误判为禁止上下文。
    """
    return re.search(rf"(?<![\w.]){re.escape(root)}\b", text) is not None


def validate_governance_block(
    block: GovernanceBlock,
    *,
    skill_allowed_tools: set[str] | None = None,
    known_tool_names: set[str] | None = None,
) -> ValidationResult:
    """校验治理块。

    Args:
        block: 待校验的治理块
        skill_allowed_tools: 技能 frontmatter 的 `tools.allowed`（规则 29 的上界）。
            None 表示技能未声明 → 不设上界。
        known_tool_names: 工具注册表中已登记的工具名（规则 1）。
            None 表示跳过该项检查（如离线校验场景）。
    """
    c = _Collector()

    # 规则 1：工具名存在 + capability 已声明
    for tool in block.tools:
        if known_tool_names is not None and tool.name not in known_tool_names:
            c.add(1, f"tools.{tool.name}", f"工具 `{tool.name}` 不在工具注册表中")

    # 规则 3：产出
    _validate_outputs(block.tools, c)

    # 规则 7：approval_required_for 只能引用已声明 step 或工具
    step_ids = {s.id for s in block.workflow.steps}
    for ref in block.approval_required_for:
        if ref not in step_ids and ref not in block.tool_names:
            c.add(
                7,
                "approval_required_for",
                f"`{ref}` 既不是已声明的 step 也不是已声明的工具",
            )
    # 规则 20：payment/destructive 必须被审批覆盖
    for tool in block.tools:
        if tool.capability in FORCE_APPROVAL_CAPABILITIES:
            covered = tool.name in block.approval_required_for or any(
                tool.name in step.tools
                for step in block.workflow.steps
                if step.id in block.approval_required_for
            )
            if not covered:
                c.add(
                    20,
                    f"tools.{tool.name}",
                    f"`{tool.capability}` 工具必须被 approval_required_for 覆盖"
                    f"（或由 capability 规则强制）",
                )

    # 规则 24/25：material 必须有 workflow 与审批覆盖
    if block.material:
        if not block.workflow.steps:
            c.add(
                24,
                "workflow",
                "material: true 的治理块必须声明 workflow 且至少含一个 step"
                "（否则『跳过 AML 直接出报告』这类偏离完全不被发现）",
            )
        has_forced = any(
            t.capability in FORCE_APPROVAL_CAPABILITIES for t in block.tools
        )
        if has_forced:
            covered = False
            for tool in block.tools:
                if tool.capability not in FORCE_APPROVAL_CAPABILITIES:
                    continue
                if tool.name in block.approval_required_for or any(
                    tool.name in step.tools
                    for step in block.workflow.steps
                    if step.id in block.approval_required_for
                ):
                    covered = True
            if not covered:
                c.add(
                    25,
                    "approval_required_for",
                    "material: true 的治理块必须覆盖至少一个 payment/destructive "
                    "工具的审批（否则高风险能力存在无人工审批的调用路径）",
                )

    # 规则 26：占位符拒绝
    for field_name in _PLACEHOLDER_FIELDS:
        value = getattr(block, field_name, "")
        if isinstance(value, str) and _has_placeholder(value):
            c.add(
                26,
                field_name,
                f"不得使用占位符（{list(PLACEHOLDERS)}）；填完再提交",
            )

    # 规则 8-13、21、22、27-29：步骤链
    _validate_workflow(block, c)

    # 规则 29：技能 tools.allowed 上界
    if skill_allowed_tools is not None:
        for tool_name in sorted(block.tool_names):
            if tool_name not in skill_allowed_tools:
                c.add(
                    29,
                    f"tools.{tool_name}",
                    f"治理块 tools 必须是技能 tools.allowed 的子集，"
                    f"但 `{tool_name}` 不在技能允许列表内",
                )

    return c.result()
