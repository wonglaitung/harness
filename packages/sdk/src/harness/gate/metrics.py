"""
Governance observability — deterministic, LLM-free metrics for the gate.

F: 关键指标（拦截率、闸失败分布、复核积压）必须可观测。 This module keeps
the accumulation logic pure and unit-testable so the harness can expose a
queryable snapshot without scraping logs.
"""

from __future__ import annotations

from typing import Any


class GateMetrics:
    """Accumulates governance outcomes across gate checks."""

    def __init__(self) -> None:
        self.checks = 0
        self.passed = 0
        self.blocked = 0
        self.findings_by_type: dict[str, int] = {}
        self.findings_by_severity: dict[str, int] = {}
        self._otel_counters: dict[str, Any] = {}

    def configure_otel(self, meter: Any = None) -> None:
        """Bind to an OpenTelemetry meter so governance counters are exported.

        No-op (stays in-memory only) when OTel is unavailable or metrics export
        is not configured. Safe to call unconditionally at startup.
        """
        if meter is None:
            try:
                from harness.core.observability import get_meter

                meter = get_meter()
            except Exception:
                meter = None
        if meter is None:
            return
        self._otel_counters = {
            "checks": meter.create_counter(
                "harness.gate.checks", description="Gate evaluations performed"
            ),
            "blocked": meter.create_counter(
                "harness.gate.blocked", description="Gate evaluations that failed/blocked"
            ),
            "findings": meter.create_counter(
                "harness.gate.findings",
                description="Findings recorded, by type and severity",
            ),
        }

    def record(self, verdict: Any) -> None:
        """Fold a single gate verdict into the running counters."""
        self.checks += 1
        passed = bool(getattr(verdict, "passed", True))
        if passed:
            self.passed += 1
        else:
            self.blocked += 1
        for f in getattr(verdict, "findings", []) or []:
            t = getattr(getattr(f, "type", None), "value", str(getattr(f, "type", "unknown")))
            s = getattr(getattr(f, "severity", None), "value", str(getattr(f, "severity", "unknown")))
            self.findings_by_type[t] = self.findings_by_type.get(t, 0) + 1
            self.findings_by_severity[s] = self.findings_by_severity.get(s, 0) + 1
            if self._otel_counters:
                self._otel_counters["findings"].add(1, {"type": t, "severity": s})
        if self._otel_counters:
            self._otel_counters["checks"].add(1)
            if not passed:
                self._otel_counters["blocked"].add(1)

    def snapshot(self, review_backlog: int | None = None) -> dict[str, Any]:
        """Return a queryable copy, optionally merged with the review backlog."""
        out: dict[str, Any] = {
            "checks": self.checks,
            "passed": self.passed,
            "blocked": self.blocked,
            "findings_by_type": dict(self.findings_by_type),
            "findings_by_severity": dict(self.findings_by_severity),
        }
        if review_backlog is not None:
            out["review_backlog"] = review_backlog
        return out
