"""Gate metrics governance rates tests (F1/F2).

Verifies that GateMetrics tracks isolation_rate, coverage_rate, grounding_rate
and exposes them in the snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pytest

from harness.gate.metrics import GateMetrics


class _FindingType(Enum):
    FORMAT = "format"
    FACT = "fact"
    LOGIC = "logic"


class _Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class _FakeFinding:
    id: str
    type: _FindingType
    severity: _Severity
    message: str = ""


@dataclass
class _FakeVerdict:
    passed: bool
    findings: list[_FakeFinding]


def test_isolation_rate_zero_when_no_checks() -> None:
    m = GateMetrics()
    s = m.snapshot()
    assert s["isolation_rate"] == 0.0


def test_isolation_rate计算正确() -> None:
    m = GateMetrics()
    # 3 checks: 1 passed, 2 blocked
    m.record(_FakeVerdict(passed=True, findings=[]))
    m.record(_FakeVerdict(passed=False, findings=[]))
    m.record(_FakeVerdict(passed=False, findings=[]))
    s = m.snapshot()
    assert s["isolation_rate"] == pytest.approx(2 / 3, abs=0.01)
    assert s["checks"] == 3
    assert s["blocked"] == 2


def test_coverage_rate_with_sourced_claims() -> None:
    m = GateMetrics()
    # 1 check with 3 findings: 2 sourced, 1 unsourced
    findings = [
        _FakeFinding(id="fact:sourced-1", type=_FindingType.FACT, severity=_Severity.WARNING),
        _FakeFinding(id="fact:sourced-2", type=_FindingType.FACT, severity=_Severity.WARNING),
        _FakeFinding(id="fact:no-source", type=_FindingType.FACT, severity=_Severity.WARNING),
    ]
    m.record(_FakeVerdict(passed=True, findings=findings))
    s = m.snapshot()
    assert s["total_claims"] == 3
    assert s["sourced_claims"] == 2
    assert s["unsourced_claims"] == 1
    assert s["coverage_rate"] == pytest.approx(2 / 3, abs=0.01)
    assert s["grounding_rate"] == pytest.approx(2 / 3, abs=0.01)


def test_coverage_rate_one_when_no_claims() -> None:
    m = GateMetrics()
    m.record(_FakeVerdict(passed=True, findings=[]))
    s = m.snapshot()
    assert s["coverage_rate"] == 1.0
    assert s["grounding_rate"] == 1.0


def test_snapshot_includes_all_governance_fields() -> None:
    m = GateMetrics()
    m.record(_FakeVerdict(passed=True, findings=[]))
    m.record(_FakeVerdict(passed=False, findings=[]))
    s = m.snapshot(review_backlog=5)
    assert "isolation_rate" in s
    assert "coverage_rate" in s
    assert "grounding_rate" in s
    assert "total_claims" in s
    assert "sourced_claims" in s
    assert "unsourced_claims" in s
    assert s["review_backlog"] == 5


def test_non_fact_findings_not_counted_as_claims() -> None:
    m = GateMetrics()
    findings = [
        _FakeFinding(id="fmt:empty", type=_FindingType.FORMAT, severity=_Severity.ERROR),
        _FakeFinding(id="logic:sum-mismatch", type=_FindingType.LOGIC, severity=_Severity.ERROR),
    ]
    m.record(_FakeVerdict(passed=False, findings=findings))
    s = m.snapshot()
    assert s["total_claims"] == 0
    assert s["coverage_rate"] == 1.0
