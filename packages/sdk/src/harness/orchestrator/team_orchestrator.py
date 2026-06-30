"""
Team Orchestrator - Multi-agent team coordination.

This module provides the TeamOrchestrator class for:
- Creating and managing agent teams
- Coordinating multi-agent execution (broadcast, sequential, hierarchical)
- Worktree isolation for team tasks
- Agent role management
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.orchestrator.types import (
    AgentRole,
    CoordinationMode,
    TeamConfig,
    TeamResult,
)
from harness.sdk.config import HarnessConfig

if TYPE_CHECKING:
    from harness.orchestrator.core import LoopOrchestrator
    from harness import AgentHarness
    from harness.loop.types import GoalConfig, GoalResult

logger = logging.getLogger(__name__)


class TeamOrchestrator:
    """
    Multi-agent team orchestrator.

    Manages teams of agents with different roles and coordination modes:
    - Broadcast: All agents execute same task simultaneously
    - Sequential: Agents execute in order, passing outputs
    - Hierarchical: Leader assigns tasks to workers

    Key Features:
    - Worktree isolation: Each team task runs in isolated environment
    - Role-based agents: Each role has its own agent instance
    - Coordination modes: Different patterns for different use cases

    Worktree Isolation:
    - Broadcast mode: Each agent gets its own subdirectory
    - Sequential/Hierarchical: Agents share directory for output passing
    """

    def __init__(self, orchestrator: LoopOrchestrator):
        """
        Initialize team orchestrator.

        Args:
            orchestrator: Parent LoopOrchestrator instance
        """
        self.orchestrator = orchestrator
        self._teams: dict[str, TeamConfig] = {}
        self._agents: dict[str, AgentHarness] = {}

    def create_team(self, config: TeamConfig) -> str:
        """
        Create an agent team.

        Creates a dedicated agent instance for each role.

        Args:
            config: Team configuration

        Returns:
            Team name
        """
        self._teams[config.name] = config

        # Create agent for each role
        for role in config.roles:
            agent = self._create_agent_for_role(role)
            self._agents[role.name] = agent

        logger.info(
            f"Created team '{config.name}' with {len(config.roles)} roles, "
            f"mode: {config.coordination_mode.value}"
        )
        return config.name

    def _create_agent_for_role(self, role: AgentRole) -> AgentHarness:
        """
        Create an agent instance for a role.

        For testing, if the orchestrator's agent is a MockHarness,
        we return a new MockHarness directly instead of creating a real AgentHarness.

        Args:
            role: Role configuration

        Returns:
            Configured agent instance (MockHarness for testing)
        """
        from harness.testing.mock_harness import MockHarness

        # If parent agent is a MockHarness, return a new MockHarness for the role
        if isinstance(self.orchestrator.agent, MockHarness):
            from harness.testing.mock_harness import MockHarnessConfig

            return MockHarness(
                config=MockHarnessConfig(
                    responses=self.orchestrator.agent.config.responses,
                    auto_tool_results=self.orchestrator.agent.config.auto_tool_results,
                )
            )

        # Otherwise, create a real AgentHarness
        from harness import AgentHarness

        model = getattr(self.orchestrator.agent.config, "model", "mock-model")

        config = HarnessConfig(
            model=model,
            system_prompt=role.system_prompt or f"You are a {role.name}. {role.description}",
            max_iterations=role.max_iterations,
        )

        agent = AgentHarness(
            llm_client=self.orchestrator.agent._llm_client,
            config=config,
        )

        # Activate skills
        for skill_name in role.skills:
            agent.activate_skill(skill_name)

        return agent

    async def run(
        self,
        team_name: str,
        task: str,
        coordination_mode: CoordinationMode | None = None,
    ) -> TeamResult:
        """
        Run a team task.

        Automatically creates isolated worktree to prevent file conflicts.

        Args:
            team_name: Team name
            task: Task description
            coordination_mode: Override team's default coordination mode

        Returns:
            Team execution result
        """
        config = self._teams.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        mode = coordination_mode or config.coordination_mode
        start_time = datetime.now()

        # Create isolated worktree
        worktree_path = None
        if self.orchestrator.worktree_orchestrator:
            worktree_path = await self._create_isolated_worktree(team_name, task)
            logger.info(f"Created isolated worktree for team '{team_name}': {worktree_path}")

        try:
            if mode == CoordinationMode.BROADCAST:
                results = await self._run_broadcast(config, task, worktree_path)
            elif mode == CoordinationMode.SEQUENTIAL:
                results = await self._run_sequential(config, task, worktree_path)
            elif mode == CoordinationMode.HIERARCHICAL:
                results = await self._run_hierarchical(config, task, worktree_path)
            else:
                raise ValueError(f"Unknown coordination mode: {mode}")

            # Calculate statistics
            total_iterations = sum(r.total_iterations for r in results.values())
            total_tokens = sum(
                r.total_tokens.get("input", 0) + r.total_tokens.get("output", 0)
                for r in results.values()
            )

            return TeamResult(
                team_name=team_name,
                success=all(r.achieved for r in results.values()),
                agent_results=results,
                total_iterations=total_iterations,
                total_tokens=total_tokens,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            logger.error(f"Team '{team_name}' execution failed: {e}")
            return TeamResult(
                team_name=team_name,
                success=False,
                agent_results={},
                total_iterations=0,
                total_tokens=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=str(e),
            )

        finally:
            # Cleanup worktree
            if worktree_path and self.orchestrator.worktree_orchestrator:
                await self._cleanup_worktree(worktree_path)

    async def _create_isolated_worktree(self, team_name: str, task: str) -> str:
        """
        Create isolated worktree for team task.

        Ensures:
        - Different agents don't interfere with each other
        - Failed executions don't pollute main branch
        - Multiple team tasks can run in parallel

        Args:
            team_name: Team name
            task: Task description

        Returns:
            Worktree path
        """
        task_hash = hashlib.md5(
            f"{team_name}_{task}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        branch_name = f"team/{team_name}/{task_hash}"

        worktree = await self.orchestrator.worktree_orchestrator.create_worktree(
            name=branch_name,
            branch=branch_name,
        )

        return worktree.path

    async def _cleanup_worktree(self, worktree_path: str) -> None:
        """
        Cleanup worktree after task completion.

        Args:
            worktree_path: Path to worktree
        """
        try:
            await self.orchestrator.worktree_orchestrator.remove_worktree(worktree_path)
            logger.info(f"Cleaned up worktree: {worktree_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup worktree {worktree_path}: {e}")

    async def _run_broadcast(
        self,
        config: TeamConfig,
        task: str,
        worktree_path: str | None = None,
    ) -> dict[str, GoalResult]:
        """
        Broadcast mode: All agents execute same task simultaneously.

        Use cases: Multi-perspective analysis, voting decisions.

        Concurrent Safety: Each agent gets its own subdirectory to
        prevent file write conflicts.

        Args:
            config: Team configuration
            task: Task description
            worktree_path: Isolated worktree path

        Returns:
            Results keyed by role name
        """
        tasks = []
        for role in config.roles:
            agent = self._agents[role.name]
            # Create role-specific subdirectory for concurrent safety
            role_worktree = self._get_role_worktree(
                worktree_path, role.name, CoordinationMode.BROADCAST
            )
            tasks.append(self._run_agent(agent, task, role_worktree))

        results = await asyncio.gather(*tasks)

        return {role.name: result for role, result in zip(config.roles, results)}

    async def _run_sequential(
        self,
        config: TeamConfig,
        task: str,
        worktree_path: str | None = None,
    ) -> dict[str, GoalResult]:
        """
        Sequential mode: Agents execute in order, passing outputs.

        Use cases: Pipeline processing, multi-stage review.

        Worktree provides natural isolation and passing mechanism.
        Each agent sees the previous agent's modifications.

        Args:
            config: Team configuration
            task: Task description
            worktree_path: Isolated worktree path

        Returns:
            Results keyed by role name
        """
        results = {}
        current_task = task

        for role in config.roles:
            agent = self._agents[role.name]
            # Sequential mode shares same directory
            result = await self._run_agent(agent, current_task, worktree_path)
            results[role.name] = result

            # Pass result to next agent
            if result.achieved:
                current_task = (
                    f"{task}\n\n"
                    f"Previous agent ({role.name}) output:\n{result.final_response}"
                )

        return results

    async def _run_hierarchical(
        self,
        config: TeamConfig,
        task: str,
        worktree_path: str | None = None,
    ) -> dict[str, GoalResult]:
        """
        Hierarchical mode: Leader assigns tasks to workers.

        Use cases: Complex task decomposition, expert scheduling.

        Worktree isolation ensures:
        - Leader can review worker modifications
        - Final results can be merged back

        Args:
            config: Team configuration
            task: Task description
            worktree_path: Isolated worktree path

        Returns:
            Results keyed by role name
        """
        if not config.roles:
            return {}

        # First role is the leader
        leader_role = config.roles[0]
        leader_agent = self._agents[leader_role.name]

        # Leader analyzes and assigns tasks
        allocation_prompt = f"""
You are the team leader. Analyze the following task and assign subtasks to team members.

Team members:
{self._format_roles(config.roles[1:])}

Task: {task}

Provide your allocation in the following format:
- [agent_name]: [subtask]
"""

        allocation_result = await self._run_agent(
            leader_agent, allocation_prompt, worktree_path
        )
        results = {leader_role.name: allocation_result}

        # Workers execute assigned tasks
        for role in config.roles[1:]:
            agent = self._agents[role.name]
            subtask = f"Complete your assigned part of: {task}"
            result = await self._run_agent(agent, subtask, worktree_path)
            results[role.name] = result

        return results

    async def _run_agent(
        self,
        agent: AgentHarness,
        task: str,
        worktree_path: str | None = None,
    ) -> GoalResult:
        """
        Run a single agent.

        Args:
            agent: Agent instance (MockHarness for testing)
            task: Task description
            worktree_path: Isolated worktree path

        Returns:
            Goal execution result
        """
        from harness.testing.mock_harness import MockHarness

        # Handle MockHarness for testing
        if isinstance(agent, MockHarness):
            return await agent.run_goal(task)

        # Real AgentHarness
        from harness.loop.types import GoalConfig

        config = GoalConfig(
            description=task,
            workspace_dir=worktree_path or agent.config.workspace_dir,
        )
        return await agent.run_goal(config)

    def _get_role_worktree(
        self,
        worktree_path: str | None,
        role_name: str,
        mode: CoordinationMode,
    ) -> str | None:
        """
        Get role-specific worktree path.

        Broadcast mode: Each role gets isolated subdirectory.
        Sequential/Hierarchical: Roles share same directory.

        Args:
            worktree_path: Team worktree path
            role_name: Role name
            mode: Coordination mode

        Returns:
            Role-specific worktree path
        """
        if not worktree_path:
            return None

        if mode == CoordinationMode.BROADCAST:
            # Create role-specific subdirectory
            role_dir = os.path.join(worktree_path, f"agent_{role_name}")
            os.makedirs(role_dir, exist_ok=True)
            return role_dir
        else:
            # Share directory in other modes
            return worktree_path

    def _format_roles(self, roles: list[AgentRole]) -> str:
        """Format role list for prompt."""
        return "\n".join(f"- {r.name}: {r.description}" for r in roles)

    def get_team(self, team_name: str) -> TeamConfig | None:
        """Get team configuration."""
        return self._teams.get(team_name)

    def get_agent(self, role_name: str) -> AgentHarness | None:
        """Get agent for a role."""
        return self._agents.get(role_name)

    def list_teams(self) -> list[str]:
        """List all team names."""
        return list(self._teams.keys())
