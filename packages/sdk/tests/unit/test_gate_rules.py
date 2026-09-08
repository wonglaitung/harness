"""Unit tests for the deterministic gate business-rule injection.

Covers:
- declarative rule specs (numeric_sum / equality / range / regex_present)
- the callable GateRule path (with an external master source merge)
- load_rule_specs from a JSON file
"""

from __future__ import annotations

import json

import pytest

from harness.gate import compile_rule_specs, load_rule_specs
from harness.gate.models import FindingType, GateFinding, GateRule, GateSeverity


def _run(rules: list[GateRule], content: str) -> list[GateFinding]:
    out: list[GateFinding] = []
    for r in rules:
        out.extend(r(content, []))
    return out


def test_numeric_sum_pass_and_fail() -> None:
    rules = compile_rule_specs(
        [
            {
                "kind": "numeric_sum",
                "left": "assets",
                "rights": ["liabilities", "equity"],
                "tolerance": 0.02,
            }
        ]
    )
    assert not _run(rules, json.dumps({"assets": 100, "liabilities": 60, "equity": 40}))
    bad = _run(rules, json.dumps({"assets": 100, "liabilities": 60, "equity": 50}))
    assert any(f.severity == GateSeverity.ERROR for f in bad)


def test_equality_and_range() -> None:
    eq = compile_rule_specs([{"kind": "equality", "left": "a", "right": "b"}])
    assert not _run(eq, json.dumps({"a": 5, "b": 5}))
    assert _run(eq, json.dumps({"a": 5, "b": 6}))

    rg = compile_rule_specs([{"kind": "range", "field": "x", "min": 0, "max": 10}])
    assert not _run(rg, json.dumps({"x": 3}))
    assert _run(rg, json.dumps({"x": 20}))


def test_regex_present() -> None:
    rules = compile_rule_specs([{"kind": "regex_present", "pattern": "合规"}])
    assert not _run(rules, "本报告已合规审阅")
    assert _run(rules, "无相关声明")


def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        compile_rule_specs([{"kind": "nope"}])


def test_callable_rule_with_master_source() -> None:
    """A≈L+E tie-out merging an external deterministic master source."""
    ctx_values = {"assets": 1000.0, "liabilities": 600.0}

    def tie_out(content: str, sources: list[str]) -> list[GateFinding]:
        spec = json.loads(content)
        vals = {**ctx_values, **spec.get("values", {})}
        a = vals["assets"]
        liab = vals["liabilities"]
        e = vals["equity"]
        dev = abs(a - (liab + e)) / max(abs(a), 1e-9)
        if dev > 0.02:
            return [
                GateFinding(
                    id="logic:tie-out",
                    type=FindingType.LOGIC,
                    severity=GateSeverity.ERROR,
                    message=f"A≠L+E 偏差 {dev:.2%}",
                )
            ]
        return []

    rules: list[GateRule] = [tie_out]
    # equity=400 -> 1000 ≈ 1000 pass
    assert not _run(rules, json.dumps({"values": {"equity": 400.0}}))
    # equity=500 -> 1000 vs 1100 fail
    assert _run(rules, json.dumps({"values": {"equity": 500.0}}))


def test_load_rule_specs_json(tmp_path) -> None:
    path = tmp_path / "rules.json"
    payload = json.dumps({"rules": [{"kind": "regex_present", "pattern": "X"}]})
    path.write_text(payload, encoding="utf-8")
    specs = load_rule_specs(str(path))
    assert specs[0]["kind"] == "regex_present"
    assert compile_rule_specs(specs)  # compiles without error
