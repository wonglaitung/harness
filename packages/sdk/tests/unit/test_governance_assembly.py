"""治理装配的单元测试：治理块缺失/不匹配/校验失败 → fail-closed。"""

from __future__ import annotations

from harness.governance.assembly import assemble_governance


class _FakeSkill:
    """最小技能替身。"""

    def __init__(self, name, governance=None, allowed=None):
        self.name = name
        self.governance = governance
        self.tools = type("_T", (), {"allowed": allowed or []})()


def _block(agent_id="agent-x", **overrides):
    block = {
        "agent_id": agent_id,
        "version": "1.0.0",
        "approved_by": "PR #1",
        "business_intent": "做点事",
        "owners": {"accountable": "A", "technical": "T"},
        "material": False,
        "tools": [{"name": "t:read", "capability": "read", "idempotent": True}],
        "workflow": {"steps": [{"id": "s1", "tools": ["t:read"]}]},
        "limits": {"max_tool_calls_per_run": 10, "max_calls_per_minute": 5,
                   "max_tokens_per_run": 1000},
    }
    block.update(overrides)
    return block


def test_assemble_single_block():
    setup = assemble_governance(
        [_FakeSkill("s", governance=_block())], agent_id="agent-x"
    )
    assert setup.policy is not None, setup.errors
    assert setup.policy.agent_id == "agent-x"
    assert setup.policy.tool_names == {"t:read"}


def test_missing_agent_id_fails_closed():
    setup = assemble_governance([_FakeSkill("s", governance=_block())], agent_id=None)
    assert setup.policy is None
    assert setup.errors


def test_missing_governance_block_fails_closed():
    """治理块缺失即拒绝（strict 下是硬门槛）。"""
    setup = assemble_governance([_FakeSkill("s")], agent_id="agent-x")
    assert setup.policy is None
    assert any("没有可用治理块" in e for e in setup.errors)


def test_agent_id_mismatch_skipped():
    """治理身份不一致的技能不参与本 run（§6.4.1）。"""
    setup = assemble_governance(
        [_FakeSkill("s", governance=_block(agent_id="other"))], agent_id="agent-x"
    )
    assert setup.policy is None


def test_invalid_block_fails_closed():
    """结构错误（缺 idempotent）在**解析期**即被拒——比等到校验期更早 fail-closed。"""
    bad = _block()
    bad["tools"][0].pop("idempotent")
    setup = assemble_governance([_FakeSkill("s", governance=bad)], agent_id="agent-x")
    assert setup.policy is None
    assert any("解析失败" in e for e in setup.errors)


def test_semantically_invalid_block_fails_closed():
    """语义错误（未知工具）在**校验期**被拒。"""
    bad = _block()
    setup = assemble_governance(
        [_FakeSkill("s", governance=bad)],
        agent_id="agent-x",
        known_tool_names={"other:tool"},
    )
    assert setup.policy is None
    assert any("校验失败" in e for e in setup.errors)


def test_skill_allowed_is_upper_bound():
    """规则 29：治理块 tools ⊆ 技能 tools.allowed。"""
    setup = assemble_governance(
        [_FakeSkill("s", governance=_block(), allowed=["other:tool"])],
        agent_id="agent-x",
    )
    assert setup.policy is None
    assert any("子集" in e or "规则 29" in e for e in setup.errors)


def test_unknown_tool_rejected_when_registry_known():
    setup = assemble_governance(
        [_FakeSkill("s", governance=_block())],
        agent_id="agent-x",
        known_tool_names={"other:tool"},
    )
    assert setup.policy is None
    assert any("不在工具注册表" in e for e in setup.errors)


def test_multi_blocks_same_agent_intersect_whitelist():
    """多份治理块：白名单取交集（取最严，§6.4.2）。"""
    a = _block()
    b = _block()
    b["tools"].append({"name": "t:write", "capability": "write", "idempotent": True})
    b["workflow"]["steps"].append({"id": "s2", "tools": ["t:write"]})
    setup = assemble_governance(
        [_FakeSkill("s1", governance=a), _FakeSkill("s2", governance=b)],
        agent_id="agent-x",
    )
    assert setup.policy is not None, setup.errors
    # a 里没有 t:write → 交集不含它（治理集取最严）
    assert setup.policy.tool_names == {"t:read"}


def test_multi_blocks_same_agent_take_strictest_limits():
    """多份治理块：限额取最严。"""
    a = _block()
    b = _block()
    b["limits"]["max_tool_calls_per_run"] = 3
    setup = assemble_governance(
        [_FakeSkill("s1", governance=a), _FakeSkill("s2", governance=b)],
        agent_id="agent-x",
    )
    assert setup.policy is not None, setup.errors
    assert setup.policy.limits.max_tool_calls_per_run == 3
