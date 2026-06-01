"""
Tests for Ralph Loop.
"""

import pytest

from harness.core.ralph_loop import RalphLoopConfig, RalphLoopHook
from harness.types import (
    HookAction,
    HookContext,
    HookPoint,
    HookResult,
    LLMResponse,
    TokenUsage,
    StopReason,
)


class TestRalphLoopConfig:
    """Test RalphLoopConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RalphLoopConfig()
        assert config.max_loops == 5
        assert config.context_threshold == 0.6
        assert config.task_complete_check is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = RalphLoopConfig(
            max_loops=3,
            context_threshold=0.8,
            task_complete_check=lambda r: "done" in r.lower(),
        )
        assert config.max_loops == 3
        assert config.context_threshold == 0.8
        assert config.task_complete_check is not None


class TestRalphLoopHook:
    """Test RalphLoopHook."""

    def test_hook_points(self):
        """Test that hook subscribes to correct points."""
        hook = RalphLoopHook()
        assert HookPoint.ON_EXIT_ATTEMPT in hook.hook_points
        assert HookPoint.ON_LOOP_END in hook.hook_points

    @pytest.mark.asyncio
    async def test_allows_exit_on_completion(self):
        """Test that hook allows exit when task is complete."""
        hook = RalphLoopHook()

        # Response indicating completion
        response = LLMResponse(
            content="Task completed successfully. All changes have been applied.",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response,
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_triggers_continuation_on_incomplete(self):
        """Test that hook triggers continuation when task is incomplete."""
        hook = RalphLoopHook()

        # Response indicating continuation needed
        response = LLMResponse(
            content="I'll continue with the next step...",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response,
        )

        result = await hook.execute(context)
        assert result.action == HookAction.REINJECT
        assert result.inject_message is not None
        assert "继续" in result.inject_message.content

    @pytest.mark.asyncio
    async def test_respects_max_loops(self):
        """Test that hook respects max_loops limit."""
        config = RalphLoopConfig(max_loops=2)
        hook = RalphLoopHook(config=config)

        # Response indicating continuation
        response = LLMResponse(
            content="I'll continue with the next step...",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response,
        )

        # First trigger
        result1 = await hook.execute(context)
        assert result1.action == HookAction.REINJECT

        # Second trigger
        result2 = await hook.execute(context)
        assert result2.action == HookAction.REINJECT

        # Third trigger - should allow exit (max reached)
        result3 = await hook.execute(context)
        assert result3.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_custom_task_complete_check(self):
        """Test custom task completion check."""
        config = RalphLoopConfig(
            task_complete_check=lambda r: "[DONE]" in r
        )
        hook = RalphLoopHook(config=config)

        # Response with custom completion marker
        response = LLMResponse(
            content="Work finished [DONE]",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response,
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

        # Response without marker
        response2 = LLMResponse(
            content="Work finished",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context2 = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response2,
        )

        result2 = await hook.execute(context2)
        assert result2.action == HookAction.REINJECT

    @pytest.mark.asyncio
    async def test_handles_empty_response(self):
        """Test that hook handles empty response gracefully."""
        hook = RalphLoopHook()

        response = LLMResponse(
            content="",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=response,
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_handles_none_response(self):
        """Test that hook handles None response gracefully."""
        hook = RalphLoopHook()

        context = HookContext(
            hook_point=HookPoint.ON_EXIT_ATTEMPT,
            session_id="test",
            iteration=10,
            llm_response=None,
        )

        result = await hook.execute(context)
        assert result.action == HookAction.CONTINUE

    def test_reset(self):
        """Test that reset clears loop count."""
        hook = RalphLoopHook()
        hook._loop_count = 3
        hook._previous_response = "test"

        hook.reset()

        assert hook._loop_count == 0
        assert hook._previous_response is None

    def test_completion_phrases_detection(self):
        """Test that various completion phrases are detected."""
        hook = RalphLoopHook()

        completion_responses = [
            "Task complete - all files updated",
            "All done with the refactoring",
            "Successfully completed the migration",
            "Implementation complete",
            "Changes have been applied to all modules",
        ]

        for content in completion_responses:
            is_complete = hook._check_task_complete(content, None)
            assert is_complete, f"Should detect completion in: {content}"

    def test_incompletion_phrases_detection(self):
        """Test that incompletion phrases are detected."""
        hook = RalphLoopHook()

        incompletion_responses = [
            "I'll continue with the next module",
            "Continuing with the analysis",
            "Next step is to refactor the tests",
            "Moving on to the next component",
        ]

        for content in incompletion_responses:
            is_complete = hook._check_task_complete(content, None)
            assert not is_complete, f"Should detect incompletion in: {content}"
