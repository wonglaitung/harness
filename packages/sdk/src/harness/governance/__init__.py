"""治理层：治理声明的解析、校验、编译与运行时上下文。

对应设计稿 `packages/sdk/docs/21-hkma-agentic-governance.md`：

- :mod:`harness.governance.schema` —— 数据模型与 frontmatter 解析
- :mod:`harness.governance.expression` —— GHA 安全子集表达式（解析 + 求值）
- :mod:`harness.governance.validation` —— 29 条校验规则
- :mod:`harness.governance.policy` —— `PolicySnapshot` 编译与多块合成
- :mod:`harness.governance.context` —— run 上下文（run_id / 步骤游标 / 计数）

**治理只在 strict 模式下生效**（设计稿 §4.3）。非 strict 时本包的任何对象都
不应被创建——`AgentHarness` 在 `strict=False` 时完全不触碰治理路径。
"""

from __future__ import annotations

from harness.governance.context import RunContext
from harness.governance.policy import PolicySnapshot, compile_policy
from harness.governance.schema import (
    GovernanceBlock,
    GovernanceError,
    Limits,
    StepSpec,
    ToolOutput,
    ToolSpec,
    WorkflowSpec,
)
from harness.governance.validation import (
    ValidationError,
    ValidationResult,
    validate_governance_block,
)

__all__ = [
    "GovernanceBlock",
    "GovernanceError",
    "Limits",
    "PolicySnapshot",
    "RunContext",
    "StepSpec",
    "ToolOutput",
    "ToolSpec",
    "ValidationError",
    "ValidationResult",
    "WorkflowSpec",
    "compile_policy",
    "validate_governance_block",
]
