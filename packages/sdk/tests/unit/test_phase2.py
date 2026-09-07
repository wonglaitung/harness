"""Phase 2 integration tests: workflow retry + team shared-state routing.

Uses lightweight fakes (no network / LLM) to verify the deterministic gate
abstraction layer is correctly wired into multi-agent execution.
"""

from __future__ import annotations

from types import SimpleNamespace

from harness.orchestrator.team_orchestrator import TeamOrchestrator
from harness.orchestrator.types import AgentRole, TeamConfig
from harness.orchestrator.workflow_engine import WorkflowEngine
from harness.review import ReviewQueue
from harness.state import create_state_store


class _FakeAgent:
    """Records run_goal calls; fails the first ``failures`` times."""

    def __init__(self, failures: int = 0, achieved: bool = True) -> None:
        self.failures = failures
        self._calls = 0
        self.achieved = achieved

    async def run_goal(self, _config: object) -> SimpleNamespace:
        self._calls += 1
        if self._calls <= self.failures:
            raise RuntimeError(f"transient {self._calls}")
        return SimpleNamespace(
            achieved=self.achieved,
            final_response="done",
            gate_verdict=None,
        )


async def test_workflow_honors_max_retries() -> None:
    agent = _FakeAgent(failures=2, achieved=True)
    orch = SimpleNamespace(agent=agent)
    engine = WorkflowEngine(orch)

    from harness.orchestrator.types import WorkflowConfig, WorkflowStep

    step = WorkflowStep(name="s", goal="do", max_retries=2, retry_delay=0.0)
    result = await engine.run(WorkflowConfig(name="w", steps=[step]))

    # initial + 2 retries = 3 calls; step then succeeds.
    assert agent._calls == 3
    assert result.steps["s"].status.value == "success"


async def test_workflow_retry_exhaustion_fails() -> None:
    agent = _FakeAgent(failures=5, achieved=True)
    orch = SimpleNamespace(agent=agent)
    engine = WorkflowEngine(orch)

    from harness.orchestrator.types import WorkflowConfig, WorkflowStep

    step = WorkflowStep(name="s", goal="do", max_retries=1, retry_delay=0.0)
    result = await engine.run(WorkflowConfig(name="w", steps=[step]))

    # initial + 1 retry = 2 calls, then exhausted -> FAILED.
    assert agent._calls == 2
    assert result.steps["s"].status.value == "failed"


async def test_team_persists_to_shared_state() -> None:
    orch = SimpleNamespace(agent=SimpleNamespace())
    to = TeamOrchestrator(orch)
    store = create_state_store("memory")
    role = AgentRole(name="researcher", description="research")
    config = TeamConfig(name="team", roles=[role], state_store=store)

    result = SimpleNamespace(
        final_response="raw output", delivered_content="reconciled", gate_verdict=None
    )
    await to._record_agent_result(config, role, result, "task")

    items = await store.list_items()
    assert len(items) == 1
    assert items[0].content == "reconciled"
    assert items[0].source_agent == "researcher"


async def test_team_escalates_gate_failure_to_review() -> None:
    orch = SimpleNamespace(agent=SimpleNamespace())
    to = TeamOrchestrator(orch)
    store = create_state_store("memory")
    queue = ReviewQueue()
    role = AgentRole(name="writer", description="write")
    config = TeamConfig(name="team", roles=[role], state_store=store, review_queue=queue)

    # A gate verdict that failed (e.g., unsourced factual claim).
    verdict = SimpleNamespace(passed=False, findings=[{"id": "fact:no-source"}])
    result = SimpleNamespace(
        final_response="x grew 12%", delivered_content="x grew 12%", gate_verdict=verdict
    )
    await to._record_agent_result(config, role, result, "task")

    assert len(queue.pending()) == 1
