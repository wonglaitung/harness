"""治理相关的创作期/运维期命令（设计稿 §13.4 / §7.5.3 / §10.2）。

- ``harness governance init <file|dir>`` 迁移工具：生成治理块并写入，能自动填的
  自动填（内置工具的能力/幂等性来自代码声明），只能人填的保留 TODO 并在报告里
  标「需手工补充」；``--dry-run`` 只预览不写
- ``harness governance check <skill>``   跑 §6.3 的校验规则，逐条报 file:line
- ``harness governance approve/reject <request_id>``  运行期审批
- ``harness governance suspend/resume/status <agent_id>``  Kill Switch

全部为确定性代码，不调用 LLM；治理的强制力在 SDK 运行时
（`AgentHarness` + `GovernanceGateway`），这些命令只负责生成与运维。
"""

from __future__ import annotations

import json
import os
import re
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


def _builtin_tool_declarations() -> dict[str, tuple[str, bool]]:
    """内置工具的 `(capability, idempotent)` 声明。

    自研/内置工具的治理声明以**代码为准**（§7.3 / §6.4.2），因此迁移工具
    可以直接回填，不需要人再抄一遍。MCP 工具只能在治理块里声明，代码侧
    查不到，调用方应保留 TODO 并在报告里标「需手工补充」。
    """
    import inspect

    from harness.tools import builtins as builtin_tools
    from harness.tools.base import Tool

    declarations: dict[str, tuple[str, bool]] = {}
    for _, cls in inspect.getmembers(builtin_tools, inspect.isclass):
        if not issubclass(cls, Tool) or cls is Tool:
            continue
        try:
            tool = cls()
        except Exception:  # noqa: BLE001 — 无默认构造的工具不参与回填
            continue
        capability = getattr(tool, "capability", None)
        idempotent = getattr(tool, "idempotent", None)
        if capability and isinstance(idempotent, bool):
            declarations[tool.name] = (capability, idempotent)
    return declarations


def _yaml_scalar(value: str) -> str:
    """安全地写一个 YAML 标量（普通名字保持可读，特殊字符才加引号）。"""
    if re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _init_block(
    skill: Any,
    agent_id: str,
    declarations: dict[str, tuple[str, bool]],
) -> tuple[str, list[str], list[str]]:
    """生成治理块文本，并返回 `(文本, 需手工补充, 需确认)`。"""
    allowed = _allowed_tools(skill)
    todo = [
        "approved_by",
        "business_intent",
        "owners.accountable",
        "owners.technical",
    ]
    review = [
        "workflow.steps（当前为单 step 机械绑定，业务步骤链需人工确认）",
    ]

    if allowed:
        tool_lines: list[str] = []
        for name in allowed:
            declaration = declarations.get(name)
            capability: str
            idempotent: str | bool
            if declaration is None:
                capability, idempotent = "TODO", "TODO"
                todo.append(f"tools[{name}].capability/idempotent")
            else:
                capability, idempotent = declaration
            rendered_idempotent = (
                str(idempotent).lower() if isinstance(idempotent, bool) else str(idempotent)
            )
            tool_lines.append(
                f"    - name: {_yaml_scalar(name)}\n"
                f"      capability: {capability}\n"
                f"      idempotent: {rendered_idempotent}"
            )
        tools_yaml = "\n".join(tool_lines)
        step_tools = ", ".join(_yaml_scalar(name) for name in allowed)
    else:
        todo.append("tools（技能未声明 tools.allowed，需手工补充）")
        tools_yaml = "    - name: TODO_tool_name\n      capability: TODO\n      idempotent: TODO"
        step_tools = "TODO_tool_name"

    text = (
        "governance:\n"
        f"  agent_id: {_yaml_scalar(agent_id)}\n"
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
    return text, todo, review


def _insert_governance(text: str, block: str) -> str | None:
    """把治理块插到 frontmatter 末尾；不重渲染 YAML，保留原有注释。"""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            head = lines[:index]
            if head and not head[-1].endswith("\n"):
                head[-1] += "\n"
            return "".join(head) + block + "".join(lines[index:])
    return None


def _skill_files(path: Path) -> list[Path]:
    """技能文件：单个文件直接返回；目录递归找带 frontmatter 的 `.md`。"""
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    files: list[Path] = []
    for candidate in sorted(path.rglob("*.md")):
        relative = candidate.relative_to(path)
        if any(part.startswith(".") for part in relative.parts):
            continue
        try:
            frontmatter = _split_frontmatter(candidate.read_text(encoding="utf-8"))
        except OSError:
            continue
        if frontmatter is None:
            continue
        try:
            data = yaml.safe_load(frontmatter[0])
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("name"):
            files.append(candidate)
    return files


NINE_STEPS = (
    "① 圈定工具（机器：取自技能 tools.allowed）\n"
    "② 定能力分级：read/write/payment/destructive（内置工具自动回填，MCP 需人填）\n"
    "③ 定幂等性（内置工具自动回填，MCP 需人填）\n"
    "④ 画业务步骤链（人）\n"
    "⑤ 定完成条件（机器出骨架，人确认）\n"
    "⑥ 定分支条件：判据必须来自工具产出（人）\n"
    "⑦ 定参数约束（人）\n"
    "⑧ 定限额与审批（机器出默认值，人调整）\n"
    "⑨ 补产出声明（人）"
)


def _init_report(
    path: Path, todo: list[str], review: list[str], *, dry_run: bool
) -> None:
    prefix = "预览" if dry_run else "写入"
    if todo:
        print(f"{path} 需手工补充：{'、'.join(todo)}", file=sys.stderr)
    else:
        print(f"{path} 无 TODO", file=sys.stderr)
    for item in review:
        print(f"{path} 需确认：{item}", file=sys.stderr)
    print(
        f"{prefix}后请跑 `harness governance check {path}` 复核（规则 26 会拒绝 TODO）。",
        file=sys.stderr,
    )


def governance_init(
    skill_path: str,
    *,
    agent_id: str | None = None,
    dry_run: bool = False,
) -> int:
    """迁移工具：生成并写入治理块（§13.4）。

    - 能自动填的自动填：工具清单取自 `tools.allowed`，内置工具的
      `capability`/`idempotent` 取自代码声明；
    - 只能人填的保留 `TODO`，在报告里逐项标「需手工补充」；
    - 默认写入；`--dry-run` 只预览。写入不整体重渲染 YAML，保留原注释。
    """
    path = Path(skill_path)
    targets = _skill_files(path)
    if not targets:
        print(f"未找到技能文件：{path}", file=sys.stderr)
        return 1

    declarations = _builtin_tool_declarations()
    resolved_agent_id = (
        agent_id or os.getenv("HARNESS_GOVERNANCE_AGENT_ID") or ""
    )
    failed = 0
    print(NINE_STEPS, file=sys.stderr)

    for target in targets:
        try:
            skill = _load_skill(target)
            text = target.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 — 命令行入口统一报错
            print(f"无法读取技能文件 {target}：{exc}", file=sys.stderr)
            failed += 1
            continue

        if getattr(skill, "governance", None):
            print(f"{target} 跳过：已存在治理块（init 不覆盖已有授权书）")
            continue

        target_agent_id = resolved_agent_id or getattr(skill, "name", "TODO_agent_id")
        block, todo, review = _init_block(skill, target_agent_id, declarations)
        if not resolved_agent_id:
            review.insert(
                0,
                f"agent_id（当前取技能名 `{target_agent_id}`，请确认治理身份）",
            )

        if dry_run:
            print(f"--- {target} ---")
            print(block, end="")
            _init_report(target, todo, review, dry_run=True)
            continue

        updated = _insert_governance(text, block)
        if updated is None:
            print(f"{target}:1: 缺少 YAML frontmatter，无法写入治理块", file=sys.stderr)
            failed += 1
            continue
        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as exc:
            print(f"写入失败 {target}：{exc}", file=sys.stderr)
            failed += 1
            continue

        print(f"{target} 已写入治理块")
        _init_report(target, todo, review, dry_run=False)
        if not todo and governance_check(str(target)) != 0:
            failed += 1

    return 1 if failed else 0


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

    from harness.governance import skill_allowed_tools

    result = validate_governance_block(
        block,
        skill_allowed_tools=skill_allowed_tools(skill),
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
