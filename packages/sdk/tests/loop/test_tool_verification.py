"""
Tests for tool-based goal verification.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from harness.loop import (
    GoalConfig,
    GoalVerifier,
    GoalStatus,
    ToolVerificationConfig,
    VerificationCommand,
    VerificationMethod,
    VerificationResult,
)
from harness.loop.tool_verification import (
    CommandResult,
    execute_verification_command,
    run_tool_verification,
)
from harness.types import LoopResult, LoopState, Session


def create_test_loop_result() -> LoopResult:
    """Create a test LoopResult for verification tests."""
    return LoopResult(
        status=LoopState.COMPLETED,
        session=Session(id="test-session"),
        final_response="Test completed",
        iterations=1,
    )


class TestVerificationCommand:
    """Tests for VerificationCommand."""

    def test_basic_command(self):
        """Test creating a basic command."""
        cmd = VerificationCommand("echo", ["echo", "hello"])
        assert cmd.name == "echo"
        assert cmd.executable == "echo"
        assert cmd.arguments == ["hello"]

    def test_command_no_args(self):
        """Test command with no arguments."""
        cmd = VerificationCommand("ls", ["ls"])
        assert cmd.name == "ls"
        assert cmd.executable == "ls"
        assert cmd.arguments == []


class TestToolVerificationConfig:
    """Tests for ToolVerificationConfig."""

    def test_basic_config(self):
        """Test creating a basic config."""
        config = ToolVerificationConfig(
            commands=[
                VerificationCommand("echo", ["echo", "test"]),
            ]
        )
        assert len(config.commands) == 1
        assert config.timeout_seconds == 300
        assert config.fail_fast is True

    def test_empty_commands_raises(self):
        """Test that empty commands raise error."""
        with pytest.raises(ValueError, match="At least one verification command"):
            ToolVerificationConfig(commands=[])

    def test_from_commands(self):
        """Test creating config from command tuples."""
        config = ToolVerificationConfig.from_commands(
            ("pytest", "pytest", "tests/"),
            ("mypy", "mypy", "src/"),
        )
        assert len(config.commands) == 2
        assert config.commands[0].name == "pytest"
        assert config.commands[1].name == "mypy"

    def test_python_defaults(self):
        """Test Python default configuration."""
        config = ToolVerificationConfig.python_defaults()
        assert len(config.commands) == 3
        assert config.commands[0].name == "pytest"
        assert config.commands[1].name == "mypy"
        assert config.commands[2].name == "ruff"

    def test_gradle_defaults(self):
        """Test Gradle default configuration."""
        config = ToolVerificationConfig.gradle_defaults()
        assert len(config.commands) == 2
        assert config.timeout_seconds == 600


class TestExecuteVerificationCommand:
    """Tests for execute_verification_command."""

    @pytest.mark.asyncio
    async def test_successful_command(self, tmp_path: Path):
        """Test executing a successful command."""
        cmd = VerificationCommand("echo", ["echo", "hello"])
        result = await execute_verification_command(cmd, str(tmp_path), 10)

        assert result.success
        assert result.exit_code == 0
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_failing_command(self, tmp_path: Path):
        """Test executing a failing command."""
        cmd = VerificationCommand("false", ["false"])  # Always exits with 1
        result = await execute_verification_command(cmd, str(tmp_path), 10)

        assert not result.success
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_nonexistent_executable(self, tmp_path: Path):
        """Test with nonexistent executable."""
        cmd = VerificationCommand("nonexistent_xyz", ["nonexistent_xyz"])
        result = await execute_verification_command(cmd, str(tmp_path), 10)

        assert not result.success
        assert "not found" in result.error_output.lower()


class TestRunToolVerification:
    """Tests for run_tool_verification."""

    @pytest.mark.asyncio
    async def test_all_commands_pass(self, tmp_path: Path):
        """Test when all commands pass."""
        config = ToolVerificationConfig(
            commands=[
                VerificationCommand("echo1", ["echo", "test1"]),
                VerificationCommand("echo2", ["echo", "test2"]),
            ],
            working_directory=str(tmp_path),
        )

        success, reasoning = await run_tool_verification(config)

        assert success
        assert "PASSED" in reasoning
        assert "echo1" in reasoning
        assert "echo2" in reasoning

    @pytest.mark.asyncio
    async def test_one_command_fails(self, tmp_path: Path):
        """Test when one command fails."""
        config = ToolVerificationConfig(
            commands=[
                VerificationCommand("echo", ["echo", "test"]),
                VerificationCommand("false", ["false"]),
            ],
            working_directory=str(tmp_path),
        )

        success, reasoning = await run_tool_verification(config)

        assert not success
        assert "FAILED" in reasoning

    @pytest.mark.asyncio
    async def test_fail_fast(self, tmp_path: Path):
        """Test fail_fast stops at first failure."""
        config = ToolVerificationConfig(
            commands=[
                VerificationCommand("false", ["false"]),
                VerificationCommand("echo", ["echo", "test"]),
            ],
            working_directory=str(tmp_path),
            fail_fast=True,
        )

        success, reasoning = await run_tool_verification(config)

        assert not success
        # Second command should not run due to fail_fast
        assert "echo" not in reasoning or "FAILED" in reasoning

    @pytest.mark.asyncio
    async def test_workspace_from_context(self, tmp_path: Path):
        """Test workspace directory from context."""
        config = ToolVerificationConfig(
            commands=[VerificationCommand("echo", ["echo", "test"])],
            working_directory="/wrong/path",
        )

        context = {"workspace_dir": str(tmp_path)}
        success, reasoning = await run_tool_verification(config, context)

        assert success


class TestGoalVerifierTool:
    """Tests for GoalVerifier with tool verification."""

    def test_missing_tool_config_raises(self):
        """Test that missing tool config raises error."""
        with pytest.raises(ValueError, match="tool_verification_config is required"):
            GoalConfig(
                description="Test goal",
                verification_method=VerificationMethod.TOOL,
            )

    @pytest.mark.asyncio
    async def test_tool_verification_success(self, tmp_path: Path):
        """Test successful tool verification."""
        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.TOOL,
            tool_verification_config=ToolVerificationConfig(
                commands=[VerificationCommand("echo", ["echo", "success"])],
                working_directory=str(tmp_path),
            ),
        )

        verifier = GoalVerifier(config)
        result = await verifier.verify(create_test_loop_result())

        assert result.achieved
        assert result.confidence == 1.0
        assert "PASSED" in result.reasoning

    @pytest.mark.asyncio
    async def test_tool_verification_failure(self, tmp_path: Path):
        """Test failed tool verification."""
        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.TOOL,
            tool_verification_config=ToolVerificationConfig(
                commands=[VerificationCommand("false", ["false"])],
                working_directory=str(tmp_path),
            ),
        )

        verifier = GoalVerifier(config)
        result = await verifier.verify(create_test_loop_result())

        assert not result.achieved
        assert "FAILED" in result.reasoning or "failed" in result.reasoning

    @pytest.mark.asyncio
    async def test_tool_verification_with_context_workspace(self, tmp_path: Path):
        """Test tool verification uses workspace from context."""
        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.TOOL,
            tool_verification_config=ToolVerificationConfig(
                commands=[VerificationCommand("echo", ["echo", "test"])],
                working_directory="/wrong/path",
            ),
        )

        verifier = GoalVerifier(config)
        result = await verifier.verify(
            create_test_loop_result(),
            context={"workspace_dir": str(tmp_path)},
        )

        assert result.achieved
