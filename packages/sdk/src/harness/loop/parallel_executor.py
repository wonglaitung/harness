"""
Parallel Goal Executor for concurrent worktree execution.

This module provides ParallelGoalExecutor for running multiple goals
in parallel across isolated git worktrees.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from harness.loop.goal_loop import GoalLoop
from harness.loop.types import GoalConfig, GoalResult, GoalStatus
from harness.loop.worktree_manager import WorktreeManager
from harness.loop.worktree_types import WorktreeConfig

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness

logger = logging.getLogger(__name__)


class ParallelGoalExecutor:
    """
    Parallel Goal execution across worktrees.

    Manages spawning and executing multiple goals in parallel,
    each in its own isolated git worktree.

    Key features:
    - Concurrent goal execution with asyncio.gather
    - Worktree isolation for each goal
    - Exception isolation (one goal failure doesn't affect others)
    - Result aggregation

    Example:
        ```python
        from harness import AgentHarness
        from harness.loop import ParallelGoalExecutor, WorktreeConfig

        agent = AgentHarness()
        executor = ParallelGoalExecutor(agent, worktree_manager)

        # Spawn goals
        await executor.spawn_goal(WorktreeConfig(
            name="feature-a",
            goal="Implement feature A",
        ))

        await executor.spawn_goal(WorktreeConfig(
            name="feature-b",
            goal="Implement feature B",
        ))

        # Execute all in parallel
        results = await executor.run_all()
        ```
    """

    def __init__(
        self,
        agent: AgentHarness,
        worktree_manager: WorktreeManager,
    ):
        """
        Initialize ParallelGoalExecutor.

        Args:
            agent: AgentHarness instance to use for goal execution
            worktree_manager: WorktreeManager for worktree lifecycle
        """
        self.agent = agent
        self.worktree_manager = worktree_manager
        self._executions: dict[str, _GoalExecution] = {}

    async def spawn_goal(self, config: WorktreeConfig) -> str:
        """
        Spawn a goal execution in an isolated worktree.

        Creates the worktree and prepares the goal for execution.
        The goal won't start executing until run_all() is called.

        Args:
            config: Worktree configuration including goal and git settings

        Returns:
            The worktree name (same as config.name)

        Raises:
            WorktreeError: If worktree creation fails
        """
        if config.name in self._executions:
            raise ValueError(f"Goal already spawned: {config.name}")

        # Create worktree
        worktree_path, branch_name = await self.worktree_manager.create_worktree(
            name=config.name,
            base_branch=config.base_branch,
            create_branch=config.create_branch,
        )

        # Build GoalConfig
        goal_config = GoalConfig(
            description=config.goal,
            workspace_dir=worktree_path,  # Isolated workspace
            max_iterations=config.max_iterations,
            timeout_seconds=config.timeout_seconds,
            custom_verifier=config.custom_verifier,
        )

        # Create GoalLoop
        goal_loop = GoalLoop(
            agent=self.agent,
            config=goal_config,
        )

        # Track execution
        self._executions[config.name] = _GoalExecution(
            config=config,
            goal_loop=goal_loop,
            worktree_path=worktree_path,
            branch_name=branch_name,
            created_at=datetime.now(),
        )

        logger.info(f"Spawned goal '{config.name}' in worktree {worktree_path}")

        return config.name

    async def run_all(self) -> dict[str, GoalResult]:
        """
        Execute all spawned goals in parallel.

        Uses asyncio.gather with return_exceptions=True to ensure
        one goal's failure doesn't affect others.

        Returns:
            Dict mapping goal names to their GoalResult.
            Failed goals will have GoalResult with ERROR status.
        """
        if not self._executions:
            return {}

        logger.info(f"Starting parallel execution of {len(self._executions)} goals")

        # Create tasks for all goals
        tasks = {
            name: asyncio.create_task(execution.goal_loop.run())
            for name, execution in self._executions.items()
        }

        # Execute all in parallel
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        # Process results
        goal_results: dict[str, GoalResult] = {}

        for (name, execution), result in zip(self._executions.items(), results, strict=True):
            execution.completed_at = datetime.now()

            if isinstance(result, GoalResult):
                goal_results[name] = result
            elif isinstance(result, Exception):
                # Convert exception to error result
                goal_results[name] = GoalResult(
                    goal=execution.config.goal,
                    status=GoalStatus.ERROR,
                    error=str(result),
                )
                logger.error(f"Goal '{name}' failed with exception: {result}")
            else:
                # Unexpected result type
                goal_results[name] = GoalResult(
                    goal=execution.config.goal,
                    status=GoalStatus.ERROR,
                    error=f"Unexpected result type: {type(result)}",
                )

        # Log summary
        achieved = sum(1 for r in goal_results.values() if r.achieved)
        logger.info(f"Parallel execution complete: {achieved}/{len(goal_results)} goals achieved")

        return goal_results

    def get_execution(self, name: str) -> _GoalExecution | None:
        """
        Get execution details for a spawned goal.

        Args:
            name: Goal name

        Returns:
            _GoalExecution if found, None otherwise
        """
        return self._executions.get(name)

    def list_executions(self) -> list[str]:
        """
        List all spawned goal names.

        Returns:
            List of goal names
        """
        return list(self._executions.keys())

    async def cancel(self, name: str) -> bool:
        """
        Cancel a running goal.

        Note: This only prevents starting if run_all hasn't been called.
        Goals already running in run_all cannot be cancelled mid-execution.

        Args:
            name: Goal name to cancel

        Returns:
            True if cancelled, False if not found
        """
        if name in self._executions:
            del self._executions[name]
            logger.info(f"Cancelled goal: {name}")
            return True
        return False

    def clear(self) -> None:
        """Clear all tracked executions (does not cleanup worktrees)."""
        self._executions.clear()


class _GoalExecution:
    """Internal class for tracking a single goal execution."""

    def __init__(
        self,
        config: WorktreeConfig,
        goal_loop: GoalLoop,
        worktree_path: str,
        branch_name: str,
        created_at: datetime,
    ):
        self.config = config
        self.goal_loop = goal_loop
        self.worktree_path = worktree_path
        self.branch_name = branch_name
        self.created_at = created_at
        self.completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration."""
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return 0.0
