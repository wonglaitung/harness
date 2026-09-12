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


class _FakeCounter:
    def __init__(self) -> None:
        self.adds: list[tuple[int, dict[str, str]]] = []

    def add(self, value: int, attributes: dict[str, str] | None = None) -> None:
        self.adds.append((value, attributes or {}))


class _FakeMeter:
    def __init__(self) -> None:
        self.counters: dict[str, _FakeCounter] = {}
        self.gauges: dict[str, _FakeCounter] = {}

    def create_counter(self, name: str, description: str = "") -> _FakeCounter:
        c = _FakeCounter()
        self.counters[name] = c
        return c

    def create_observable_gauge(
        self, name: str, callbacks=None, description: str = "", unit: str = ""
    ) -> _FakeCounter:
        c = _FakeCounter()
        self.gauges[name] = c
        return c


def test_configure_otel_pushes_counters() -> None:
    """F: when an OTel meter is bound, governance counters are exported."""
    m = GateMetrics()
    fake = _FakeMeter()
    m.configure_otel(fake)
    m.record(
        _verdict(
            False,
            [GateFinding("a", FindingType.FACT, GateSeverity.ERROR, "no src")],
        )
    )
    m.record(_verdict(True))

    assert fake.counters["harness.gate.checks"].adds == [(1, {}), (1, {})]
    assert fake.counters["harness.gate.blocked"].adds == [(1, {})]
    assert fake.counters["harness.gate.findings"].adds == [
        (1, {"type": "fact", "severity": "error"})
    ]


def test_no_otel_stays_in_memory() -> None:
    """Without a meter, metrics stay in-memory only and never raise."""
    m = GateMetrics()
    assert m._otel_counters == {}
    m.record(_verdict(False))
    finding = GateFinding("b", FindingType.RECONCILIATION, GateSeverity.WARNING, "x")
    m.record(_verdict(False, [finding]))
    assert m.blocked == 2
    assert m.snapshot()["blocked"] == 2
    assert m.snapshot()["findings_by_severity"]["warning"] == 1
