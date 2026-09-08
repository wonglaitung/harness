"""Declarative business-rule specs for the deterministic gate.

Compile a list of spec dicts into :data:`~harness.gate.models.GateRule`
callables — the exact contract :class:`~harness.gate.validators.LogicReconciler`
consumes. This lets operators author invariants (e.g. a numeric-sum tie-out)
in YAML/JSON without writing Python.

IMPORTANT: declarative specs only see the delivery *text*. Checks that need an
external deterministic master source (e.g. a finance pipeline's ``ctx["values"]``
merged with the agent's spec) must be expressed as a Python callable via
``GateConfig.rules`` instead — the declarative engine has no access to that
context. Both paths feed the same ``LogicReconciler(rules=...)``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from harness.gate.models import (
    FindingType,
    GateFinding,
    GateRule,
    GateSeverity,
)


def _severity_of(spec: dict[str, Any]) -> GateSeverity:
    return GateSeverity.ERROR if spec.get("severity", "error") == "error" else GateSeverity.WARNING


def _to_number(raw: str | float | int | None) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    if raw is None:
        return None
    s = str(raw).replace(",", "").replace("%", "")
    for unit in ("亿元", "万元", "元", "USD", "$"):
        s = s.replace(unit, "")
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None


def _extract_labeled_number(text: str, label: str) -> float | None:
    """Pull a number following ``label`` in free text (e.g. ``资产总计 1234``)."""
    pat = re.compile(re.escape(label) + r"[:：\s]+[¥$]?\s?([\d][\d,]*(?:\.\d+)?)")
    m = pat.search(text)
    if m:
        return _to_number(m.group(1))
    return None


def _values_from_content(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _lookup(key: str, content: str, data: dict[str, Any] | None) -> float | None:
    """Resolve ``key`` from JSON content first, then labeled text extraction."""
    if data is not None:
        v = data.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return _extract_labeled_number(content, key)


def _numeric_sum_rule(spec: dict[str, Any]) -> GateRule:
    rid = spec.get("id", "numeric_sum")
    left = spec["left"]
    rights = spec["rights"]
    tol = float(spec.get("tolerance", 0.01))
    sev = _severity_of(spec)
    msg = spec.get("message", f"{left} 应≈ Σ{rights}（容差 {tol:.0%}）")

    def rule(content: str, sources: list[str]) -> list[GateFinding]:
        findings: list[GateFinding] = []
        data = _values_from_content(content)
        lv = _lookup(left, content, data)
        rv = [_lookup(r, content, data) for r in rights]
        if lv is None or any(v is None for v in rv):
            findings.append(
                GateFinding(
                    id=f"logic:{rid}:missing",
                    type=FindingType.LOGIC,
                    severity=GateSeverity.WARNING,
                    message=f"{rid}: 无法取数（{left} 或 {rights}）",
                )
            )
            return findings
        rv_f = [v for v in rv if v is not None]
        s = sum(rv_f)
        if abs(lv - s) / max(abs(lv), 1e-9) > tol:
            dev = abs(lv - s) / max(abs(lv), 1e-9)
            findings.append(
                GateFinding(
                    id=f"logic:{rid}",
                    type=FindingType.LOGIC,
                    severity=sev,
                    message=f"{msg}：{left}={lv:.4g}, Σ{rights}={s:.4g}, 偏差 {dev:.2%}",
                )
            )
        return findings

    return rule


def _equality_rule(spec: dict[str, Any]) -> GateRule:
    rid = spec.get("id", "equality")
    left = spec["left"]
    right = spec["right"]
    sev = _severity_of(spec)
    msg = spec.get("message", f"{left} 应= {right}")

    def rule(content: str, sources: list[str]) -> list[GateFinding]:
        data = _values_from_content(content)
        lv = _lookup(left, content, data)
        rv = _lookup(right, content, data)
        if lv is None or rv is None:
            return [
                GateFinding(
                    id=f"logic:{rid}:missing",
                    type=FindingType.LOGIC,
                    severity=GateSeverity.WARNING,
                    message=f"{rid}: 无法取数（{left} 或 {right}）",
                )
            ]
        if abs(lv - rv) / max(abs(lv), 1e-9) > 1e-9:
            return [
                GateFinding(
                    id=f"logic:{rid}",
                    type=FindingType.LOGIC,
                    severity=sev,
                    message=f"{msg}：{left}={lv:.4g}, {right}={rv:.4g}",
                )
            ]
        return []

    return rule


def _range_rule(spec: dict[str, Any]) -> GateRule:
    rid = spec.get("id", "range")
    field = spec["field"]
    lo = spec.get("min")
    hi = spec.get("max")
    sev = _severity_of(spec)
    msg = spec.get("message", f"{field} 应在 [{lo}, {hi}] 内")

    def rule(content: str, sources: list[str]) -> list[GateFinding]:
        data = _values_from_content(content)
        v = _lookup(field, content, data)
        if v is None:
            return [
                GateFinding(
                    id=f"logic:{rid}:missing",
                    type=FindingType.LOGIC,
                    severity=GateSeverity.WARNING,
                    message=f"{rid}: 无法取数（{field}）",
                )
            ]
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            return [
                GateFinding(
                    id=f"logic:{rid}",
                    type=FindingType.LOGIC,
                    severity=sev,
                    message=f"{msg}：{field}={v:.4g}",
                )
            ]
        return []

    return rule


def _regex_present_rule(spec: dict[str, Any]) -> GateRule:
    rid = spec.get("id", "regex_present")
    pattern = spec["pattern"]
    sev = _severity_of(spec)
    msg = spec.get("message", f"交付必须包含匹配 /{pattern}/ 的内容")
    compiled = re.compile(pattern)

    def rule(content: str, sources: list[str]) -> list[GateFinding]:
        if not compiled.search(content or ""):
            return [
                GateFinding(
                    id=f"logic:{rid}",
                    type=FindingType.LOGIC,
                    severity=sev,
                    message=msg,
                )
            ]
        return []

    return rule


_DISPATCH: dict[str, Any] = {
    "numeric_sum": _numeric_sum_rule,
    "equality": _equality_rule,
    "range": _range_rule,
    "regex_present": _regex_present_rule,
}


def compile_rule_specs(specs: list[dict[str, Any]] | None) -> list[GateRule]:
    """Compile declarative rule specs into ``GateRule`` callables.

    Raises ``ValueError`` on an unknown ``kind``.
    """
    rules: list[GateRule] = []
    for spec in specs or []:
        kind = spec.get("kind")
        if kind is None:
            raise ValueError("rule spec missing 'kind'")
        factory = _DISPATCH.get(kind)
        if factory is None:
            raise ValueError(f"Unknown rule kind: {kind!r} (expected one of {sorted(_DISPATCH)})")
        rules.append(factory(spec))
    return rules


def load_rule_specs(path: str) -> list[dict[str, Any]]:
    """Load declarative rule specs from a YAML or JSON file.

    Accepts either a bare list or ``{"rules": [...]}``.
    """
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        import yaml  # type: ignore[import-untyped]

        data: Any = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if isinstance(data, dict) and "rules" in data:
        data = data["rules"]
    if not isinstance(data, list):
        raise ValueError("rule specs must be a list or {'rules': [...]}")
    return data
