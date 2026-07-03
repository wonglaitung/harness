"""
Tool Verification Configuration - Configuration for tool-based goal verification.

This module provides configuration for running commands (tests, lint, type check)
to verify if a goal has been achieved.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationCommand:
    """
    A single verification command.

    Attributes:
        name: Human-readable name for the command
        command: Command and arguments to execute
    """

    name: str
    command: list[str]

    @property
    def executable(self) -> str:
        """Get the executable (first element of command)."""
        return self.command[0] if self.command else ""

    @property
    def arguments(self) -> list[str]:
        """Get the arguments (all elements after the first)."""
        return self.command[1:] if len(self.command) > 1 else []

    def __str__(self) -> str:
        return f"VerificationCommand(name={self.name!r}, command={self.command!r})"


@dataclass
class ToolVerificationConfig:
    """
    Configuration for tool-based goal verification.

    Tool verification runs commands (tests, lint, type check) to verify
    if a goal has been achieved. This provides objective, deterministic
    verification compared to LLM-based verification.

    Attributes:
        commands: List of verification commands to run
        working_directory: Directory to run commands in
        timeout_seconds: Timeout for each command
        fail_fast: Stop on first command failure
        continue_on_warning: Continue if command exits with warning

    Example:
        ```python
        # Python project verification
        config = ToolVerificationConfig(
            commands=[
                VerificationCommand("pytest", ["pytest", "tests/", "-v"]),
                VerificationCommand("mypy", ["mypy", "src/"]),
                VerificationCommand("ruff", ["ruff", "check", "src/"]),
            ],
            working_directory="./project",
            timeout_seconds=300,
        )

        # Combined with GoalConfig
        goal_config = GoalConfig(
            description="Fix all type errors",
            verification_method=VerificationMethod.TOOL,
            tool_verification_config=config,
        )
        ```

    Verification Logic:
        - All commands must succeed (exit code 0) for verification to pass
        - If any command fails, verification fails with details
        - Commands are run in sequence, stopping on first failure if fail_fast=True
        - Output is captured and included in reasoning
    """

    commands: list[VerificationCommand] = field(default_factory=list)
    working_directory: str = "."
    timeout_seconds: int = 300
    fail_fast: bool = True
    continue_on_warning: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.commands:
            raise ValueError("At least one verification command is required")

    @classmethod
    def from_commands(
        cls,
        *commands: tuple[str, ...] | list[str],
        working_directory: str = ".",
        timeout_seconds: int = 300,
    ) -> ToolVerificationConfig:
        """
        Create config from simple command tuples.

        Args:
            commands: Commands as tuples/lists (first element is name, rest is command)
            working_directory: Directory to run commands in
            timeout_seconds: Timeout for each command

        Returns:
            ToolVerificationConfig

        Example:
            ```python
            config = ToolVerificationConfig.from_commands(
                ("pytest", "pytest", "tests/", "-v"),
                ("mypy", "mypy", "src/"),
                working_directory="./project",
            )
            ```
        """
        cmds = []
        for cmd in commands:
            if len(cmd) < 2:
                raise ValueError(f"Command must have at least 2 elements (name, executable): {cmd}")
            name = cmd[0]
            command = list(cmd[1:])
            cmds.append(VerificationCommand(name, command))

        return cls(
            commands=cmds,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Pre-defined verification configurations
    # -------------------------------------------------------------------------

    @classmethod
    def python_defaults(cls) -> ToolVerificationConfig:
        """Create a Python project verification config (pytest + mypy + ruff)."""
        return cls(
            commands=[
                VerificationCommand("pytest", ["pytest", "tests/", "-v"]),
                VerificationCommand("mypy", ["mypy", "src/"]),
                VerificationCommand("ruff", ["ruff", "check", "src/"]),
            ],
        )

    @classmethod
    def python_project(
        cls,
        test_path: str = "tests/",
        src_path: str = "src/",
    ) -> ToolVerificationConfig:
        """Create a Python project verification config with custom paths."""
        return cls(
            commands=[
                VerificationCommand("pytest", ["pytest", test_path, "-v"]),
                VerificationCommand("mypy", ["mypy", src_path]),
                VerificationCommand("ruff", ["ruff", "check", src_path]),
            ],
        )

    @classmethod
    def gradle_defaults(cls) -> ToolVerificationConfig:
        """Create a Java/Gradle project verification config."""
        return cls(
            commands=[
                VerificationCommand("gradle test", ["gradle", "test"]),
                VerificationCommand("gradle check", ["gradle", "check"]),
            ],
            timeout_seconds=600,  # Java tests can be slow
        )

    @classmethod
    def maven_defaults(cls) -> ToolVerificationConfig:
        """Create a Java/Maven project verification config."""
        return cls(
            commands=[
                VerificationCommand("mvn test", ["mvn", "test"]),
            ],
            timeout_seconds=600,
        )

    @classmethod
    def npm_defaults(cls) -> ToolVerificationConfig:
        """Create a Node.js/npm project verification config."""
        return cls(
            commands=[
                VerificationCommand("npm test", ["npm", "test"]),
                VerificationCommand("npm lint", ["npm", "run", "lint"]),
            ],
        )


@dataclass
class CommandResult:
    """Result of a single verification command execution."""

    name: str
    success: bool
    exit_code: int
    output: str
    error_output: str = ""


async def execute_verification_command(
    cmd: VerificationCommand,
    working_dir: str,
    timeout_seconds: int,
) -> CommandResult:
    """
    Execute a verification command asynchronously.

    Args:
        cmd: Command to execute
        working_dir: Working directory
        timeout_seconds: Timeout in seconds

    Returns:
        CommandResult with execution details
    """
    try:
        # Check if executable exists
        executable = cmd.executable
        if not shutil.which(executable):
            return CommandResult(
                name=cmd.name,
                success=False,
                exit_code=-1,
                output="",
                error_output=f"Executable not found: {executable}",
            )

        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd.command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return CommandResult(
                name=cmd.name,
                success=False,
                exit_code=-1,
                output="",
                error_output=f"Command timed out after {timeout_seconds}s",
            )

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")

        return CommandResult(
            name=cmd.name,
            success=process.returncode == 0,
            exit_code=process.returncode or 0,
            output=output,
            error_output=error_output if process.returncode != 0 else "",
        )

    except Exception as e:
        return CommandResult(
            name=cmd.name,
            success=False,
            exit_code=-1,
            output="",
            error_output=str(e),
        )


async def run_tool_verification(
    config: ToolVerificationConfig,
    context: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """
    Run all verification commands and return result.

    Args:
        config: Tool verification configuration
        context: Optional context with 'workspace_dir' override

    Returns:
        Tuple of (success, reasoning)
    """
    context = context or {}

    # Determine working directory
    working_dir = context.get("workspace_dir", config.working_directory)

    results: list[CommandResult] = []
    all_passed = True
    first_failure = None

    for cmd in config.commands:
        result = await execute_verification_command(
            cmd,
            working_dir,
            config.timeout_seconds,
        )
        results.append(result)

        if not result.success:
            all_passed = False
            if first_failure is None:
                first_failure = f"{cmd.name} failed (exit code {result.exit_code}): {result.error_output}"

            if config.fail_fast:
                break

    # Build reasoning
    if all_passed:
        reasoning = "All verification commands passed.\n"
        for r in results:
            reasoning += f"- {r.name}: PASSED\n"
        return True, reasoning
    else:
        reasoning = "Verification failed.\n"
        reasoning += f"{first_failure}\n\n"
        reasoning += "Command results:\n"
        for r in results:
            reasoning += f"- {r.name}: {'PASSED' if r.success else 'FAILED'}\n"
            if not r.success and r.error_output:
                # Include last few lines of error output
                lines = r.error_output.split("\n")
                start_line = max(0, len(lines) - 10)
                reasoning += "  Output:\n"
                for i in range(start_line, len(lines)):
                    reasoning += f"    {lines[i]}\n"
        return False, reasoning
