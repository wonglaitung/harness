"""治理装配：把技能上的治理块编译成运行策略。

在 `AgentHarness` 初始化时调用（strict 开启时）。语义见设计稿：

- §4.3 治理块在 strict 下是**硬门槛**：缺失或校验不过 → 拒绝注册与执行
- §6.4.1 治理身份由部署方预先指定，**不随运行时技能命中变化**——
  否则提示词注入可改变本次运行的授权集
- §6.4.2 多份治理块按确定性规则合成（见 `harness.governance.policy`）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from harness.governance.policy import PolicySnapshot, compile_policy
from harness.governance.schema import (
    GovernanceBlock,
    GovernanceError,
    parse_governance_block,
)
from harness.governance.validation import validate_governance_block

logger = logging.getLogger(__name__)


@dataclass
class GovernanceSetup:
    """治理装配结果。"""

    policy: PolicySnapshot | None = None
    errors: tuple[str, ...] = ()
    blocks: tuple[GovernanceBlock, ...] = ()
    # 被装配的技能名 → 其治理块 agent_id
    skill_agents: dict[str, str] = field(default_factory=dict)


def skill_allowed_tools(skill: Any) -> set[str] | None:
    """技能的 `tools.allowed`（治理块 tools 的上界，§6.2.1）。

    None 表示技能未声明 → 不设上界。
    """
    tools = getattr(skill, "tools", None)
    if tools is None:
        return None
    allowed = getattr(tools, "allowed", None)
    if not allowed:
        return None
    return set(allowed)


def assemble_governance(
    skills: list[Any],
    *,
    agent_id: str | None,
    known_tool_names: set[str] | None = None,
) -> GovernanceSetup:
    """从技能列表装配治理策略。

    Args:
        skills: 技能实例列表（需有 `.governance` 与 `.tools.allowed`）
        agent_id: 部署方指定的治理身份。None → 无治理身份
        known_tool_names: 工具注册表中已登记的工具名（规则 1）

    Returns:
        `GovernanceSetup`。`policy` 为 None 表示未装配出策略（此时 `errors`
        说明原因）。**fail-closed**：有错误就不产出策略。
    """
    errors: list[str] = []
    blocks: list[GovernanceBlock] = []
    skill_agents: dict[str, str] = {}

    if not agent_id:
        return GovernanceSetup(
            policy=None,
            errors=("治理身份未指定（governance_agent_id / HARNESS_GOVERNANCE_AGENT_ID）",),
        )

    for skill in skills:
        raw = getattr(skill, "governance", None)
        if raw is None:
            continue
        skill_name = getattr(skill, "name", "?")
        try:
            block = parse_governance_block(raw)
        except GovernanceError as exc:
            errors.append(f"技能 `{skill_name}` 的治理块解析失败：{exc}")
            continue
        # 治理身份一致性：只有与部署指定一致的治理块参与本 run
        if block.agent_id != agent_id:
            logger.debug(
                "跳过治理身份不匹配的技能 %s：%s != %s",
                skill_name,
                block.agent_id,
                agent_id,
            )
            continue
        result = validate_governance_block(
            block,
            skill_allowed_tools=skill_allowed_tools(skill),
            known_tool_names=known_tool_names,
        )
        if not result.ok:
            errors.extend(
                f"技能 `{skill_name}` 的治理块校验失败：{msg}"
                for msg in result.messages()
            )
            continue
        blocks.append(block)
        skill_agents[skill_name] = block.agent_id

    if not blocks:
        if not errors:
            errors.append(
                f"治理身份 `{agent_id}` 下没有可用治理块"
                "（治理块缺失即拒绝，§4.3）"
            )
        return GovernanceSetup(policy=None, errors=tuple(errors))

    try:
        policy = compile_policy(blocks)
    except GovernanceError as exc:
        errors.append(f"治理块合成失败：{exc}")
        return GovernanceSetup(policy=None, errors=tuple(errors))

    return GovernanceSetup(
        policy=policy,
        errors=tuple(errors),
        blocks=tuple(blocks),
        skill_agents=skill_agents,
    )
