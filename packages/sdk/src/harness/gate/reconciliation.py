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

_QUARANTINE_NOTICE = "[内容未通过确定性闸门（含错误级发现），已隔离，不交付原始内容]"


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

    @staticmethod
    def redact(
        content: str, report: dict[str, Any], *, hold_back: bool = False
    ) -> str:
        """Produce a delivery-safe version by quarantining unsourced claims.

        Each claim that could not be grounded against the trusted source set is
        replaced with a visible ``[已隔离:无溯源]`` marker.

        Args:
            content: 待交付内容
            report: `reconcile()` 的报告
            hold_back: 交付**未通过闸门**时由调用方传 True。此时若没有任何
                可隔离的声明（空报告，或声明不在内容中），整段硬隔离，避免
                原始内容被静默交付。通过闸门且无无溯源声明时保持原样。

        Returns:
            可交付内容（可能已标注/隔离）。
        """
        unsourced = (report or {}).get("unsourced_claims") or []
        safe = content
        for claim in unsourced:
            if claim and claim in safe:
                safe = safe.replace(claim, "[已隔离:无溯源]")
        if not unsourced:
            return _QUARANTINE_NOTICE if hold_back else content
        if safe.strip() == content.strip():
            return _QUARANTINE_NOTICE
        return safe
