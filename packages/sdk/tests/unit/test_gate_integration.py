"""
Gate integration tests through the real AgentHarness / AgentLoop wiring.

These cover the integration gaps S1/S2/S3 found in re-analysis:
- S1: side-effect tools (write/edit/bash) are blocked before execution when the
     deterministic gate fails (loop-level pre-check, not just gate unit tests).
- S2: AgentHarness._apply_gate produces a quarantined delivered_content on failure.
- S3: gate activity is accumulated into gate_metrics() via the real path.

No real LLM is contacted: AgentHarness is built with a stub llm_client.
"""

from __future__ import annotations

import types

from harness.core.agent_loop import AgentLoop
from harness.gate import (
    DeterministicGate,
    GateFinding,
    GateSeverity,
    LogicReconciler,
    Reconciler,
)
from harness.gate.models import FindingType, GateVerdict
from harness.sdk.config import HarnessConfig
from harness.sdk.harness import AgentHarness
from harness.tools.base import Tool
from harness.tools.executor import ExecutorConfig, ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.types import ToolCall, ToolResult


def _always_fail(content: str, sources: list[str]) -> list[GateFinding]:
    return [
        GateFinding(
            id="block",
            type=FindingType.LOGIC,
            severity=GateSeverity.ERROR,
            message="pre-gate blocked",
        )
    ]


def _strict_harness() -> AgentHarness:
    # stub llm_client avoids any network in __init__
    return AgentHarness(config=HarnessConfig(strict=True), llm_client=object())


def _tool_session() -> object:
    # _apply_gate derives provenance from tool-role messages on the session.
    msg = types.SimpleNamespace(role="tool", content="营收5亿元。")
    return types.SimpleNamespace(id="sess", messages=[msg])


class _FakeReadTool(Tool):
    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "read a file"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"path": {"type": "string"}}}

    async def execute(self, arguments: dict, context: object) -> ToolResult:
        return ToolResult(tool_call_id="", success=True, content="read-ok")


def _loop_with_gate(gate: DeterministicGate) -> AgentLoop:
    registry = ToolRegistry()
    registry.register(_FakeReadTool())
    loop = AgentLoop(
        llm_client=object(),
        tool_executor=ToolExecutor(registry, ExecutorConfig(timeout=1)),
        context_builder=object(),
        session_manager=object(),
        config=None,
    )
    loop.gate = gate
    return loop


# -- S2 / S3: AgentHarness._apply_gate + gate_metrics -------------------------


def test_apply_gate_blocks_unsourced_and_records_metrics() -> None:
    h = _strict_harness()
    # No sources (empty session) -> FactGrounder raises fact:no-source (ERROR).
    # Note: a leading space gives the digit a word boundary so the claim regex
    # (which requires \b before the number) fires — a quirk of CJK text.
    verdict = h._apply_gate("根据分析，整体估值 5000亿元，建议据此推进。")
    assert isinstance(verdict, GateVerdict)
    assert not verdict.passed
    # S3: metrics accumulated through the real _apply_gate path.
    snap = h.gate_metrics()
    assert snap["checks"] == 1
    assert snap["blocked"] == 1
    assert snap["passed"] == 0
    assert snap["findings_by_type"].get("fact", 0) >= 1


def test_apply_gate_quarantines_unsourced_claim_in_delivery() -> None:
    h = _strict_harness()
    # One grounded claim (from session), one not -> recon WARNING; stripped.
    verdict = h._apply_gate("营收5亿元，利润-3亿元。", _tool_session())
    assert isinstance(verdict, GateVerdict)
    assert "已隔离" in verdict.delivered_content
    assert "3亿元" not in verdict.delivered_content
    assert "5亿元" in verdict.delivered_content
    snap = h.gate_metrics()
    assert snap["checks"] == 1
    assert snap["passed"] == 1  # only a warning, so the verdict still passes


# -- S1: loop-level side-effect tool pre-gate ---------------------------------


async def test_side_effect_tool_blocked_by_pregate() -> None:
    gate = DeterministicGate(
        validators=[LogicReconciler(rules=[_always_fail])],
        reconciler=Reconciler(),
    )
    loop = _loop_with_gate(gate)
    session = types.SimpleNamespace(id="sess-1")
    results = await loop._execute_tools(
        [ToolCall(id="1", name="write", arguments={"path": "/etc/passwd", "content": "x"})],
        session,
    )
    assert len(results) == 1
    assert results[0].success is False
    assert "确定性闸门" in results[0].error


async def test_non_side_effect_tool_not_pregated() -> None:
    gate = DeterministicGate(
        validators=[LogicReconciler(rules=[_always_fail])],
        reconciler=Reconciler(),
    )
    loop = _loop_with_gate(gate)
    session = types.SimpleNamespace(id="sess-2")
    # `read` is not in _SIDE_EFFECT_TOOLS, so the gate is never consulted and the
    # (failing) gate cannot block it; execution reaches the real tool.
    results = await loop._execute_tools(
        [ToolCall(id="2", name="read", arguments={"path": "/etc/hosts"})],
        session,
    )
    assert any(r.success and r.content == "read-ok" for r in results)
