"""
Goal Verifier - Verifies if a goal has been achieved.

This module implements the verification layer for Loop Engineering,
supporting multiple verification methods:
- LLM verification: Ask LLM to judge completion
- Custom verification: User-provided function
- Tool verification: Run tests/lint/type check (future)

Design principles:
- Stateless: All context passed via parameters
- Async-first: Supports long-running verification
- Fault-tolerant: Retry mechanism for transient failures
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from harness.loop.types import (
    GoalConfig,
    VerificationMethod,
    VerificationRecord,
    VerificationResult,
)
from harness.loop.tool_verification import run_tool_verification

if TYPE_CHECKING:
    from harness.llm.base import LLMClient
    from harness.types import LoopResult

logger = logging.getLogger(__name__)


# Default verification prompt template
DEFAULT_VERIFICATION_PROMPT = """# Goal Verification

## Original Goal
{goal}

## Success Criteria
{success_criteria}

## Agent's Final Response
{response}

## Your Task
Determine if the goal has been achieved. Respond in JSON format:
{{
    "achieved": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your judgment"
}}

Be strict but fair. Only mark as achieved if the agent has clearly completed the goal."""


class VerificationError(Exception):
    """Exception raised when verification fails."""

    def __init__(self, message: str, should_retry: bool = True):
        super().__init__(message)
        self.should_retry = should_retry


class GoalVerifier:
    """
    Verifies if a goal has been achieved.

    This class is stateless - all context is passed via parameters.
    Supports multiple verification methods with fault tolerance.

    Example:
        ```python
        verifier = GoalVerifier(config, llm_client)

        result = await verifier.verify(
            loop_result,
            context={"workspace_dir": "/tmp/worktree-a"},
        )

        if result.achieved:
            print("Goal achieved!")
        elif result.should_retry:
            print("Verifier fault, should retry")
        ```
    """

    def __init__(
        self,
        config: GoalConfig,
        llm_client: LLMClient | None = None,
    ):
        """
        Initialize the goal verifier.

        Args:
            config: Goal configuration
            llm_client: LLM client for LLM verification (optional if using custom verifier)
        """
        self.config = config
        self.llm = llm_client
        self._verification_history: list[VerificationRecord] = []

        # Validate configuration
        if config.verification_method == VerificationMethod.LLM and llm_client is None:
            raise ValueError("LLM client is required when verification_method is LLM")

    @property
    def verification_history(self) -> list[VerificationRecord]:
        """Get the history of verification attempts (read-only)."""
        return self._verification_history.copy()

    async def verify(
        self,
        result: LoopResult,
        context: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """
        Verify if the goal has been achieved.

        This method is stateless - all necessary context is passed via parameters.

        Args:
            result: The LoopResult from agent execution
            context: Additional context for verification:
                - workspace_dir: Working directory for tool verification
                - Additional metadata for custom verifiers

        Returns:
            VerificationResult with achieved status and reasoning
        """
        context = context or {}
        attempt = 0
        max_retries = self.config.verifier_max_retries
        delay = self.config.verifier_retry_delay

        while attempt <= max_retries:
            try:
                verification = await self._verify_once(result, context)

                # Record successful verification
                self._verification_history.append(
                    VerificationRecord(
                        iteration=result.iterations,
                        achieved=verification.achieved,
                        confidence=verification.confidence,
                        reasoning=verification.reasoning,
                        method=self.config.verification_method,
                    )
                )

                return verification

            except VerificationError as e:
                attempt += 1

                if attempt <= max_retries and e.should_retry:
                    logger.warning(
                        f"Verification attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.config.verifier_retry_backoff
                else:
                    # Max retries reached or non-retryable error
                    logger.error(f"Verification failed after {attempt} attempts: {e}")

                    self._verification_history.append(
                        VerificationRecord(
                            iteration=result.iterations,
                            achieved=False,
                            confidence=0.0,
                            reasoning=f"Verifier fault: {e}",
                            method=self.config.verification_method,
                            error=str(e),
                        )
                    )

                    # When max retries exceeded, should_retry is always False
                    return VerificationResult.fault(str(e), should_retry=False)

        # Should not reach here, but return fault just in case
        return VerificationResult.fault("Max retries exceeded", should_retry=False)

    async def _verify_once(
        self,
        result: LoopResult,
        context: dict[str, Any],
    ) -> VerificationResult:
        """
        Perform a single verification attempt.

        Args:
            result: The LoopResult from agent execution
            context: Additional context for verification

        Returns:
            VerificationResult

        Raises:
            VerificationError: If verification fails (for retry logic)
        """
        method = self.config.verification_method

        if method == VerificationMethod.CUSTOM:
            return await self._verify_custom(result, context)
        elif method == VerificationMethod.LLM:
            return await self._verify_llm(result, context)
        elif method == VerificationMethod.TOOL:
            return await self._verify_tool(result, context)
        else:
            raise VerificationError(f"Unknown verification method: {method}", should_retry=False)

    async def _verify_custom(
        self,
        result: LoopResult,
        context: dict[str, Any],
    ) -> VerificationResult:
        """
        Verify using custom verification function.

        Supports both sync and async custom verifiers.
        """
        verifier = self.config.custom_verifier

        if verifier is None:
            raise VerificationError("No custom verifier provided", should_retry=False)

        try:
            # Check if the verifier is async
            import asyncio

            if asyncio.iscoroutinefunction(verifier):
                achieved = await verifier(result)
            else:
                # Run sync verifier in executor to avoid blocking
                achieved = await asyncio.get_event_loop().run_in_executor(
                    None,
                    verifier,
                    result,
                )

            # Handle different return types
            if isinstance(achieved, bool):
                return VerificationResult(
                    achieved=achieved,
                    confidence=1.0 if achieved else 0.0,
                    reasoning="Custom verifier result",
                )
            elif isinstance(achieved, VerificationResult):
                return achieved
            else:
                # Assume truthy/falsy
                return VerificationResult(
                    achieved=bool(achieved),
                    confidence=0.8 if achieved else 0.2,
                    reasoning=f"Custom verifier returned: {type(achieved).__name__}",
                )

        except Exception as e:
            logger.exception(f"Custom verifier raised exception: {e}")
            raise VerificationError(f"Custom verifier error: {e}", should_retry=False) from None

    async def _verify_llm(
        self,
        result: LoopResult,
        context: dict[str, Any],
    ) -> VerificationResult:
        """
        Verify using LLM.

        Sends the goal, success criteria, and agent response to an LLM
        for verification.
        """
        if self.llm is None:
            raise VerificationError("LLM client not available", should_retry=False)

        # Build verification prompt
        prompt = self._build_verification_prompt(result)

        try:
            # Call LLM for verification
            response = await self.llm.call(
                messages=[{"role": "user", "content": prompt}],
                system="You are a goal verification assistant. Respond only in valid JSON format.",
            )

            response_text = response.content or ""

            # Parse JSON response
            verification_data = self._parse_llm_response(response_text)

            return VerificationResult(
                achieved=verification_data.get("achieved", False),
                confidence=verification_data.get("confidence", 0.5),
                reasoning=verification_data.get("reasoning", ""),
            )

        except json.JSONDecodeError as e:
            raise VerificationError(
                f"Failed to parse LLM response: {e}", should_retry=True
            ) from None
        except Exception as e:
            # Check for rate limiting or transient errors
            error_str = str(e).lower()
            should_retry = any(
                keyword in error_str for keyword in ["rate limit", "timeout", "503", "502", "429"]
            )
            raise VerificationError(
                f"LLM verification error: {e}", should_retry=should_retry
            ) from None

    async def _verify_tool(
        self,
        result: LoopResult,
        context: dict[str, Any],
    ) -> VerificationResult:
        """
        Verify using tools (tests, lint, type check).

        Runs configured verification commands in the workspace directory.
        All commands must succeed (exit code 0) for verification to pass.
        """
        tool_config = self.config.tool_verification_config

        if tool_config is None:
            raise VerificationError(
                "No tool verification config provided",
                should_retry=False,
            )

        try:
            all_passed, reasoning = await run_tool_verification(tool_config, context)

            return VerificationResult(
                achieved=all_passed,
                confidence=1.0 if all_passed else 0.9,
                reasoning=reasoning,
            )

        except Exception as e:
            # Check for retryable errors
            error_str = str(e).lower()
            should_retry = any(
                keyword in error_str
                for keyword in ["timeout", "rate limit", "503", "502"]
            )
            raise VerificationError(
                f"Tool verification error: {e}",
                should_retry=should_retry,
            ) from None

    def _build_verification_prompt(self, result: LoopResult) -> str:
        """Build the verification prompt for LLM."""
        # Truncate response if too long
        max_response_len = 2000
        response_text = result.content or ""
        if len(response_text) > max_response_len:
            response_text = response_text[:max_response_len] + "\n... (truncated)"

        return DEFAULT_VERIFICATION_PROMPT.format(
            goal=self.config.description,
            success_criteria=(
                self.config.success_criteria or "Goal is achieved when the task is complete."
            ),
            response=response_text,
        )

    def _parse_llm_response(self, response_text: str) -> dict[str, Any]:
        """
        Parse LLM response as JSON.

        Handles various response formats:
        - Pure JSON
        - JSON in markdown code blocks
        - Key-value text
        """
        # Try direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        import re

        json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_pattern, response_text)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # Try finding JSON-like content
        json_pattern2 = r"\{[\s\S]*\}"
        matches2 = re.findall(json_pattern2, response_text)

        for match in matches2:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Fallback: keyword detection
        response_lower = response_text.lower()
        achieved = any(
            keyword in response_lower for keyword in ["achieved", "completed", "success", "done"]
        ) and not any(
            keyword in response_lower for keyword in ["not achieved", "incomplete", "failed"]
        )

        return {
            "achieved": achieved,
            "confidence": 0.3,
            "reasoning": "Fallback keyword detection (JSON parse failed)",
        }

    def clear_history(self) -> None:
        """Clear verification history (for new goal execution)."""
        self._verification_history.clear()
