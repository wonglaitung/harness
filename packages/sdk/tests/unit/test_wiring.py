"""Wiring / strict-propagation tests (no heavy AgentHarness construction).

Validates that governance layer is OFF by default (zero migration) and turns on
with strict=True, and that HARNESS_REQUIRE_STRICT fails fast when off.
"""

from __future__ import annotations

import json

import pytest

from harness.gate.models import FindingType, GateFinding, GateSeverity
from harness.review import ReviewItem, ReviewQueue
from harness.sdk.config import GateConfig, HarnessConfig, ReviewConfig
from harness.sdk.harness import AgentHarness
from harness.state import create_state_store


class _Probe:
    """Expose governance-build methods without running AgentHarness.__init__."""

    def __init__(self, cfg: HarnessConfig) -> None:
        self.config = cfg
        self._review_queue = None

    _build_gate = AgentHarness._build_gate
    _build_state_store = AgentHarness._build_state_store
    _build_review_queue = AgentHarness._build_review_queue
    _require_strict_if_env = AgentHarness._require_strict_if_env


def test_default_off_is_zero_migration() -> None:
    c = HarnessConfig()
    assert c.strict is False
    assert c.gate is None and c.state is None and c.review is None
    p = _Probe(c)
    assert p._build_gate() is None
    assert p._build_state_store() is None
    assert p._build_review_queue() is None


def test_strict_builds_governance() -> None:
    c = HarnessConfig(strict=True)
    p = _Probe(c)
    assert p._build_gate() is not None
    assert p._build_state_store() is not None
    assert p._build_review_queue() is not None


def test_require_strict_env_fails_when_off(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_REQUIRE_STRICT", "1")
    try:
        p = _Probe(HarnessConfig(strict=False))
        with pytest.raises(RuntimeError):
            p._require_strict_if_env()
    finally:
        monkeypatch.delenv("HARNESS_REQUIRE_STRICT", raising=False)


def test_require_strict_env_ok_when_on(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_REQUIRE_STRICT", "1")
    try:
        p = _Probe(HarnessConfig(strict=True))
        p._require_strict_if_env()  # should not raise
    finally:
        monkeypatch.delenv("HARNESS_REQUIRE_STRICT", raising=False)


def test_gate_rules_injected_into_auto_gate() -> None:
    def _always_fail(content: str, sources: list[str]) -> list[GateFinding]:
        return [
            GateFinding(
                id="x", type=FindingType.LOGIC, severity=GateSeverity.ERROR, message="boom"
            )
        ]

    c = HarnessConfig(strict=True, gate=GateConfig(rules=[_always_fail]))
    gate = _Probe(c)._build_gate()
    assert gate is not None
    verdict = gate.check("anything")
    assert verdict.passed is False
    assert verdict.errors


def test_gate_rule_specs_compiled_into_auto_gate() -> None:
    spec = {
        "kind": "numeric_sum",
        "id": "balance",
        "left": "assets",
        "rights": ["liabilities", "equity"],
        "tolerance": 0.02,
        "severity": "error",
    }
    c = HarnessConfig(strict=True, gate=GateConfig(rule_specs=[spec]))
    gate = _Probe(c)._build_gate()
    # 100 vs 60+50=110 -> deviation 10% > 2% -> must fail
    verdict = gate.check(json.dumps({"assets": 100, "liabilities": 60, "equity": 50}))
    assert verdict.passed is False
    # 100 vs 60+40=100 -> pass
    ok = gate.check(json.dumps({"assets": 100, "liabilities": 60, "equity": 40}))
    assert ok.passed is True


def test_review_queue_persisted(tmp_path) -> None:
    db = str(tmp_path / "review.db")
    c = HarnessConfig(strict=True, review=ReviewConfig(backend="file", path=db))
    q = _Probe(c)._build_review_queue()
    assert q is not None
    q.submit(ReviewItem(content="x", source="t"))
    # A fresh queue on the same file (simulating another process) sees the item.
    reopened = ReviewQueue(store=create_state_store("file", path=db))
    assert len(reopened.pending()) == 1


async def test_strict_store_allows_control_layer_role_write() -> None:
    """Gap 1: the strict verifier accepts the control layer writing for a role."""
    from types import SimpleNamespace

    from harness.orchestrator.team_orchestrator import TeamOrchestrator
    from harness.orchestrator.types import AgentRole, TeamConfig

    store = _Probe(HarnessConfig(strict=True))._build_state_store()
    role = AgentRole(name="researcher", description="research")
    cfg = TeamConfig(name="team", roles=[role], state_store=store)
    orch = TeamOrchestrator(SimpleNamespace(agent=SimpleNamespace()))
    result = SimpleNamespace(
        final_response="raw", delivered_content="reconciled", gate_verdict=None
    )

    await orch._record_agent_result(cfg, role, result, "task")

    items = await store.list_items()
    assert len(items) == 1
    assert items[0].source_agent == "researcher"
    assert items[0].writer_id == "harness"


async def test_strict_store_rejects_rogue_authoritative_write() -> None:
    """A non-control writer cannot create an authoritative decision."""
    store = _Probe(HarnessConfig(strict=True))._build_state_store()
    with pytest.raises(PermissionError):
        await store.put_authoritative("decision", "v", source_agent="rogue_role")
