"""
Governance observability — deterministic, LLM-free metrics for the gate.

F: 关键指标（拦截率、闸失败分布、复核积压）必须可观测。 This module keeps
the accumulation logic pure and unit-testable so the harness can expose a
queryable snapshot without scraping logs.

Named governance metrics (F1/F2):
- harness.gate.isolation_rate: fraction of checks that were blocked (quarantined)
- harness.gate.coverage_rate: fraction of claims that were sourced (grounded)
- harness.gate.grounding_rate: fraction of findings that were fact:no-source
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
        # F1/F2: Named governance rate accumulators
        self._total_claims = 0
        self._sourced_claims = 0
        self._unsourced_claims = 0
        self._otel_counters: dict[str, Any] = {}
        self._otel_gauges: dict[str, Any] = {}

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
            # F1/F2: Named governance counters
            "claims_total": meter.create_counter(
                "harness.gate.claims_total",
                description="Total factual claims evaluated",
            ),
            "claims_sourced": meter.create_counter(
                "harness.gate.claims_sourced",
                description="Claims with supporting source (grounded)",
            ),
            "claims_unsourced": meter.create_counter(
                "harness.gate.claims_unsourced",
                description="Claims without supporting source (quarantined)",
            ),
        }
        # F1/F2: Observable gauges for rates (derived from counters)
        self._otel_gauges = {
            "isolation_rate": meter.create_observable_gauge(
                "harness.gate.isolation_rate",
                callbacks=[self._observe_isolation_rate],
                description="Fraction of checks blocked (0.0-1.0)",
                unit="1",
            ),
            "coverage_rate": meter.create_observable_gauge(
                "harness.gate.coverage_rate",
                callbacks=[self._observe_coverage_rate],
                description="Fraction of claims sourced/grounded (0.0-1.0)",
                unit="1",
            ),
        }

    def _observe_isolation_rate(self, options: Any) -> list[Any]:
        """OTel callback for isolation_rate gauge."""
        from opentelemetry import metrics as otel_metrics

        rate = self.blocked / self.checks if self.checks > 0 else 0.0
        return [otel_metrics.Observation(rate, {"metric": "isolation_rate"})]

    def _observe_coverage_rate(self, options: Any) -> list[Any]:
        """OTel callback for coverage_rate gauge."""
        from opentelemetry import metrics as otel_metrics

        rate = self._sourced_claims / self._total_claims if self._total_claims > 0 else 1.0
        return [otel_metrics.Observation(rate, {"metric": "coverage_rate"})]

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
            # F1/F2: Track fact grounding outcomes
            fid = getattr(f, "id", "")
            if fid.startswith("fact:"):
                self._total_claims += 1
                if fid == "fact:no-source":
                    self._unsourced_claims += 1
                    if self._otel_counters:
                        self._otel_counters["claims_unsourced"].add(1)
                else:
                    self._sourced_claims += 1
                    if self._otel_counters:
                        self._otel_counters["claims_sourced"].add(1)
        if self._otel_counters:
            self._otel_counters["checks"].add(1)
            if not passed:
                self._otel_counters["blocked"].add(1)
            if self._total_claims > 0:
                self._otel_counters["claims_total"].add(self._total_claims)

    def snapshot(self, review_backlog: int | None = None) -> dict[str, Any]:
        """Return a queryable copy, optionally merged with the review backlog."""
        isolation_rate = self.blocked / self.checks if self.checks > 0 else 0.0
        coverage_rate = (
            self._sourced_claims / self._total_claims
            if self._total_claims > 0
            else 1.0
        )
        grounding_rate = (
            1.0 - (self._unsourced_claims / self._total_claims)
            if self._total_claims > 0
            else 1.0
        )
        out: dict[str, Any] = {
            "checks": self.checks,
            "passed": self.passed,
            "blocked": self.blocked,
            "findings_by_type": dict(self.findings_by_type),
            "findings_by_severity": dict(self.findings_by_severity),
            # F1/F2: Named governance rates
            "isolation_rate": round(isolation_rate, 4),
            "coverage_rate": round(coverage_rate, 4),
            "grounding_rate": round(grounding_rate, 4),
            "total_claims": self._total_claims,
            "sourced_claims": self._sourced_claims,
            "unsourced_claims": self._unsourced_claims,
        }
        if review_backlog is not None:
            out["review_backlog"] = review_backlog
        return out
