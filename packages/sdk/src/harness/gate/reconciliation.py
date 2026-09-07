"""Delivery-time reconciliation.

Cross-checks each extracted factual claim against the trusted-source fields
(collected by :class:`FactGrounder`). The result is a structured report so the
caller can decide whether to strip/flag unsourced conclusions rather than
silently delivering them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.gate.validators import _CLAIM_PATTERN

_CLAIM_RE = _CLAIM_PATTERN


@dataclass
class Reconciler:
    """Produce a deterministic reconciliation report (claims <-> sources)."""

    def reconcile(
        self,
        content: str,
        sources: list[str],
        findings: list[Any] | None = None,
    ) -> dict[str, Any]:
        claims = [m.group(0) for m in _CLAIM_RE.finditer(content)]
        if not claims:
            return {
                "checked_claims": 0,
                "sourced_claims": 0,
                "unsourced_claims": [],
                "source_count": len(sources or []),
            }

        unsourced: list[str] = []
        sourced = 0
        for claim in claims:
            needle = claim.strip()
            if len(needle) > 40:
                needle = needle[:40]
            if any(needle in src for src in (sources or [])):
                sourced += 1
            else:
                unsourced.append(claim)

        return {
            "checked_claims": len(claims),
            "sourced_claims": sourced,
            "unsourced_claims": unsourced,
            "source_count": len(sources or []),
        }
