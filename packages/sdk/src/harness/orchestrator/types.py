"""
Orchestrator types - Phase 5 Loop Orchestrator type definitions.

This module defines types for workflow orchestration and multi-agent teams:
- WorkflowStatus: Workflow execution status
- StepStatus: Workflow step status
- ExecutionMode: Step execution mode
- WorkflowStep: Single workflow step configuration
- WorkflowConfig: Complete workflow configuration
- StepResult: Step execution result
- WorkflowResult: Workflow execution result
- AgentRole: Agent role definition
- TeamConfig: Multi-agent team configuration
- TeamResult: Team execution result
- OrchestratorConfig: Orchestrator configuration
- OrchestratorStatus: Orchestrator runtime status
- ExecutionMetric: Execution metrics for monitoring
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.loop.types import GoalResult


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"  # Waiting to execute
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Execution failed
    CANCELLED = "cancelled"  # User cancelled


class StepStatus(Enum):
    """Workflow step execution status."""

    PENDING = "pending"  # Waiting to execute
    RUNNING = "running"  # Currently executing
    SUCCESS = "success"  # Successfully completed
    FAILED = "failed"  # Execution failed
    SKIPPED = "skipped"  # Skipped due to condition or dependency


class ExecutionMode(Enum):
    """Step execution mode."""

    SEQUENTIAL = "sequential"  # Execute steps one after another
    PARALLEL = "parallel"  # Execute steps concurrently
    CONDITIONAL = "conditional"  # Execute based on condition


@dataclass
class WorkflowStep:
    """
    Single workflow step configuration.

    Each step is a Goal execution unit. Supports template variables
    in the goal description to reference outputs from previous steps.

    Attributes:
        name: Unique step name within the workflow
        goal: Goal description (supports {{steps.prev.exports.key}} template syntax)
        mode: Execution mode (sequential, parallel, conditional)
        depends_on: List of step names this step depends on
        workspace_dir: Working directory for this step
        max_iterations: Maximum goal iterations
        timeout_seconds: Execution timeout in seconds
        custom_verifier: Optional custom verification function
        skills: Skills to activate for this step
        condition: Python expression for conditional execution
        exports: Export configuration to extract data from GoalResult
        max_retries: Maximum retry attempts on failure
        retry_delay: Delay between retries in seconds

    Example:
        ```python
        step = WorkflowStep(
            name="analyze",
            goal="Analyze code changes and identify issues",
            skills=["code-analysis"],
            exports={"report_path": "$.artifacts.report_file"},
        )
        ```
    """

    name: str
    goal: str

    # Execution configuration
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)

    # Goal configuration
    workspace_dir: str = "."
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None

    # Skills configuration
    skills: list[str] = field(default_factory=list)

    # Conditional execution
    condition: str | None = None

    # Export configuration
    exports: dict[str, str] = field(default_factory=dict)

    # Retry configuration
    max_retries: int = 0
    retry_delay: float = 5.0

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("step name cannot be empty")

        if not self.goal:
            raise ValueError("step goal cannot be empty")

        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")


@dataclass
class WorkflowConfig:
    """
    Complete workflow configuration.

    A workflow consists of multiple steps with dependencies and
    execution modes. Supports declarative definition via YAML.

    Attributes:
        name: Workflow name
        description: Workflow description
        steps: List of workflow steps
        default_mode: Default execution mode for steps
        max_parallel_steps: Maximum concurrent parallel steps
        workspace_dir: Default working directory
        trigger_on: Trigger configuration (cron or event)
        output_channels: Output channels for results

    Example:
        ```python
        workflow = WorkflowConfig(
            name="code-review",
            steps=[
                WorkflowStep(name="analyze", goal="Analyze code"),
                WorkflowStep(name="review", goal="Review code", depends_on=["analyze"]),
            ],
        )
        ```
    """

    name: str
    description: str = ""

    # Step definitions
    steps: list[WorkflowStep] = field(default_factory=list)

    # Execution configuration
    default_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_parallel_steps: int = 5

    # Global configuration
    workspace_dir: str = "."

    # Trigger configuration
    trigger_on: str | None = None  # "cron:0 9 * * *" or "event:github.pull_request.opened"

    # Output configuration
    output_channels: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("workflow name cannot be empty")

        if self.max_parallel_steps < 1:
            raise ValueError("max_parallel_steps must be at least 1")

        # Validate step names are unique
        step_names = [s.name for s in self.steps]
        if len(step_names) != len(set(step_names)):
            raise ValueError("step names must be unique within workflow")


@dataclass
class StepResult:
    """
    Step execution result.

    Contains the outcome of a single workflow step execution,
    including the goal result and any exported data.

    Attributes:
        step_name: Name of the step
        status: Execution status
        goal_result: Goal execution result (if executed)
        exports: Exported data from this step
        error: Error message if failed
        started_at: Execution start time
        completed_at: Execution completion time
    """

    step_name: str
    status: StepStatus
    goal_result: GoalResult | None = None
    exports: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate step duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class WorkflowResult:
    """
    Workflow execution result.

    Contains comprehensive information about workflow execution
    including all step results and overall status.

    Attributes:
        workflow_name: Name of the workflow
        status: Overall workflow status
        steps: Results for each step (keyed by step name)
        started_at: Workflow start time
        completed_at: Workflow completion time
        error: Error message if failed
    """

    workflow_name: str
    status: WorkflowStatus
    steps: dict[str, StepResult]
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def duration_seconds(self) -> float:
        """Calculate total workflow duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def get_step_result(self, step_name: str) -> StepResult | None:
        """Get result for a specific step."""
        return self.steps.get(step_name)

    def get_successful_steps(self) -> list[str]:
        """Get names of successfully completed steps."""
        return [name for name, result in self.steps.items() if result.status == StepStatus.SUCCESS]

    def get_failed_steps(self) -> list[str]:
        """Get names of failed steps."""
        return [name for name, result in self.steps.items() if result.status == StepStatus.FAILED]

    def get_skipped_steps(self) -> list[str]:
        """Get names of skipped steps."""
        return [name for name, result in self.steps.items() if result.status == StepStatus.SKIPPED]


# =============================================================================
# Team Orchestration Types
# =============================================================================


class CoordinationMode(Enum):
    """Team coordination mode."""

    BROADCAST = "broadcast"  # All agents execute same task simultaneously
    SEQUENTIAL = "sequential"  # Agents execute in sequence, passing outputs
    HIERARCHICAL = "hierarchical"  # Leader assigns tasks to workers


@dataclass
class AgentRole:
    """
    Agent role definition.

    Defines a specific role within a multi-agent team,
    including skills, tools, and behavioral configuration.

    Attributes:
        name: Role name (e.g., "architect", "developer")
        description: Role description
        skills: Skills to activate for this role
        allowed_tools: Optional list of allowed tool names
        system_prompt: Custom system prompt for this role
        max_iterations: Maximum goal iterations for this role
    """

    name: str
    description: str

    # Skills and tools
    skills: list[str] = field(default_factory=list)
    allowed_tools: list[str] | None = None

    # Behavior configuration
    system_prompt: str | None = None
    max_iterations: int = 20

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("role name cannot be empty")

        if not self.description:
            raise ValueError("role description cannot be empty")


@dataclass
class TeamConfig:
    """
    Multi-agent team configuration.

    Defines a team of agents that can work together on tasks
    using different coordination modes.

    Attributes:
        name: Team name
        description: Team description
        roles: List of agent roles in the team
        coordination_mode: How agents coordinate (broadcast/sequential/hierarchical)
        shared_memory: Whether agents share memory
        message_bus: Communication mechanism ("internal" | "redis" | "eventbus")

    Example:
        ```python
        team = TeamConfig(
            name="dev-team",
            roles=[
                AgentRole(name="architect", description="System design"),
                AgentRole(name="developer", description="Implementation"),
            ],
            coordination_mode="sequential",
        )
        ```
    """

    name: str
    description: str = ""

    # Role definitions
    roles: list[AgentRole] = field(default_factory=list)

    # Coordination configuration
    coordination_mode: CoordinationMode = CoordinationMode.BROADCAST

    # Communication configuration
    shared_memory: bool = True
    message_bus: str = "internal"  # "internal" | "redis" | "eventbus"

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("team name cannot be empty")

        if not self.roles:
            raise ValueError("team must have at least one role")

        # Validate role names are unique
        role_names = [r.name for r in self.roles]
        if len(role_names) != len(set(role_names)):
            raise ValueError("role names must be unique within team")


@dataclass
class TeamResult:
    """
    Team execution result.

    Contains the outcome of a team task execution,
    including results from each agent role.

    Attributes:
        team_name: Name of the team
        success: Whether all agents succeeded
        agent_results: Results from each agent (keyed by role name)
        total_iterations: Total iterations across all agents
        total_tokens: Total tokens across all agents
        duration_seconds: Total execution duration
        error: Error message if failed
    """

    team_name: str
    success: bool
    agent_results: dict[str, GoalResult]
    total_iterations: int
    total_tokens: int
    duration_seconds: float
    error: str | None = None

    def get_agent_result(self, role_name: str) -> GoalResult | None:
        """Get result for a specific agent role."""
        return self.agent_results.get(role_name)


# =============================================================================
# Orchestrator Configuration and Status
# =============================================================================


@dataclass
class OrchestratorConfig:
    """
    Orchestrator configuration.

    Controls global orchestrator behavior including concurrency
    limits and monitoring settings.

    Attributes:
        max_concurrent_goals: Maximum concurrent goal executions
        max_parallel_steps: Maximum parallel workflow steps
        max_teams: Maximum concurrent team executions
        metrics_retention: Number of metrics to retain in memory
    """

    max_concurrent_goals: int = 5
    max_parallel_steps: int = 5
    max_teams: int = 10
    metrics_retention: int = 1000

    def __post_init__(self):
        """Validate configuration."""
        if self.max_concurrent_goals < 1:
            raise ValueError("max_concurrent_goals must be at least 1")

        if self.max_parallel_steps < 1:
            raise ValueError("max_parallel_steps must be at least 1")

        if self.max_teams < 1:
            raise ValueError("max_teams must be at least 1")


@dataclass
class OrchestratorStatus:
    """
    Orchestrator runtime status.

    Provides a snapshot of the orchestrator's current state.

    Attributes:
        running: Whether the orchestrator is running
        active_workflows: Number of active workflow executions
        registered_triggers: Number of registered triggers
        registered_connectors: Number of registered connectors
    """

    running: bool
    active_workflows: int
    registered_triggers: int
    registered_connectors: int


@dataclass
class ExecutionMetric:
    """
    Execution metric for monitoring.

    Records details about a single execution (workflow, team, or goal).

    Attributes:
        name: Execution name (workflow/team/goal)
        type: Execution type ("workflow" | "team" | "goal")
        status: Execution status
        duration_seconds: Execution duration
        iterations: Number of iterations
        tokens_used: Total tokens used
        timestamp: When the execution occurred
    """

    name: str
    type: str  # "workflow" | "team" | "goal"
    status: str
    duration_seconds: float
    iterations: int
    tokens_used: int
    timestamp: datetime = field(default_factory=datetime.now)
