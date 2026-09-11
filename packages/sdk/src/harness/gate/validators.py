"""Gate validators — the deterministic three-dimensional check.

Each validator is pure deterministic code. The LLM never participates in the
verdict. Validators return a list of :class:`GateFinding`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from harness.gate.models import (
    FindingType,
    GateFinding,
    GateSeverity,
)

# Heuristic markers for factual claims that require provenance.
# Numbers with units, percentages, dates, money, named entities in quotes.
#
# Boundary note: a leading ``\b`` requires a word boundary before the digit, but
# CJK text has no spaces, so claims like "营收5亿元" were never detected (only
# "x-3亿元" matched because '-' is a non-word char). We instead forbid an ASCII
# word char or digit immediately before the number, which lets CJK characters
# precede a claim while still excluding identifiers such as "abc5".
_CLAIM_PATTERN = re.compile(
    r"(?:(?<![\dA-Za-z])\d[\d,.]*\s?(?:%|percent|kg|km|m|s|USD|\$|元|万元|万吨|亿元|倍)(?!\d)"
    r"|(?<![\d])(?:19|20)\d{2}[-/年]\d{1,2}(?:[-/月]\d{1,2})?(?!\d)"
    r"|(?<![\dA-Za-z])[Qq][1-4]\s?\d{4}(?!\d))"
)


class GateValidator(Protocol):
    """Validators implement ``check`` returning findings."""

    def check(
        self,
        content: str,
        sources: list[str],
        tool_records: list[dict[str, Any]] | None = None,
    ) -> list[GateFinding]:
        ...


@dataclass
class FormatValidator:
    """Validate structural well-formedness of the delivery.

    Optionally validates against a pydantic model / dataclass when one is
    supplied (``output_model``). Without an output model it only performs
    generic structural sanity checks (non-empty, balanced markers).
    """

    output_model: Any | None = None

    def check(
        self,
        content: str,
        sources: list[str],
        tool_records: list[dict[str, Any]] | None = None,
    ) -> list[GateFinding]:
        findings: list[GateFinding] = []
        if not content or not content.strip():
            findings.append(
                GateFinding(
                    id="fmt:empty",
                    type=FindingType.FORMAT,
                    severity=GateSeverity.ERROR,
                    message="交付内容为空",
                )
            )
            return findings

        if self.output_model is not None:
            findings.extend(self._check_model(content))

        # Generic structural sanity: unbalanced code fences are a WARNING.
        fence_count = content.count("```")
        if fence_count % 2 != 0:
            findings.append(
                GateFinding(
                    id="fmt:code-fence",
                    type=FindingType.FORMAT,
                    severity=GateSeverity.WARNING,
                    message="代码围栏 ``` 未闭合",
                )
            )
        return findings

    def _check_model(self, content: str) -> list[GateFinding]:
        model = self.output_model
        try:
            if isinstance(model, type) and hasattr(model, "model_validate"):
                # pydantic v2
                model.model_validate(_maybe_extract_json(content))
                return []
            if isinstance(model, type) and hasattr(model, "from_dict"):
                model.from_dict(_maybe_extract_json(content))
                return []
        except Exception as e:  # noqa: BLE001 - deterministic structure failure
            return [
                GateFinding(
                    id="fmt:model",
                    type=FindingType.FORMAT,
                    severity=GateSeverity.ERROR,
                    message=f"结构与输出模型不符: {e}",
                    evidence=str(content)[:500],
                )
            ]
        return []


@dataclass
class FactGrounder:
    """Ensure key conclusions carry provenance (dual-channel sourcing).

    Channel A (auto): provenance extracted from tool call records.
    Channel B (explicit): ``sources=`` passed at call time.
    The usable source set is the union; on conflict, explicit ``sources=`` wins
    (handled by the caller merging with precedence). When the union is empty and
    the content contains factual claims, findings are flagged (not silently
    passed). This is a deterministic heuristic, not a semantic guarantee.
    """

    min_content_len: int = 200
    block_on_unsourced: bool = True

    def check(
        self,
        content: str,
        sources: list[str],
        tool_records: list[dict[str, Any]] | None = None,
    ) -> list[GateFinding]:
        findings: list[GateFinding] = []
        usable = list(sources or [])
        claims = self._extract_claims(content)

        if not claims:
            return findings  # No factual claims -> nothing to ground.

        if not usable:
            sev = GateSeverity.ERROR if self.block_on_unsourced else GateSeverity.WARNING
            findings.append(
                GateFinding(
                    id="fact:no-source",
                    type=FindingType.FACT,
                    severity=sev,
                    message=(
                        "交付含事实性结论（数字/日期/实体）但无溯源引用："
                        "未提供 sources= 且无可用的工具溯源记录"
                    ),
                    evidence="; ".join(claims[:3]),
                )
            )
            return findings

        # Flag claims that look unsupported by any provided source substring.
        for claim in claims:
            if not self._claim_supported(claim, usable):
                findings.append(
                    GateFinding(
                        id="fact:unsupported",
                        type=FindingType.FACT,
                        severity=GateSeverity.WARNING,
                        message="事实性结论未能在溯源中匹配到支撑证据",
                        evidence=claim,
                    )
                )
        return findings

    @staticmethod
    def _extract_claims(content: str) -> list[str]:
        return [m.group(0) for m in _CLAIM_PATTERN.finditer(content)]

    @staticmethod
    def _claim_supported(claim: str, sources: list[str]) -> bool:
        needle = claim.strip()
        if len(needle) > 40:
            needle = needle[:40]
        return any(needle in src for src in sources)


@dataclass
class LogicReconciler:
    """Apply user-supplied deterministic business rules.

    Rules are pure functions ``(content, sources) -> list[GateFinding]``. The
    default set is empty; callers register cross-field / business invariants.
    """

    rules: list[Any] | None = None

    def check(
        self,
        content: str,
        sources: list[str],
        tool_records: list[dict[str, Any]] | None = None,
    ) -> list[GateFinding]:
        findings: list[GateFinding] = []
        for i, rule in enumerate(self.rules or []):
            try:
                findings.extend(rule(content, sources))
            except Exception as e:  # noqa: BLE001 - rule failure must not crash gate
                findings.append(
                    GateFinding(
                        id=f"logic:rule-{i}-error",
                        type=FindingType.LOGIC,
                        severity=GateSeverity.WARNING,
                        message=f"业务规则执行异常: {e}",
                    )
                )
        return findings


def _maybe_extract_json(content: str) -> Any:
    """Best-effort extract a JSON object/array from text for model validation."""
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        import json

        return json.loads(content[start : end + 1])
    return content
