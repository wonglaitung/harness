"""GateMetrics observability unit tests (F: 拦截率/失败分布/复核积压)."""

from __future__ import annotations

from harness.gate.metrics import GateMetrics
from harness.gate.models import (
    FindingType,
    GateFinding,
    GateSeverity,
    GateVerdict,
)


def _verdict(passed: bool, findings: list[GateFinding] | None = None) -> GateVerdict:
    return GateVerdict(
        passed=passed,
        findings=findings or [],
        delivered_content="x",
        reconciliation_report={},
    )


def test_record_counts_passed_and_blocked() -> None:
    m = GateMetrics()
    m.record(_verdict(True))
    m.record(_verdict(False))
    m.record(_verdict(False))
    snap = m.snapshot()
    assert snap["checks"] == 3
    assert snap["passed"] == 1
    assert snap["blocked"] == 2


def test_record_buckets_findings_by_type_and_severity() -> None:
    m = GateMetrics()
    m.record(
        _verdict(
            False,
            [
                GateFinding("a", FindingType.FACT, GateSeverity.ERROR, "no src"),
                GateFinding("b", FindingType.FACT, GateSeverity.ERROR, "no src"),
                GateFinding("c", FindingType.RECONCILIATION, GateSeverity.WARNING, "x"),
            ],
        )
    )
    snap = m.snapshot()
    assert snap["findings_by_type"]["fact"] == 2
    assert snap["findings_by_type"]["reconciliation"] == 1
    assert snap["findings_by_severity"]["error"] == 2
    assert snap["findings_by_severity"]["warning"] == 1


def test_snapshot_merges_review_backlog() -> None:
    m = GateMetrics()
    snap = m.snapshot(review_backlog=4)
    assert snap["review_backlog"] == 4
    # snapshot is a copy, not the live counters
    snap["checks"] = 99
    assert m.checks == 0
