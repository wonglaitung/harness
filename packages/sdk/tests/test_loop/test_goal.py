"""
Tests for GoalVerifier.

Tests cover:
- Custom verifier (sync and async)
- LLM verifier
- Retry mechanism
- Error handling
"""

import asyncio

import pytest

from harness.loop import (
    GoalConfig,
    GoalVerifier,
    VerificationMethod,
    VerificationResult,
)
from harness.types import LoopResult, LoopState, Session


def create_mock_loop_result(
    content: str = "Task completed",
    iterations: int = 1,
) -> LoopResult:
    """Create a mock LoopResult for testing."""
    return LoopResult(
        status=LoopState.COMPLETED,
        session=Session(id="test-session"),
        iterations=iterations,
        final_response=content,
    )


class TestGoalVerifierCustom:
    """Tests for custom verifier."""

    def test_custom_method_without_verifier_raises_at_config(self):
        """Test that CUSTOM method without verifier raises at config time."""
        with pytest.raises(ValueError, match="custom_verifier is required"):
            GoalConfig(
                description="Test goal",
                verification_method=VerificationMethod.CUSTOM,
                custom_verifier=None,
            )

    @pytest.mark.asyncio
    async def test_sync_custom_verifier_returns_true(self):
        """Test sync custom verifier that returns True."""

        def verifier(result: LoopResult) -> bool:
            return "success" in result.content.lower()

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        goal_verifier = GoalVerifier(config)
        result = create_mock_loop_result(content="The task was a success!")

        verification = await goal_verifier.verify(result)

        assert verification.achieved is True
        assert verification.confidence == 1.0

    @pytest.mark.asyncio
    async def test_sync_custom_verifier_returns_false(self):
        """Test sync custom verifier that returns False."""

        def verifier(result: LoopResult) -> bool:
            return "done" in result.content.lower()

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        goal_verifier = GoalVerifier(config)
        result = create_mock_loop_result(content="Still working...")

        verification = await goal_verifier.verify(result)

        assert verification.achieved is False
        assert verification.confidence == 0.0

    @pytest.mark.asyncio
    async def test_async_custom_verifier(self):
        """Test async custom verifier."""

        async def verifier(result: LoopResult) -> bool:
            # Simulate async operation
            await asyncio.sleep(0.01)
            return True

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        goal_verifier = GoalVerifier(config)
        result = create_mock_loop_result()

        verification = await goal_verifier.verify(result)

        assert verification.achieved is True

    @pytest.mark.asyncio
    async def test_custom_verifier_returns_verification_result(self):
        """Test custom verifier that returns VerificationResult directly."""

        def verifier(result: LoopResult) -> VerificationResult:
            return VerificationResult.success("Custom check passed", confidence=0.8)

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        goal_verifier = GoalVerifier(config)
        result = create_mock_loop_result()

        verification = await goal_verifier.verify(result)

        assert verification.achieved is True
        assert verification.confidence == 0.8
        assert verification.reasoning == "Custom check passed"

    @pytest.mark.asyncio
    async def test_custom_verifier_exception_handling(self):
        """Test that exceptions in custom verifier are handled."""

        def verifier(result: LoopResult) -> bool:
            raise ValueError("Something went wrong")

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.CUSTOM,
            custom_verifier=verifier,
        )

        goal_verifier = GoalVerifier(config)
        result = create_mock_loop_result()

        verification = await goal_verifier.verify(result)

        assert verification.achieved is False
        assert verification.error is not None
        assert "Something went wrong" in verification.error


class TestGoalVerifierLLM:
    """Tests for LLM verifier."""

    @pytest.mark.asyncio
    async def test_llm_verifier_requires_client(self):
        """Test that LLM verifier requires an LLM client."""
        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.LLM,
        )

        # Should raise during init
        with pytest.raises(ValueError, match="LLM client is required"):
            GoalVerifier(config)

    @pytest.mark.asyncio
    async def test_llm_verifier_parses_json_response(self):
        """Test LLM verifier parses JSON response correctly."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock LLM client
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"achieved": true, "confidence": 0.9, "reasoning": "Task completed"}'
        )
        mock_llm.call = AsyncMock(return_value=mock_response)

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.LLM,
        )

        verifier = GoalVerifier(config, llm_client=mock_llm)
        result = create_mock_loop_result()

        verification = await verifier.verify(result)

        assert verification.achieved is True
        assert verification.confidence == 0.9
        assert verification.reasoning == "Task completed"

    @pytest.mark.asyncio
    async def test_llm_verifier_handles_markdown_json(self):
        """Test LLM verifier handles JSON in markdown code blocks."""
        from unittest.mock import AsyncMock, MagicMock

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        Here's my analysis:
        ```json
        {"achieved": false, "confidence": 0.6, "reasoning": "Not quite done"}
        ```
        """
        mock_llm.call = AsyncMock(return_value=mock_response)

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.LLM,
        )

        verifier = GoalVerifier(config, llm_client=mock_llm)
        result = create_mock_loop_result()

        verification = await verifier.verify(result)

        assert verification.achieved is False
        assert verification.confidence == 0.6


class TestGoalVerifierRetry:
    """Tests for retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Test that verifier retries on rate limit errors."""
        from unittest.mock import MagicMock

        mock_llm = MagicMock()

        # First call fails with rate limit, second succeeds
        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")
            mock_response = MagicMock()
            mock_response.content = '{"achieved": true, "confidence": 1.0, "reasoning": "OK"}'
            return mock_response

        mock_llm.call = mock_call

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.LLM,
            verifier_max_retries=2,
            verifier_retry_delay=0.01,  # Fast for testing
        )

        verifier = GoalVerifier(config, llm_client=mock_llm)
        result = create_mock_loop_result()

        verification = await verifier.verify(result)

        assert verification.achieved is True
        assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that verifier gives up after max retries."""
        from unittest.mock import AsyncMock, MagicMock

        mock_llm = MagicMock()
        mock_llm.call = AsyncMock(side_effect=Exception("Rate limit exceeded"))

        config = GoalConfig(
            description="Test goal",
            verification_method=VerificationMethod.LLM,
            verifier_max_retries=2,
            verifier_retry_delay=0.01,
        )

        verifier = GoalVerifier(config, llm_client=mock_llm)
        result = create_mock_loop_result()

        verification = await verifier.verify(result)

        assert verification.achieved is False
        assert verification.should_retry is False
        assert "Rate limit" in verification.error


class TestVerificationResult:
    """Tests for VerificationResult factory methods."""

    def test_success_factory(self):
        """Test success factory method."""
        result = VerificationResult.success("All good", confidence=0.9)

        assert result.achieved is True
        assert result.confidence == 0.9
        assert result.reasoning == "All good"
        assert result.should_retry is False

    def test_failure_factory(self):
        """Test failure factory method."""
        result = VerificationResult.failure("Not quite", confidence=0.3)

        assert result.achieved is False
        assert result.confidence == 0.3
        assert result.reasoning == "Not quite"

    def test_fault_factory(self):
        """Test fault factory method."""
        result = VerificationResult.fault("API error", should_retry=True)

        assert result.achieved is False
        assert result.error == "API error"
        assert result.should_retry is True
        assert "Verifier fault" in result.reasoning


class TestGoalConfig:
    """Tests for GoalConfig validation."""

    def test_valid_config(self):
        """Test that valid config is accepted."""
        config = GoalConfig(
            description="Test goal",
            max_iterations=10,
        )

        assert config.description == "Test goal"
        assert config.max_iterations == 10

    def test_empty_description_raises(self):
        """Test that empty description raises error."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            GoalConfig(description="")

    def test_invalid_max_iterations_raises(self):
        """Test that invalid max_iterations raises error."""
        with pytest.raises(ValueError, match="max_iterations must be at least 1"):
            GoalConfig(description="Test", max_iterations=0)

    def test_custom_method_without_verifier_raises(self):
        """Test that CUSTOM method without verifier raises error."""
        with pytest.raises(ValueError, match="custom_verifier is required"):
            GoalConfig(
                description="Test",
                verification_method=VerificationMethod.CUSTOM,
                custom_verifier=None,
            )
