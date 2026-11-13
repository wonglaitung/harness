"""运行上下文：run_id、步骤游标、限额计数。

一个 run 一份上下文，随 `ToolContext.metadata` 送达执行路径（设计稿 §4.4）。
`ToolExecutor` 是每 harness 一个、被多 session 共享的对象，**不能**在其上挂
per-run 状态——所以状态走 `ToolContext.metadata`。

步骤游标语义沿用 GHA 内层 step（设计稿 §8.3）：
- ``success``：完成条件满足
- ``skipped``：``if`` 求值为假 → **不阻断后续**（GHA 内层 step 语义）
- ``failure``：工具失败或声明的产出未产出 → **阻断后续**（隐含 ``success()`` 失效）
- ``cancelled``：Kill Switch / 中止 → 阻断后续

**多份治理块的步骤链各自独立**（§6.4.2），不合并：每条链有自己的游标，
某条链的前进不影响其他链。因此上下文内部是"链"的集合而非单条链。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from harness.governance.expression import (
    ExpressionContext,
    ExpressionError,
    evaluate_expression,
)
from harness.governance.policy import PolicySnapshot
from harness.governance.schema import StepSpec, WorkflowSpec

# 步骤结论
OUTCOME_SUCCESS = "success"
OUTCOME_SKIPPED = "skipped"
OUTCOME_FAILURE = "failure"
OUTCOME_CANCELLED = "cancelled"


@dataclass
class StepState:
    """单个 step 的运行状态。"""

    step_id: str
    outcome: str | None = None
    conclusion: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)
    tools_called: set[str] = field(default_factory=set)
    tools_succeeded: set[str] = field(default_factory=set)


@dataclass
class _Chain:
    """一条独立的步骤链。

    多份治理块时每份各有一条链（§6.4.2「步骤链各自独立，不合并」）。
    """

    workflow: WorkflowSpec
    order: list[str] = field(default_factory=list)
    steps: dict[str, StepState] = field(default_factory=dict)
    cursor: int = 0

    def step_spec(self, step_id: str) -> StepSpec | None:
        return self.workflow.step_by_id(step_id)

    def current_step(self) -> StepSpec | None:
        if self.cursor >= len(self.order):
            return None
        return self.step_spec(self.order[self.cursor])

    def chain_for_tool(self, tool_name: str) -> str | None:
        """工具所属的 step id（本链内唯一归属）。"""
        for step in self.workflow.steps:
            if tool_name in step.tools:
                return step.id
        return None


class RunContext:
    """一次 run 的治理运行上下文。"""

    def __init__(
        self,
        policy: PolicySnapshot,
        *,
        run_id: str | None = None,
        env: dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id or uuid.uuid4().hex
        self.policy = policy
        self._env = env or {}
        self._chains: list[_Chain] = []
        for workflow in policy.all_workflows:
            chain = _Chain(workflow=workflow)
            for step in workflow.steps:
                chain.order.append(step.id)
                chain.steps[step.id] = StepState(step_id=step.id)
            self._chains.append(chain)
        # 限额计数
        self.tool_calls = 0
        self.token_usage = 0
        self._call_times: list[float] = []
        # 每工具调用计数（约束 `max_calls_per_run` 按工具计）
        self.tool_call_counts: dict[str, int] = {}
        # 行为信号计数
        self.signals: dict[str, int] = {}
        self._consecutive_denials = 0
        self._consecutive_failures = 0
        # 事实（工具产出）
        self._facts: dict[str, str] = {}
        self._fact_sources: dict[str, str] = {}
        self.cancelled = False

    # -- 步骤状态 ---------------------------------------------------------

    @property
    def step_ids(self) -> list[str]:
        return [sid for chain in self._chains for sid in chain.order]

    def step_state(self, step_id: str) -> StepState | None:
        for chain in self._chains:
            state = chain.steps.get(step_id)
            if state is not None:
                return state
        return None

    def _chain_of_step(self, step_id: str) -> _Chain | None:
        for chain in self._chains:
            if step_id in chain.steps:
                return chain
        return None

    def _chain_for_tool(self, tool_name: str) -> _Chain | None:
        for chain in self._chains:
            if chain.chain_for_tool(tool_name) is not None:
                return chain
        return None

    def _expr_context(self) -> ExpressionContext:
        steps: dict[str, dict[str, Any]] = {}
        for chain in self._chains:
            for step_id, state in chain.steps.items():
                steps[step_id] = {
                    "outputs": state.outputs,
                    "outcome": state.outcome or "",
                    "conclusion": state.conclusion or "",
                }
        return ExpressionContext(steps=steps, env=self._env)

    def _record_fact(self, step_id: str, name: str, value: str) -> None:
        self._facts[name] = value
        self._fact_sources[name] = step_id

    def facts_for_step(self, step_id: str) -> dict[str, str]:
        """某个 step 产出的事实。"""
        return {
            name: value
            for name, value in self._facts.items()
            if self._fact_sources.get(name) == step_id
        }

    # -- 游标推进（设计稿 §8.3）-----------------------------------------

    def advance_cursor(self) -> StepSpec | None:
        """推进游标，返回当前 step（`None` 表示已走完全链）。

        推进规则：
        a. 已有结论 → 越过
        b. 完成条件已满足 → success，前移
        c. ``if`` 为假 → skipped，前移（**不阻断**）
        d. 否则 → 当前 step，停止

        多链时**各自推进**：某条链走完不影响其他链（§6.4.2）。
        """
        for chain in self._chains:
            self._advance_chain(chain)
        for chain in self._chains:
            step = chain.current_step()
            if step is not None:
                return step
        return None

    def _advance_chain(self, chain: _Chain) -> StepSpec | None:
        while chain.cursor < len(chain.order):
            step_id = chain.order[chain.cursor]
            step = chain.step_spec(step_id)
            state = chain.steps[step_id]
            if state.outcome is not None:
                chain.cursor += 1
                continue
            if step is None:
                chain.cursor += 1
                continue
            if self._step_complete(step, state):
                state.outcome = OUTCOME_SUCCESS
                state.conclusion = OUTCOME_SUCCESS
                chain.cursor += 1
                continue
            if step.condition:
                try:
                    active = evaluate_expression(
                        step.condition, self._expr_context()
                    )
                except ExpressionError:
                    # 无法判定 → fail-closed：视为 if 为假（不激活），
                    # 但记录信号（由调用方处理）
                    active = False
                    self.bump_signal("guard_unresolved")
                if not active:
                    state.outcome = OUTCOME_SKIPPED
                    state.conclusion = OUTCOME_SKIPPED
                    chain.cursor += 1
                    continue
            return step
        return None

    def _step_complete(self, step: StepSpec, state: StepState) -> bool:
        """完成条件判定（§8.3）。"""
        if not step.tools:
            return False
        if step.complete == "all":
            return all(t in state.tools_succeeded for t in step.tools)
        if step.complete == "any":
            return any(t in state.tools_succeeded for t in step.tools)
        return step.complete in state.tools_succeeded

    def current_step(self, tool_name: str | None = None) -> StepSpec | None:
        """当前 step（不推进游标）。

        给定 `tool_name` 时返回**该工具所属链**的当前 step——多链场景下
        "当前 step" 是按链定义的。
        """
        if tool_name:
            chain = self._chain_for_tool(tool_name)
            if chain is not None:
                return chain.current_step()
        for chain in self._chains:
            step = chain.current_step()
            if step is not None:
                return step
        return None

    def step_for_tool(self, tool_name: str) -> StepSpec | None:
        """工具所属的 step（唯一归属；`shared_tools` 不属于任何 step）。"""
        for chain in self._chains:
            step_id = chain.chain_for_tool(tool_name)
            if step_id is not None:
                return chain.step_spec(step_id)
        return None

    def is_reachable(self, tool_name: str) -> tuple[bool, str]:
        """该工具此刻是否可达。

        Returns:
            ``(是否可达, 原因)``；不可达时原因用于事件记录。

        原因优先级：**上游失败 > 跳步**。上游失败时下游既不可达、也是跳步，
        但报"跳步"会误导开发者去检查步骤顺序，而真正的原因是前一步失败了。
        """
        kind, reason = self.classify_reachability(tool_name)
        return kind == "ok", reason

    def classify_reachability(self, tool_name: str) -> tuple[str, str]:
        """可达性分类（比 `is_reachable` 多给出原因类别）。

        Returns:
            ``(kind, reason)``。kind 取值：

            - ``ok``：可达
            - ``unassigned``：工具不属于任何 step（治理块未覆盖）
            - ``blocked``：上游失败 / 取消导致不可达（**不是模型偏离**）
            - ``skip``：跳步（调用了更靠后的 step 的工具）——**行为信号**
        """
        if tool_name in self.shared_tools:
            return "ok", ""
        chain = self._chain_for_tool(tool_name)
        if chain is None:
            return "unassigned", f"工具 `{tool_name}` 不属于任何 step"
        step_id = chain.chain_for_tool(tool_name)
        assert step_id is not None  # chain_for_tool 已判定
        state = chain.steps.get(step_id)
        if state is None:
            return "blocked", f"step `{step_id}` 未在步骤链中"

        # 上游失败/取消 → 阻断（优先于跳步判断）
        for earlier_id in chain.order[: chain.order.index(step_id)]:
            earlier = chain.steps.get(earlier_id)
            if earlier is None:
                continue
            if earlier.outcome == OUTCOME_FAILURE:
                return "blocked", (
                    f"step `{earlier.step_id}` 已失败，"
                    f"后续 step `{step_id}` 不可达"
                )
            if earlier.outcome == OUTCOME_CANCELLED:
                return "blocked", (
                    f"step `{earlier.step_id}` 已取消，"
                    f"后续 step `{step_id}` 不可达"
                )

        if state.outcome == OUTCOME_FAILURE:
            return "blocked", f"step `{step_id}` 已失败，后续不可达"
        if state.outcome == OUTCOME_CANCELLED:
            return "blocked", f"step `{step_id}` 已取消"

        # 目标 step 必须在游标位置或更早（已完成）
        index = chain.order.index(step_id)
        if index > chain.cursor:
            current = chain.current_step()
            current_id = current.id if current else "（无）"
            return "skip", (
                f"跳步：当前 step 是 `{current_id}`，"
                f"调用了更靠后的 `{step_id}`"
            )
        return "ok", ""

    @property
    def shared_tools(self) -> tuple[str, ...]:
        """跨所有链的共享工具（不属于任何 step，随时可调用）。"""
        names: list[str] = []
        for chain in self._chains:
            for name in chain.workflow.shared_tools:
                if name not in names:
                    names.append(name)
        return tuple(names)

    # -- 执行结果回写 -----------------------------------------------------

    def record_tool_success(
        self, step_id: str, tool_name: str, outputs: dict[str, str]
    ) -> None:
        """工具成功：推进 step 状态并记录事实。"""
        chain = self._chain_of_step(step_id)
        if chain is None:
            return
        state = chain.steps.get(step_id)
        if state is None:
            return
        state.tools_called.add(tool_name)
        state.tools_succeeded.add(tool_name)
        for name, value in outputs.items():
            state.outputs[name] = value
            self._record_fact(step_id, name, value)

    def record_tool_failure(self, step_id: str, tool_name: str) -> None:
        """工具失败：当前 step 判 failure，阻断后续。"""
        chain = self._chain_of_step(step_id)
        if chain is None:
            return
        state = chain.steps.get(step_id)
        if state is None:
            return
        state.tools_called.add(tool_name)
        state.outcome = OUTCOME_FAILURE
        state.conclusion = OUTCOME_FAILURE
        self._consecutive_failures += 1
        self._consecutive_denials = 0

    def record_denial(self) -> None:
        """网关拒绝一次调用。"""
        self._consecutive_denials += 1
        self._consecutive_failures = 0

    def record_success(self) -> None:
        self._consecutive_denials = 0
        self._consecutive_failures = 0

    def bump_signal(self, name: str, amount: int = 1) -> int:
        self.signals[name] = self.signals.get(name, 0) + amount
        return self.signals[name]

    def signal_count(self, name: str) -> int:
        return self.signals.get(name, 0)

    def signal_exceeded(self, name: str) -> bool:
        """信号是否达阈值（§9.2）。未配置阈值则不算超。"""
        threshold = self.policy.limits.signal_thresholds.get(name)
        if threshold is None:
            return False
        return self.signal_count(name) >= threshold

    # -- 限额（设计稿 §9.1）----------------------------------------------

    def check_rate_limit(self, now: float) -> bool:
        """速率窗口是否已超限。"""
        window = self.policy.limits.max_calls_per_minute
        if window <= 0:
            return False
        cutoff = now - 60.0
        self._call_times = [t for t in self._call_times if t >= cutoff]
        return len(self._call_times) >= window

    def note_call(self, now: float, tool_name: str | None = None) -> None:
        """记一次工具调用（限额计数）。"""
        self.tool_calls += 1
        self._call_times.append(now)
        if tool_name:
            self.tool_call_counts[tool_name] = (
                self.tool_call_counts.get(tool_name, 0) + 1
            )

    def call_count(self, tool_name: str) -> int:
        """某工具在本次 run 内已被调用的次数。"""
        return self.tool_call_counts.get(tool_name, 0)

    def check_run_limit(self) -> bool:
        return self.tool_calls > self.policy.limits.max_tool_calls_per_run

    def check_token_limit(self) -> bool:
        return self.token_usage > self.policy.limits.max_tokens_per_run

    # -- 取消 --------------------------------------------------------------

    def cancel(self) -> None:
        """取消 run（Kill Switch / 中止）。"""
        self.cancelled = True
        for chain in self._chains:
            for state in chain.steps.values():
                if state.outcome is None:
                    state.outcome = OUTCOME_CANCELLED
                    state.conclusion = OUTCOME_CANCELLED

    @property
    def all_steps_resolved(self) -> bool:
        return all(
            state.outcome is not None
            for chain in self._chains
            for state in chain.steps.values()
        )

    @property
    def terminal_step_skipped(self) -> bool:
        """末端 step 是否为 skipped → run 结论 INCOMPLETE（§8.3）。"""
        for chain in self._chains:
            if not chain.order:
                continue
            last = chain.steps.get(chain.order[-1])
            if last is not None and last.outcome == OUTCOME_SKIPPED:
                return True
        return False
