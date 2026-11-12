"""`AgentHarness` 治理装配的集成测试。

覆盖设计稿 §4.3：strict=False 不触碰治理路径；strict=True 时治理块是硬门槛。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.sdk.config import HarnessConfig
from harness.sdk.harness import AgentHarness

SKILL_WITH_GOVERNANCE = """---
name: credit-paper-assembler
description: 组装信贷报告初稿
tools:
  allowed: [core_banking_api:read_only, aml_screening:run]
governance:
  agent_id: credit-paper-assembler
  version: 1.2.0
  approved_by: "PR #1284"
  business_intent: 组装信贷报告初稿供信用分析师复核
  owners:
    accountable: Head of Credit Risk
    technical: DevOps Lead A
  material: true
  tools:
    - name: core_banking_api:read_only
      capability: read
      idempotent: true
    - name: aml_screening:run
      capability: write
      idempotent: true
      outputs:
        - name: aml_hit
          from: metadata
          path: aml_hit
  workflow:
    steps:
      - id: collect_data
        tools: [core_banking_api:read_only]
      - id: aml_check
        tools: [aml_screening:run]
  limits:
    max_tool_calls_per_run: 50
    max_calls_per_minute: 20
    max_tokens_per_run: 200000
---

正文
"""

SKILL_WITHOUT_GOVERNANCE = """---
name: plain-skill
description: 没有治理块的技能
---

正文
"""


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    (d / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    (d / "plain.md").write_text(SKILL_WITHOUT_GOVERNANCE, encoding="utf-8")
    return d


def _harness(tmp_path: Path, **overrides):
    config = HarnessConfig(
        api_key="test-key",
        model="mock-model",
        **overrides,
    )
    return AgentHarness(config=config)


def test_strict_false_does_not_touch_governance(tmp_path, monkeypatch):
    """strict=False → 不装配治理、不要求治理身份（零迁移）。"""
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "plain.md").write_text(SKILL_WITHOUT_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = _harness(tmp_path, strict=False)
    assert harness.governance_policy() is None


def test_strict_true_without_agent_id_raises(tmp_path, monkeypatch):
    """strict=True 但未指定治理身份 → 拒绝启动（fail-closed）。"""
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = _harness(tmp_path, strict=True)
    with pytest.raises(RuntimeError, match="治理身份"):
        harness.governance_policy()


def test_strict_true_with_agent_id_assembles(tmp_path, monkeypatch):
    """strict=True + 治理身份 + 合法治理块 → 装配成功。"""
    from harness.skills import loader
    from harness.tools.base import Tool

    class _Read(Tool):
        @property
        def name(self):
            return "core_banking_api:read_only"

        @property
        def description(self):
            return "read"

        async def execute(self, arguments, context):
            from harness.types import ToolResult

            return ToolResult(tool_call_id="", success=True, content="ok")

    class _Aml(Tool):
        @property
        def name(self):
            return "aml_screening:run"

        @property
        def description(self):
            return "aml"

        async def execute(self, arguments, context):
            from harness.types import ToolResult

            return ToolResult(tool_call_id="", success=True, content="ok")

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = _harness(
        tmp_path, strict=True, governance_agent_id="credit-paper-assembler"
    )
    harness.register_tool(_Read())
    harness.register_tool(_Aml())
    policy = harness.governance_policy()
    assert policy is not None
    assert policy.agent_id == "credit-paper-assembler"
    assert policy.tool_names == {"core_banking_api:read_only", "aml_screening:run"}
    assert policy.material is True


def test_strict_true_with_invalid_block_raises(tmp_path, monkeypatch):
    """治理块违反规则 29（治理块 tools ⊄ 技能 tools.allowed）→ 拒绝启动。"""
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    bad = SKILL_WITH_GOVERNANCE.replace(
        "  allowed: [core_banking_api:read_only, aml_screening:run]",
        "  allowed: [core_banking_api:read_only]",
    )
    (skills / "governed.md").write_text(bad, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = _harness(
        tmp_path, strict=True, governance_agent_id="credit-paper-assembler"
    )
    with pytest.raises(RuntimeError, match="治理装配失败"):
        harness.governance_policy()


def test_skill_roundtrip_preserves_governance(tmp_path):
    """治理块在技能文件往返后必须保持不变。

    客户端编辑器保存一次即抹掉授权书，是设计稿 §9.4 要防的事。
    """
    from harness.skills.base import Skill

    src = tmp_path / "s.md"
    src.write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    skill = Skill.from_file(src)
    assert skill.governance is not None
    assert skill.governance["agent_id"] == "credit-paper-assembler"

    dst = tmp_path / "out.md"
    skill.to_file(dst)
    reloaded = Skill.from_file(dst)
    assert reloaded.governance == skill.governance
