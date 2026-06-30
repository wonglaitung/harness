"""
Phase 5: Loop Orchestrator - Unified orchestration API.

This module provides the Loop Orchestrator for:
- Workflow execution with declarative step definitions
- Multi-agent team coordination
- Integration with Phase 1-4 components
- Unified monitoring and metrics

Key Components:
- LoopOrchestrator: Main orchestration class
- WorkflowEngine: Workflow execution engine
- TeamOrchestrator: Multi-agent team coordination
- DependencyGraph: Step dependency resolution
- MonitorService: Execution monitoring

Example:
    ```python
    from harness import AgentHarness
    from harness.orchestrator import LoopOrchestrator, WorkflowConfig, WorkflowStep

    agent = AgentHarness(model="claude-sonnet-4-6")
    orchestrator = LoopOrchestrator(agent)

    # Create and run workflow
    workflow = WorkflowConfig(
        name="code-review",
        steps=[
            WorkflowStep(name="analyze", goal="Analyze code"),
            WorkflowStep(name="review", goal="Review code", depends_on=["analyze"]),
        ],
    )
    orchestrator.create_workflow(workflow)
    result = await orchestrator.run_workflow("code-review")
    ```
"""

from harness.orchestrator.core import LoopOrchestrator
from harness.orchestrator.dependency_graph import DependencyGraph
from harness.orchestrator.monitor import MonitorService
from harness.orchestrator.team_orchestrator import TeamOrchestrator
from harness.orchestrator.types import (
    AgentRole,
    CoordinationMode,
    ExecutionMetric,
    ExecutionMode,
    OrchestratorConfig,
    OrchestratorStatus,
    StepResult,
    StepStatus,
    TeamConfig,
    TeamResult,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from harness.orchestrator.workflow_engine import WorkflowEngine

__all__ = [
    # Core
    "LoopOrchestrator",
    "WorkflowEngine",
    "TeamOrchestrator",
    "DependencyGraph",
    "MonitorService",
    # Types
    "WorkflowConfig",
    "WorkflowStep",
    "WorkflowResult",
    "WorkflowStatus",
    "StepResult",
    "StepStatus",
    "ExecutionMode",
    "TeamConfig",
    "TeamResult",
    "AgentRole",
    "CoordinationMode",
    "OrchestratorConfig",
    "OrchestratorStatus",
    "ExecutionMetric",
]
