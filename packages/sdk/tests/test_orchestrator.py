"""
Tests for Phase 5: Loop Orchestrator.

Tests the core orchestration functionality:
- DependencyGraph: Step dependency resolution
- WorkflowEngine: Workflow execution
- TeamOrchestrator: Team coordination
- LoopOrchestrator: End-to-end orchestration
"""

import pytest

from harness.orchestrator.dependency_graph import DependencyGraph
from harness.orchestrator.types import (
    AgentRole,
    CoordinationMode,
    ExecutionMode,
    OrchestratorConfig,
    StepResult,
    StepStatus,
    TeamConfig,
    WorkflowConfig,
    WorkflowStep,
)


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_add_step(self):
        """Test adding steps to graph."""
        graph = DependencyGraph()
        step = WorkflowStep(name="test", goal="Test step")

        graph.add_step(step)

        assert graph.get_step("test") == step
        assert graph.has_pending()

    def test_add_dependency(self):
        """Test adding dependencies."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First")
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step2", "step1")

        deps = graph.get_dependencies("step2")
        assert "step1" in deps

    def test_get_ready_steps(self):
        """Test getting ready steps."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First")
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step2", "step1")

        # Only step1 is ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].name == "step1"

        # Mark step1 complete
        graph.mark_completed("step1")

        # Now step2 is ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].name == "step2"

    def test_detect_deadlock(self):
        """Test deadlock detection."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First", depends_on=["step2"])
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step1", "step2")
        graph.add_dependency("step2", "step1")

        assert graph.detect_deadlock() is True

    def test_no_deadlock(self):
        """Test no deadlock in valid graph."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First")
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step2", "step1")

        assert graph.detect_deadlock() is False

    def test_mark_skipped_cascade(self):
        """Test cascading skip."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First")
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])
        step3 = WorkflowStep(name="step3", goal="Third", depends_on=["step2"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)
        graph.add_dependency("step2", "step1")
        graph.add_dependency("step3", "step2")

        # Skip step1
        graph.mark_skipped("step1")

        # step2 and step3 should be skipped too
        assert graph.is_skipped("step1")
        assert graph.is_skipped("step2")
        assert graph.is_skipped("step3")

    def test_has_only_skipped_pending(self):
        """Test detection of all-pending-skipped."""
        graph = DependencyGraph()
        step1 = WorkflowStep(name="step1", goal="First")
        step2 = WorkflowStep(name="step2", goal="Second", depends_on=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step2", "step1")

        # Skip step1
        graph.mark_skipped("step1")

        # All pending depend on skipped
        assert graph.has_only_skipped_pending() is True


class TestWorkflowTypes:
    """Tests for workflow type definitions."""

    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="analyze",
            goal="Analyze code",
            skills=["code-analysis"],
            exports={"report": "$.artifacts.report"},
        )

        assert step.name == "analyze"
        assert step.mode == ExecutionMode.SEQUENTIAL
        assert "code-analysis" in step.skills
        assert step.exports["report"] == "$.artifacts.report"

    def test_workflow_step_validation(self):
        """Test step validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorkflowStep(name="", goal="Test")

        with pytest.raises(ValueError, match="goal cannot be empty"):
            WorkflowStep(name="test", goal="")

    def test_workflow_config_creation(self):
        """Test creating a workflow config."""
        config = WorkflowConfig(
            name="test-workflow",
            description="Test workflow",
            steps=[
                WorkflowStep(name="step1", goal="First"),
                WorkflowStep(name="step2", goal="Second", depends_on=["step1"]),
            ],
        )

        assert config.name == "test-workflow"
        assert len(config.steps) == 2
        assert config.default_mode == ExecutionMode.SEQUENTIAL

    def test_workflow_config_unique_names(self):
        """Test workflow requires unique step names."""
        with pytest.raises(ValueError, match="unique"):
            WorkflowConfig(
                name="test",
                steps=[
                    WorkflowStep(name="step1", goal="First"),
                    WorkflowStep(name="step1", goal="Duplicate"),
                ],
            )


class TestTeamTypes:
    """Tests for team type definitions."""

    def test_agent_role_creation(self):
        """Test creating an agent role."""
        role = AgentRole(
            name="developer",
            description="Writes code",
            skills=["coding", "testing"],
            max_iterations=30,
        )

        assert role.name == "developer"
        assert "coding" in role.skills
        assert role.max_iterations == 30

    def test_agent_role_validation(self):
        """Test role validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            AgentRole(name="", description="Test")

        with pytest.raises(ValueError, match="description cannot be empty"):
            AgentRole(name="test", description="")

    def test_team_config_creation(self):
        """Test creating a team config."""
        config = TeamConfig(
            name="dev-team",
            roles=[
                AgentRole(name="architect", description="Designs"),
                AgentRole(name="developer", description="Codes"),
            ],
            coordination_mode=CoordinationMode.SEQUENTIAL,
        )

        assert config.name == "dev-team"
        assert len(config.roles) == 2
        assert config.coordination_mode == CoordinationMode.SEQUENTIAL

    def test_team_config_requires_roles(self):
        """Test team requires at least one role."""
        with pytest.raises(ValueError, match="at least one role"):
            TeamConfig(name="empty-team", roles=[])

    def test_team_config_unique_role_names(self):
        """Test team requires unique role names."""
        with pytest.raises(ValueError, match="unique"):
            TeamConfig(
                name="test",
                roles=[
                    AgentRole(name="dev", description="First"),
                    AgentRole(name="dev", description="Duplicate"),
                ],
            )


class TestOrchestratorConfig:
    """Tests for orchestrator configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.max_concurrent_goals == 5
        assert config.max_parallel_steps == 5
        assert config.max_teams == 10
        assert config.metrics_retention == 1000

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            OrchestratorConfig(max_concurrent_goals=0)

        with pytest.raises(ValueError):
            OrchestratorConfig(max_parallel_steps=0)


class TestStepResult:
    """Tests for step result."""

    def test_step_result_duration(self):
        """Test step result duration calculation."""
        from datetime import datetime, timedelta

        now = datetime.now()
        result = StepResult(
            step_name="test",
            status=StepStatus.SUCCESS,
            started_at=now,
            completed_at=now + timedelta(seconds=10),
        )

        assert result.duration_seconds == 10.0

    def test_step_result_exports(self):
        """Test step result exports."""
        result = StepResult(
            step_name="test",
            status=StepStatus.SUCCESS,
            exports={"report_path": "/tmp/report.txt", "count": 5},
        )

        assert result.exports["report_path"] == "/tmp/report.txt"
        assert result.exports["count"] == 5
