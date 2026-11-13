"""`PolicySnapshot`：治理块编译后的运行策略。

一个 run 用一份快照。快照在**编译期**（启动同步后）确定，run 内固定不变
（设计稿 §4.4）——这是"变更随下次启动生效"的实现方式。

多份治理块的合成规则（设计稿 §6.4.2）：
- 工具白名单：交集（取最严）
- 业务参数约束：并集（都生效）
- 限额：取最严
- 步骤链：各自独立，不合并
- `approval_required_for`：并集
- `material`：并集（任一份为 true 即 true）
- capability 冲突 → 编译期拒绝
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.governance.schema import (
    GovernanceBlock,
    GovernanceError,
    Limits,
    ToolSpec,
    WorkflowSpec,
)


@dataclass(frozen=True)
class PolicySnapshot:
    """编译后的运行策略。"""

    agent_id: str
    version: str
    tools: tuple[ToolSpec, ...]
    limits: Limits
    workflow: WorkflowSpec
    material: bool
    allowed_paths: tuple[str, ...] = ()
    allowed_hosts: tuple[str, ...] = ()
    approval_required_for: tuple[str, ...] = ()
    #: 多份治理块时**各自的步骤链**（§6.4.2：各自独立，不合并）。
    #: 为空时回退到单条 `workflow`。
    workflows: tuple[WorkflowSpec, ...] = ()

    @property
    def all_workflows(self) -> tuple[WorkflowSpec, ...]:
        """本次 run 需要执行的全部步骤链。"""
        return self.workflows or (self.workflow,)

    @property
    def tool_names(self) -> set[str]:
        return {t.name for t in self.tools}

    def tool_by_name(self, name: str) -> ToolSpec | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def requires_approval(self, tool_name: str) -> bool:
        """该工具是否需要人工审批。

        `payment` / `destructive` 恒为真（治理块不可关闭，§6.3）；
        `write` 需治理块显式声明；`read` 默认否。
        """
        spec = self.tool_by_name(tool_name)
        if spec is None:
            return False
        if spec.capability in ("payment", "destructive"):
            return True
        if spec.capability == "write":
            if tool_name in self.approval_required_for:
                return True
            return any(
                tool_name in step.tools
                for step in self.workflow.steps
                if step.id in self.approval_required_for
            )
        return False


def _merge_limits(blocks: list[GovernanceBlock]) -> Limits:
    """限额取最严；`signal_thresholds` 取各块中更严（更小）的值。"""
    if not blocks:
        return Limits()
    result = Limits(
        max_tool_calls_per_run=min(b.limits.max_tool_calls_per_run for b in blocks),
        max_calls_per_minute=min(b.limits.max_calls_per_minute for b in blocks),
        max_tokens_per_run=min(b.limits.max_tokens_per_run for b in blocks),
        approval_timeout_seconds=min(
            b.limits.approval_timeout_seconds for b in blocks
        ),
    )
    thresholds: dict[str, int] = {}
    for block in blocks:
        for name, value in block.limits.signal_thresholds.items():
            current = thresholds.get(name)
            thresholds[name] = value if current is None else min(current, value)
    return Limits(
        max_tool_calls_per_run=result.max_tool_calls_per_run,
        max_calls_per_minute=result.max_calls_per_minute,
        max_tokens_per_run=result.max_tokens_per_run,
        approval_timeout_seconds=result.approval_timeout_seconds,
        signal_thresholds=thresholds,
    )


def _merge_constraints(specs: list[ToolSpec]) -> dict[str, Any]:
    """业务参数约束取并集（§6.4.2：都生效）。

    同一字段被多份治理块同时声明时**取最严**：
    - `numeric_ranges`：区间取交集（低界取大、高界取小）
    - `allowed_values`：取交集（更小的允许集）
    - `max_amount` / `min_amount`：金额上限取小、下限取大
    - `max_calls_per_run`：取小
    其余字段（列表型）取并集。
    """
    merged: dict[str, Any] = {}
    required: list[str] = []
    deny_paths: list[str] = []
    ranges: dict[str, tuple[float, float]] = {}
    allowed_values: dict[str, list[Any]] = {}

    for spec in specs:
        constraints = spec.constraints or {}
        for name in constraints.get("required_fields", []) or []:
            if name not in required:
                required.append(name)
        for name in constraints.get("deny_paths", []) or []:
            if name not in deny_paths:
                deny_paths.append(name)
        for name, bounds in (constraints.get("numeric_ranges") or {}).items():
            low, high = float(bounds[0]), float(bounds[1])
            current_range = ranges.get(name)
            if current_range is None:
                ranges[name] = (low, high)
            else:
                ranges[name] = (
                    max(current_range[0], low),
                    min(current_range[1], high),
                )
        for name, values in (constraints.get("allowed_values") or {}).items():
            current_values = allowed_values.get(name)
            allowed_values[name] = (
                list(values)
                if current_values is None
                else [v for v in current_values if v in values]
            )

    if required:
        merged["required_fields"] = required
    if deny_paths:
        merged["deny_paths"] = deny_paths
    if ranges:
        merged["numeric_ranges"] = {k: list(v) for k, v in ranges.items()}
    if allowed_values:
        merged["allowed_values"] = allowed_values

    # 金额与次数上限：取最严
    for spec in specs:
        constraints = spec.constraints or {}
        for key, reducer in (
            ("max_amount", min),
            ("min_amount", max),
            ("max_calls_per_run", min),
        ):
            value = constraints.get(key)
            if value is None:
                continue
            current = merged.get(key)
            merged[key] = value if current is None else reducer(current, value)
    amount_field = next(
        (
            (spec.constraints or {}).get("amount_field")
            for spec in specs
            if (spec.constraints or {}).get("amount_field")
        ),
        None,
    )
    if amount_field:
        merged["amount_field"] = amount_field
    return merged


def _merge_tools(blocks: list[GovernanceBlock]) -> tuple[ToolSpec, ...]:
    """工具白名单取交集；capability 冲突 → 报错。"""
    per_block = [b.tool_names for b in blocks]
    common = set.intersection(*per_block) if per_block else set()

    merged: list[ToolSpec] = []
    for name in sorted(common):
        specs = [s for s in (b.tool_by_name(name) for b in blocks) if s is not None]
        if not specs:
            continue
        capabilities = {s.capability for s in specs}
        if len(capabilities) > 1:
            raise GovernanceError(
                f"工具 `{name}` 在多份治理块中的 capability 冲突："
                f"{sorted(capabilities)}；不能猜测哪个正确"
            )
        base = specs[0]
        merged.append(
            ToolSpec(
                name=name,
                capability=base.capability,
                idempotent=all(s.idempotent for s in specs),
                outputs=base.outputs,
                constraints=_merge_constraints(specs),
            )
        )
    return tuple(merged)


def compile_policy(blocks: list[GovernanceBlock]) -> PolicySnapshot:
    """把同一治理身份下的多份治理块合成一份运行策略。

    单份治理块是最常见的情况；多份来自"同一 `agent_id` 被多个技能声明"
    （设计稿 §6.4.2）。
    """
    if not blocks:
        raise GovernanceError("没有可编译的治理块")

    agent_ids = {b.agent_id for b in blocks}
    if len(agent_ids) > 1:
        raise GovernanceError(
            f"治理块 agent_id 不一致：{sorted(agent_ids)}；不能合并成一份策略"
        )

    first = blocks[0]
    workflows = tuple(b.workflow for b in blocks if b.workflow.steps)
    return PolicySnapshot(
        agent_id=first.agent_id,
        version=first.version,
        tools=_merge_tools(blocks),
        limits=_merge_limits(blocks),
        # 步骤链各自独立，不合并（设计稿 §6.4.2）：每份治理块一条链
        workflow=workflows[0] if workflows else first.workflow,
        workflows=workflows,
        material=any(b.material for b in blocks),
        allowed_paths=tuple(
            sorted({p for b in blocks for p in b.allowed_paths})
        ),
        allowed_hosts=tuple(
            sorted({h for b in blocks for h in b.allowed_hosts})
        ),
        approval_required_for=tuple(
            sorted({a for b in blocks for a in b.approval_required_for})
        ),
    )
