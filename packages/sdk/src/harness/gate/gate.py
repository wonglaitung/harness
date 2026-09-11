"""DeterministicGate — the single delivery-before-handoff checkpoint.

Composes the three validators (format / fact / logic) plus reconciliation into
one 100%-deterministic verdict. The LLM never decides; it only produces the
candidate content. When the verdict fails and a review queue is attached, the
findings are submitted for human-in-the-loop resolution.
"""

from __future__ import annotations

from typing import Any

from harness.gate.models import (
    GateFinding,
    GateSeverity,
    GateVerdict,
)
from harness.gate.reconciliation import Reconciler
from harness.gate.validators import (
    FactGrounder,
    FormatValidator,
    GateValidator,
    LogicReconciler,
)
from harness.review.queue import ReviewItem


class DeterministicGate:
    """Run the deterministic gate over a candidate delivery.

    Args:
        validators: Ordered list of validators. Defaults to
            Format + Fact + Logic.
        reconciler: Delivery-time reconciliation pass.
        review_queue: Optional human-in-the-loop queue; failed verdicts are
            submitted here when provided.
    """

    def __init__(
        self,
        validators: list[GateValidator] | None = None,
        reconciler: Reconciler | None = None,
        review_queue: Any | None = None,
    ) -> None:
        self.validators = validators or [
            FormatValidator(),
            FactGrounder(),
            LogicReconciler(),
        ]
        self.reconciler = reconciler or Reconciler()
        self.review_queue = review_queue

    def check(
        self,
        content: str,
        sources: list[str] | None = None,
        tool_records: list[dict[str, Any]] | None = None,
    ) -> GateVerdict:
        """Run all validators + reconciliation and return a verdict.

        ``sources`` takes precedence over tool-derived provenance. When both are
        present the union is used (explicit wins on conflict via caller merge).
        """
        src = list(sources or [])
        findings: list[GateFinding] = []
        for v in self.validators:
            findings.extend(v.check(content, src, tool_records))

        report = self.reconciler.reconcile(content, src, findings)
        passed = not any(f.severity == GateSeverity.ERROR for f in findings)

        # Delivery-time enforcement: on failure, never hand back the raw content.
        # Unsourced claims are quarantined; if nothing is redactable the whole
        # delivery is held back so the raw result is not silently leaked.
        delivered_content = (
            content if passed else self.reconciler.redact(content, report)
        )

        verdict = GateVerdict(
            passed=passed,
            findings=findings,
            delivered_content=delivered_content,
            reconciliation_report=report,
        )

        if not passed and self.review_queue is not None:
            import contextlib

            with contextlib.suppress(Exception):
                # Review submission must never block delivery.
                self.review_queue.submit(
                    ReviewItem(
                        gate_findings=[f.as_dict() for f in findings],
                        content=content,
                        source="deterministic_gate",
                    )
                )

        return verdict
