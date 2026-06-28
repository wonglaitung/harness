"""
Goal Loop - Goal-driven execution loop.

This module implements the core execution loop for Loop Engineering,
where an agent runs autonomously until a goal is achieved.

Key features:
- Iteration control with max limits
- Context reset to prevent "context anxiety"
- Timeout handling
- Cost control
- Progress reporting
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from harness.loop.goal import GoalVerifier
from harness.loop.types import (
    GoalConfig,
    GoalResult,
    GoalStatus,
    VerificationRecord,
    VerificationResult,
)

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness
    from harness.types import LoopResult, ProgressCallback

logger = logging.getLogger(__name__)


# Prompt templates
INITIAL_PROMPT_TEMPLATE = """# Goal: {goal}

Please work towards achieving this goal. You can use tools to make progress.

## Success Criteria
{success_criteria}

## Instructions
1. Break down the goal into actionable steps
2. Use tools to make progress
3. Verify your work at each step
4. Continue until the goal is fully achieved

Take action and report your progress. Continue until the goal is achieved."""


CONTINUATION_PROMPT_TEMPLATE = """# Goal Continuation

The previous context was reset due to size limits. Continue working towards the goal.

## Original Goal
{goal}

## Previous Progress
{previous_response}

## Current Status
- Iterations completed: {iterations}
- Context resets: {resets}

## Instructions
Continue from where you left off. Focus on completing the remaining work.
Do not repeat what was already done. Proceed with the next steps."""


NEXT_STEP_PROMPT_TEMPLATE = """The goal is not yet achieved.

## Verification Feedback
{verification_reasoning}

## Current Progress
{progress}

## What's Still Needed
Based on the verification feedback, continue working towards:
{goal}

Take the next step to make progress. Focus on what remains to be done."""


@dataclass
class GoalLoopState:
    """State tracked during goal execution."""

    iteration: int = 0
    context_resets: int = 0
    start_time: float = 0.0
    session_id: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    verification_log: list[VerificationRecord] = field(default_factory=list)


class GoalLoop:
    """
    Goal-driven execution loop.

    Continues execution until one of the following:
    1. Goal is achieved (verified)
    2. Max iterations reached
    3. Max context resets reached
    4. Timeout exceeded
    5. Error occurs

    Example:
        ```python
        agent = AgentHarness()
        config = GoalConfig(description="Fix all type errors")

        loop = GoalLoop(agent, config)
        result = await loop.run()

        if result.achieved:
            print(f"Goal achieved in {result.total_iterations} iterations")
        ```
    """

    def __init__(
        self,
        agent: AgentHarness,
        config: GoalConfig,
        on_progress: ProgressCallback | None = None,
    ):
        """
        Initialize the goal loop.

        Args:
            agent: The AgentHarness instance to use
            config: Goal configuration
            on_progress: Optional progress callback
        """
        self.agent = agent
        self.config = config
        self.on_progress = on_progress

        # Initialize verifier
        self.verifier = GoalVerifier(config, agent._llm if hasattr(agent, "_llm") else None)

        # State tracking
        self._state = GoalLoopState()

    async def run(self) -> GoalResult:
        """
        Run the goal-driven loop.

        Returns:
            GoalResult with execution status and details
        """
        # Initialize state
        self._state = GoalLoopState(
            iteration=0,
            context_resets=0,
            start_time=time.time(),
            session_id=f"goal-{uuid.uuid4().hex[:8]}",
        )

        # Build initial prompt
        current_prompt = self._build_initial_prompt()

        logger.info(f"Starting goal loop: {self.config.description[:100]}...")

        try:
            while True:
                # Check timeout
                if self._check_timeout():
                    return self._create_result(GoalStatus.TIMEOUT)

                # Check max iterations
                if self._state.iteration >= self.config.max_iterations:
                    logger.warning(f"Max iterations ({self.config.max_iterations}) reached")
                    return self._create_result(GoalStatus.MAX_ITERATIONS)

                # Check max context resets
                if self._state.context_resets > self.config.max_context_resets:
                    logger.warning(
                        f"Max context resets ({self.config.max_context_resets}) exceeded"
                    )
                    return self._create_result(GoalStatus.MAX_RESETS)

                # Emit progress
                self._emit_progress(
                    "iteration",
                    f"Iteration {self._state.iteration + 1}/{self.config.max_iterations}",
                    {
                        "iteration": self._state.iteration + 1,
                        "context_resets": self._state.context_resets,
                    },
                )

                # Run agent
                logger.debug(f"Running agent iteration {self._state.iteration + 1}")
                result = await self.agent.run(
                    prompt=current_prompt,
                    session_id=self._state.session_id,
                )

                self._state.iteration += 1

                # Update token usage
                if result.token_usage:
                    self._state.total_input_tokens += result.token_usage.input_tokens
                    self._state.total_output_tokens += result.token_usage.output_tokens

                # Check cost control
                if self._check_cost_exceeded():
                    return self._create_result(GoalStatus.ERROR, error="Cost budget exceeded")

                # Verify goal
                verification = await self._verify_goal(result)

                if verification.achieved:
                    logger.info(f"Goal achieved after {self._state.iteration} iterations")
                    return self._create_result(GoalStatus.ACHIEVED, result=result)

                # Check if we need context reset
                if self._should_reset_context(result):
                    self._state.context_resets += 1
                    logger.info(
                        f"Context reset {self._state.context_resets}/"
                        f"{self.config.max_context_resets}"
                    )

                    # Create new session for fresh context
                    self._state.session_id = f"goal-{uuid.uuid4().hex[:8]}"
                    current_prompt = self._build_continuation_prompt(result)

                    self._emit_progress(
                        "context_reset",
                        "Resetting context to prevent overflow",
                        {"reset_count": self._state.context_resets},
                    )
                else:
                    # Continue in same session
                    current_prompt = self._build_next_step_prompt(result, verification)

                # Let other tasks run (prevent event loop blocking)
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Goal loop cancelled")
            return self._create_result(GoalStatus.CANCELLED)

        except Exception as e:
            logger.exception(f"Goal loop error: {e}")
            return self._create_result(GoalStatus.ERROR, error=str(e))

    async def _verify_goal(self, result: LoopResult) -> VerificationResult:
        """Verify if the goal has been achieved."""
        verification = await self.verifier.verify(
            result,
            context={"workspace_dir": self.config.workspace_dir},
        )

        # Record verification
        record = VerificationRecord(
            iteration=self._state.iteration,
            achieved=verification.achieved,
            confidence=verification.confidence,
            reasoning=verification.reasoning,
        )
        self._state.verification_log.append(record)

        self._emit_progress(
            "verification",
            f"Verification: {'achieved' if verification.achieved else 'not achieved'}",
            {
                "achieved": verification.achieved,
                "confidence": verification.confidence,
                "reasoning": verification.reasoning[:200] if verification.reasoning else None,
            },
        )

        return verification

    def _should_reset_context(self, result: LoopResult) -> bool:
        """
        Determine if context should be reset.

        Context is reset when:
        1. Token usage approaches model limit
        2. Session has many messages (heuristic)
        """
        # Check token usage ratio
        if result.token_usage and hasattr(self.agent, "config"):
            context_window = self.agent.config.get_context_window()
            if context_window > 0:
                used_tokens = self._state.total_input_tokens + self._state.total_output_tokens
                ratio = used_tokens / context_window
                if ratio >= self.config.context_reset_threshold:
                    logger.debug(f"Context reset triggered: {ratio:.1%} of context used")
                    return True

        # Check message count (fallback heuristic)
        session = self.agent.get_session(self._state.session_id)
        if session and len(session.messages) > 50:
            logger.debug(f"Context reset triggered: {len(session.messages)} messages")
            return True

        return False

    def _check_timeout(self) -> bool:
        """Check if execution has exceeded timeout."""
        elapsed = time.time() - self._state.start_time
        return elapsed >= self.config.timeout_seconds

    def _check_cost_exceeded(self) -> bool:
        """Check if cost budget has been exceeded."""
        if self.config.max_tokens is None and self.config.max_cost_usd is None:
            return False

        total_tokens = self._state.total_input_tokens + self._state.total_output_tokens

        # Check token budget
        exceeded = self.config.max_tokens is not None and total_tokens >= self.config.max_tokens

        # Check cost budget (USD)
        # TODO: Implement cost tracking when pricing info is available

        return exceeded

    def _create_result(
        self,
        status: GoalStatus,
        result: LoopResult | None = None,
        error: str | None = None,
    ) -> GoalResult:
        """Create a GoalResult from the current state."""
        duration = time.time() - self._state.start_time

        return GoalResult(
            goal=self.config.description,
            status=status,
            total_iterations=self._state.iteration,
            context_resets=self._state.context_resets,
            total_tokens={
                "input": self._state.total_input_tokens,
                "output": self._state.total_output_tokens,
            },
            duration_seconds=duration,
            final_response=result.content if result else "",
            session=self.agent.get_session(self._state.session_id) if result else None,
            verification_log=self._state.verification_log,
            error=error,
        )

    def _build_initial_prompt(self) -> str:
        """Build the initial prompt for goal execution."""
        return INITIAL_PROMPT_TEMPLATE.format(
            goal=self.config.description,
            success_criteria=(
                self.config.success_criteria
                or "Goal is achieved when the task is complete and verified."
            ),
        )

    def _build_continuation_prompt(self, result: LoopResult) -> str:
        """Build continuation prompt after context reset."""
        # Truncate previous response if too long
        max_response_len = 1000
        previous_response = result.content or ""
        if len(previous_response) > max_response_len:
            previous_response = previous_response[:max_response_len] + "\n... (truncated)"

        return CONTINUATION_PROMPT_TEMPLATE.format(
            goal=self.config.description,
            previous_response=previous_response,
            iterations=self._state.iteration,
            resets=self._state.context_resets,
        )

    def _build_next_step_prompt(
        self,
        result: LoopResult,
        verification: VerificationResult,
    ) -> str:
        """Build prompt for next iteration."""
        # Truncate progress if too long
        max_progress_len = 500
        progress = result.content or ""
        if len(progress) > max_progress_len:
            progress = progress[:max_progress_len] + "\n... (truncated)"

        return NEXT_STEP_PROMPT_TEMPLATE.format(
            goal=self.config.description,
            verification_reasoning=verification.reasoning,
            progress=progress,
        )

    def _emit_progress(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit a progress event if callback is set."""
        if self.on_progress is None:
            return

        from harness.types import ProgressEvent, ProgressEventType

        # Map event types
        type_map = {
            "iteration": ProgressEventType.ITERATION,
            "context_reset": ProgressEventType.STATE_CHANGE,
            "verification": ProgressEventType.STATE_CHANGE,
        }

        event = ProgressEvent(
            type=type_map.get(event_type, ProgressEventType.STATE_CHANGE),
            message=message,
            data=data or {},
        )

        self.on_progress(event)
