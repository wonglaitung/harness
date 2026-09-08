"""Example: gating a tool-persisted spec (the "Gap 3" integration pattern).

The SDK's auto-gate runs on ``goal_result.final_response`` (harness.py
``_apply_gate``). When your agent delivers via a *tool* — e.g. a ``submit_spec``
tool that writes a JSON spec to ``specs/`` — the auto-gate never sees that spec.
This example shows how to manually drive the deterministic gate on the spec
itself, using the SDK's ``DeterministicGate`` + ``ReviewQueue`` so you still get
100%-deterministic tie-out checking and human-in-the-loop escalation.

Run:  python -m examples.spec_submit_governance
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness.gate import DeterministicGate, LogicReconciler
from harness.gate.models import FindingType, GateFinding, GateSeverity
from harness.review import ReviewItem, ReviewQueue
from harness.state import create_state_store

# --- Your deterministic master source (the "spine" the agent fills in) --------
# In a real pipeline this comes from a trusted upstream system, not the LLM.
CTX_VALUES: dict[str, float] = {
    "assets": 1000.0,
    "liabilities": 600.0,
    # equity is intentionally NOT in the master source; the agent's spec supplies it
}


def _tie_out_rule(content: str, sources: list[str]) -> list[GateFinding]:
    """A≈L+E within 2%, merging the deterministic master source with the spec.

    This is a Python callable (GateRule) because it needs ``CTX_VALUES`` — the
    declarative engine (rule_specs) only sees the delivery text and cannot.
    """
    try:
        spec = json.loads(content)
    except (ValueError, TypeError):
        return [
            GateFinding(
                id="logic:spec:json",
                type=FindingType.LOGIC,
                severity=GateSeverity.ERROR,
                message="submit_spec 内容不是合法 JSON",
            )
        ]
    vals = {**CTX_VALUES, **spec.get("values", {})}
    a = vals.get("assets")
    liab = vals.get("liabilities")
    e = vals.get("equity")
    if None in (a, liab, e):
        return [
            GateFinding(
                id="logic:tie-out:missing",
                type=FindingType.LOGIC,
                severity=GateSeverity.WARNING,
                message=f"勾稽缺字段: assets={a}, liabilities={liab}, equity={e}",
            )
        ]
    deviation = abs(a - (liab + e)) / max(abs(a), 1e-9)
    if deviation > 0.02:
        return [
            GateFinding(
                id="logic:tie-out",
                type=FindingType.LOGIC,
                severity=GateSeverity.ERROR,
                message=f"A≠L+E 偏差 {deviation:.2%} > 2%（assets={a}, L+E={liab + e}）",
            )
        ]
    return []


def make_spec_gate() -> DeterministicGate:
    """Build the gate with the tie-out rule.

    NOTE: the gate is *not* given a review_queue here — the ``submit_spec`` tool
    owns the escalation so it can also write the rejected spec to quarantine.
    (If you instead want the gate to auto-escalate, pass ``review_queue=`` and do
    not submit again in the tool, otherwise items are queued twice.)
    """
    return DeterministicGate(validators=[LogicReconciler(rules=[_tie_out_rule])])


def submit_spec(
    spec_json: str,
    *,
    gate: DeterministicGate,
    review_queue: ReviewQueue,
    specs_dir: Path,
    quarantine_dir: Path,
) -> str:
    """The manual gate point. Call this from your ``submit_spec`` tool.

    Returns "delivered" when the spec passes the tie-out, or "review" when it is
    isolated for human resolution (written to quarantine, not to specs/).
    """
    verdict = gate.check(spec_json)
    if not verdict.passed:
        review_queue.submit(
            ReviewItem(
                gate_findings=[f.as_dict() for f in verdict.findings],
                content=spec_json,
                source="submit_spec",
            )
        )
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        (quarantine_dir / "rejected.json").write_text(spec_json, encoding="utf-8")
        return "review"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.json").write_text(spec_json, encoding="utf-8")
    return "delivered"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = create_state_store("file", path=f"{tmp}/review.db")
        review_queue = ReviewQueue(store=store)
        gate = make_spec_gate()

        specs_dir = Path(tmp) / "specs"
        quarantine_dir = Path(tmp) / "quarantine"

        # 1) Failing spec (equity makes A ≠ L+E by >2%) -> isolated for review.
        bad = json.dumps({"values": {"equity": 500.0}})
        out = submit_spec(
            bad, gate=gate, review_queue=review_queue,
            specs_dir=specs_dir, quarantine_dir=quarantine_dir,
        )
        assert out == "review"
        assert len(review_queue.pending()) == 1
        print("FAIL case -> pending:", len(review_queue.pending()))

        # 2) Passing spec (equity = 400 -> 1000 ≈ 600+400) -> delivered.
        good = json.dumps({"values": {"equity": 400.0}})
        out = submit_spec(
            good, gate=gate, review_queue=review_queue,
            specs_dir=specs_dir, quarantine_dir=quarantine_dir,
        )
        assert out == "delivered"
        assert (specs_dir / "spec.json").exists()
        print("PASS case -> spec delivered:", (specs_dir / "spec.json").exists())

        # Cross-process proof: a fresh queue on the same file sees the item.
        reopened = ReviewQueue(store=create_state_store("file", path=f"{tmp}/review.db"))
        assert len(reopened.pending()) == 1
        print("Cross-process: reopened sees", len(reopened.pending()), "pending item(s)")


if __name__ == "__main__":
    main()
