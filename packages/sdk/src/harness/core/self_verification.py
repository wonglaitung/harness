"""
Self-Verification Hook - Automatic test execution after code changes.

This hook implements the write-code → run-tests → fix-errors cycle.
After code modifications, it automatically runs tests and injects
any failures back into the context for the LLM to fix.

Usage:
    from harness.core import SelfVerificationHook

    agent = AgentHarness()
    agent.add_hook(SelfVerificationHook(
        test_command="pytest",
        test_args=["-x", "-v"],
    ))

    # Tests will run automatically after code changes
    result = await agent.run("Fix the bug in src/main.py")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from harness.core.hooks import LifecycleHook
from harness.types import HookAction, HookContext, HookPoint, HookResult, Message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class SelfVerificationConfig:
    """Configuration for self-verification hook."""

    # Command to run tests
    test_command: str = "pytest"

    # Arguments for test command
    test_args: list[str] = field(default_factory=lambda: ["-x", "--tb=short"])

    # Tools that trigger verification (code modification tools)
    trigger_tools: list[str] = field(
        default_factory=lambda: ["write", "edit", "write_file", "edit_file"]
    )

    # Working directory for tests (None = current directory)
    working_directory: Path | None = None

    # Timeout for test execution in seconds
    timeout: float = 60.0

    # Maximum test retry attempts
    max_retries: int = 3

    # Whether to run tests on every code change (True) or only when model claims done (False)
    verify_on_change: bool = True

    # Whether to skip verification if no tests exist
    skip_if_no_tests: bool = True

    # Pattern to detect test files
    test_pattern: str = "test_*.py"


class SelfVerificationHook(LifecycleHook):
    """
    Hook that automatically runs tests after code modifications.

    This creates a self-improving loop where the agent:
    1. Modifies code
    2. Tests are automatically run
    3. If tests fail, errors are injected back
    4. Agent fixes the issues
    5. Loop continues until tests pass

    Example:
        agent = AgentHarness()
        agent.add_hook(SelfVerificationHook(
            test_command="pytest",
            test_args=["-x", "-v"],
            verify_on_change=True,
        ))
    """

    def __init__(self, config: SelfVerificationConfig | None = None):
        self.config = config or SelfVerificationConfig()
        self._retry_count: dict[str, int] = {}  # session_id -> retry count
        self._last_test_results: dict[str, str] = {}  # session_id -> last test output

    @property
    def hook_points(self) -> list[HookPoint]:
        """Subscribe to after tool execute hook."""
        return [HookPoint.AFTER_TOOL_EXECUTE]

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the verification logic after tool execution."""
        if context.hook_point != HookPoint.AFTER_TOOL_EXECUTE:
            return HookResult.continue_()

        tool_name = context.tool_name
        if not tool_name or tool_name not in self.config.trigger_tools:
            return HookResult.continue_()

        # Check if we should verify
        if not self.config.verify_on_change:
            return HookResult.continue_()

        # Run tests
        logger.info(f"Self-verification: Running tests after {tool_name}")

        test_result = await self._run_tests(context)

        if test_result is None:
            # No tests to run or error
            return HookResult.continue_()

        if test_result["success"]:
            logger.info("Self-verification: Tests passed")
            self._retry_count[context.session_id] = 0
            return HookResult.continue_()

        # Tests failed - inject error message
        session_key = context.session_id
        self._retry_count[session_key] = self._retry_count.get(session_key, 0) + 1

        if self._retry_count[session_key] > self.config.max_retries:
            logger.warning(
                f"Self-verification: Max retries ({self.config.max_retries}) reached, "
                "stopping verification loop"
            )
            self._retry_count[session_key] = 0
            return HookResult.continue_()

        logger.info(
            f"Self-verification: Tests failed, injecting error "
            f"(attempt {self._retry_count[session_key]}/{self.config.max_retries})"
        )

        # Build error message
        error_message = self._build_error_message(test_result, context)

        # Inject as user message
        return HookResult(
            action=HookAction.INJECT_MESSAGE,
            inject_message=Message(
                role="user",
                content=error_message,
                metadata={"type": "test_failure", "injected": True},
            ),
        )

    async def _run_tests(self, context: HookContext) -> dict | None:
        """Run the test command and return results."""
        work_dir = self.config.working_directory or Path.cwd()

        # Check if tests exist
        if self.config.skip_if_no_tests and not self._has_tests(work_dir):
            logger.info("Self-verification: No tests found, skipping")
            return None

        cmd = [self.config.test_command] + self.config.test_args

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout,
            )

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            success = process.returncode == 0

            self._last_test_results[context.session_id] = output + error_output

            return {
                "success": success,
                "output": output,
                "error": error_output,
                "returncode": process.returncode,
            }

        except TimeoutError:
            logger.warning(f"Self-verification: Tests timed out after {self.config.timeout}s")
            return {
                "success": False,
                "output": "",
                "error": f"Test execution timed out after {self.config.timeout} seconds",
                "returncode": -1,
            }

        except FileNotFoundError:
            logger.warning(f"Self-verification: Test command not found: {self.config.test_command}")
            return None

        except Exception as e:
            logger.exception(f"Self-verification: Error running tests: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1,
            }

    def _has_tests(self, work_dir: Path) -> bool:
        """Check if any test files exist."""
        # Check common test directories
        test_dirs = ["tests", "test", "src/tests"]

        for test_dir in test_dirs:
            test_path = work_dir / test_dir
            if test_path.exists():
                # Check for test files
                test_files = list(test_path.glob(self.config.test_pattern))
                if test_files:
                    return True

        # Check for test files in root
        root_test_files = list(work_dir.glob(self.config.test_pattern))
        return bool(root_test_files)

    def _build_error_message(self, test_result: dict, context: HookContext) -> str:
        """Build the error message to inject."""
        output = test_result["output"]
        error = test_result["error"]

        # Truncate if too long
        max_len = 2000
        combined = f"{output}\n{error}".strip()
        if len(combined) > max_len:
            combined = combined[:max_len] + "\n... [output truncated]"

        retry_count = self._retry_count.get(context.session_id, 0)

        return (
            f"[自验证] 测试失败 (尝试 {retry_count}/{self.config.max_retries})\n\n"
            f"测试输出：\n```\n{combined}\n```\n\n"
            f"请修复上述测试失败的问题。确保：\n"
            f"1. 分析错误信息找出根本原因\n"
            f"2. 修复代码中的问题\n"
            f"3. 重新运行测试确认修复成功"
        )

    def reset(self, session_id: str | None = None) -> None:
        """Reset retry count."""
        if session_id:
            self._retry_count.pop(session_id, None)
            self._last_test_results.pop(session_id, None)
        else:
            self._retry_count.clear()
            self._last_test_results.clear()

    def get_last_test_results(self, session_id: str) -> str | None:
        """Get the last test results for a session."""
        return self._last_test_results.get(session_id)
