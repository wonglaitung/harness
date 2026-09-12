"""Tests for GoalVerifier deterministic override (C4: LLM裁决覆盖)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from harness.loop.goal import GoalVerifier
from harness.loop.types import GoalConfig, VerificationMethod, VerificationResult


def _dummy_loop_result():
    """Create a minimal LoopResult for testing."""
    lr = MagicMock()
    lr.goal = "test goal"
    lr.response = "test response"
    lr.iterations = 1
    lr.messages = []
    return lr


def _mock_llm(response_json: str):
    """Create a mock LLM client that returns the given JSON."""
    llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = response_json
    llm.call = AsyncMock(return_value=mock_response)
    return llm


class TestDeterministicOverride:
    """C4: When deterministic_verifier is set alongside LLM verification,
    deterministic wins on conflict."""

    @pytest.mark.asyncio
    async def test_llm_alone_unchanged(self):
        """Without deterministic_verifier, LLM verdict stands."""
        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.9, "reasoning": "looks good"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is True
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_deterministic_overrides_llm_disagreement(self):
        """Deterministic says NOT achieved, LLM says achieved → deterministic wins."""
        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
            deterministic_verifier=lambda lr: False,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.8, "reasoning": "LLM thinks ok"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is False  # deterministic wins
        assert "deterministic override" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_deterministic_agrees_with_llm(self):
        """Both agree → no override, LLM reasoning preserved."""
        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
            deterministic_verifier=lambda lr: True,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.9, "reasoning": "LLM says ok"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is True
        # When they agree, LLM reasoning is used directly (no override prefix)
        assert "deterministic override" not in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_deterministic_fallback_to_llm_on_error(self):
        """If deterministic verifier throws, LLM verdict stands."""
        def bad_verifier(lr):
            raise RuntimeError("verifier crashed")

        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
            deterministic_verifier=bad_verifier,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.7, "reasoning": "LLM ok"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is True  # LLM verdict stands

    @pytest.mark.asyncio
    async def test_deterministic_returns_verification_result(self):
        """Deterministic verifier can return VerificationResult directly."""
        det = VerificationResult(achieved=False, confidence=1.0, reasoning="deterministic says no")

        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
            deterministic_verifier=lambda lr: det,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.5, "reasoning": "LLM unsure"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is False
        assert result.confidence == 1.0
        assert "deterministic says no" in result.reasoning

    @pytest.mark.asyncio
    async def test_deterministic_async_verifier(self):
        """Async deterministic verifier works."""
        async def async_det(lr):
            return False

        config = GoalConfig(
            description="test",
            verification_method=VerificationMethod.LLM,
            deterministic_verifier=async_det,
        )
        llm = _mock_llm('{"achieved": true, "confidence": 0.8, "reasoning": "ok"}')
        verifier = GoalVerifier(config, llm_client=llm)

        result = await verifier._verify_llm(_dummy_loop_result(), {})
        assert result.achieved is False  # deterministic wins
