"""执行网关：每次工具调用的 11 步校验流水线（设计稿 §7.2）。

流水线顺序（§7.2）：

1. 治理一致性   agent_id / version / skill_version 与 PolicySnapshot 一致
2. 工具白名单   工具已登记且在治理块 tools 列表内
3. 能力声明     capability 已声明
4. 步骤游标     当前 step 判定 + 可达性检查（§8.3）
5. 业务约束     业务参数约束求值（§7.4）
6. 权限范围     路径 / 主机 / 命令（PermissionSet + 治理块 allowed_paths/hosts）
7. 限额         run 次数 / 速率 / token（§9.1）
8. 审批关卡     按 capability 定档（§7.3 / §7.5）
9. 事件记录     判定事件（执行前）：allow / deny + 原因
10. 执行
11. 结果事件    结果 + 耗时 + step 状态推进（§11.1）

**全部判定由确定性代码完成**——LLM 不参与放行或阻断（§1.3）。

**拒绝也留痕**：每次拒绝写一条 `tool_call_decision`（decision=deny），
并计入行为信号（§9.2）。信号是**检出式**链路（事后可见、不阻断），
与判定本身分开。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.governance.approval import ApprovalManager

from harness.governance.constraints import evaluate_constraints
from harness.governance.context import RunContext
from harness.governance.policy import PolicySnapshot

# 判定结果
ALLOW = "allow"
DENY = "deny"

# 判定规则名（写进事件的 `rule` 字段）
RULE_CONTROL = "控制面"
RULE_CONSISTENCY = "治理一致性"
RULE_WHITELIST = "工具白名单"
RULE_CAPABILITY = "能力声明"
RULE_STEP = "步骤游标"
RULE_CONSTRAINTS = "业务约束"
RULE_PERMISSIONS = "权限范围"
RULE_LIMITS = "限额"
RULE_APPROVAL = "审批关卡"

# 规则 → 行为信号（设计稿 §9.2）。只有"模型偏离"类拒绝才计信号：
# 上游失败导致的不可达是**预期内的阻断**，不是偏离。
_RULE_SIGNALS = {
    RULE_WHITELIST: "out_of_scope_attempts",
    RULE_STEP: "step_violations",
}


@dataclass
class Decision:
    """一次网关判定的结果。"""

    allowed: bool
    reason: str = ""
    rule: str = ""
    step_id: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)


class GovernanceGateway:
    """治理网关。所有工具调用（除 MCP/自定义外均经 `ToolExecutor`）在此判定。

    网关**不执行**工具——它只做判定；执行由 `ToolExecutor` 负责。

    网关本身**不持有 per-run 状态**：步骤游标、限额计数都在 `RunContext` 里，
    由调用方按 run 传入（§4.4）。因此同一个网关实例可跨 run 复用。
    """

    def __init__(
        self,
        policy: PolicySnapshot,
        *,
        approval: ApprovalManager | None = None,
        permissions: Any | None = None,
        control: Any | None = None,
        event_log: Any | None = None,
        sandbox: Any | None = None,
        file_validator: Any | None = None,
        working_directory: str | os.PathLike[str] | None = None,
    ) -> None:
        self.policy = policy
        self.approval = approval
        self.permissions = permissions
        self.control = control
        self.event_log = event_log
        # 沙箱与文件校验（§7.1：从 `ToolGateHook` 迁入流水线，不留在 Hook）
        self.sandbox = sandbox
        self.file_validator = file_validator
        self.working_directory = Path(working_directory) if working_directory else None

    # -- run 上下文 --------------------------------------------------------

    def new_context(self, *, run_id: str | None = None) -> RunContext:
        """新建一个 run 的运行上下文（§4.4）。"""
        return RunContext(self.policy, run_id=run_id)

    # -- 单步判定 ---------------------------------------------------------

    def check(
        self,
        ctx: RunContext,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        now: float | None = None,
    ) -> Decision:
        """对一次工具调用做完整判定（流水线第 1-9 步）。

        Returns:
            `Decision`。`allowed=False` 时 `reason` 说明原因（写进事件，不含实际值）。
        """
        timestamp = time.monotonic() if now is None else now

        # 0. 控制面检查点（Kill Switch，§10.3「每次工具执行前」）
        decision = self._check_control(ctx, tool_name)
        if decision is not None:
            return decision

        # 1. 治理一致性
        decision = self._check_consistency(ctx, tool_name)
        if decision is not None:
            return decision

        # 2. 工具白名单
        decision = self._check_whitelist(ctx, tool_name)
        if decision is not None:
            return decision

        # 3. 能力声明
        decision = self._check_capability(ctx, tool_name)
        if decision is not None:
            return decision

        # 4. 步骤游标 / 可达性
        decision = self._check_step(ctx, tool_name)
        if decision is not None:
            return decision

        # 5. 业务约束
        decision = self._check_constraints(ctx, tool_name, arguments)
        if decision is not None:
            return decision

        # 6. 权限范围
        decision = self._check_permissions(ctx, tool_name, arguments)
        if decision is not None:
            return decision

        # 7. 限额
        decision = self._check_limits(ctx, tool_name, timestamp)
        if decision is not None:
            return decision

        # 8. 审批关卡
        decision = self._check_approval(ctx, tool_name, arguments)
        if decision is not None:
            return decision

        # 9. 判定事件（执行前）
        self._record_decision(ctx, tool_name, ALLOW, "")
        # 计入本次调用（限额计数在放行后累加，避免拒绝也占额度）
        ctx.note_call(timestamp, tool_name)
        return Decision(allowed=True, step_id=self._current_step_id(ctx, tool_name))

    # -- 各步实现 ---------------------------------------------------------

    def _current_step_id(self, ctx: RunContext, tool_name: str | None = None) -> str | None:
        step = ctx.current_step(tool_name)
        return step.id if step else None

    def _deny(
        self,
        ctx: RunContext,
        tool_name: str,
        reason: str,
        rule: str,
    ) -> Decision:
        """统一的拒绝出口：写事件 + 计信号。"""
        self._record_decision(ctx, tool_name, DENY, reason)
        ctx.record_denial()
        signal = _RULE_SIGNALS.get(rule)
        if signal:
            count = ctx.bump_signal(signal)
            self._record_signal(ctx, signal, count)
        return Decision(
            allowed=False,
            reason=reason,
            rule=rule,
            step_id=self._current_step_id(ctx, tool_name),
        )

    def _check_control(self, ctx: RunContext, tool_name: str) -> Decision | None:
        """0. 控制面：Kill Switch 暂停 / 撤销 → 拒绝该工具（§10.3）。"""
        if self.control is None:
            return None
        state = self.control.read(self.policy.agent_id)
        if not state.blocking:
            return None
        return self._deny(
            ctx,
            tool_name,
            f"Agent 已被控制面置为 `{state.state}`"
            f"{('：' + state.reason) if state.reason else ''}",
            RULE_CONTROL,
        )

    def _check_consistency(self, ctx: RunContext, tool_name: str) -> Decision | None:
        """1. 治理一致性：run 上下文绑定的策略必须仍是当前策略。"""
        if ctx.policy is not self.policy:
            return self._deny(
                ctx,
                tool_name,
                "治理策略与运行上下文不一致",
                RULE_CONSISTENCY,
            )
        return None

    def _check_whitelist(self, ctx: RunContext, tool_name: str) -> Decision | None:
        """2. 工具白名单：必须在治理块 tools 内。"""
        if tool_name not in self.policy.tool_names:
            return self._deny(
                ctx,
                tool_name,
                f"工具 `{tool_name}` 不在治理块白名单内",
                RULE_WHITELIST,
            )
        return None

    def _check_capability(self, ctx: RunContext, tool_name: str) -> Decision | None:
        """3. 能力声明：capability 必须已声明（§7.3 不保留 unknown 后门）。"""
        spec = self.policy.tool_by_name(tool_name)
        if spec is None or not spec.capability:
            return self._deny(
                ctx,
                tool_name,
                f"工具 `{tool_name}` 未声明 capability",
                RULE_CAPABILITY,
            )
        return None

    def _check_step(self, ctx: RunContext, tool_name: str) -> Decision | None:
        """4. 步骤游标：目标工具当前是否可达（§8.3）。

        先推进游标（已完成 / 被跳过的 step 让位），再判可达性。
        """
        ctx.advance_cursor()
        kind, reason = ctx.classify_reachability(tool_name)
        if kind == "ok":
            return None
        rule = RULE_STEP
        if kind == "skip":
            return self._deny(ctx, tool_name, reason, rule)
        return self._deny(ctx, tool_name, reason, rule)

    def _check_constraints(
        self, ctx: RunContext, tool_name: str, arguments: dict[str, Any]
    ) -> Decision | None:
        """5. 业务约束：确定性求值，fail-closed（§7.4）。"""
        spec = self.policy.tool_by_name(tool_name)
        constraints = spec.constraints if spec else None
        result = evaluate_constraints(arguments, constraints)
        if not result.ok:
            return self._deny(
                ctx,
                tool_name,
                "；".join(result.messages()),
                RULE_CONSTRAINTS,
            )
        # 每工具调用次数上限（约束里的 `max_calls_per_run`）
        max_calls = (constraints or {}).get("max_calls_per_run")
        if isinstance(max_calls, int) and ctx.call_count(tool_name) >= max_calls:
            return self._deny(
                ctx,
                tool_name,
                f"工具 `{tool_name}` 在本次 run 内调用次数已达上限"
                f"（{max_calls}）",
                RULE_CONSTRAINTS,
            )
        return None

    def _check_permissions(
        self, ctx: RunContext, tool_name: str, arguments: dict[str, Any]
    ) -> Decision | None:
        """6. 权限范围：路径 / 主机 / 命令（治理块范围 + PermissionSet）。

        治理块的 `allowed_paths` / `allowed_hosts` 与 `PermissionSet` **同时生效**
        ——任一不允许即拒绝（§7.2 第 6 步）。
        """
        spec = self.policy.tool_by_name(tool_name)
        capability = spec.capability if spec else "read"
        mode = "write" if capability in ("write", "payment", "destructive") else "read"

        target = arguments.get("path") or arguments.get("file_path")
        if target:
            resolved = self._resolve_path(str(target))
            allowed_paths = self.policy.allowed_paths
            if allowed_paths and not _within_any(resolved, allowed_paths):
                return self._deny(
                    ctx,
                    tool_name,
                    "路径不在治理块 allowed_paths 范围内",
                    RULE_PERMISSIONS,
                )
            if self.permissions is not None and not self.permissions.is_path_allowed(
                str(resolved), mode
            ):
                return self._deny(
                    ctx,
                    tool_name,
                    f"路径越界（{mode}）：{resolved}",
                    RULE_PERMISSIONS,
                )
            # 文件校验（从 ToolGateHook 迁入，§7.1）：写类工具必过
            if mode == "write":
                decision = self._check_write_target(ctx, tool_name, str(target))
                if decision is not None:
                    return decision

        command = arguments.get("command")
        if command:
            decision = self._check_command(ctx, tool_name, str(command))
            if decision is not None:
                return decision

        host = arguments.get("host") or arguments.get("url")
        if host:
            hostname = _hostname(str(host))
            if self.policy.allowed_hosts and not _host_allowed(
                hostname, self.policy.allowed_hosts
            ):
                return self._deny(
                    ctx,
                    tool_name,
                    "目标主机不在治理块 allowed_hosts 范围内",
                    RULE_PERMISSIONS,
                )
            if (
                self.permissions is not None
                and hostname
                and not self.permissions.is_host_allowed(hostname)
            ):
                return self._deny(
                    ctx,
                    tool_name,
                    f"主机越界：{hostname}",
                    RULE_PERMISSIONS,
                )
        return None

    def _resolve_path(self, target: str) -> Path:
        """把路径解析为绝对路径（相对路径按工作目录解析）。"""
        path = Path(target).expanduser()
        if not path.is_absolute():
            base = self.working_directory or Path.cwd()
            path = base / path
        try:
            return path.resolve()
        except OSError:
            return path

    def _check_command(
        self, ctx: RunContext, tool_name: str, command: str
    ) -> Decision | None:
        """命令校验：PermissionSet 白名单 + 沙箱阻断模式（fail-closed）。"""
        if self.permissions is not None and not self.permissions.is_command_allowed(
            command
        ):
            return self._deny(
                ctx,
                tool_name,
                "命令不在允许范围内",
                RULE_PERMISSIONS,
            )
        if self.sandbox is not None:
            try:
                valid, reason = self.sandbox.validate_command(command)
            except Exception as exc:  # noqa: BLE001 — fail-closed
                return self._deny(
                    ctx,
                    tool_name,
                    f"命令校验出错（fail-closed）：{exc}",
                    RULE_PERMISSIONS,
                )
            if not valid:
                return self._deny(
                    ctx,
                    tool_name,
                    f"命令被沙箱拒绝：{reason}",
                    RULE_PERMISSIONS,
                )
        return None

    def _check_write_target(
        self, ctx: RunContext, tool_name: str, target: str
    ) -> Decision | None:
        """写目标校验：FileInputValidator + 危险路径（fail-closed）。"""
        if self.file_validator is not None:
            try:
                result = self.file_validator.validate_path(target)
            except Exception as exc:  # noqa: BLE001 — fail-closed
                return self._deny(
                    ctx,
                    tool_name,
                    f"文件校验出错（fail-closed）：{exc}",
                    RULE_PERMISSIONS,
                )
            if not result.valid:
                reasons = "；".join(result.errors or ["文件校验失败"])
                return self._deny(
                    ctx,
                    tool_name,
                    f"写入目标被拒绝：{reasons}",
                    RULE_PERMISSIONS,
                )
        if self.sandbox is not None:
            try:
                ok, reason = self.sandbox.validate_path_write(target)
            except Exception as exc:  # noqa: BLE001 — fail-closed
                return self._deny(
                    ctx,
                    tool_name,
                    f"写入目标校验出错（fail-closed）：{exc}",
                    RULE_PERMISSIONS,
                )
            if not ok:
                return self._deny(
                    ctx,
                    tool_name,
                    f"写入目标被拒绝：{reason}",
                    RULE_PERMISSIONS,
                )
        return None

    def _check_limits(
        self, ctx: RunContext, tool_name: str, timestamp: float
    ) -> Decision | None:
        """7. 限额：run 总次数 / 速率（§9.1）。"""
        if ctx.check_run_limit():
            return self._deny(
                ctx,
                tool_name,
                "超出单次 run 工具调用总数上限",
                RULE_LIMITS,
            )
        if ctx.check_rate_limit(timestamp):
            return self._deny(
                ctx,
                tool_name,
                "超出速率上限",
                RULE_LIMITS,
            )
        return None

    def _check_approval(
        self, ctx: RunContext, tool_name: str, arguments: dict[str, Any]
    ) -> Decision | None:
        """8. 审批关卡：按 capability 定档（§7.3）。"""
        if not self.policy.requires_approval(tool_name):
            return None
        if self.approval is None:
            # 没有审批通道 → fail-closed：不可放行未审批的高风险调用
            return self._deny(
                ctx,
                tool_name,
                "该工具需要人工审批，但审批通道不可用",
                RULE_APPROVAL,
            )
        approved, reason = self.approval.request(
            ctx,
            tool_name,
            arguments,
            spec=self.policy.tool_by_name(tool_name),
        )
        if not approved:
            decision = self._deny(ctx, tool_name, reason, RULE_APPROVAL)
            if "超时" in reason:
                count = ctx.bump_signal("approval_timeout")
                self._record_signal(ctx, "approval_timeout", count)
            return decision
        return None

    # -- 事件 -------------------------------------------------------------

    def _record_decision(
        self,
        ctx: RunContext,
        tool_name: str,
        decision: str,
        reason: str,
        *,
        step_id: str | None = None,
        duration_ms: int | None = None,
        outcome: str | None = None,
    ) -> None:
        if self.event_log is None:
            return
        self.event_log.write_decision(
            ctx,
            tool_name,
            decision,
            reason,
            step_id=step_id or self._current_step_id(ctx, tool_name),
            duration_ms=duration_ms,
            outcome=outcome,
        )

    def _record_signal(self, ctx: RunContext, signal: str, count: int) -> None:
        if self.event_log is None:
            return
        self.event_log.write(
            "signal",
            run_id=ctx.run_id,
            agent_id=self.policy.agent_id,
            signal=signal,
            count=count,
        )

    def record_result(
        self,
        ctx: RunContext,
        tool_name: str,
        *,
        success: bool,
        duration_ms: int,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """执行后写结果事件（流水线第 11 步）并推进 step 状态。

        **产出缺失即失败**（§8.2）：工具声明了产出却没产出 → 该 step 判
        `failure` → 后续 step 不可达。GHA 在此处给空串（分支静默不激活），
        治理里必须是阻断。
        """
        step_id = step_id or self._current_step_id(ctx, tool_name)
        spec = self.policy.tool_by_name(tool_name)
        declared = {o.name for o in (spec.outputs if spec else ())}
        outputs = extract_outputs(metadata or {}, declared)

        outcome = "success" if success else "failure"
        result_error = error

        if success:
            missing = declared - set(outputs)
            if missing:
                outcome = "failure"
                result_error = (
                    "声明的产出未产出：" + "、".join(sorted(missing))
                )
                if step_id:
                    ctx.record_tool_failure(step_id, tool_name)
            elif step_id:
                ctx.record_tool_success(step_id, tool_name, outputs)
                for name in outputs:
                    self._record_fact(ctx, tool_name, name, step_id)
        elif step_id:
            ctx.record_tool_failure(step_id, tool_name)

        if self.event_log is not None:
            self.event_log.write_result(
                ctx,
                tool_name,
                success=outcome == "success",
                duration_ms=duration_ms,
                step_id=step_id,
                outcome=outcome,
                error=result_error,
            )
        if outcome == "success":
            ctx.record_success()

    def _record_fact(
        self, ctx: RunContext, tool_name: str, name: str, step_id: str | None
    ) -> None:
        """事实观测事件：只记事实名与类型，不记事实值（§8.2 / §11.3）。"""
        if self.event_log is None:
            return
        self.event_log.write(
            "fact_observed",
            run_id=ctx.run_id,
            agent_id=self.policy.agent_id,
            tool=tool_name,
            step=step_id,
            fact=name,
        )


# -- 事实抽取（设计稿 §8.2）------------------------------------------------


def _as_text(value: Any) -> str:
    """事实值转文本。布尔用小写 `true` / `false`（与 YAML 解析一致）。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def extract_outputs(
    metadata: dict[str, Any], declared: set[str]
) -> dict[str, str]:
    """从工具结果里抽取事实（§8.2）。

    来源优先级：

    1. ``metadata["outputs"]``：工具显式声明的产出字典
    2. ``metadata["json"]``：MCP 工具的 JSON content（§8.2 要求）
    3. ``metadata`` 顶层键：与**声明的产出名同名**的标量值

    只取声明过的产出名——不把工具返回的任意字段当事实，避免模型用
    未声明字段影响分支判定。
    """
    outputs: dict[str, str] = {}
    raw = metadata.get("outputs")
    if isinstance(raw, dict):
        for name, value in raw.items():
            if name in declared:
                outputs[name] = _as_text(value)
    if not outputs:
        raw_json = metadata.get("json")
        if isinstance(raw_json, dict):
            for name, value in raw_json.items():
                if name in declared:
                    outputs[name] = _as_text(value)
    for name in declared:
        if name in outputs:
            continue
        value = metadata.get(name)
        if isinstance(value, (str, int, float, bool)):
            outputs[name] = _as_text(value)
    return outputs


# -- 路径 / 主机判定 ------------------------------------------------------


def _within_any(path: Path, prefixes: tuple[str, ...]) -> bool:
    """路径是否落在任一前缀内。

    用 `Path` 语义而非字符串前缀——`/data/foo` 不应匹配 `/data/foobar`。
    """
    for prefix in prefixes:
        root = Path(prefix).expanduser()
        if not root.is_absolute():
            root = (Path.cwd() / root).resolve()
        try:
            if path == root or root in path.parents:
                return True
        except OSError:
            continue
    return False


def _hostname(target: str) -> str:
    """从 URL / host 字面量中取主机名（去 scheme、去端口）。"""
    host = target
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0]
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host.strip().lower()


def _host_allowed(hostname: str, allowed: tuple[str, ...]) -> bool:
    """主机是否在允许集合内（支持 `*.example.com` 形式）。"""
    host = hostname.strip().lower()
    for entry in allowed:
        candidate = entry.strip().lower()
        if candidate.startswith("*."):
            if host.endswith(candidate[1:]):
                return True
        elif host == candidate:
            return True
    return False
