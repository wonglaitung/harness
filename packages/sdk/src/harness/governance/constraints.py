"""业务参数约束的确定性求值（设计稿 §6.4）。

约束是工具的**内在属性**——与工具定义放在一起（自研工具在代码里，MCP 工具在
治理块里），由网关确定性求值。

设计要点：
- **fail-closed**：约束求值出错（类型不符、解析失败）→ 拒绝，不放行
- **不记实际值**：违反时只记字段名与判定结论（脱敏口径，§10.3）
- 约束与工具 Schema 冲突 → 注册期报错，不留到运行期
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

# 约束支持的形态（与设计稿 §6.4 的 `ToolConstraints` 对应）
# required_fields: list[str]
# numeric_ranges: {field: (min, max)}
# allowed_values: {field: [v1, v2, ...]}
# amount_field / max_amount / min_amount
# max_calls_per_run: int
# deny_paths: list[str]


@dataclass(frozen=True)
class ConstraintViolation:
    """一条约束违反。"""

    field_name: str
    reason: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.reason}"


@dataclass(frozen=True)
class ConstraintResult:
    """约束求值结果。"""

    violations: tuple[ConstraintViolation, ...] = ()
    error: str | None = None  # 求值出错（fail-closed 的原因）

    @property
    def ok(self) -> bool:
        return not self.violations and self.error is None

    def messages(self) -> list[str]:
        if self.error is not None:
            return [f"约束求值失败（fail-closed）：{self.error}"]
        return [str(v) for v in self.violations]


def _as_number(value: Any, field_name: str) -> float | None:
    """把值转数字；不可转换返回 None（调用方按 fail-closed 处理）。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """把 glob 模式转成正则（`**` 跨目录，`*` 不跨目录）。"""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
            continue
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        ch = pattern[i]
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _matches_deny(target: str, pattern: str) -> bool:
    """目标路径是否命中禁止清单。

    - 普通路径：前缀匹配（`/etc` 命中 `/etc/passwd`，但不命中 `/etcx`）
    - glob 模式：匹配目标本身或其任一上级目录
      （`**/.git/**` 命中 `/repo/.git/config`）
    """
    normalized = os.path.normpath(os.path.expanduser(target))
    expanded = os.path.normpath(os.path.expanduser(pattern))
    if any(ch in expanded for ch in "*?["):
        regex = _glob_to_regex(expanded)
        candidates = [normalized]
        parts = normalized.split(os.sep)
        for i in range(1, len(parts)):
            candidates.append(os.sep.join(parts[:i]))
        return any(regex.match(candidate) for candidate in candidates)
    return normalized == expanded or normalized.startswith(expanded + os.sep)


def evaluate_constraints(
    arguments: dict[str, Any],
    constraints: dict[str, Any] | None,
) -> ConstraintResult:
    """对工具参数求值业务约束。

    Args:
        arguments: 工具调用的**最终态**参数（§6.1）
        constraints: 约束声明；None 或空 → 无约束

    Returns:
        `ConstraintResult`。`ok=False` 时必须拒绝该次调用。
    """
    if not constraints:
        return ConstraintResult()

    violations: list[ConstraintViolation] = []

    # 必填字段
    for name in constraints.get("required_fields", []) or []:
        if name not in arguments:
            violations.append(
                ConstraintViolation(name, "缺少必填参数")
            )

    # 枚举取值
    for name, allowed in (constraints.get("allowed_values") or {}).items():
        if name not in arguments:
            continue
        value = arguments[name]
        if value not in allowed:
            violations.append(
                ConstraintViolation(
                    name,
                    f"取值不在允许集合内（允许 {len(allowed)} 个取值）",
                )
            )

    # 数值区间
    for name, bounds in (constraints.get("numeric_ranges") or {}).items():
        if name not in arguments:
            continue
        try:
            low, high = bounds
        except (TypeError, ValueError):
            return ConstraintResult(
                error=f"数值区间声明非法：{name}（应为 (min, max)）"
            )
        numeric = _as_number(arguments[name], name)
        if numeric is None:
            return ConstraintResult(
                error=f"参数 `{name}` 不是数值，无法求值区间"
            )
        if numeric < low or numeric > high:
            violations.append(
                ConstraintViolation(name, "数值超出允许区间")
            )

    # 金额上下限
    amount_field = constraints.get("amount_field")
    if amount_field and amount_field in arguments:
        numeric = _as_number(arguments[amount_field], amount_field)
        if numeric is None:
            return ConstraintResult(
                error=f"金额字段 `{amount_field}` 不是数值"
            )
        max_amount = constraints.get("max_amount")
        min_amount = constraints.get("min_amount")
        if max_amount is not None and numeric > float(max_amount):
            violations.append(
                ConstraintViolation(amount_field, "金额超出上限")
            )
        if min_amount is not None and numeric < float(min_amount):
            violations.append(
                ConstraintViolation(amount_field, "金额低于下限")
            )

    # 调用次数上限
    max_calls = constraints.get("max_calls_per_run")
    if max_calls is not None and not isinstance(max_calls, int):
        return ConstraintResult(
            error="max_calls_per_run 必须是整数"
        )

    # 禁止路径
    deny_paths = constraints.get("deny_paths") or []
    if deny_paths:
        target = arguments.get("path") or arguments.get("file_path")
        if target:
            for pattern in deny_paths:
                if _matches_deny(str(target), str(pattern)):
                    violations.append(
                        ConstraintViolation("path", "路径命中禁止清单")
                    )
                    break

    return ConstraintResult(violations=tuple(violations))


def validate_constraint_schema(
    constraints: dict[str, Any] | None,
) -> list[str]:
    """注册期校验约束声明自身是否合法（§6.4：冲突在注册期报错）。

    Returns:
        问题列表，空列表表示合法。
    """
    if not constraints:
        return []
    problems: list[str] = []
    for name, bounds in (constraints.get("numeric_ranges") or {}).items():
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            problems.append(f"numeric_ranges.{name} 应为 (min, max)")
            continue
        low, high = bounds
        if _as_number(low, name) is None or _as_number(high, name) is None:
            problems.append(f"numeric_ranges.{name} 的边界必须是数值")
        elif float(low) > float(high):
            problems.append(f"numeric_ranges.{name} 的下界大于上界")
    for name, allowed in (constraints.get("allowed_values") or {}).items():
        if not isinstance(allowed, (list, tuple)) or not allowed:
            problems.append(f"allowed_values.{name} 必须是非空列表")
    amount_field = constraints.get("amount_field")
    if amount_field and constraints.get("max_amount") is None and (
        constraints.get("min_amount") is None
    ):
        problems.append("amount_field 需要配合 max_amount 或 min_amount")
    return problems
