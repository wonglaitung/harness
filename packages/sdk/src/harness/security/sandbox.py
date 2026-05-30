"""
Sandbox Executor - Isolated command execution.

Provides lightweight sandboxing for bash commands with:
- Command validation and blocking
- Resource limits
- Clean environment
"""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LightweightSandboxConfig:
    """
    Lightweight sandbox configuration.

    Provides basic isolation without requiring Docker.
    """

    allowed_commands: set[str] | None = None
    blocked_patterns: list[str] | None = None
    max_execution_time: float = 30.0
    max_output_size: int = 1_000_000  # 1MB
    allowed_env_vars: set[str] | None = None


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    error: str | None = None


class LightweightSandbox:
    """
    Lightweight sandbox executor.

    Provides basic command isolation through:
    - Command pattern blocking
    - Optional command whitelist
    - Clean environment variables
    - Execution timeout
    """

    DEFAULT_BLOCKED_PATTERNS = [
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "mkfs",
        "dd if=",
        "> /dev/",
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  # Fork bomb
        "rm -rf /",
        "rm -rf ~",
        "chmod -R 777",
        "> /etc/",
        "> ~/.ssh/",
    ]

    DANGEROUS_PATHS = [
        "/etc",
        "/root",
        "~/.ssh",
        "~/.aws",
        "~/.gnupg",
        "~/.config",
    ]

    def __init__(self, config: LightweightSandboxConfig | None = None):
        """
        Initialize sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config or LightweightSandboxConfig()
        if not self.config.blocked_patterns:
            self.config.blocked_patterns = self.DEFAULT_BLOCKED_PATTERNS.copy()

    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command safety.

        Args:
            command: Command to validate

        Returns:
            (is_valid, reason) tuple
        """
        if not command or not command.strip():
            return False, "Empty command"

        # Check blocked patterns
        for pattern in self.config.blocked_patterns or []:
            if pattern in command:
                return False, f"Blocked pattern: {pattern}"

        # Check whitelist
        if self.config.allowed_commands:
            cmd_base = command.split()[0] if command.split() else ""
            if shutil.which(cmd_base) not in self.config.allowed_commands:
                return False, f"Command not in whitelist: {cmd_base}"

        # Check dangerous paths
        for path in self.DANGEROUS_PATHS:
            expanded = os.path.expanduser(path)
            if expanded in command:
                return False, f"Dangerous path: {path}"

        return True, ""

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        """
        Execute command in sandbox.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Additional environment variables
            timeout: Execution timeout

        Returns:
            SandboxResult with execution outcome
        """
        # Validate command
        valid, reason = self.validate_command(command)
        if not valid:
            return SandboxResult(success=False, error=reason)

        # Build clean environment
        clean_env = self._build_clean_env(env)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=clean_env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.config.max_execution_time,
            )

            # Truncate output if needed
            stdout_str = stdout[: self.config.max_output_size].decode(
                "utf-8", errors="replace"
            )
            stderr_str = stderr.decode("utf-8", errors="replace")

            return SandboxResult(
                success=process.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode or 0,
            )

        except asyncio.TimeoutError:
            process.kill()
            return SandboxResult(
                success=False,
                error=f"Timeout after {timeout or self.config.max_execution_time}s",
            )
        except Exception as e:
            return SandboxResult(success=False, error=str(e))

    def _build_clean_env(self, extra_env: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build clean environment variables.

        Removes sensitive variables and keeps only safe ones.

        Args:
            extra_env: Additional environment variables

        Returns:
            Cleaned environment dictionary
        """
        safe_vars = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM"}
        if self.config.allowed_env_vars:
            safe_vars.update(self.config.allowed_env_vars)

        env = {k: v for k, v in os.environ.items() if k in safe_vars}

        # Remove sensitive variables
        sensitive = {
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "GITLAB_TOKEN",
            "DATABASE_URL",
            "DB_PASSWORD",
        }
        for var in sensitive:
            env.pop(var, None)

        if extra_env:
            env.update(extra_env)

        return env


@dataclass
class SandboxExecutor:
    """
    Full sandbox executor with permission checking.

    Integrates with PermissionSet for comprehensive access control.
    """

    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /",
        "rm -rf ~",
        "sudo",
        "chmod -R 777",
        "mkfs",
        "dd if=",
    ])
    max_execution_time: float = 60.0
    max_memory_mb: int = 512

    def is_command_allowed(self, command: str) -> bool:
        """
        Check if command is allowed.

        Args:
            command: Command to check

        Returns:
            True if command is allowed
        """
        for blocked in self.blocked_commands:
            if blocked in command:
                return False
        return True

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """
        Execute command with permission check.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables

        Returns:
            SandboxResult
        """
        if not self.is_command_allowed(command):
            return SandboxResult(
                success=False,
                error=f"Command not allowed: contains blocked pattern",
            )

        sandbox = LightweightSandbox(
            LightweightSandboxConfig(
                max_execution_time=self.max_execution_time,
                blocked_patterns=self.blocked_commands,
            )
        )

        return await sandbox.execute(command, cwd, env)
