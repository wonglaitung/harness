"""
Worktree types for Phase 3 parallel execution.

This module defines types for git worktree-based parallel execution:
- WorktreeConfig: Configuration for a worktree-based goal
- WorktreeResult: Result of worktree execution
- MergeResult: Result of merge operations
- WorktreeError: Exception for worktree operations
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.loop.types import GoalResult


# Global constant: Worktree storage directory
WORKTREES_DIR = ".worktrees"


class WorktreeError(Exception):
    """
    Exception raised for worktree operation failures.

    Common scenarios:
    - Failed to create worktree (git error)
    - Failed to cleanup worktree
    - Merge conflict in main repository
    - Invalid repository state
    """

    pass


@dataclass
class WorktreeConfig:
    """
    Configuration for a worktree-based goal execution.

    Each WorktreeConfig represents an isolated execution environment
    with its own git worktree and optional branch.

    Attributes:
        name: Unique identifier for this worktree (also branch name prefix)
        goal: Goal description for the agent to achieve
        base_branch: Base branch to create worktree from
        create_branch: Whether to create a new branch (True) or use base_branch
        branch_name: Custom branch name (defaults to name if create_branch=True)
        max_iterations: Maximum iterations for goal execution
        timeout_seconds: Timeout for goal execution
        custom_verifier: Optional custom verification function
        auto_cleanup: Whether to auto-cleanup worktree on completion
        auto_merge: Whether to auto-merge successful branches

    Example:
        ```python
        config = WorktreeConfig(
            name="feature-auth",
            goal="Implement user authentication",
            base_branch="main",
            create_branch=True,
        )
        ```
    """

    # Goal definition
    name: str
    goal: str

    # Git configuration
    base_branch: str = "main"
    create_branch: bool = True
    branch_name: str | None = None  # Defaults to name if create_branch=True

    # Goal configuration
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None

    # Cleanup configuration
    auto_cleanup: bool = True
    auto_merge: bool = False  # User should call merge_successful() manually

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("Worktree name cannot be empty")

        if not self.goal:
            raise ValueError("Goal cannot be empty")

        # Validate name is safe for branch names
        import re

        if not re.match(r"^[\w\-/.]+$", self.name):
            raise ValueError(
                f"Invalid worktree name '{self.name}': "
                "must contain only alphanumeric, dash, underscore, slash, or dot"
            )

    @property
    def effective_branch_name(self) -> str:
        """Get the effective branch name for this worktree."""
        if self.branch_name:
            return self.branch_name
        return self.name if self.create_branch else self.base_branch


@dataclass
class WorktreeResult:
    """
    Result of a worktree execution.

    Contains both the goal execution result and git-specific information.

    Attributes:
        name: Worktree name
        goal_result: Result from goal execution
        worktree_path: Path to the worktree directory
        branch_name: Branch name used
        commits_made: Number of commits created during execution
        cleanup_done: Whether the worktree was cleaned up
        created_at: When the worktree was created
        completed_at: When execution completed
    """

    name: str
    goal_result: GoalResult | None = None

    # Git information
    worktree_path: str = ""
    branch_name: str = ""
    commits_made: int = 0

    # Status
    cleanup_done: bool = False
    created_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def achieved(self) -> bool:
        """Check if the goal was achieved."""
        return self.goal_result is not None and self.goal_result.achieved

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration."""
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "achieved": self.achieved,
            "worktree_path": self.worktree_path,
            "branch_name": self.branch_name,
            "commits_made": self.commits_made,
            "cleanup_done": self.cleanup_done,
            "duration_seconds": self.duration_seconds,
            "goal_result": self.goal_result.to_dict() if self.goal_result else None,
        }


@dataclass
class MergeResult:
    """
    Result of merge operations.

    Returned by WorktreeOrchestrator.merge_successful() to indicate
    which branches were successfully merged, which had conflicts,
    and which were skipped due to failed goals.

    Attributes:
        merged: List of successfully merged branch names
        conflicts: List of branches with merge conflicts
        skipped: List of branches skipped (goal not achieved)
        error: Error message if merge process failed (e.g., dirty state)
        merged_at: When the merge operation was performed
    """

    merged: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None
    merged_at: datetime | None = None

    @property
    def success(self) -> bool:
        """Check if all merges were successful."""
        return len(self.conflicts) == 0 and self.error is None

    @property
    def total_attempted(self) -> int:
        """Total branches attempted to merge."""
        return len(self.merged) + len(self.conflicts)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "merged": self.merged,
            "conflicts": self.conflicts,
            "skipped": self.skipped,
            "success": self.success,
            "error": self.error,
        }
