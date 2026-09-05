"""
Tests for Self-Verification Hook.
"""

import tempfile
from pathlib import Path

import pytest

from harness.core.self_verification import (
    SelfVerificationConfig,
    SelfVerificationHook,
)
from harness.types import (
    HookAction,
    HookContext,
    HookPoint,
    ToolResult,
)


class TestSelfVerificationConfig:
    """Test SelfVerificationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SelfVerificationConfig()
        assert config.test_command == "pytest"
        assert "-x" in config.test_args
        assert "write" in config.trigger_tools
        assert "edit" in config.trigger_tools
        assert config.timeout == 60.0
        assert config.max_retries == 3
        assert config.verify_on_change is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = SelfVerificationConfig(
            test_command="npm",
            test_args=["test", "--verbose"],
            trigger_tools=["write_file"],
            timeout=120.0,
            max_retries=5,
            verify_on_change=False,
        )
        assert config.test_command == "npm"
        assert "--verbose" in config.test_args
        assert config.trigger_tools == ["write_file"]
        assert config.timeout == 120.0
        assert config.max_retries == 5
        assert config.verify_on_change is False


class TestSelfVerificationHook:
    """Test SelfVerificationHook."""

    def test_hook_points(self):
        """Test that hook subscribes to correct points."""
        hook = SelfVerificationHook()
        assert HookPoint.AFTER_TOOL_EXECUTE in hook.hook_points

    @pytest.mark.asyncio
    async def test_ignores_non_trigger_tools(self):
        """Test that hook ignores tools that don't trigger verification."""
        hook = SelfVerificationHook()

        context = HookContext(
            hook_point=HookPoint.AFTER_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="read",
            tool_args={"file_path": "/tmp/test.txt"},
            tool_result=ToolResult(
                tool_call_id="1",
                success=True,
                content="file contents",
            ),
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_ignores_when_verify_on_change_false(self):
        """Test that hook skips verification when verify_on_change is False."""
        config = SelfVerificationConfig(verify_on_change=False)
        hook = SelfVerificationHook(config=config)

        context = HookContext(
            hook_point=HookPoint.AFTER_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="write",
            tool_args={"file_path": "/tmp/test.py", "content": "# test"},
            tool_result=ToolResult(
                tool_call_id="1",
                success=True,
                content="File written",
            ),
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

    def test_has_tests_detects_test_directory(self):
        """Test detection of test directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create tests directory with test file
            tests_dir = work_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("# test")

            hook = SelfVerificationHook()
            assert hook._has_tests(work_dir) is True

    def test_has_tests_detects_root_test_files(self):
        """Test detection of test files in root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create test file in root
            (work_dir / "test_example.py").write_text("# test")

            hook = SelfVerificationHook()
            assert hook._has_tests(work_dir) is True

    def test_has_tests_returns_false_when_no_tests(self):
        """Test that no tests returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # No test files
            hook = SelfVerificationHook()
            assert hook._has_tests(work_dir) is False

    def test_build_error_message(self):
        """Test error message building."""
        hook = SelfVerificationHook()
        hook._retry_count["test"] = 1

        test_result = {
            "output": "FAILED test_example.py::test_one",
            "error": "AssertionError: assert False",
            "returncode": 1,
        }

        context = HookContext(
            hook_point=HookPoint.AFTER_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
        )

        message = hook._build_error_message(test_result, context)

        assert "测试失败" in message
        assert "FAILED test_example.py" in message
        assert "AssertionError" in message
        assert "1/3" in message

    def test_build_error_message_truncates_long_output(self):
        """Test that long output is truncated."""
        hook = SelfVerificationHook()
        hook._retry_count["test"] = 1

        # Very long output
        long_output = "x" * 5000
        test_result = {
            "output": long_output,
            "error": "",
            "returncode": 1,
        }

        context = HookContext(
            hook_point=HookPoint.AFTER_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
        )

        message = hook._build_error_message(test_result, context)

        assert len(message) < 3000
        assert "truncated" in message

    def test_reset_session(self):
        """Test reset for specific session."""
        hook = SelfVerificationHook()
        hook._retry_count["session1"] = 2
        hook._retry_count["session2"] = 1
        hook._last_test_results["session1"] = "results"

        hook.reset(session_id="session1")

        assert "session1" not in hook._retry_count
        assert "session1" not in hook._last_test_results
        assert "session2" in hook._retry_count

    def test_reset_all(self):
        """Test reset for all sessions."""
        hook = SelfVerificationHook()
        hook._retry_count["session1"] = 2
        hook._retry_count["session2"] = 1

        hook.reset()

        assert len(hook._retry_count) == 0

    def test_get_last_test_results(self):
        """Test getting last test results."""
        hook = SelfVerificationHook()
        hook._last_test_results["session1"] = "test output"

        result = hook.get_last_test_results("session1")
        assert result == "test output"

        result = hook.get_last_test_results("nonexistent")
        assert result is None


class TestSelfVerificationHookIntegration:
    """Integration tests for SelfVerificationHook."""

    @pytest.mark.asyncio
    async def test_injects_message_on_test_failure(self):
        """Test that failed tests result in message injection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create tests directory with a failing test
            tests_dir = work_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("""
def test_always_fails():
    assert False, "This test always fails"
""")

            config = SelfVerificationConfig(
                working_directory=work_dir,
                test_args=["-x", "--tb=short"],
            )
            hook = SelfVerificationHook(config=config)

            context = HookContext(
                hook_point=HookPoint.AFTER_TOOL_EXECUTE,
                session_id="test",
                iteration=1,
                tool_name="write",
                tool_args={"file_path": str(work_dir / "main.py")},
                tool_result=ToolResult(
                    tool_call_id="1",
                    success=True,
                    content="File written",
                ),
            )

            result = await hook.execute(context)

            # Should inject message because test failed
            assert result.action == HookAction.INJECT_MESSAGE
            assert result.inject_message is not None
            assert "测试失败" in result.inject_message.content

    @pytest.mark.asyncio
    async def test_continues_on_test_success(self):
        """Test that passing tests result in continue action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Create tests directory with a passing test
            tests_dir = work_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("""
def test_always_passes():
    assert True
""")

            config = SelfVerificationConfig(
                working_directory=work_dir,
                test_args=["-x", "--tb=short"],
            )
            hook = SelfVerificationHook(config=config)

            context = HookContext(
                hook_point=HookPoint.AFTER_TOOL_EXECUTE,
                session_id="test",
                iteration=1,
                tool_name="write",
                tool_args={"file_path": str(work_dir / "main.py")},
                tool_result=ToolResult(
                    tool_call_id="1",
                    success=True,
                    content="File written",
                ),
            )

            result = await hook.execute(context)

            # Should continue because test passed
            assert result.action == HookAction.CONTINUE
