"""
Loop Orchestrator - Central orchestration API.

This module provides the LoopOrchestrator class for:
- Unified API for all Phase 1-4 components
- Workflow creation and execution
- Team management and coordination
- Connector integration
- Lifecycle management
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from harness.orchestrator.monitor import MonitorService
from harness.orchestrator.team_orchestrator import TeamOrchestrator
from harness.orchestrator.types import (
    OrchestratorConfig,
    OrchestratorStatus,
    TeamConfig,
    TeamResult,
    WorkflowConfig,
    WorkflowResult,
)
from harness.orchestrator.workflow_engine import WorkflowEngine

if TYPE_CHECKING:
    from harness import AgentHarness
    from harness.connectors import Connector, ConnectorManager
    from harness.connectors.types import OutputChannel
    from harness.loop.worktree_orchestrator import WorktreeOrchestrator

logger = logging.getLogger(__name__)


class LoopOrchestrator:
    """
    Loop Orchestrator - Unified orchestration API.

    Integrates Phase 1-4 components and provides a unified entry point:
    - Phase 1: Goal Verifier (via AgentHarness)
    - Phase 2: TriggerManager (Automations)
    - Phase 3: WorktreeOrchestrator (Parallel execution)
    - Phase 4: ConnectorManager (External systems)
    - Phase 5: WorkflowEngine + TeamOrchestrator

    Example:
        ```python
        from harness import AgentHarness
        from harness.orchestrator import LoopOrchestrator

        agent = AgentHarness(model="claude-sonnet-4-6")
        orchestrator = LoopOrchestrator(agent)

        # Run workflow
        result = await orchestrator.run_workflow("my-workflow.yaml")

        # Run team
        orchestrator.create_team(team_config)
        result = await orchestrator.run_team("dev-team", "Implement auth")
        ```
    """

    def __init__(
        self,
        agent: AgentHarness,
        config: OrchestratorConfig | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            agent: AgentHarness instance
            config: Orchestrator configuration
        """
        self.agent = agent
        self.config = config or OrchestratorConfig()

        # Initialize Phase 2 TriggerManager
        from harness.triggers import TriggerManager

        self.trigger_manager = TriggerManager(
            agent,
            max_concurrent_goals=self.config.max_concurrent_goals,
        )

        # Phase 3 WorktreeOrchestrator (lazy init)
        self.worktree_orchestrator: WorktreeOrchestrator | None = None

        # Phase 4 ConnectorManager (lazy init)
        self.connector_manager: ConnectorManager | None = None

        # Phase 5 Engines
        self.workflow_engine = WorkflowEngine(self)
        self.team_orchestrator = TeamOrchestrator(self)

        # Monitoring
        self.monitor = MonitorService(self, self.config)

        # State
        self._running = False
        self._workflows: dict[str, WorkflowConfig] = {}
        self._teams: dict[str, TeamConfig] = {}

    # =========================================================================
    # Workflow API
    # =========================================================================

    def create_workflow(self, config: WorkflowConfig) -> str:
        """
        Create a workflow.

        Args:
            config: Workflow configuration

        Returns:
            Workflow name
        """
        self._workflows[config.name] = config

        # Register trigger if configured
        if config.trigger_on:
            self._register_workflow_trigger(config)

        logger.info(f"Created workflow: {config.name}")
        return config.name

    def create_workflow_from_yaml(self, yaml_path: str) -> str:
        """
        Create a workflow from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Workflow name
        """
        config = self._parse_workflow_yaml(yaml_path)
        return self.create_workflow(config)

    async def run_workflow(
        self,
        name: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            name: Workflow name or YAML path
            context: Execution context

        Returns:
            Workflow execution result
        """
        # Check if it's a file path
        if (name.endswith(".yaml") or name.endswith(".yml")) and name not in self._workflows:
            self.create_workflow_from_yaml(name)

        config = self._workflows.get(name)
        if not config:
            raise ValueError(f"Workflow not found: {name}")

        result = await self.workflow_engine.run(config, context)

        # Record metric
        self.monitor.record_workflow(
            name=config.name,
            status="success" if result.success else "failed",
            duration_seconds=result.duration_seconds,
            iterations=sum(
                sr.goal_result.total_iterations if sr.goal_result else 0
                for sr in result.steps.values()
            ),
        )

        return result

    # =========================================================================
    # Team API
    # =========================================================================

    def create_team(self, config: TeamConfig) -> str:
        """
        Create an agent team.

        Args:
            config: Team configuration

        Returns:
            Team name
        """
        self._teams[config.name] = config
        return self.team_orchestrator.create_team(config)

    async def run_team(
        self,
        name: str,
        task: str,
        mode: str | None = None,
    ) -> TeamResult:
        """
        Execute a team task.

        Args:
            name: Team name
            task: Task description
            mode: Override coordination mode

        Returns:
            Team execution result
        """
        from harness.orchestrator.types import CoordinationMode

        coordination_mode = CoordinationMode(mode) if mode else None

        result = await self.team_orchestrator.run(name, task, coordination_mode)

        # Record metric
        self.monitor.record_team(
            name=name,
            status="success" if result.success else "failed",
            duration_seconds=result.duration_seconds,
            iterations=result.total_iterations,
            tokens_used=result.total_tokens,
        )

        return result

    # =========================================================================
    # Connector API
    # =========================================================================

    def register_connector(self, connector: Connector) -> str:
        """
        Register a connector.

        Args:
            connector: Connector instance

        Returns:
            Connector ID
        """
        if not self.connector_manager:
            from harness.connectors import ConnectorManager

            self.connector_manager = ConnectorManager(self.trigger_manager)

        return self.connector_manager.register_connector(connector)

    def register_output_channel(self, channel: OutputChannel) -> str:
        """
        Register an output channel.

        Args:
            channel: Output channel configuration

        Returns:
            Channel name
        """
        if not self.connector_manager:
            from harness.connectors import ConnectorManager

            self.connector_manager = ConnectorManager(self.trigger_manager)

        return self.connector_manager.register_output_channel(channel)

    # =========================================================================
    # Worktree API (Phase 3)
    # =========================================================================

    def enable_worktrees(self, repo_path: str = ".") -> None:
        """
        Enable worktree isolation.

        Args:
            repo_path: Git repository path
        """
        from harness.loop.worktree_orchestrator import WorktreeOrchestrator

        self.worktree_orchestrator = WorktreeOrchestrator(repo_path)
        logger.info(f"Worktree isolation enabled for: {repo_path}")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start orchestrator and all components."""
        self._running = True

        # Start TriggerManager
        await self.trigger_manager.start()

        # Start ConnectorManager
        if self.connector_manager:
            await self.connector_manager.start()

        # Start monitor
        await self.monitor.start()

        logger.info("LoopOrchestrator started")

    async def stop(self) -> None:
        """Stop orchestrator and all components."""
        self._running = False

        # Stop ConnectorManager
        if self.connector_manager:
            await self.connector_manager.stop()

        # Stop TriggerManager
        await self.trigger_manager.stop()

        # Stop monitor
        await self.monitor.stop()

        logger.info("LoopOrchestrator stopped")

    # =========================================================================
    # Status and Monitoring
    # =========================================================================

    def get_status(self) -> OrchestratorStatus:
        """
        Get orchestrator status.

        Returns:
            Status snapshot
        """
        return OrchestratorStatus(
            running=self._running,
            active_workflows=len(self.workflow_engine._active_workflows),
            registered_triggers=self.trigger_manager.trigger_count,
            registered_connectors=len(self.connector_manager._connectors)
            if self.connector_manager
            else 0,
        )

    def get_metrics(self, limit: int = 100) -> list:
        """
        Get execution metrics.

        Args:
            limit: Maximum number of metrics

        Returns:
            List of metrics
        """
        return self.monitor.get_metrics(limit)

    def get_summary(self) -> dict[str, Any]:
        """
        Get execution summary.

        Returns:
            Summary statistics
        """
        return self.monitor.get_summary()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _register_workflow_trigger(self, config: WorkflowConfig) -> None:
        """
        Register trigger for workflow.

        Args:
            config: Workflow configuration
        """
        trigger_on = config.trigger_on

        if trigger_on.startswith("cron:"):
            from harness.triggers import CronTrigger, TriggerAction

            schedule = trigger_on[5:]
            trigger = CronTrigger(
                schedule=schedule,
                action=TriggerAction(
                    goal=f"Execute workflow: {config.name}",
                    output_channels=config.output_channels,
                ),
            )
            self.trigger_manager.register(trigger)
            logger.info(f"Registered cron trigger for workflow '{config.name}': {schedule}")

        elif trigger_on.startswith("event:"):
            # Event trigger requires ConnectorManager
            logger.info(f"Event trigger configured for workflow '{config.name}': {trigger_on[6:]}")

    def _parse_workflow_yaml(self, yaml_path: str) -> WorkflowConfig:
        """
        Parse workflow from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Workflow configuration
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            from harness.orchestrator.types import ExecutionMode, WorkflowStep

            step = WorkflowStep(
                name=step_data["name"],
                goal=step_data["goal"],
                mode=ExecutionMode(step_data.get("mode", "sequential")),
                depends_on=step_data.get("depends_on", []),
                workspace_dir=step_data.get("workspace_dir", "."),
                max_iterations=step_data.get("max_iterations", 50),
                timeout_seconds=step_data.get("timeout_seconds", 3600),
                skills=step_data.get("skills", []),
                condition=step_data.get("condition"),
                exports=step_data.get("exports", {}),
            )
            steps.append(step)

        return WorkflowConfig(
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            default_mode=ExecutionMode(data.get("default_mode", "sequential")),
            max_parallel_steps=data.get("max_parallel_steps", 5),
            workspace_dir=data.get("workspace_dir", "."),
            trigger_on=data.get("trigger_on"),
            output_channels=data.get("output_channels", []),
        )

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    @property
    def workflow_count(self) -> int:
        """Get number of registered workflows."""
        return len(self._workflows)

    @property
    def team_count(self) -> int:
        """Get number of registered teams."""
        return len(self._teams)
