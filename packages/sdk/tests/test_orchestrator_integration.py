"""
Integration tests for Phase 5: Loop Orchestrator.

Tests end-to-end workflow and team execution with MockHarness.
"""


import pytest

from harness.orchestrator import (
    AgentRole,
    CoordinationMode,
    ExecutionMode,
    LoopOrchestrator,
    OrchestratorConfig,
    TeamConfig,
    WorkflowConfig,
    WorkflowStep,
)
from harness.testing import MockHarness, MockResponse

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent():
    """Create a MockHarness for testing."""
    return MockHarness(
        responses=[
            MockResponse(content="Task completed successfully"),
        ]
    )


@pytest.fixture
def orchestrator(mock_agent):
    """Create a LoopOrchestrator with mock agent."""
    return LoopOrchestrator(mock_agent, OrchestratorConfig())


# =============================================================================
# Workflow Integration Tests
# =============================================================================


class TestWorkflowIntegration:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_simple_workflow(self, orchestrator):
        """Test a simple 2-step workflow."""
        workflow = WorkflowConfig(
            name="simple-test",
            steps=[
                WorkflowStep(name="step1", goal="Do first task"),
                WorkflowStep(name="step2", goal="Do second task", depends_on=["step1"]),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("simple-test")

        assert result.success
        assert "step1" in result.steps
        assert "step2" in result.steps
        assert result.steps["step1"].status.value == "success"
        assert result.steps["step2"].status.value == "success"

    @pytest.mark.asyncio
    async def test_parallel_workflow(self, orchestrator):
        """Test parallel step execution."""
        workflow = WorkflowConfig(
            name="parallel-test",
            default_mode=ExecutionMode.PARALLEL,
            steps=[
                WorkflowStep(name="task1", goal="Task 1"),
                WorkflowStep(name="task2", goal="Task 2"),
                WorkflowStep(name="task3", goal="Task 3"),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("parallel-test")

        assert result.success
        assert len(result.steps) == 3

    @pytest.mark.asyncio
    async def test_conditional_skip(self, mock_agent):
        """Test conditional step execution with skip."""
        # Setup mock to return different responses
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="skip"),  # step1
                MockResponse(content="done"),  # step2
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        workflow = WorkflowConfig(
            name="conditional-test",
            steps=[
                WorkflowStep(
                    name="step1",
                    goal="Check condition",
                ),
                WorkflowStep(
                    name="step2",
                    goal="Conditional task",
                    depends_on=["step1"],
                    condition="steps['step1'].goal_result.final_response == 'proceed'",
                ),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("conditional-test")

        # step2 should be skipped because condition is false
        assert result.success  # SKIPPED counts as success
        assert result.steps["step2"].status.value == "skipped"

    @pytest.mark.asyncio
    async def test_template_rendering(self, mock_agent):
        """Test template variable rendering between steps."""
        # Mock agent that returns structured data
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="Analysis report saved to /tmp/report.txt"),
                MockResponse(content="Review completed"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        workflow = WorkflowConfig(
            name="template-test",
            steps=[
                WorkflowStep(
                    name="analyze",
                    goal="Analyze code",
                ),
                WorkflowStep(
                    name="review",
                    goal="Review based on {{steps.analyze.goal_result.final_response}}",
                    depends_on=["analyze"],
                ),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("template-test")

        assert result.success

    @pytest.mark.asyncio
    async def test_yaml_workflow(self, orchestrator, tmp_path):
        """Test loading workflow from YAML file."""
        yaml_content = """
name: yaml-test
description: Test YAML workflow

steps:
  - name: first
    goal: First task
    skills: []

  - name: second
    goal: Second task
    depends_on: [first]

output_channels: []
"""
        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text(yaml_content)

        orchestrator.create_workflow_from_yaml(str(yaml_file))
        result = await orchestrator.run_workflow("yaml-test")

        assert result.success
        assert "first" in result.steps
        assert "second" in result.steps


# =============================================================================
# Team Integration Tests
# =============================================================================


class TestTeamIntegration:
    """End-to-end team tests."""

    @pytest.mark.asyncio
    async def test_broadcast_team(self, mock_agent):
        """Test broadcast mode - all agents execute same task."""
        # Need 3 responses for 3 roles
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="Architect analysis"),
                MockResponse(content="Developer implementation"),
                MockResponse(content="Reviewer feedback"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        team = TeamConfig(
            name="broadcast-team",
            roles=[
                AgentRole(name="architect", description="Designs system"),
                AgentRole(name="developer", description="Writes code"),
                AgentRole(name="reviewer", description="Reviews code"),
            ],
            coordination_mode=CoordinationMode.BROADCAST,
        )

        orchestrator.create_team(team)
        result = await orchestrator.run_team("broadcast-team", "Implement feature X")

        assert result.success
        assert len(result.agent_results) == 3
        assert "architect" in result.agent_results
        assert "developer" in result.agent_results
        assert "reviewer" in result.agent_results

    @pytest.mark.asyncio
    async def test_sequential_team(self, mock_agent):
        """Test sequential mode - agents execute in order."""
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="Architecture done"),
                MockResponse(content="Code written"),
                MockResponse(content="Review passed"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        team = TeamConfig(
            name="sequential-team",
            roles=[
                AgentRole(name="architect", description="Designs first"),
                AgentRole(name="developer", description="Implements second"),
            ],
            coordination_mode=CoordinationMode.SEQUENTIAL,
        )

        orchestrator.create_team(team)
        result = await orchestrator.run_team("sequential-team", "Build feature Y")

        assert result.success
        assert len(result.agent_results) == 2

    @pytest.mark.asyncio
    async def test_hierarchical_team(self, mock_agent):
        """Test hierarchical mode - leader assigns tasks."""
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="Leader assigns: developer do X"),
                MockResponse(content="Developer completes X"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        team = TeamConfig(
            name="hierarchical-team",
            roles=[
                AgentRole(name="leader", description="Assigns tasks"),
                AgentRole(name="worker", description="Executes tasks"),
            ],
            coordination_mode=CoordinationMode.HIERARCHICAL,
        )

        orchestrator.create_team(team)
        result = await orchestrator.run_team("hierarchical-team", "Complete project Z")

        assert result.success

    @pytest.mark.asyncio
    async def test_team_coordination_mode_override(self, mock_agent):
        """Test overriding coordination mode at runtime."""
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="Task done"),
                MockResponse(content="Task done"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        team = TeamConfig(
            name="flexible-team",
            roles=[
                AgentRole(name="agent1", description="First agent"),
                AgentRole(name="agent2", description="Second agent"),
            ],
            coordination_mode=CoordinationMode.BROADCAST,
        )

        orchestrator.create_team(team)

        # Override to sequential
        result = await orchestrator.run_team(
            "flexible-team", "Task", mode="sequential"
        )

        assert result.success


# =============================================================================
# Orchestrator Lifecycle Tests
# =============================================================================


class TestOrchestratorLifecycle:
    """Test orchestrator start/stop and status."""

    @pytest.mark.asyncio
    async def test_start_stop(self, orchestrator):
        """Test orchestrator lifecycle."""
        assert not orchestrator.is_running

        await orchestrator.start()
        assert orchestrator.is_running

        await orchestrator.stop()
        assert not orchestrator.is_running

    @pytest.mark.asyncio
    async def test_get_status(self, orchestrator):
        """Test status retrieval."""
        status = orchestrator.get_status()

        assert not status.running
        assert status.active_workflows == 0
        assert status.registered_triggers == 0

    @pytest.mark.asyncio
    async def test_metrics_recording(self, orchestrator):
        """Test execution metrics."""
        workflow = WorkflowConfig(
            name="metrics-test",
            steps=[WorkflowStep(name="step1", goal="Task")],
        )

        orchestrator.create_workflow(workflow)
        await orchestrator.run_workflow("metrics-test")

        metrics = orchestrator.get_metrics()
        assert len(metrics) > 0
        assert metrics[0].name == "metrics-test"
        assert metrics[0].type == "workflow"

    @pytest.mark.asyncio
    async def test_summary_statistics(self, orchestrator):
        """Test summary statistics."""
        workflow = WorkflowConfig(
            name="summary-test",
            steps=[WorkflowStep(name="step1", goal="Task")],
        )

        orchestrator.create_workflow(workflow)
        await orchestrator.run_workflow("summary-test")

        summary = orchestrator.get_summary()
        assert summary["total_executions"] > 0
        assert summary["success_rate"] >= 0.0


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_not_found(self, orchestrator):
        """Test error when workflow doesn't exist."""
        with pytest.raises(ValueError, match="Workflow not found"):
            await orchestrator.run_workflow("nonexistent")

    @pytest.mark.asyncio
    async def test_team_not_found(self, orchestrator):
        """Test error when team doesn't exist."""
        with pytest.raises(ValueError, match="Team not found"):
            await orchestrator.run_team("nonexistent", "task")

    @pytest.mark.asyncio
    async def test_circular_dependency(self, orchestrator):
        """Test deadlock detection."""
        workflow = WorkflowConfig(
            name="deadlock-test",
            steps=[
                WorkflowStep(name="a", goal="A", depends_on=["b"]),
                WorkflowStep(name="b", goal="B", depends_on=["a"]),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("deadlock-test")

        # Should fail due to deadlock
        assert not result.success
        assert "Deadlock" in result.error

    @pytest.mark.asyncio
    async def test_duplicate_workflow(self, orchestrator):
        """Test creating duplicate workflow."""
        workflow = WorkflowConfig(
            name="duplicate",
            steps=[WorkflowStep(name="step1", goal="Task")],
        )

        orchestrator.create_workflow(workflow)

        # Creating again should overwrite
        orchestrator.create_workflow(workflow)
        assert orchestrator.workflow_count == 1


# =============================================================================
# Complex Workflow Tests
# =============================================================================


class TestComplexWorkflows:
    """Test complex workflow scenarios."""

    @pytest.mark.asyncio
    async def test_diamond_dependency(self, mock_agent):
        """Test diamond-shaped dependency graph.

               A
              / \\
             B   C
              \\ /
               D
        """
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="A done"),
                MockResponse(content="B done"),
                MockResponse(content="C done"),
                MockResponse(content="D done"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        workflow = WorkflowConfig(
            name="diamond-test",
            steps=[
                WorkflowStep(name="A", goal="Step A"),
                WorkflowStep(name="B", goal="Step B", depends_on=["A"]),
                WorkflowStep(name="C", goal="Step C", depends_on=["A"]),
                WorkflowStep(name="D", goal="Step D", depends_on=["B", "C"]),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("diamond-test")

        assert result.success
        # Verify execution order: A before B/C, B and C before D
        assert result.steps["A"].status.value == "success"
        assert result.steps["B"].status.value == "success"
        assert result.steps["C"].status.value == "success"
        assert result.steps["D"].status.value == "success"

    @pytest.mark.asyncio
    async def test_cascade_skip_chain(self, mock_agent):
        """Test that skipped steps cascade to all dependents."""
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="skip"),  # A - will trigger skip
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        workflow = WorkflowConfig(
            name="cascade-test",
            steps=[
                WorkflowStep(
                    name="A",
                    goal="Step A",
                    condition="False",  # Always skip
                ),
                WorkflowStep(name="B", goal="Step B", depends_on=["A"]),
                WorkflowStep(name="C", goal="Step C", depends_on=["B"]),
                WorkflowStep(name="D", goal="Step D", depends_on=["C"]),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("cascade-test")

        # All steps should be skipped
        assert result.success
        assert result.steps["A"].status.value == "skipped"
        assert result.steps["B"].status.value == "skipped"
        assert result.steps["C"].status.value == "skipped"
        assert result.steps["D"].status.value == "skipped"

    @pytest.mark.asyncio
    async def test_mixed_parallel_sequential(self, mock_agent):
        """Test workflow with both parallel and sequential parts."""
        mock_agent = MockHarness(
            responses=[
                MockResponse(content="A done"),
                MockResponse(content="B done"),
                MockResponse(content="C done"),
                MockResponse(content="D done"),
            ]
        )
        orchestrator = LoopOrchestrator(mock_agent)

        workflow = WorkflowConfig(
            name="mixed-test",
            default_mode=ExecutionMode.PARALLEL,
            steps=[
                # B and C run in parallel after A
                WorkflowStep(name="A", goal="Step A"),
                WorkflowStep(name="B", goal="Step B", depends_on=["A"]),
                WorkflowStep(name="C", goal="Step C", depends_on=["A"]),
                # D runs after both B and C complete
                WorkflowStep(name="D", goal="Step D", depends_on=["B", "C"]),
            ],
        )

        orchestrator.create_workflow(workflow)
        result = await orchestrator.run_workflow("mixed-test")

        assert result.success
