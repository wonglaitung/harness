"""
Worktree Orchestrator - Top-level API for parallel goal execution.

This module provides WorktreeOrchestrator, which integrates WorktreeManager
and ParallelGoalExecutor to provide a simple API for running multiple
goals in parallel with git worktree isolation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from harness.loop.parallel_executor import ParallelGoalExecutor
from harness.loop.worktree_manager import WorktreeManager
from harness.loop.worktree_types import (
    MergeResult,
    WorktreeConfig,
    WorktreeError,
    WorktreeResult,
)

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness

logger = logging.getLogger(__name__)


class WorktreeOrchestrator:
    """
    Top-level orchestrator for parallel goal execution in worktrees.

    Integrates:
    - WorktreeManager: Git worktree lifecycle
    - ParallelGoalExecutor: Concurrent goal execution

    Key features:
    - Simple API for parallel goal execution
    - Automatic worktree creation and optional cleanup
    - Safe merge with conflict detection
    - Dirty state checking before merge

    Example:
        ```python
        from harness import AgentHarness
        from harness.loop import WorktreeOrchestrator, WorktreeConfig

        agent = AgentHarness(model="claude-sonnet-4-6")
        orchestrator = WorktreeOrchestrator(agent, ".")

        # Define parallel goals
        goals = [
            WorktreeConfig(
                name="feature-auth",
                goal="Implement user authentication",
                base_branch="main",
            ),
            WorktreeConfig(
                name="feature-api",
                goal="Implement API endpoints",
                base_branch="main",
            ),
        ]

        # Execute in parallel
        results = await orchestrator.run_parallel(goals)

        # Check results
        for name, result in results.items():
            if result.achieved:
                print(f"✓ {name}: {result.branch_name}")
            else:
                print(f"✗ {name}: failed")

        # Merge successful branches (optional)
        merge_result = await orchestrator.merge_successful(results)
        print(f"Merged: {merge_result.merged}")
        print(f"Conflicts: {merge_result.conflicts}")
        ```
    """

    def __init__(
        self,
        agent: AgentHarness,
        repo_root: str = ".",
    ):
        """
        Initialize WorktreeOrchestrator.

        Args:
            agent: AgentHarness instance for goal execution
            repo_root: Path to git repository root (default: current directory)
        """
        self.agent = agent
        self.repo_root = repo_root

        # Initialize components
        self.worktree_manager = WorktreeManager(repo_root)
        self.executor = ParallelGoalExecutor(agent, self.worktree_manager)

        # Lock for serializing worktree creation (prevents index.lock conflicts)
        self._create_lock = asyncio.Lock()

    async def run_parallel(
        self,
        configs: list[WorktreeConfig],
    ) -> dict[str, WorktreeResult]:
        """
        Execute multiple goals in parallel with worktree isolation.

        Each goal runs in its own git worktree, providing complete isolation.
        Worktrees are created sequentially (to avoid index.lock conflicts)
        but goals execute in parallel.

        Args:
            configs: List of WorktreeConfig defining goals and git settings

        Returns:
            Dict mapping goal names to WorktreeResult

        Example:
            ```python
            results = await orchestrator.run_parallel([
                WorktreeConfig(name="feature-a", goal="Task A"),
                WorktreeConfig(name="feature-b", goal="Task B"),
            ])

            for name, result in results.items():
                print(f"{name}: {'✓' if result.achieved else '✗'}")
            ```
        """
        results: dict[str, WorktreeResult] = {}

        # Phase 1: Create worktrees sequentially (avoid index.lock conflicts)
        logger.info(f"Creating {len(configs)} worktrees...")

        for config in configs:
            async with self._create_lock:
                try:
                    await self.executor.spawn_goal(config)
                except WorktreeError as e:
                    # Record failed spawn
                    results[config.name] = WorktreeResult(
                        name=config.name,
                        goal_result=None,
                        worktree_path="",
                        branch_name=config.effective_branch_name,
                        created_at=datetime.now(),
                        completed_at=datetime.now(),
                    )
                    logger.error(f"Failed to spawn goal '{config.name}': {e}")

        # Phase 2: Execute all goals in parallel
        logger.info("Starting parallel goal execution...")
        goal_results = await self.executor.run_all()

        # Phase 3: Build WorktreeResult objects
        for config in configs:
            execution = self.executor.get_execution(config.name)
            goal_result = goal_results.get(config.name)

            if execution:
                # Get commit count for this worktree
                commits_made = await self.worktree_manager.get_commit_count(
                    config.name, config.base_branch
                )

                results[config.name] = WorktreeResult(
                    name=config.name,
                    goal_result=goal_result,
                    worktree_path=execution.worktree_path,
                    branch_name=execution.branch_name,
                    commits_made=commits_made,
                    created_at=execution.created_at,
                    completed_at=execution.completed_at,
                )

        # Phase 4: Optional auto-cleanup
        for config in configs:
            result = results.get(config.name)
            if config.auto_cleanup and result and result.achieved:
                # Only cleanup achieved goals
                try:
                    await self.worktree_manager.cleanup_worktree(config.name, force=False)
                    result.cleanup_done = True
                    logger.info(f"Auto-cleaned worktree: {config.name}")
                except WorktreeError as e:
                    logger.warning(f"Failed to cleanup worktree {config.name}: {e}")

        return results

    async def merge_successful(
        self,
        results: dict[str, WorktreeResult],
        target_branch: str = "main",
    ) -> MergeResult:
        """
        Merge successful goal branches into target branch.

        This operation:
        1. Checks main repo is clean (no uncommitted changes)
        2. Merges each successful branch
        3. Aborts merges with conflicts, keeping repo clean
        4. Returns detailed merge status

        Args:
            results: Results from run_parallel()
            target_branch: Target branch to merge into (default: main)

        Returns:
            MergeResult with lists of merged, conflicted, and skipped branches

        Raises:
            WorktreeError: If main repo has uncommitted changes
        """
        # Check main repo is clean
        if await self.worktree_manager.is_dirty():
            raise WorktreeError(
                "Main repository has uncommitted changes. Please commit or stash before merging."
            )

        merged = []
        conflicts = []
        skipped = []

        for name, result in results.items():
            # Skip failed goals
            if not result.achieved:
                skipped.append(result.branch_name)
                logger.info(f"Skipped merge for failed goal: {name}")
                continue

            # Attempt merge
            logger.info(f"Merging branch: {result.branch_name}")

            proc = await asyncio.create_subprocess_exec(
                "git",
                "merge",
                result.branch_name,
                "--no-edit",
                cwd=self.repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            returncode = await proc.wait()

            if returncode == 0:
                merged.append(result.branch_name)
                logger.info(f"Successfully merged: {result.branch_name}")
            else:
                conflicts.append(result.branch_name)
                logger.warning(f"Merge conflict in: {result.branch_name}")

                # Abort the merge to keep repo clean
                abort_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "merge",
                    "--abort",
                    cwd=self.repo_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await abort_proc.wait()

        return MergeResult(
            merged=merged,
            conflicts=conflicts,
            skipped=skipped,
            merged_at=datetime.now(),
        )

    async def cleanup_all(self, force: bool = False) -> int:
        """
        Clean up all tracked worktrees.

        Args:
            force: If True, force cleanup even with uncommitted changes

        Returns:
            Number of worktrees cleaned up
        """
        count = await self.worktree_manager.cleanup_all(force=force)

        # Clear executor tracking
        self.executor.clear()

        return count

    def list_worktrees(self) -> list[str]:
        """
        List all tracked worktrees.

        Returns:
            List of worktree names
        """
        return self.worktree_manager.list_worktrees()

    async def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """
        Delete a branch after merging.

        Args:
            branch_name: Name of the branch to delete
            force: If True, force delete unmerged branch

        Returns:
            True if branch was deleted
        """
        cmd = ["git", "branch", "-d" if not force else "-D", branch_name]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        returncode = await proc.wait()

        if returncode == 0:
            logger.info(f"Deleted branch: {branch_name}")
            return True
        else:
            logger.warning(f"Failed to delete branch: {branch_name}")
            return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorktreeOrchestrator(repo_root='{self.repo_root}', "
            f"worktrees={len(self.list_worktrees())})"
        )
