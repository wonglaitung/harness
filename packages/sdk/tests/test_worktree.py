"""
Tests for Phase 3: Worktrees

This module tests:
- WorktreeManager: Git worktree lifecycle
- ParallelGoalExecutor: Parallel goal execution
- WorktreeOrchestrator: Top-level API
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from harness.loop.worktree_manager import WorktreeManager
from harness.loop.worktree_types import (
    WORKTREES_DIR,
    MergeResult,
    WorktreeConfig,
    WorktreeError,
    WorktreeResult,
)


def run_git(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    """Helper to run git commands."""
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize repo
        run_git(["init"], tmpdir)
        run_git(["config", "user.email", "test@example.com"], tmpdir)
        run_git(["config", "user.name", "Test User"], tmpdir)

        # Create initial commit on main branch
        readme_path = Path(tmpdir) / "README.md"
        readme_path.write_text("# Test Repository\n")
        run_git(["add", "README.md"], tmpdir)
        run_git(["commit", "-m", "Initial commit"], tmpdir)

        # Ensure we're on main branch
        try:
            run_git(["branch", "-M", "main"], tmpdir)
        except subprocess.CalledProcessError:
            pass

        yield tmpdir


class TestWorktreeConfig:
    """Tests for WorktreeConfig validation."""

    def test_valid_config(self):
        """Test creating a valid WorktreeConfig."""
        config = WorktreeConfig(
            name="feature-auth",
            goal="Implement authentication",
            base_branch="main",
        )
        assert config.name == "feature-auth"
        assert config.goal == "Implement authentication"
        assert config.base_branch == "main"
        assert config.create_branch is True
        assert config.auto_cleanup is True

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorktreeConfig(name="", goal="Test goal")

    def test_empty_goal_raises_error(self):
        """Test that empty goal raises ValueError."""
        with pytest.raises(ValueError, match="Goal cannot be empty"):
            WorktreeConfig(name="test", goal="")

    def test_invalid_name_characters_raises_error(self):
        """Test that invalid characters in name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid worktree name"):
            WorktreeConfig(name="feature@test", goal="Test goal")

    def test_effective_branch_name(self):
        """Test effective_branch_name property."""
        # When create_branch is True, returns name
        config = WorktreeConfig(name="feature-auth", goal="Test")
        assert config.effective_branch_name == "feature-auth"

        # When branch_name is specified, uses it
        config = WorktreeConfig(
            name="feature-auth",
            goal="Test",
            branch_name="custom-branch",
        )
        assert config.effective_branch_name == "custom-branch"

        # When create_branch is False, returns base_branch
        config = WorktreeConfig(
            name="test",
            goal="Test",
            create_branch=False,
            base_branch="develop",
        )
        assert config.effective_branch_name == "develop"


class TestWorktreeManager:
    """Tests for WorktreeManager."""

    def test_init_valid_repo(self, temp_git_repo):
        """Test initializing WorktreeManager with valid repo."""
        manager = WorktreeManager(temp_git_repo)
        assert manager.repo_root == temp_git_repo
        assert manager.list_worktrees() == []

    def test_init_invalid_repo_raises_error(self):
        """Test that invalid repo raises WorktreeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(WorktreeError, match="Not a git repository"):
                WorktreeManager(tmpdir)

    @pytest.mark.asyncio
    async def test_create_worktree(self, temp_git_repo):
        """Test creating a worktree."""
        manager = WorktreeManager(temp_git_repo)

        path, branch = await manager.create_worktree(
            name="feature-test",
            base_branch="main",
            create_branch=True,
        )

        assert path.endswith("feature-test")
        assert branch == "feature-test"
        assert Path(path).exists()
        assert "feature-test" in manager.list_worktrees()

        # Verify it's a valid git worktree
        result = run_git(["worktree", "list"], temp_git_repo)
        assert "feature-test" in result.stdout

    @pytest.mark.asyncio
    async def test_create_worktree_duplicate_raises_error(self, temp_git_repo):
        """Test that duplicate worktree name raises error."""
        manager = WorktreeManager(temp_git_repo)

        await manager.create_worktree("test", "main")

        with pytest.raises(WorktreeError, match="already exists"):
            await manager.create_worktree("test", "main")

    @pytest.mark.asyncio
    async def test_cleanup_worktree(self, temp_git_repo):
        """Test cleaning up a worktree."""
        manager = WorktreeManager(temp_git_repo)

        await manager.create_worktree("test", "main")
        assert "test" in manager.list_worktrees()

        result = await manager.cleanup_worktree("test")
        assert result is True
        assert "test" not in manager.list_worktrees()

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_worktree(self, temp_git_repo):
        """Test cleaning up a non-existent worktree."""
        manager = WorktreeManager(temp_git_repo)

        result = await manager.cleanup_worktree("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_orphan_recovery(self, temp_git_repo):
        """Test recovery of orphaned worktrees."""
        # Create a worktree
        manager1 = WorktreeManager(temp_git_repo)
        await manager1.create_worktree("orphan-test", "main")

        # Create new manager (simulates process restart)
        manager2 = WorktreeManager(temp_git_repo)

        # Verify orphan was recovered
        assert "orphan-test" in manager2.list_worktrees()

        # Cleanup
        await manager2.cleanup_worktree("orphan-test")

    @pytest.mark.asyncio
    async def test_is_dirty(self, temp_git_repo):
        """Test checking if repo has uncommitted changes."""
        manager = WorktreeManager(temp_git_repo)

        # Clean repo
        assert await manager.is_dirty() is False

        # Make a change
        readme_path = Path(temp_git_repo) / "README.md"
        readme_path.write_text("# Modified\n")

        assert await manager.is_dirty() is True

    @pytest.mark.asyncio
    async def test_get_commit_count(self, temp_git_repo):
        """Test getting commit count in worktree branch."""
        manager = WorktreeManager(temp_git_repo)

        await manager.create_worktree("test", "main")

        # No commits ahead yet
        count = await manager.get_commit_count("test", "main")
        assert count == 0

        # Make a commit in the worktree
        worktree_path = manager.get_worktree_path("test")
        test_file = Path(worktree_path) / "test.txt"
        test_file.write_text("test content")
        run_git(["add", "test.txt"], worktree_path)
        run_git(["commit", "-m", "Test commit"], worktree_path)

        # Now should be 1 commit ahead
        count = await manager.get_commit_count("test", "main")
        assert count == 1

        # Cleanup
        await manager.cleanup_worktree("test")


class TestWorktreeResult:
    """Tests for WorktreeResult."""

    def test_achieved_property(self):
        """Test achieved property."""
        from harness.loop.types import GoalResult, GoalStatus

        # Without goal_result
        result = WorktreeResult(name="test")
        assert result.achieved is False

        # With failed goal_result
        result = WorktreeResult(
            name="test",
            goal_result=GoalResult(
                goal="test",
                status=GoalStatus.ERROR,
            ),
        )
        assert result.achieved is False

        # With successful goal_result
        result = WorktreeResult(
            name="test",
            goal_result=GoalResult(
                goal="test",
                status=GoalStatus.ACHIEVED,
            ),
        )
        assert result.achieved is True

    def test_duration_seconds(self):
        """Test duration calculation."""
        result = WorktreeResult(
            name="test",
            created_at=datetime(2026, 1, 1, 10, 0, 0),
            completed_at=datetime(2026, 1, 1, 10, 5, 30),
        )
        assert result.duration_seconds == 330.0

    def test_to_dict(self):
        """Test serialization."""
        result = WorktreeResult(
            name="test",
            worktree_path="/path/to/worktree",
            branch_name="feature-test",
            commits_made=2,
            cleanup_done=True,
        )

        data = result.to_dict()
        assert data["name"] == "test"
        assert data["worktree_path"] == "/path/to/worktree"
        assert data["branch_name"] == "feature-test"
        assert data["commits_made"] == 2
        assert data["cleanup_done"] is True


class TestMergeResult:
    """Tests for MergeResult."""

    def test_success_property(self):
        """Test success property."""
        # No conflicts
        result = MergeResult(merged=["branch-a", "branch-b"])
        assert result.success is True

        # With conflicts
        result = MergeResult(merged=["branch-a"], conflicts=["branch-b"])
        assert result.success is False

        # With error
        result = MergeResult(merged=["branch-a"], error="Dirty state")
        assert result.success is False

    def test_total_attempted(self):
        """Test total_attempted property."""
        result = MergeResult(
            merged=["branch-a", "branch-b"],
            conflicts=["branch-c"],
        )
        assert result.total_attempted == 3

    def test_to_dict(self):
        """Test serialization."""
        result = MergeResult(
            merged=["branch-a"],
            conflicts=["branch-b"],
            skipped=["branch-c"],
        )

        data = result.to_dict()
        assert data["merged"] == ["branch-a"]
        assert data["conflicts"] == ["branch-b"]
        assert data["skipped"] == ["branch-c"]
        assert data["success"] is False


class TestWorktreeOrchestratorIntegration:
    """Integration tests for WorktreeOrchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_init(self, temp_git_repo):
        """Test WorktreeOrchestrator initialization."""
        from harness.loop import WorktreeOrchestrator

        # Create a simple mock agent with minimal requirements
        class MinimalMockAgent:
            pass

        orchestrator = WorktreeOrchestrator(MinimalMockAgent(), temp_git_repo)

        assert orchestrator.repo_root == temp_git_repo
        assert orchestrator.worktree_manager is not None
        assert orchestrator.executor is not None

    @pytest.mark.asyncio
    async def test_list_worktrees(self, temp_git_repo):
        """Test listing worktrees through orchestrator."""
        from harness.loop import WorktreeOrchestrator

        class MinimalMockAgent:
            pass

        orchestrator = WorktreeOrchestrator(MinimalMockAgent(), temp_git_repo)

        # Initially no worktrees
        assert orchestrator.list_worktrees() == []

        # Create a worktree directly
        await orchestrator.worktree_manager.create_worktree("test-branch", "main")

        # Now should have one
        assert len(orchestrator.list_worktrees()) == 1

        # Cleanup
        await orchestrator.cleanup_all()

    @pytest.mark.asyncio
    async def test_merge_successful_checks_dirty_state(self, temp_git_repo):
        """Test that merge_successful checks for dirty state."""
        from harness.loop import WorktreeOrchestrator

        class MinimalMockAgent:
            pass

        orchestrator = WorktreeOrchestrator(MinimalMockAgent(), temp_git_repo)

        # Make repo dirty
        readme_path = Path(temp_git_repo) / "README.md"
        readme_path.write_text("# Modified\n")

        results = {"test": WorktreeResult(name="test", branch_name="test")}

        with pytest.raises(WorktreeError, match="uncommitted changes"):
            await orchestrator.merge_successful(results)

    @pytest.mark.asyncio
    async def test_cleanup_all(self, temp_git_repo):
        """Test cleanup_all removes all worktrees."""
        from harness.loop import WorktreeOrchestrator

        class MinimalMockAgent:
            pass

        orchestrator = WorktreeOrchestrator(MinimalMockAgent(), temp_git_repo)

        # Create worktrees directly through manager
        await orchestrator.worktree_manager.create_worktree("test-a", "main")
        await orchestrator.worktree_manager.create_worktree("test-b", "main")

        assert len(orchestrator.list_worktrees()) == 2

        # Cleanup all
        count = await orchestrator.cleanup_all()
        assert count == 2
        assert len(orchestrator.list_worktrees()) == 0

    @pytest.mark.asyncio
    async def test_delete_branch(self, temp_git_repo):
        """Test deleting a branch after merge."""
        from harness.loop import WorktreeOrchestrator

        class MinimalMockAgent:
            pass

        orchestrator = WorktreeOrchestrator(MinimalMockAgent(), temp_git_repo)

        # Create a branch via worktree
        await orchestrator.worktree_manager.create_worktree(
            "test-branch", "main", create_branch=True
        )

        # Verify branch exists
        result = run_git(["branch", "--list", "test-branch"], temp_git_repo)
        assert "test-branch" in result.stdout

        # Cleanup worktree first
        await orchestrator.worktree_manager.cleanup_worktree("test-branch")

        # Delete branch
        deleted = await orchestrator.delete_branch("test-branch")
        assert deleted is True

        # Verify branch is gone
        result = run_git(["branch", "--list", "test-branch"], temp_git_repo)
        assert "test-branch" not in result.stdout


class TestConstants:
    """Test module constants."""

    def test_worktrees_dir(self):
        """Test WORKTREES_DIR constant."""
        assert WORKTREES_DIR == ".worktrees"
