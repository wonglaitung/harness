"""Deterministic gate unit tests (100% deterministic, no LLM)."""

from __future__ import annotations

from harness.gate import (
    DeterministicGate,
    FactGrounder,
    FormatValidator,
    GateSeverity,
    LogicReconciler,
    Reconciler,
)
from harness.gate.models import GateVerdict


def _gate() -> DeterministicGate:
    return DeterministicGate(
        validators=[FormatValidator(), FactGrounder(), LogicReconciler()],
        reconciler=Reconciler(),
    )


def test_format_empty_is_error() -> None:
    verdict: GateVerdict = _gate().check("")
    assert verdict.passed is False
    assert any(f.severity == GateSeverity.ERROR for f in verdict.findings)


def test_factual_claim_without_source_blocks() -> None:
    # A numeric/date claim with no provenance and no tool records -> ERROR.
    content = "2024年Q1营收增长12.5%，达到3.2亿元。"
    verdict = _gate().check(content)
    assert verdict.passed is False
    assert any(f.type.value == "fact" for f in verdict.findings)
    assert verdict.reconciliation_report["checked_claims"] >= 1
    assert verdict.reconciliation_report["sourced_claims"] == 0


def test_factual_claim_with_matching_source_passes() -> None:
    content = "2024年Q1营收增长12.5%，达到3.2亿元。"
    verdict = _gate().check(content, sources=["2024年Q1营收增长12.5%，达到3.2亿元。"])
    assert verdict.passed is True  # no ERROR findings
    assert verdict.reconciliation_report["sourced_claims"] >= 1


def test_short_content_skips_fact_grounding() -> None:
    # Below min_content_len, no factual claim heuristic triggered.
    verdict = _gate().check("好的。", sources=[])
    assert verdict.passed is True


def test_logic_rule_fires() -> None:
    def no_negative_rule(content: str, sources: list[str]):
        from harness.gate.models import FindingType, GateFinding, GateSeverity

        return [
            GateFinding(
                id="logic:neg",
                type=FindingType.LOGIC,
                severity=GateSeverity.ERROR,
                message="不允许负值",
            )
            if "-1" in content
            else GateFinding(
                id="logic:ok",
                type=FindingType.LOGIC,
                severity=GateSeverity.INFO,
                message="ok",
            )
        ]

    gate = DeterministicGate(
        validators=[
            FormatValidator(),
            FactGrounder(min_content_len=0),
            LogicReconciler(rules=[no_negative_rule]),
        ],
        reconciler=Reconciler(),
    )
    bad = gate.check("结果是 -1 个单位。")
    assert bad.passed is False
    good = gate.check("结果是 5 个单位。")
    assert good.passed is True


def test_failure_delivers_quarantined_content() -> None:
    # No provenance -> ERROR; delivered_content must be quarantined, not raw.
    content = "2024年Q1营收增长12.5%，达到3.2亿元。"
    verdict = _gate().check(content)
    assert verdict.passed is False
    assert verdict.delivered_content != content
    assert "已隔离" in verdict.delivered_content


def test_redact_replaces_unsourced_claims() -> None:
    r = Reconciler()
    report = r.reconcile("营收3.2亿元。", sources=[])
    safe = Reconciler.redact("营收3.2亿元。", report)
    assert "已隔离:无溯源" in safe
    assert "3.2亿元" not in safe


def test_redact_quarantines_when_nothing_redactable() -> None:
    r = Reconciler()
    report = {"unsourced_claims": []}
    safe = Reconciler.redact("任意内容", report)
    assert "已隔离" in safe


def test_unsourced_claim_quarantined_from_delivery() -> None:
    # One claim grounded, one not: the unsupported one must be stripped/flagged
    # from the delivered content (D2/D3: 无来源即删/存疑).
    content = "营收5亿元，利润-3亿元。"
    verdict = _gate().check(content, sources=["营收5亿元。"])
    assert verdict.reconciliation_report["unsourced_claims"]
    assert "已隔离" in verdict.delivered_content
    assert "5亿元" in verdict.delivered_content  # grounded claim kept
    assert "3亿元" not in verdict.delivered_content  # unsupported stripped
    assert any(f.type.value == "reconciliation" for f in verdict.findings)
