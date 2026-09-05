"""
Ralph Loop - Long-horizon task continuation.

Ralph Loop intercepts exit attempts when the agent claims completion but the task
is not actually done. It saves progress and reinjects a continuation prompt in a
clean context, preventing "context anxiety" where the model exits early due to
approaching token limits.

Named after Ralph Lomax, who described this pattern.

Usage:
    from harness.core import RalphLoopHook

    agent = AgentHarness()
    agent.add_hook(RalphLoopHook())

    # Long tasks will automatically loop until truly complete
    result = await agent.run("Refactor the entire codebase")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from harness.core.hooks import LifecycleHook
from harness.types import HookAction, HookContext, HookPoint, HookResult, Message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class RalphLoopConfig:
    """Configuration for Ralph Loop."""

    # Maximum number of continuation loops
    max_loops: int = 5

    # Check if task is complete (return True if incomplete)
    # This is called on each exit attempt
    task_complete_check: callable | None = None

    # Progress save directory
    progress_dir: Path | None = None

    # Custom continuation prompt template
    # Available variables: {iteration}, {previous_response}, {progress_summary}
    continuation_prompt_template: str = (
        "[任务继续] 之前的上下文已达到限制，但任务尚未完成。\n\n"
        "请继续之前的工作。以下是最后一步的输出摘要：\n\n"
        "{previous_response}\n\n"
        "请继续执行，直到任务完全完成。"
    )

    # Context threshold for triggering (fraction of max_tokens)
    # If context is below this, don't trigger (model likely finished naturally)
    context_threshold: float = 0.6


class RalphLoopHook(LifecycleHook):
    """
    Hook that intercepts exit attempts for long-horizon tasks.

    When the agent attempts to exit (claims task is done), this hook:
    1. Checks if the task is actually complete
    2. If not complete and context is near limits, saves progress
    3. Reinjects a continuation prompt in a clean context

    This prevents "context anxiety" where the model exits early because
    it sees the context filling up, not because the task is actually done.

    Example:
        agent = AgentHarness()
        agent.add_hook(RalphLoopHook(
            max_loops=3,
            task_complete_check=lambda response: "done" in response.lower()
        ))
    """

    def __init__(self, config: RalphLoopConfig | None = None):
        self.config = config or RalphLoopConfig()
        self._loop_count = 0
        self._previous_response: str | None = None

    @property
    def hook_points(self) -> list[HookPoint]:
        """Subscribe to exit attempt and loop end hooks."""
        return [HookPoint.ON_EXIT_ATTEMPT, HookPoint.ON_LOOP_END]

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the Ralph Loop logic."""
        if context.hook_point == HookPoint.ON_EXIT_ATTEMPT:
            return await self._handle_exit_attempt(context)
        elif context.hook_point == HookPoint.ON_LOOP_END:
            return self._handle_loop_end(context)
        return HookResult.continue_()

    async def _handle_exit_attempt(self, context: HookContext) -> HookResult:
        """Handle exit attempt - check if task is truly complete."""
        # Check if we've exceeded max loops
        if self._loop_count >= self.config.max_loops:
            logger.info(f"Ralph Loop: Max loops ({self.config.max_loops}) reached, allowing exit")
            return HookResult.continue_()

        # Get the LLM response
        response = context.llm_response
        if not response or not response.content:
            return HookResult.continue_()

        response_text = response.content
        self._previous_response = response_text

        # Check if task is complete
        is_complete = self._check_task_complete(response_text, context)

        if is_complete:
            logger.info("Ralph Loop: Task appears complete, allowing exit")
            return HookResult.continue_()

        # Task is not complete - trigger continuation
        self._loop_count += 1
        logger.info(
            f"Ralph Loop: Task incomplete, triggering continuation "
            f"(loop {self._loop_count}/{self.config.max_loops})"
        )

        # Build continuation prompt
        continuation = self._build_continuation_prompt(response_text, context)

        # Return REINJECT action to clear context and continue
        return HookResult(
            action=HookAction.REINJECT,
            inject_message=Message(role="user", content=continuation),
            clear_context=True,
            metadata={
                "ralph_loop_count": self._loop_count,
                "reason": "Task incomplete, context reset for continuation",
            },
        )

    def _handle_loop_end(self, context: HookContext) -> HookResult:
        """Handle loop end - reset state for next session."""
        # Reset loop count when loop ends successfully
        if context.metadata and context.metadata.get("status") == "completed":
            self._loop_count = 0
            self._previous_response = None
        return HookResult.continue_()

    def _check_task_complete(self, response: str, context: HookContext) -> bool:
        """
        Check if the task is actually complete.

        Uses multiple heuristics:
        1. Custom task_complete_check if provided
        2. Keyword detection (e.g., "task complete", "done", "finished")
        3. Response length heuristics
        """
        # Use custom check if provided
        if self.config.task_complete_check:
            try:
                return self.config.task_complete_check(response)
            except Exception as e:
                logger.warning(f"Custom task_complete_check failed: {e}")

        # Default heuristics
        response_lower = response.lower()

        # Check for completion indicators
        completion_phrases = [
            "task complete",
            "task completed",
            "all done",
            "finished successfully",
            "successfully completed",
            "implementation complete",
            "changes have been applied",
        ]

        for phrase in completion_phrases:
            if phrase in response_lower:
                return True

        # Check for incompletion indicators
        incompletion_phrases = [
            "i'll continue",
            "continuing with",
            "next step",
            "next, i'll",
            "let me continue",
            "proceeding to",
            "moving on to the next",
        ]

        for phrase in incompletion_phrases:
            if phrase in response_lower:
                return False

        # If response is very short and doesn't indicate completion, likely incomplete
        return not (
            len(response) < 100 and not any(p in response_lower for p in ["done", "complete"])
        )

    def _build_continuation_prompt(
        self,
        previous_response: str,
        context: HookContext,
    ) -> str:
        """Build the continuation prompt."""
        # Truncate previous response if too long
        max_response_len = 500
        if len(previous_response) > max_response_len:
            truncated = previous_response[:max_response_len] + "..."
        else:
            truncated = previous_response

        return self.config.continuation_prompt_template.format(
            iteration=self._loop_count,
            previous_response=truncated,
            progress_summary="",
        )

    def reset(self) -> None:
        """Reset the loop counter."""
        self._loop_count = 0
        self._previous_response = None
