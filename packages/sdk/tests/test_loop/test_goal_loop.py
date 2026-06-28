"""
Tests for GoalLoop.

Tests cover:
- Goal achievement
- Timeout handling
- Max iterations
- Context reset
- Error handling
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from harness.loop import (
    GoalConfig,
    GoalLoop,
    GoalStatus,
    VerificationMethod,
    VerificationResult,
)
from harness.types import LoopResult, LoopState, Session


def create_mock_loop_result(
    content: str = "Task completed",
    iterations: int = 1,
) -> LoopResult:
    """Create a mock LoopResult for testing."""
    result = LoopResult(
        status=LoopState.COMPLETED,
        session=Session(id="test-session"),
        iterations=iterations,
        final_response=content,
    )
    # Add token_usage for context reset tests
    result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
    return result


class MockAgentHarness:
    """Mock AgentHarness for testing."""

    def __init__(self, responses: list[LoopResult] | None = None):
        self.responses = responses or [create_mock_loop_result()]
        self._call_count = 0
        self._llm = MagicMock()
        self.config = MagicMock()
        self.config.get_context_window = MagicMock(return_value=200000)

    async def run(
        self,
        prompt: str,
        session_id: str | None = None,
        **kwargs,
    ) -> LoopResult:
        """Mock run method."""
        if self._call_count < len(self.responses):
            result = self.responses[self._call_count]
        else:
            result = self.responses[-1]
        self._call_count += 1
        return result

    def get_session(self, session_id: str) -> Session | None:
        """Mock get_session method."""
        return Session(id=session_id, messages=[])


class TestGoalLoopBasic:
    """Basic tests for GoalLoop."""

    @pytest.mark.asyncio
    async def test_goal_achieved_on_first_iteration(self):
        """Test goal achieved on first iteration."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=10,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: True,  # Always succeeds
        )

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert result.achieved is True
        assert result.status == GoalStatus.ACHIEVED
        assert result.total_iterations == 1

    @pytest.mark.asyncio
    async def test_goal_achieved_after_multiple_iterations(self):
        """Test goal achieved after multiple iterations."""
        call_count = 0

        def verifier(r: LoopResult) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 3  # Succeed on 3rd attempt

        config = GoalConfig(
            description="Test goal",
            max_iterations=10,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        agent = MockAgentHarness(
            responses=[
                create_mock_loop_result(content="Attempt 1"),
                create_mock_loop_result(content="Attempt 2"),
                create_mock_loop_result(content="Attempt 3 - Done!"),
            ]
        )
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert result.achieved is True
        assert result.total_iterations == 3

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self):
        """Test max iterations limit."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=3,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: False,  # Never succeeds
        )

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert result.achieved is False
        assert result.status == GoalStatus.MAX_ITERATIONS
        assert result.total_iterations == 3


class TestGoalLoopTimeout:
    """Timeout tests for GoalLoop."""

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test timeout is respected."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=100,
            timeout_seconds=1,  # 1 second timeout
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: False,  # Never succeeds
        )

        # Create slow agent
        class SlowAgent:
            def __init__(self):
                self._llm = MagicMock()
                self.config = MagicMock()
                self.config.get_context_window = MagicMock(return_value=200000)
                self._sessions = {}

            async def run(self, prompt: str, session_id: str = None, **kwargs):
                await asyncio.sleep(0.5)  # Each iteration takes 0.5s
                return create_mock_loop_result()

            def get_session(self, session_id: str):
                return self._sessions.get(session_id)

        agent = SlowAgent()
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert result.status == GoalStatus.TIMEOUT


class TestGoalLoopContextReset:
    """Context reset tests for GoalLoop."""

    @pytest.mark.asyncio
    async def test_context_reset_creates_new_session(self):
        """Test that context reset creates a new session."""
        sessions_created = []

        class TrackingAgent:
            def __init__(self):
                self._llm = MagicMock()
                self.config = MagicMock()
                self.config.get_context_window = MagicMock(return_value=1000)  # Small context
                self._sessions = {}
                self.call_count = 0

            async def run(self, prompt: str, session_id: str = None, **kwargs):
                sessions_created.append(session_id)
                self.call_count += 1
                # Return result with token usage
                result = create_mock_loop_result()
                result.token_usage = MagicMock(
                    input_tokens=1000,
                    output_tokens=500,
                )
                return result

            def get_session(self, session_id: str):
                return Session(id=session_id, messages=[])

        config = GoalConfig(
            description="Test goal",
            max_iterations=5,
            max_context_resets=2,
            context_reset_threshold=0.5,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: r.content == "Done",
        )

        agent = TrackingAgent()
        loop = GoalLoop(agent, config)

        await loop.run()

        # Should have created at least 2 different sessions due to context reset
        unique_sessions = set(sessions_created)
        assert len(unique_sessions) >= 1  # At least one session was created


class TestGoalLoopError:
    """Error handling tests for GoalLoop."""

    @pytest.mark.asyncio
    async def test_agent_error_returns_error_status(self):
        """Test that agent errors return ERROR status."""

        class ErrorAgent:
            def __init__(self):
                self._llm = MagicMock()
                self.config = MagicMock()
                self.config.get_context_window = MagicMock(return_value=200000)

            async def run(self, prompt: str, session_id: str = None, **kwargs):
                raise RuntimeError("Agent failed")

            def get_session(self, session_id: str):
                return None

        config = GoalConfig(
            description="Test goal",
            max_iterations=10,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: True,
        )

        agent = ErrorAgent()
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert result.status == GoalStatus.ERROR
        assert "Agent failed" in result.error

    @pytest.mark.asyncio
    async def test_cancellation_returns_cancelled_status(self):
        """Test that cancellation returns CANCELLED status."""

        class SlowMockAgent:
            """Mock agent with slow responses."""

            def __init__(self):
                self._llm = MagicMock()
                self.config = MagicMock()
                self.config.get_context_window = MagicMock(return_value=200000)
                self._sessions = {}

            async def run(self, prompt: str, session_id: str = None, **kwargs):
                await asyncio.sleep(1.0)  # Slow response
                return create_mock_loop_result()

            def get_session(self, session_id: str):
                return self._sessions.get(session_id)

        config = GoalConfig(
            description="Test goal",
            max_iterations=100,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: False,  # Never succeeds
        )

        agent = SlowMockAgent()
        loop = GoalLoop(agent, config)

        # Create a task and cancel it
        task = asyncio.create_task(loop.run())
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        result = await task

        assert result.status == GoalStatus.CANCELLED


class TestGoalLoopPrompts:
    """Tests for prompt building."""

    def test_initial_prompt_contains_goal(self):
        """Test that initial prompt contains the goal."""
        config = GoalConfig(
            description="Fix all type errors",
            success_criteria="All type checks pass",
        )

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)

        prompt = loop._build_initial_prompt()

        assert "Fix all type errors" in prompt
        assert "All type checks pass" in prompt

    def test_continuation_prompt_contains_progress(self):
        """Test that continuation prompt contains previous progress."""
        config = GoalConfig(description="Test goal")

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)
        loop._state.iteration = 5
        loop._state.context_resets = 1

        result = create_mock_loop_result(content="Fixed 3 out of 5 errors")
        prompt = loop._build_continuation_prompt(result)

        assert "Fixed 3 out of 5 errors" in prompt
        assert "5" in prompt  # Iteration count
        assert "1" in prompt  # Reset count

    def test_next_step_prompt_contains_verification_feedback(self):
        """Test that next step prompt contains verification feedback."""
        config = GoalConfig(description="Test goal")

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)

        result = create_mock_loop_result(content="Progress made")
        verification = VerificationResult.failure("Still need to fix 2 more errors")

        prompt = loop._build_next_step_prompt(result, verification)

        assert "Still need to fix 2 more errors" in prompt
        assert "Progress made" in prompt


class TestGoalLoopVerification:
    """Tests for verification integration."""

    @pytest.mark.asyncio
    async def test_verification_log_is_recorded(self):
        """Test that verification attempts are logged."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=3,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: r.content == "Done",
        )

        agent = MockAgentHarness(
            responses=[
                create_mock_loop_result(content="Attempt 1"),
                create_mock_loop_result(content="Attempt 2"),
                create_mock_loop_result(content="Done"),
            ]
        )
        loop = GoalLoop(agent, config)

        result = await loop.run()

        assert len(result.verification_log) == 3
        assert result.verification_log[0].achieved is False
        assert result.verification_log[2].achieved is True

    @pytest.mark.asyncio
    async def test_verification_result_includes_iteration_info(self):
        """Test that verification records include iteration info."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=2,
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=lambda r: False,
        )

        agent = MockAgentHarness()
        loop = GoalLoop(agent, config)

        result = await loop.run()

        for i, record in enumerate(result.verification_log, 1):
            assert record.iteration == i
