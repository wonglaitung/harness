"""Minimal CLI for the Harness SDK.

M6-dep: ships a ``harness doctor --deps`` command that audits the installed
dependency tree for known vulnerabilities (via ``uv pip audit`` or
``pip-audit``). The SDK keeps no built-in CVE database — it delegates to the
platform auditor so remediation stays a human-reviewed, deploy-side concern.

治理 CLI（设计稿 §13.4 / §7.5.3 / §10.2）：

- ``harness governance init <skill>``    生成治理块骨架（含 TODO，不写文件）
- ``harness governance check <skill>``   跑 §6.3 的校验规则，逐条报 file:line
- ``harness governance approve/reject <request_id>``  运行期审批
- ``harness governance suspend/resume/status <agent_id>``  Kill Switch

全部为确定性代码，不调用 LLM。

Example:
    harness doctor --deps
    harness governance check ./skills/report.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# 治理块：YAML 行号定位（`check` 的 file:line 报告）
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[str, int] | None:
    """拆出 frontmatter；返回 `(yaml 文本, 行号偏移)`。"""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), 1
    return None


def _path_parts(field: str) -> list[str]:
    """把 `workflow.steps[2].tools` 拆成路径段。"""
    parts: list[str] = []
    for chunk in field.split("."):
        match = re.match(r"^([^\[\]]+)\[([^\]]+)\]$", chunk)
        if match:
            parts.extend([match.group(1), match.group(2)])
        else:
            parts.append(chunk)
    return parts


def _walk(node: Any, parts: list[str]) -> Any:
    """在 YAML 节点树里按路径定位；找不到时返回最深的已知节点。"""
    deepest = node
    for part in parts:
        if isinstance(node, yaml.MappingNode):
            found = None
            for key_node, value_node in node.value:
                if isinstance(key_node, yaml.ScalarNode) and str(key_node.value) == part:
                    found = (key_node, value_node)
                    break
            if found is None:
                return deepest
            key_node, node = found
            deepest = key_node
        elif isinstance(node, yaml.SequenceNode):
            if part.isdigit() and int(part) < len(node.value):
                node = node.value[int(part)]
                deepest = node
                continue
            matched = None
            for item in node.value:
                if not isinstance(item, yaml.MappingNode):
                    continue
                for key_node, value_node in item.value:
                    if (
                        isinstance(key_node, yaml.ScalarNode)
                        and str(key_node.value) in ("name", "id")
                        and str(value_node.value) == part
                    ):
                        matched = item
                        break
                if matched is not None:
                    break
            if matched is None:
                for item in node.value:
                    if isinstance(item, yaml.ScalarNode) and str(item.value) == part:
                        matched = item
                        break
            if matched is None:
                return deepest
            node = matched
            deepest = node
        else:
            return deepest
    return deepest


def _line_for(root: Any, offset: int, field: str) -> int | None:
    """治理块字段 → 文件行号（1-based）。"""
    if root is None:
        return None
    node = root
    if isinstance(node, yaml.MappingNode):
        found = None
        for key_node, value_node in node.value:
            if isinstance(key_node, yaml.ScalarNode) and str(key_node.value) == "governance":
                found = value_node
                break
        if found is None:
            return None
        node = found
    target = _walk(node, _path_parts(field))
    if target is None:
        return None
    return int(target.start_mark.line) + 1 + offset


# ---------------------------------------------------------------------------
# governance init / check
# ---------------------------------------------------------------------------


def _load_skill(path: Path) -> Any:
    from harness.skills.base import Skill

    return Skill.from_file(path)


def _allowed_tools(skill: Any) -> list[str]:
    tools = getattr(skill, "tools", None)
    allowed = getattr(tools, "allowed", None) or []
    return list(allowed)


def _init_skeleton(skill: Any) -> str:
    allowed = _allowed_tools(skill) or ["TODO_tool_name"]
    tools_yaml = "\n".join(
        f"    - name: {name}\n      capability: TODO\n      idempotent: TODO"
        for name in allowed
    )
    # 骨架只做机械绑定：把工具清单放进唯一 step，避免无谓的规则 27/28
    # 噪音（业务步骤链必须由人画，§13.4）。
    step_tools = ", ".join(allowed)
    return (
        "governance:\n"
        f"  agent_id: {getattr(skill, 'name', 'TODO_agent_id')}\n"
        "  version: 0.1.0\n"
        "  approved_by: TODO\n"
        "  business_intent: TODO\n"
        "  owners:\n"
        "    accountable: TODO\n"
        "    technical: TODO\n"
        "  material: false\n"
        "  tools:\n"
        f"{tools_yaml}\n"
        "  workflow:\n"
        "    steps:\n"
        "      - id: step_1\n"
        f"        tools: [{step_tools}]\n"
        "  limits:\n"
        "    max_tool_calls_per_run: 50\n"
        "    max_calls_per_minute: 20\n"
        "    max_tokens_per_run: 200000\n"
    )


NINE_STEPS = (
    "① 圈定工具（机器：取自技能 tools.allowed）\n"
    "② 定能力分级：read/write/payment/destructive（人）\n"
    "③ 定幂等性（人；不确定填 false）\n"
    "④ 画业务步骤链（人）\n"
    "⑤ 定完成条件（机器出骨架，人确认）\n"
    "⑥ 定分支条件：判据必须来自工具产出（人）\n"
    "⑦ 定参数约束（人）\n"
    "⑧ 定限额与审批（机器出默认值，人调整）\n"
    "⑨ 补产出声明（人）"
)


def governance_init(skill_path: str) -> int:
    """生成治理块骨架。含 TODO 时**不写文件**（§13.4）。"""
    path = Path(skill_path)
    try:
        skill = _load_skill(path)
    except Exception as exc:  # noqa: BLE001 — 命令行入口统一报错
        print(f"无法读取技能文件 {path}：{exc}", file=sys.stderr)
        return 1
    if getattr(skill, "governance", None):
        print(
            f"{path} 已存在治理块；init 不覆盖已有授权书。",
            file=sys.stderr,
        )
        return 1

    skeleton = _init_skeleton(skill)
    print(skeleton)
    print(
        "骨架含 TODO，**未写入文件**（规则 26：占位符视为未完成）。\n"
        "请把下列 `governance:` 块并入技能 frontmatter 后逐项填写：",
        file=sys.stderr,
    )
    print(NINE_STEPS, file=sys.stderr)
    if not _allowed_tools(skill):
        print(
            "注意：技能未声明 tools.allowed，工具清单需要人工补齐（§6.2.1）。",
            file=sys.stderr,
        )
    return 0


def governance_check(skill_path: str) -> int:
    """跑校验规则；非零退出，逐条报 `file:line` + 规则号（§13.4）。"""
    from harness.governance import GovernanceError, validate_governance_block
    from harness.governance.schema import parse_governance_block
    from harness.skills.base import Skill

    path = Path(skill_path)
    try:
        text = path.read_text(encoding="utf-8")
        skill = Skill.from_file(path)
    except Exception as exc:  # noqa: BLE001
        print(f"{path}:1: 无法读取技能文件：{exc}", file=sys.stderr)
        return 1

    raw = getattr(skill, "governance", None)
    if not raw:
        print(f"{path}:1: 治理块缺失（strict 下拒绝，§4.3）", file=sys.stderr)
        return 1

    frontmatter = _split_frontmatter(text)
    offset = frontmatter[1] if frontmatter else 0
    root: Any = None
    if frontmatter:
        try:
            root = yaml.compose(frontmatter[0])
        except yaml.YAMLError:
            root = None

    try:
        block = parse_governance_block(raw)
    except GovernanceError as exc:
        print(f"{path}:1: 解析失败：{exc}", file=sys.stderr)
        return 1

    from harness.governance.assembly import _skill_allowed_tools

    result = validate_governance_block(
        block,
        skill_allowed_tools=_skill_allowed_tools(skill),
        known_tool_names=None,  # 离线：规则 1 的注册表校验需要运行时信息
    )
    if result.ok:
        print(f"{path}: 校验通过（{len(block.tools)} 个工具，"
              f"{len(block.workflow.steps)} 个 step）")
        return 0

    for error in result.errors:
        line = _line_for(root, offset, error.field)
        location = f"{path}:{line}" if line else f"{path}:?"
        print(f"{location}: 规则 {error.rule}｜{error.field}：{error.message}",
              file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# governance approve / reject / suspend / resume / status
# ---------------------------------------------------------------------------


def governance_decide(
    request_id: str,
    *,
    approved: bool,
    actor: str,
    reason: str,
    run_id: str | None,
) -> int:
    from harness.governance.approval import ApprovalManager

    manager = ApprovalManager()
    ok = manager.decide(
        request_id,
        approved=approved,
        actor=actor,
        reason=reason,
        run_id=run_id,
    )
    if not ok:
        print(
            f"审批请求 {request_id} 不存在或已过期，未做决定。",
            file=sys.stderr,
        )
        return 1
    print(
        f"{'已批准' if approved else '已拒绝'} {request_id}"
        f"（actor={actor or 'anonymous'}）"
    )
    return 0


def governance_control(
    agent_id: str, action: str, *, reason: str, actor: str
) -> int:
    from harness.governance.control import ControlPlane

    plane = ControlPlane()
    if action == "status":
        state = plane.read(agent_id)
        print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if action == "suspend":
        state = plane.suspend(agent_id, reason=reason, actor=actor)
    else:
        state = plane.resume(agent_id, reason=reason, actor=actor)
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def doctor_deps() -> int:
    """Audit dependencies for known CVEs.

    Returns an int exit code suitable for ``sys.exit``.
    """
    if shutil.which("uv"):
        cmd = ["uv", "pip", "audit"]
    elif shutil.which("pip-audit"):
        cmd = ["pip-audit"]
    else:
        print(
            "No dependency auditor found. Install 'uv' or 'pip-audit' to run "
            "dependency CVE checks (harness does not bundle a CVE database)."
        )
        return 1
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="Harness SDK CLI")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Run diagnostics")
    doctor.add_argument(
        "--deps", action="store_true", help="Audit dependencies for known CVEs"
    )

    governance = sub.add_parser("governance", help="治理块与运行期治理")
    gov = governance.add_subparsers(dest="governance_command")

    init = gov.add_parser("init", help="生成治理块骨架（含 TODO，不写文件）")
    init.add_argument("skill", help="技能文件路径")

    check = gov.add_parser("check", help="校验治理块（29 条规则）")
    check.add_argument("skill", help="技能文件路径")

    for name, help_text in (("approve", "批准审批请求"), ("reject", "拒绝审批请求")):
        decide = gov.add_parser(name, help=help_text)
        decide.add_argument("request_id", help="审批请求 id（如 apr-0001）")
        decide.add_argument("--actor", default="", help="操作人（自由文本）")
        decide.add_argument("--reason", default="", help="原因")
        decide.add_argument("--run-id", default=None, help="限定 run（可选）")

    for name, help_text in (
        ("suspend", "暂停 Agent"),
        ("resume", "恢复 Agent"),
        ("status", "查看 Agent 控制状态"),
    ):
        control = gov.add_parser(name, help=help_text)
        control.add_argument("agent_id", help="治理身份 agent_id")
        control.add_argument("--reason", default="", help="原因")
        control.add_argument("--actor", default="", help="操作人（自由文本）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        if args.deps:
            return doctor_deps()
        parser.print_help()
        return 0

    if args.command == "governance":
        action = args.governance_command
        if action == "init":
            return governance_init(args.skill)
        if action == "check":
            return governance_check(args.skill)
        if action in ("approve", "reject"):
            return governance_decide(
                args.request_id,
                approved=action == "approve",
                actor=args.actor,
                reason=args.reason,
                run_id=args.run_id,
            )
        if action in ("suspend", "resume", "status"):
            return governance_control(
                args.agent_id,
                action,
                reason=args.reason,
                actor=args.actor,
            )
        parser.parse_args(["governance", "--help"])
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
