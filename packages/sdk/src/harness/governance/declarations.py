"""工具治理声明的注册期校验（设计稿 §7.3 / §7.4）。

自研工具在**代码里**声明 `capability` / `idempotent` / `constraints`；
MCP 工具在治理块里声明。两处声明必须一致——不一致说明登记有误，
**编译期拒绝**（§6.4.2 capability 冲突同理），不能猜哪个对。

**缺声明即拒绝注册**（§7.3）：不保留 `unknown` 后门——"以后再补"在治理
场景等于"永远不补"。
"""

from __future__ import annotations

from typing import Any

from harness.governance.constraints import validate_constraint_schema

# 合法的能力分级（§7.3）
CAPABILITIES = ("read", "write", "payment", "destructive")


def validate_tool_declaration(tool: Any) -> list[str]:
    """校验一个工具**代码侧**的治理声明。

    Returns:
        问题列表，空列表表示合法。
    """
    problems: list[str] = []
    name = getattr(tool, "name", "?")
    capability = getattr(tool, "capability", None)
    if not capability:
        problems.append(f"工具 `{name}` 未声明 capability")
    elif capability not in CAPABILITIES:
        problems.append(
            f"工具 `{name}` 的 capability `{capability}` 非法"
            f"（只能是 {list(CAPABILITIES)}）"
        )
    idempotent = getattr(tool, "idempotent", None)
    if idempotent is None:
        problems.append(f"工具 `{name}` 未声明 idempotent")
    elif not isinstance(idempotent, bool):
        problems.append(f"工具 `{name}` 的 idempotent 必须是布尔值")
    for problem in validate_constraint_schema(getattr(tool, "constraints", None)):
        problems.append(f"工具 `{name}` 的 constraints 非法：{problem}")
    return problems


def check_declaration_conflicts(tool: Any, spec: Any) -> list[str]:
    """核对工具的代码声明与治理块声明是否一致。

    Args:
        tool: 工具实例
        spec: 治理块里的 `ToolSpec`

    Returns:
        冲突列表，空列表表示一致。**只核对两侧都声明了的字段**——
        治理块是运行期的唯一权威，代码侧缺声明由注册期校验兜底。
    """
    problems: list[str] = []
    name = getattr(tool, "name", getattr(spec, "name", "?"))
    code_capability = getattr(tool, "capability", None)
    block_capability = getattr(spec, "capability", None)
    if code_capability and block_capability and code_capability != block_capability:
        problems.append(
            f"工具 `{name}` 的代码声明 capability=`{code_capability}` "
            f"与治理块 `{block_capability}` 冲突"
        )
    code_idempotent = getattr(tool, "idempotent", None)
    block_idempotent = getattr(spec, "idempotent", None)
    if (
        code_idempotent is not None
        and block_idempotent is not None
        and bool(code_idempotent) != bool(block_idempotent)
    ):
        problems.append(
            f"工具 `{name}` 的代码声明 idempotent=`{code_idempotent}` "
            f"与治理块 `{block_idempotent}` 冲突"
        )
    return problems
