"""
Worktree manager for git worktree lifecycle management.

This module provides WorktreeManager for creating, tracking, and cleaning up
git worktrees for parallel goal execution.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from harness.loop.worktree_types import WORKTREES_DIR, WorktreeError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class WorktreeManager:
    """
    Git worktree lifecycle manager.

    Manages creation, tracking, and cleanup of git worktrees for
    parallel goal execution in isolated environments.

    Features:
    - Async git command execution
    - Orphan worktree recovery on startup
    - Thread-safe operation tracking

    Example:
        ```python
        manager = WorktreeManager("/path/to/repo")

        # Create worktree
        path, branch = await manager.create_worktree(
            name="feature-auth",
            base_branch="main",
            create_branch=True,
        )

        # List active worktrees
        for name in manager.list_worktrees():
            print(f"Active: {name}")

        # Cleanup
        await manager.cleanup_worktree("feature-auth")
        ```
    """

    def __init__(self, repo_root: str):
        """
        Initialize WorktreeManager.

        Args:
            repo_root: Path to the main git repository root

        Raises:
            WorktreeError: If repo_root is not a valid git repository
        """
        self.repo_root = os.path.abspath(repo_root)
        self._worktrees: dict[str, str] = {}  # name -> path

        # Verify this is a git repository
        if not os.path.isdir(os.path.join(self.repo_root, ".git")):
            # Check if it's a worktree itself (git dir is in .git file)
            git_file = os.path.join(self.repo_root, ".git")
            if not os.path.isfile(git_file):
                raise WorktreeError(f"Not a git repository: {self.repo_root}")

        # Recover orphaned worktrees from previous runs
        self._recover_orphaned_worktrees()

    def _recover_orphaned_worktrees(self) -> None:
        """
        Recover orphaned worktrees from previous runs.

        Scans git worktree list and rebuilds internal tracking for
        worktrees created by this system (identified by path prefix).

        This provides resilience against process crashes - the system
        can recover state and clean up properly on restart.
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Exact prefix matching to avoid recovering unrelated worktrees
            expected_prefix = f"{self.repo_root}/{WORKTREES_DIR}/"

            current_path = None
            for line in result.stdout.splitlines():
                if line.startswith("worktree "):
                    current_path = line.split(" ", 1)[1]
                elif line.startswith("branch ") and current_path:
                    # Only recover if path matches our expected prefix
                    if current_path.startswith(expected_prefix):
                        name = Path(current_path).name
                        self._worktrees[name] = current_path
                        logger.info(f"Recovered orphan worktree: {name}")
                    current_path = None

            if self._worktrees:
                logger.info(
                    f"Recovered {len(self._worktrees)} orphan worktree(s)"
                )

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to list worktrees for recovery: {e}")
        except Exception as e:
            logger.warning(f"Error during worktree recovery: {e}")

    async def create_worktree(
        self,
        name: str,
        base_branch: str,
        create_branch: bool = True,
    ) -> tuple[str, str]:
        """
        Create a git worktree for isolated execution.

        Args:
            name: Unique name for this worktree
            base_branch: Base branch to create from
            create_branch: If True, create a new branch named `name`;
                          if False, checkout base_branch in worktree

        Returns:
            Tuple of (worktree_path, branch_name)

        Raises:
            WorktreeError: If worktree creation fails
        """
        # Check if worktree already exists
        if name in self._worktrees:
            raise WorktreeError(f"Worktree already exists: {name}")

        # Determine branch name
        branch_name = name if create_branch else base_branch

        # Build worktree path
        worktree_path = f"{self.repo_root}/{WORKTREES_DIR}/{name}"

        # Build git worktree add command
        cmd = ["git", "worktree", "add"]

        if create_branch:
            cmd.extend(["-b", branch_name])

        cmd.extend([worktree_path, base_branch])

        logger.debug(f"Creating worktree: {' '.join(cmd)}")

        # Execute git command
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise WorktreeError(f"Failed to create worktree '{name}': {error_msg}")

        # Track the worktree
        self._worktrees[name] = worktree_path
        logger.info(f"Created worktree: {name} at {worktree_path}")

        return worktree_path, branch_name

    async def cleanup_worktree(self, name: str, force: bool = False) -> bool:
        """
        Remove a git worktree.

        Args:
            name: Name of the worktree to remove
            force: If True, force removal even with uncommitted changes

        Returns:
            True if cleanup succeeded, False if worktree not found

        Raises:
            WorktreeError: If cleanup fails
        """
        path = self._worktrees.get(name)
        if not path:
            logger.warning(f"Worktree not found for cleanup: {name}")
            return False

        # Build git worktree remove command
        cmd = ["git", "worktree", "remove", path]
        if force:
            cmd.append("--force")

        logger.debug(f"Removing worktree: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            if force:
                # Try more aggressive cleanup
                logger.warning(
                    f"Force cleanup for worktree {name}: {error_msg}"
                )
                # Use git worktree prune
                await self._prune_worktrees()

        # Remove from tracking
        if name in self._worktrees:
            del self._worktrees[name]

        logger.info(f"Cleaned up worktree: {name}")
        return True

    async def _prune_worktrees(self) -> None:
        """
        Prune stale worktree references.

        Called when force cleanup is needed to clean up git's internal
        worktree tracking.
        """
        proc = await asyncio.create_subprocess_exec(
            "git",
            "worktree",
            "prune",
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await proc.communicate()

    def list_worktrees(self) -> list[str]:
        """
        List all tracked worktrees.

        Returns:
            List of worktree names
        """
        return list(self._worktrees.keys())

    def get_worktree_path(self, name: str) -> str | None:
        """
        Get the path to a worktree.

        Args:
            name: Worktree name

        Returns:
            Path to the worktree, or None if not found
        """
        return self._worktrees.get(name)

    async def get_commit_count(
        self,
        name: str,
        base_branch: str = "main",
    ) -> int:
        """
        Get the number of commits in a worktree branch vs base branch.

        Args:
            name: Worktree name
            base_branch: Base branch to compare against

        Returns:
            Number of commits ahead of base branch
        """
        path = self._worktrees.get(name)
        if not path:
            return 0

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-list",
                "--count",
                f"{base_branch}..HEAD",
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                return int(stdout.decode().strip())

        except (ValueError, subprocess.CalledProcessError):
            pass

        return 0

    async def is_dirty(self) -> bool:
        """
        Check if the main repository has uncommitted changes.

        Returns:
            True if there are uncommitted changes
        """
        proc = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            cwd=self.repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await proc.communicate()

        return bool(stdout.decode().strip())

    async def cleanup_all(self, force: bool = False) -> int:
        """
        Clean up all tracked worktrees.

        Args:
            force: If True, force cleanup

        Returns:
            Number of worktrees cleaned up
        """
        count = 0
        for name in list(self._worktrees.keys()):
            try:
                if await self.cleanup_worktree(name, force=force):
                    count += 1
            except WorktreeError as e:
                logger.warning(f"Failed to cleanup worktree {name}: {e}")

        return count

    def __repr__(self) -> str:
        """String representation."""
        return f"WorktreeManager(repo_root='{self.repo_root}', worktrees={len(self._worktrees)})"
