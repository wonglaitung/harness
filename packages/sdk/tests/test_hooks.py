"""
Tests for Lifecycle Hooks system.
"""

import pytest

from harness.core.hooks import (
    AbortOnDangerousToolHook,
    HookManager,
    LifecycleHook,
    LoggingHook,
    MaxToolCallsHook,
)
from harness.types import (
    HookAction,
    HookContext,
    HookPoint,
    HookResult,
)


class TestHookResult:
    """Test HookResult convenience methods."""

    def test_continue_method(self):
        """Test continue_() creates CONTINUE action."""
        result = HookResult.continue_()
        assert result.action == HookAction.CONTINUE

    def test_abort_method(self):
        """Test abort() creates ABORT action."""
        result = HookResult.abort("Test abort")
        assert result.action == HookAction.ABORT
        assert result.metadata.get("reason") == "Test abort"

    def test_inject_message_method(self):
        """Test inject_message() creates INJECT_MESSAGE action."""
        from harness.types import Message
        msg = Message(role="user", content="test")
        result = HookResult.inject_message(msg)
        assert result.action == HookAction.INJECT_MESSAGE
        assert result.inject_message == msg

    def test_modify_args_method(self):
        """Test modify_args() creates MODIFY_ARGS action."""
        args = {"key": "value"}
        result = HookResult.modify_args(args)
        assert result.action == HookAction.MODIFY_ARGS
        assert result.modified_args == args


class TestHookManager:
    """Test HookManager functionality."""

    def test_register_hook(self):
        """Test registering a hook."""
        manager = HookManager()
        hook = LoggingHook()
        manager.register(hook)

        # Should be registered for all hook points
        assert manager.has_hooks(HookPoint.BEFORE_LLM_CALL)
        assert manager.has_hooks(HookPoint.AFTER_LLM_CALL)

    def test_unregister_hook(self):
        """Test unregistering a hook."""
        manager = HookManager()
        hook = LoggingHook()
        manager.register(hook)
        manager.unregister(hook)

        assert not manager.has_hooks(HookPoint.BEFORE_LLM_CALL)

    @pytest.mark.asyncio
    async def test_execute_hooks_continue(self):
        """Test executing hooks returns CONTINUE when no hooks block."""
        manager = HookManager()
        hook = LoggingHook()
        manager.register(hook)

        context = HookContext(
            hook_point=HookPoint.BEFORE_LLM_CALL,
            session_id="test",
            iteration=1,
        )
        result = await manager.execute_hooks(HookPoint.BEFORE_LLM_CALL, context)

        assert result.action == HookAction.CONTINUE


class TestAbortOnDangerousToolHook:
    """Test AbortOnDangerousToolHook."""

    @pytest.mark.asyncio
    async def test_blocks_dangerous_tools(self):
        """Test that dangerous tools are blocked."""
        hook = AbortOnDangerousToolHook()

        context = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="rm",
            tool_args={"path": "/tmp/test"},
        )
        result = await hook.execute(context)

        assert result.action == HookAction.ABORT

    @pytest.mark.asyncio
    async def test_allows_safe_tools(self):
        """Test that safe tools are allowed."""
        hook = AbortOnDangerousToolHook()

        context = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="read",
            tool_args={"file_path": "/tmp/test.txt"},
        )
        result = await hook.execute(context)

        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_blocks_dangerous_bash_commands(self):
        """Test that dangerous bash commands are blocked."""
        hook = AbortOnDangerousToolHook()

        context = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="bash",
            tool_args={"command": "rm -rf /"},
        )
        result = await hook.execute(context)

        assert result.action == HookAction.ABORT

    @pytest.mark.asyncio
    async def test_custom_blocklist(self):
        """Test custom blocklist."""
        hook = AbortOnDangerousToolHook(blocked_tools=["custom_tool"])

        context = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="custom_tool",
            tool_args={},
        )
        result = await hook.execute(context)

        assert result.action == HookAction.ABORT


class TestMaxToolCallsHook:
    """Test MaxToolCallsHook."""

    @pytest.mark.asyncio
    async def test_limits_tool_calls(self):
        """Test that tool call limit is enforced."""
        hook = MaxToolCallsHook(tool_name="test_tool", max_calls=2)

        # First call should be allowed
        context1 = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="test_tool",
            tool_args={},
        )
        result1 = await hook.execute(context1)
        assert result1.action == HookAction.CONTINUE

        # Second call should be allowed
        context2 = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=2,
            tool_name="test_tool",
            tool_args={},
        )
        result2 = await hook.execute(context2)
        assert result2.action == HookAction.CONTINUE

        # Third call should be blocked
        context3 = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=3,
            tool_name="test_tool",
            tool_args={},
        )
        result3 = await hook.execute(context3)
        assert result3.action == HookAction.ABORT

    @pytest.mark.asyncio
    async def test_different_tools_tracked_separately(self):
        """Test that different tools are tracked separately."""
        hook = MaxToolCallsHook(tool_name="tool_a", max_calls=1)

        # tool_a should be blocked after 1 call
        context_a = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="tool_a",
            tool_args={},
        )
        result_a = await hook.execute(context_a)
        assert result_a.action == HookAction.CONTINUE

        result_a2 = await hook.execute(context_a)
        assert result_a2.action == HookAction.ABORT

        # tool_b should not be affected
        context_b = HookContext(
            hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
            session_id="test",
            iteration=1,
            tool_name="tool_b",
            tool_args={},
        )
        result_b = await hook.execute(context_b)
        assert result_b.action == HookAction.CONTINUE

    def test_reset(self):
        """Test resetting call counts."""
        hook = MaxToolCallsHook(tool_name="test_tool", max_calls=1)

        # Reset should not raise
        hook.reset(session_id="test")
        hook.reset()  # Reset all
