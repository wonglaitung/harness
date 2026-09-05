"""
Integration tests for Loop Engineering.

Tests the full goal-driven execution flow from AgentHarness.run_goal().
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from harness import AgentHarness, GoalStatus


class TestRunGoalIntegration:
    """Integration tests for AgentHarness.run_goal()."""

    @pytest.mark.asyncio
    async def test_run_goal_with_custom_verifier(self):
        """Test run_goal with a custom verifier."""
        call_count = 0

        def verifier(result) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 2

        # Create mock LLM
        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        # Mock the run method
        run_count = 0

        async def mock_run(prompt, session_id=None, **kwargs):
            nonlocal run_count
            run_count += 1
            result = MagicMock()
            result.content = f"Attempt {run_count}"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Test goal",
            max_iterations=5,
            custom_verifier=verifier,
        )

        assert result.achieved is True
        assert result.status == GoalStatus.ACHIEVED
        assert result.total_iterations == 2

    @pytest.mark.asyncio
    async def test_run_goal_max_iterations(self):
        """Test run_goal stops at max iterations."""

        def always_false(result) -> bool:
            return False

        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        async def mock_run(prompt, session_id=None, **kwargs):
            result = MagicMock()
            result.content = "Progress"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Impossible goal",
            max_iterations=3,
            custom_verifier=always_false,
        )

        assert result.achieved is False
        assert result.status == GoalStatus.MAX_ITERATIONS
        assert result.total_iterations == 3

    @pytest.mark.asyncio
    async def test_run_goal_with_success_criteria(self):
        """Test run_goal with success criteria."""
        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        async def mock_run(prompt, session_id=None, **kwargs):
            result = MagicMock()
            result.content = "Done"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Fix all errors",
            success_criteria="All tests pass",
            max_iterations=5,
            custom_verifier=lambda r: True,
        )

        assert result.achieved is True
        assert result.total_iterations == 1

    @pytest.mark.asyncio
    async def test_run_goal_with_progress_callback(self):
        """Test run_goal calls progress callback."""
        progress_events = []

        def on_progress(event):
            progress_events.append(event)

        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        async def mock_run(prompt, session_id=None, **kwargs):
            result = MagicMock()
            result.content = "Progress"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Test goal",
            max_iterations=2,
            custom_verifier=lambda r: True,
            on_progress=on_progress,
        )

        assert result.achieved is True
        # Should have at least iteration and verification events
        assert len(progress_events) >= 2

    @pytest.mark.asyncio
    async def test_run_goal_with_timeout(self):
        """Test run_goal respects timeout."""

        async def slow_verifier(result):
            await asyncio.sleep(0.5)
            return False

        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        async def mock_run(prompt, session_id=None, **kwargs):
            await asyncio.sleep(0.3)  # Slow response
            result = MagicMock()
            result.content = "Progress"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Test timeout",
            max_iterations=100,
            timeout_seconds=1,
            custom_verifier=slow_verifier,
        )

        assert result.status == GoalStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_run_goal_async_verifier(self):
        """Test run_goal with async custom verifier."""
        call_count = 0

        async def async_verifier(result) -> bool:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate async work
            return call_count >= 2

        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        agent = AgentHarness(llm_client=mock_llm)

        async def mock_run(prompt, session_id=None, **kwargs):
            result = MagicMock()
            result.content = "Progress"
            result.token_usage = MagicMock(input_tokens=100, output_tokens=50)
            return result

        agent.run = mock_run

        result = await agent.run_goal(
            goal="Test async verifier",
            max_iterations=5,
            custom_verifier=async_verifier,
        )

        assert result.achieved is True
        assert result.total_iterations == 2
