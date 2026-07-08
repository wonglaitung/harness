"""
Agent Loop - The core execution engine.

Implements the ReAct-style loop that drives agent behavior.
Includes circuit breaker and error handling for production resilience.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from harness.core.cost_controller import CostController
from harness.core.error_handler import ErrorAction, ErrorContext, ErrorDecision, ErrorHandler
from harness.core.hooks import HookManager, LifecycleHook
from harness.core.observability import (
    SpanBuilder,
    is_tracing,
    record_token_usage,
    traced_operation,
)
from harness.core.output_offload import OffloadConfig, OutputOffloader
from harness.core.step_budget import StepBudgetConfig, StepBudgetController
from harness.core.stuck_detector import StuckDetector, StuckDetectorConfig, StuckDetectionResult
from harness.llm.base import LLMClient, ToolDefinition
from harness.memory.context_builder import ContextBuilder

if TYPE_CHECKING:
    from harness.sdk.config import SecurityConfig
from harness.memory.session import SessionManager
from harness.tools.executor import ToolContext, ToolExecutor
from harness.types import (
    BudgetExceededError,
    CostConfig,
    HookAction,
    HookContext,
    HookPoint,
    HookResult,
    LoopResult,
    LoopSnapshot,
    LoopState,
    Message,
    ProgressCallback,
    ProgressEvent,
    ProgressEventType,
    Session,
    ToolCall,
)

logger = logging.getLogger(__name__)


@dataclass
class LoopConfig:
    """Configuration for agent loop.

    Attributes:
        max_iterations: Maximum number of iterations (LLM calls).
            - Simple tasks (read files, answer questions): 2-3
            - Medium tasks (code analysis, multi-step reasoning): 5-7
            - Complex tasks (code generation, research): 10-15
            Default is 10 (industry standard: OpenAI Agents SDK, LangChain).
        timeout_per_tool: Timeout in seconds for each tool execution.
        enable_parallel_tools: Whether to execute tools in parallel when possible.
        retry_on_error: Number of retries on LLM API errors.
        enable_progress: Whether to emit progress events.
        enable_circuit_breaker: Whether to enable circuit breaker for tool failures.
        enable_cost_control: Whether to enable token/cost tracking.
        cost_config: Cost control configuration.
        security_config: Security configuration.
        working_directory: Working directory for tool execution.
        max_stuck_feedbacks: Maximum stuck feedback injection attempts.
        stuck_min_iterations: Minimum iterations before stuck detection.
        stuck_consecutive_failures: Consecutive failures to trigger stuck detection.
        stuck_detector_config: Semantic stuck detection configuration.
        offload_config: Output offload configuration for large tool results.
        enable_offload: Whether to enable output offloading.
        step_budget_config: Step budget configuration for fine-grained control.
        enable_step_budget: Whether to enable step budget control.
    """
    max_iterations: int = 10  # Industry standard (OpenAI Agents SDK: 10, LangChain: 10-15)
    timeout_per_tool: float = 30.0
    enable_parallel_tools: bool = True
    retry_on_error: int = 3
    enable_progress: bool = True  # Enable progress events
    enable_circuit_breaker: bool = True  # Enable circuit breaker
    enable_cost_control: bool = True  # Enable cost control
    cost_config: CostConfig | None = None  # Cost control configuration
    security_config: SecurityConfig | None = None  # Security configuration
    working_directory: str | None = None  # Working directory for tool execution

    # Stuck Detection
    max_stuck_feedbacks: int = 2  # Maximum feedback injection attempts
    stuck_min_iterations: int = 3  # Minimum iterations before stuck detection
    stuck_consecutive_failures: int = 3  # Consecutive empty/error results to trigger
    stuck_detector_config: StuckDetectorConfig | None = None  # Semantic stuck detection config

    # Tool Output Offload (Phase 24)
    offload_config: OffloadConfig | None = None  # Output offload configuration
    enable_offload: bool = True  # Enable output offloading

    # Step Budget (Phase 25)
    step_budget_config: StepBudgetConfig | None = None  # Step budget configuration
    enable_step_budget: bool = True  # Enable step budget control

    # Memory path for UpdateCoreMemoryTool
    memory_md_path: Path | None = None  # Optional path to MEMORY.md


class AgentLoop:
    """
    The core agent execution loop.

    Implements a ReAct-style loop:
    1. Build context from session
    2. Call LLM
    3. Execute tools if needed
    4. Repeat until done
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor,
        context_builder: ContextBuilder,
        session_manager: SessionManager,
        config: LoopConfig | None = None,
    ):
        self.llm = llm_client
        self.tools = tool_executor
        self.context = context_builder
        self.sessions = session_manager
        self.config = config or LoopConfig()

        self.state = LoopState.IDLE
        self._interrupt_flag = False
        self._on_progress: ProgressCallback | None = None
        self._loop_start_time: float | None = None
        self._last_event_time: float | None = None
        self._iteration = 0  # Track current iteration for error context
        self._stuck_feedback_count = 0  # Track stuck feedback injections
        self._circuit_breaker_stop_injected = False  # Track if we've injected stop message

        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker() if self.config.enable_circuit_breaker else None

        # Initialize error handler
        self._error_handler = ErrorHandler(max_retries=self.config.retry_on_error)

        # Initialize cost controller
        cost_config = self.config.cost_config or CostConfig()
        self._cost_controller = CostController(
            config=cost_config,
            on_progress=None,  # Will be set in run()
        ) if self.config.enable_cost_control else None

        # Initialize output offloader (Phase 24)
        self._offloader = OutputOffloader(
            config=self.config.offload_config or OffloadConfig(),
        ) if self.config.enable_offload else None

        # Initialize step budget controller (Phase 25)
        self._step_budget = StepBudgetController(
            config=self.config.step_budget_config or StepBudgetConfig(),
        ) if self.config.enable_step_budget else None

        # Initialize stuck detector (semantic similarity detection)
        self._stuck_detector = StuckDetector(
            config=self.config.stuck_detector_config,
        ) if self.config.stuck_detector_config else None

        # Initialize security components (lazy import to avoid circular dependency)
        from harness.security import AuditLogger, InputValidator, ResultSanitizer

        if self.config.security_config:
            sec = self.config.security_config

            self._input_validator = InputValidator(
                max_length=sec.max_input_length,
                check_injection=sec.check_prompt_injection,
            ) if sec.enable_input_validation else None

            self._sanitizer = ResultSanitizer(
                max_length=sec.max_output_length,
            ) if sec.enable_output_sanitization else None

            self._audit_logger = AuditLogger(
                log_dir=sec.audit_log_dir,
                retention_days=sec.audit_retention_days,
            ) if sec.enable_audit_log else None
        else:
            # Default: enable all security features
            self._input_validator = InputValidator()
            self._sanitizer = ResultSanitizer()
            self._audit_logger = AuditLogger()

        # Initialize hook manager
        self._hooks = HookManager()

    def add_hook(
        self,
        hook: LifecycleHook,
        points: list[HookPoint] | None = None,
    ) -> None:
        """
        Register a lifecycle hook.

        Args:
            hook: The hook to register
            points: Specific hook points (uses hook.hook_points if None)
        """
        self._hooks.register(hook, points)
        logger.debug(f"Added hook: {hook}")

    def remove_hook(self, hook: LifecycleHook) -> None:
        """
        Unregister a lifecycle hook.

        Args:
            hook: The hook to unregister
        """
        self._hooks.unregister(hook)

    def _emit_progress(
        self,
        event_type: ProgressEventType,
        message: str,
        data: dict | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Emit a progress event if callback is set."""
        if self._on_progress and self.config.enable_progress:
            event = ProgressEvent(
                type=event_type,
                message=message,
                data=data or {},
                duration_ms=duration_ms,
            )
            self._on_progress(event)
            self._last_event_time = time.time()

    async def run(
        self,
        prompt: str | list[dict[str, Any]],
        session: Session,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """
        Run the agent loop.

        Args:
            prompt: User input - can be text (str) or multimodal content (list of dicts)
                    Multimodal format: [{"type": "text", "text": "..."}, {"type": "image", ...}]
            session: Current session
            tools: Available tools
            on_chunk: Streaming callback
            on_progress: Progress event callback

        Returns:
            LoopResult: Final result
        """
        # Wrap with OpenTelemetry tracing if available
        if is_tracing():
            return await self._run_with_tracing(prompt, session, tools, on_chunk, on_progress)
        return await self._run_impl(prompt, session, tools, on_chunk, on_progress)

    async def _run_with_tracing(
        self,
        prompt: str,
        session: Session,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """Run with OpenTelemetry tracing."""
        with SpanBuilder("agent_loop.run") as span:
            span.set_attr("session.id", session.id)
            span.set_attr("prompt.length", len(prompt))
            span.set_attr("model", self.llm.model_name)

            result = await self._run_impl(prompt, session, tools, on_chunk, on_progress)

            span.set_attr("result.status", result.status.value)
            span.set_attr("result.iterations", result.iterations)
            if result.token_usage:
                record_token_usage(result.token_usage, span.span)

            return result

    async def _run_impl(
        self,
        prompt: str,
        session: Session,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """Internal implementation of run."""
        tool_names = [t.name for t in tools] if tools else []
        logger.info(f"_run_impl called, prompt length={len(prompt)}, tools={len(tools) if tools else 0}: {tool_names}")

        # Input validation
        if self._input_validator:
            validation_result = self._input_validator.validate(prompt)
            if not validation_result.valid:
                raise ValueError(f"Invalid input: {validation_result.errors}")
            if validation_result.warnings:
                self._emit_progress(
                    ProgressEventType.WARNING,
                    f"Input validation warnings: {validation_result.warnings}",
                    {"warnings": validation_result.warnings},
                )

        self._on_progress = on_progress
        self._loop_start_time = time.time()
        self._interrupt_flag = False

        # Update cost controller progress callback
        if self._cost_controller:
            self._cost_controller._on_progress = on_progress

        # Emit loop start
        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        self._emit_progress(
            ProgressEventType.LOOP_START,
            f"Starting agent loop",
            {"prompt": prompt_preview, "session_id": session.id},
        )

        # Execute ON_LOOP_START hooks
        hook_result = await self._hooks.execute_hooks(
            HookPoint.ON_LOOP_START,
            HookContext(
                hook_point=HookPoint.ON_LOOP_START,
                session_id=session.id,
                iteration=0,
            ),
        )
        if hook_result.action == HookAction.ABORT:
            self.state = LoopState.ERROR
            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                iterations=0,
                error=hook_result.metadata.get("reason", "Aborted by hook"),
            )

        self.state = LoopState.BUILDING_CONTEXT
        iteration = 0
        total_usage = session.token_usage
        self._iteration = 0  # Reset for error handler context
        self._stuck_feedback_count = 0  # Reset for stuck detection
        self._circuit_breaker_stop_injected = False  # Reset circuit breaker stop flag

        # Reset circuit breaker for new task
        # Each user message is a new task, so previous stuck behavior
        # shouldn't affect new requests
        if self._circuit_breaker:
            self._circuit_breaker.reset()

        # Start step budget task
        if self._step_budget:
            self._step_budget.start_task()

        try:
            logger.info(f"Starting loop, max_iterations={self.config.max_iterations}")
            while iteration < self.config.max_iterations:
                # Check step budget (Phase 25)
                if self._step_budget and iteration > 0:
                    budget_result = self._step_budget.advance_iteration()
                    if budget_result.should_stop:
                        self.state = LoopState.ERROR
                        self._emit_progress(
                            ProgressEventType.ERROR,
                            budget_result.message,
                            {"step_budget": self._step_budget.get_usage_report()},
                        )
                        return LoopResult(
                            status=LoopState.ERROR,
                            session=session,
                            messages=session.messages,
                            iterations=iteration,
                            error=budget_result.message,
                            token_usage=total_usage,
                        )

                # Check cost budget
                if self._cost_controller:
                    budget_status = self._cost_controller.check(total_usage, session.id)
                    if not budget_status.is_within_budget:
                        self.state = LoopState.ERROR
                        self._emit_progress(
                            ProgressEventType.ERROR,
                            budget_status.warning_message or "Budget exceeded",
                            {
                                "total_tokens": total_usage.total_tokens,
                                "limit": self._cost_controller.config.max_tokens_per_session,
                            },
                        )
                        raise BudgetExceededError(
                            budget_status.warning_message or "Budget exceeded",
                            usage=total_usage,
                            limit=self._cost_controller.config.max_tokens_per_session,
                        )

                # Emit iteration event
                self._emit_progress(
                    ProgressEventType.ITERATION,
                    f"Iteration {iteration + 1}/{self.config.max_iterations}",
                    {"iteration": iteration + 1},
                )

                # Check for interruption
                if self._interrupt_flag:
                    self.state = LoopState.INTERRUPTED
                    self._emit_progress(
                        ProgressEventType.LOOP_END,
                        "Loop interrupted",
                        {"status": "interrupted", "iterations": iteration},
                    )
                    return LoopResult(
                        status=LoopState.INTERRUPTED,
                        session=session,
                        iterations=iteration,
                    )

                # Build context
                self.state = LoopState.BUILDING_CONTEXT
                context_build_start = time.time()
                self._emit_progress(
                    ProgressEventType.STATE_CHANGE,
                    "Building context",
                    {"state": LoopState.BUILDING_CONTEXT.value},
                )
                # Add user message to session on first iteration if not already present
                # This fixes USER message loss when caller doesn't add it to session
                if iteration == 0 and prompt:
                    # Check if the last message is already the same user prompt
                    last_msg = session.messages[-1] if session.messages else None
                    if not (last_msg and last_msg.role == "user" and last_msg.content == prompt):
                        session.add_message(Message(role="user", content=prompt))

                # Remaining steps hint: warn model to wrap up when approaching iteration limit
                remaining_steps = self.config.max_iterations - iteration
                if remaining_steps <= 2 and iteration > 0:
                    session.add_message(Message(
                        role="user",
                        content=f"[系统提示] 还有 {remaining_steps} 步达到迭代上限。请立即总结当前进展并给出最终回答。",
                        metadata={"type": "remaining_steps_hint", "injected": True},
                    ))

                context = self.context.build(session)
                context_duration = (time.time() - context_build_start) * 1000

                # Call LLM
                self.state = LoopState.CALLING_LLM
                llm_call_start = time.time()
                self._emit_progress(
                    ProgressEventType.LLM_CALL,
                    f"Calling LLM: {self.llm.model_name}",
                    {"model": self.llm.model_name, "message_count": len(context.messages)},
                )

                # LLM call with error handling
                response = None
                llm_error = None
                max_llm_retries = self.config.retry_on_error or 3
                for llm_attempt in range(max_llm_retries):
                    try:
                        # Execute BEFORE_LLM_CALL hooks
                        hook_result = await self._hooks.execute_hooks(
                            HookPoint.BEFORE_LLM_CALL,
                            HookContext(
                                hook_point=HookPoint.BEFORE_LLM_CALL,
                                session_id=session.id,
                                iteration=iteration,
                                messages=context.messages,
                            ),
                        )
                        if hook_result.action == HookAction.ABORT:
                            self.state = LoopState.ERROR
                            return LoopResult(
                                status=LoopState.ERROR,
                                session=session,
                                iterations=iteration,
                                error=hook_result.metadata.get("reason", "Aborted by hook"),
                            )
                        if hook_result.action == HookAction.INJECT_MESSAGE:
                            session.add_message(hook_result.inject_message)

                        logger.info(f"Calling LLM, attempt={llm_attempt + 1}, messages={len(context.messages)}")
                        response = await self.llm.call(
                            messages=context.messages,
                            tools=tools,
                            system=context.system_prompt,
                        )
                        logger.info(f"LLM response: content_len={len(response.content) if response.content else 0}, stop_reason={response.stop_reason}, tool_calls={len(response.tool_calls) if response.tool_calls else 0}")

                        # Execute AFTER_LLM_CALL hooks
                        hook_result = await self._hooks.execute_hooks(
                            HookPoint.AFTER_LLM_CALL,
                            HookContext(
                                hook_point=HookPoint.AFTER_LLM_CALL,
                                session_id=session.id,
                                iteration=iteration,
                                llm_response=response,
                            ),
                        )
                        if hook_result.action == HookAction.ABORT:
                            self.state = LoopState.ERROR
                            return LoopResult(
                                status=LoopState.ERROR,
                                session=session,
                                iterations=iteration,
                                error=hook_result.metadata.get("reason", "Aborted by hook"),
                            )

                        break  # Success, exit retry loop
                    except Exception as e:
                        logger.exception(f"LLM call exception: {type(e).__name__}: {e}")
                        llm_error = e
                        error_ctx = ErrorContext(
                            error=e,
                            iteration=self._iteration,
                            context_tokens=getattr(context, 'token_count', 0),
                        )
                        decision = self._error_handler.handle(e, error_ctx)

                        if decision.action == ErrorAction.RETRY and llm_attempt < max_llm_retries - 1:
                            # Use ErrorHandler's delay or fallback to exponential backoff with jitter
                            if decision.delay_seconds > 0:
                                delay = decision.delay_seconds
                            else:
                                # Exponential backoff with jitter (cap at 30s)
                                import random
                                base_backoff = min(2 ** llm_attempt, 30)
                                jitter = random.uniform(0, 0.5)
                                delay = base_backoff + jitter

                            self._emit_progress(
                                ProgressEventType.ERROR,
                                f"LLM call failed, retrying: {decision.message}",
                                {"error": str(e), "attempt": llm_attempt + 1, "delay": delay},
                            )
                            await asyncio.sleep(delay)
                            continue
                        elif decision.action == ErrorAction.COMPRESS_CONTEXT:
                            self._emit_progress(
                                ProgressEventType.STATE_CHANGE,
                                "Compressing context due to error",
                                {"action": "compress_context"},
                            )
                            # Context compression would be implemented here
                            # For now, just retry with reduced context
                            continue
                        else:
                            # Abort or escalate
                            raise

                if response is None and llm_error:
                    raise llm_error

                llm_duration = (time.time() - llm_call_start) * 1000

                # Prepare response content for progress event
                response_content = response.content if response.content else ""
                # Truncate long responses for display (keep first 500 chars)
                content_preview = response_content[:500] + "..." if len(response_content) > 500 else response_content

                self._emit_progress(
                    ProgressEventType.LLM_RESPONSE,
                    f"LLM responded",
                    {
                        "stop_reason": response.stop_reason.value,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "content": content_preview,
                        "has_tool_calls": response.is_tool_use,
                        "tool_names": [tc.name for tc in response.tool_calls] if response.is_tool_use else [],
                    },
                    duration_ms=llm_duration,
                )

                # Update usage
                total_usage.input_tokens += response.usage.input_tokens
                total_usage.output_tokens += response.usage.output_tokens

                # Add assistant message (skip if content is empty and has tool calls)
                # Empty assistant messages can confuse models in compatibility mode
                if response.content or not response.is_tool_use:
                    assistant_msg = Message(
                        role="assistant",
                        content=response.content,
                    )
                    session.add_message(assistant_msg)

                # Check if we need tools
                if response.is_tool_use:
                    self.state = LoopState.EXECUTING_TOOLS
                    self._emit_progress(
                        ProgressEventType.STATE_CHANGE,
                        f"Executing {len(response.tool_calls)} tool(s)",
                        {
                            "state": LoopState.EXECUTING_TOOLS.value,
                            "tool_count": len(response.tool_calls),
                            "tools": [tc.name for tc in response.tool_calls],
                        },
                    )

                    # Execute tools
                    tool_results = await self._execute_tools(
                        response.tool_calls,
                        session,
                    )

                    # Add tool results to session (encode errors in content for stuck detection)
                    has_circuit_breaker_error = False
                    for result in tool_results:
                        content = result.content if result.success else f"Error: {result.error}"
                        # Check if this is a circuit breaker error
                        if result.error and "Circuit breaker" in result.error:
                            has_circuit_breaker_error = True
                        tool_msg = Message(
                            role="tool",
                            content=content,
                            metadata={
                                "tool_call_id": result.tool_call_id,
                                "tool_name": result.tool_name,
                                "is_error": not result.success,
                            },
                        )
                        session.add_message(tool_msg)

                    # If circuit breaker is open, inject a stop message to force the model to answer
                    if has_circuit_breaker_error and not self._circuit_breaker_stop_injected:
                        self._circuit_breaker_stop_injected = True
                        stop_message = Message(
                            role="user",
                            content="[系统强制停止] 工具调用被阻止，因为检测到重复调用相同工具。请立即停止调用工具，基于当前已有信息给出最终回答。不要再尝试调用任何工具。",
                            metadata={"type": "circuit_breaker_stop", "injected": True},
                        )
                        session.add_message(stop_message)
                        logger.info("Injected circuit breaker stop message")
                        self._emit_progress(
                            ProgressEventType.STATE_CHANGE,
                            "Circuit breaker triggered, injecting stop message",
                            {"circuit_breaker": self._circuit_breaker.stats if self._circuit_breaker else None},
                        )

                    iteration += 1
                    self._iteration = iteration

                    # Stuck detection: check if agent is making progress
                    stuck_result = await self._is_stuck(session, iteration)
                    if stuck_result.is_stuck:
                        if self._stuck_feedback_count < self.config.max_stuck_feedbacks:
                            self._stuck_feedback_count += 1
                            feedback = self._generate_stuck_feedback(
                                self._stuck_feedback_count, session, stuck_result
                            )
                            session.add_message(Message(
                                role="user",
                                content=feedback,
                                metadata={"type": "stuck_feedback", "injected": True},
                            ))
                            self._emit_progress(
                                ProgressEventType.STATE_CHANGE,
                                f"Stuck state detected at iteration {iteration} ({stuck_result.reason}), "
                                f"injecting feedback ({self._stuck_feedback_count}/{self.config.max_stuck_feedbacks})",
                                {
                                    "stuck_feedback_count": self._stuck_feedback_count,
                                    "stuck_reason": stuck_result.reason,
                                    "stuck_similarity": stuck_result.similarity,
                                },
                            )
                            # Clear stuck detector state after feedback injection
                            if self._stuck_detector:
                                self._stuck_detector.clear_session(session.id)
                        else:
                            # Feedback exhausted, terminate
                            self.state = LoopState.STUCK
                            self._emit_progress(
                                ProgressEventType.ERROR,
                                "Agent stuck: repeated failures after feedback attempts",
                                {
                                    "stuck_feedback_count": self._stuck_feedback_count,
                                    "stuck_reason": stuck_result.reason,
                                },
                            )
                            return LoopResult(
                                status=LoopState.STUCK,
                                session=session,
                                messages=session.messages,
                                iterations=iteration,
                                error="Agent stuck: repeated failures after feedback attempts",
                                token_usage=total_usage,
                            )

                    continue

                # Done!
                self.state = LoopState.COMPLETED
                session.token_usage = total_usage

                # Execute ON_EXIT_ATTEMPT hooks (for Ralph Loop)
                exit_hook_result = await self._hooks.execute_hooks(
                    HookPoint.ON_EXIT_ATTEMPT,
                    HookContext(
                        hook_point=HookPoint.ON_EXIT_ATTEMPT,
                        session_id=session.id,
                        iteration=iteration,
                        llm_response=response,
                    ),
                )
                if exit_hook_result.action == HookAction.REINJECT:
                    # Ralph Loop: clear context and reinject continuation prompt
                    self._emit_progress(
                        ProgressEventType.STATE_CHANGE,
                        "Ralph Loop: Reinjecting continuation prompt",
                        {"reason": exit_hook_result.metadata.get("reason", "Long task continuation")},
                    )
                    # Clear session messages except the first user message
                    if session.messages:
                        first_user_msg = next(
                            (m for m in session.messages if m.role == "user"),
                            None
                        )
                        session.messages.clear()
                        if first_user_msg:
                            session.add_message(first_user_msg)
                    # Add continuation prompt
                    if exit_hook_result.inject_message:
                        session.add_message(exit_hook_result.inject_message)
                    else:
                        session.add_message(Message(
                            role="user",
                            content="[继续] 请继续之前的任务。",
                        ))
                    iteration += 1
                    self._iteration = iteration
                    continue  # Continue the loop with fresh context

                # Emit completion
                total_duration = (time.time() - self._loop_start_time) * 1000
                self._emit_progress(
                    ProgressEventType.LOOP_END,
                    "Loop completed successfully",
                    {
                        "status": "completed",
                        "iterations": iteration + 1,
                        "total_tokens": total_usage.total_tokens,
                    },
                    duration_ms=total_duration,
                )

                # Execute ON_LOOP_END hooks
                await self._hooks.execute_hooks(
                    HookPoint.ON_LOOP_END,
                    HookContext(
                        hook_point=HookPoint.ON_LOOP_END,
                        session_id=session.id,
                        iteration=iteration,
                    ),
                )

                # Reset error handler state
                self._error_handler.reset()

                logger.info(f"Loop completed, iterations={iteration}, content_len={len(response.content) if response.content else 0}")
                return LoopResult(
                    status=LoopState.COMPLETED,
                    session=session,
                    messages=session.messages,
                    final_response=response.content,
                    iterations=iteration,
                    token_usage=total_usage,
                )

            # Max iterations reached
            self.state = LoopState.ERROR
            self._emit_progress(
                ProgressEventType.ERROR,
                "Max iterations reached",
                {"iterations": iteration},
            )

            # Execute ON_LOOP_END hooks
            await self._hooks.execute_hooks(
                HookPoint.ON_LOOP_END,
                HookContext(
                    hook_point=HookPoint.ON_LOOP_END,
                    session_id=session.id,
                    iteration=iteration,
                ),
            )

            # Try to extract a meaningful response from the session
            # This handles cases where the loop was interrupted mid-task
            final_response = None
            for msg in reversed(session.messages):
                if msg.role == "assistant" and msg.content:
                    final_response = msg.content
                    break

            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                final_response=final_response,
                iterations=iteration,
                error="Max iterations reached",
                token_usage=total_usage,
            )

        except Exception as e:
            logger.exception(f"Loop exception: {type(e).__name__}: {e}")

            # Execute ON_ERROR hooks
            await self._hooks.execute_hooks(
                HookPoint.ON_ERROR,
                HookContext(
                    hook_point=HookPoint.ON_ERROR,
                    session_id=session.id,
                    iteration=self._iteration,
                    error=e,
                ),
            )

            # Use ErrorHandler to determine action
            error_ctx = ErrorContext(
                error=e,
                iteration=self._iteration,
                context_tokens=total_usage.total_tokens,
            )
            decision = self._error_handler.handle(e, error_ctx)

            self.state = LoopState.ERROR
            self._emit_progress(
                ProgressEventType.ERROR,
                f"Error: {str(e)}",
                {
                    "error": str(e),
                    "type": type(e).__name__,
                    "action": decision.action.value,
                    "message": decision.message,
                },
            )

            # Execute ON_LOOP_END hooks
            await self._hooks.execute_hooks(
                HookPoint.ON_LOOP_END,
                HookContext(
                    hook_point=HookPoint.ON_LOOP_END,
                    session_id=session.id,
                    iteration=self._iteration,
                ),
            )

            # Reset error handler state
            self._error_handler.reset()

            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=self._iteration,
                error=str(e),
                token_usage=total_usage,
            )

        finally:
            # Ensure step budget task is always ended to prevent leaks
            if self._step_budget:
                try:
                    self._step_budget.end_task()
                except Exception:
                    logger.exception("Error while ending step budget task")

    async def _execute_tools(
        self,
        tool_calls: list[ToolCall],
        session: Session,
    ) -> list:
        """Execute tool calls with progress tracking and circuit breaker."""
        from harness.tools.permissions import PermissionSet, get_harness_config_dir

        # Determine memory path: use config if specified, otherwise global ~/.harness/
        memory_path = self.config.memory_md_path or get_harness_config_dir()

        context = ToolContext(
            session_id=session.id,
            working_directory=Path(self.config.working_directory or os.getcwd()),
            permissions=PermissionSet.sandbox(self.config.working_directory or os.getcwd()),
            metadata={"memory_md_path": memory_path},
        )

        results = []
        for tool_call in tool_calls:
            # Check step budget before tool call (Phase 25)
            if self._step_budget:
                budget_result = self._step_budget.check_before_tool_call(tool_call.name)
                logger.debug(f"Step budget check: {budget_result}")
                if budget_result.should_stop:
                    from harness.types import ToolResult
                    results.append(ToolResult(
                        tool_call_id=tool_call.id,
                        success=False,
                        content="",
                        error=f"Step budget exceeded: {budget_result.message}",
                        tool_name=tool_call.name,
                    ))
                    break  # 停止执行后续工具，而不是跳过当前工具

            # Check circuit breaker
            if self._circuit_breaker and self._circuit_breaker.is_open():
                reason = self._circuit_breaker.get_reason()
                self._emit_progress(
                    ProgressEventType.ERROR,
                    f"Circuit breaker open: {reason}",
                    {"circuit_breaker": self._circuit_breaker.stats},
                )
                # Return error for all remaining tools
                from harness.types import ToolResult
                results.append(ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error=f"Circuit breaker open: {reason}",
                    tool_name=tool_call.name,
                ))
                continue

            # Record call for circuit breaker
            if self._circuit_breaker:
                self._circuit_breaker.record_call(tool_call.name, tool_call.arguments)

            # Emit tool call start
            self._emit_progress(
                ProgressEventType.TOOL_CALL,
                f"Executing: {tool_call.name}",
                {
                    "tool": tool_call.name,
                    "tool_call_id": tool_call.id,
                    "arguments": tool_call.arguments,
                },
            )

            # Execute BEFORE_TOOL_EXECUTE hooks
            from harness.types import ToolResult
            hook_result = await self._hooks.execute_hooks(
                HookPoint.BEFORE_TOOL_EXECUTE,
                HookContext(
                    hook_point=HookPoint.BEFORE_TOOL_EXECUTE,
                    session_id=session.id,
                    iteration=self._iteration,
                    tool_name=tool_call.name,
                    tool_args=tool_call.arguments,
                ),
            )
            if hook_result.action == HookAction.ABORT:
                results.append(ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error=hook_result.metadata.get("reason", "Aborted by hook"),
                    tool_name=tool_call.name,
                ))
                continue
            if hook_result.action == HookAction.MODIFY_ARGS:
                tool_call.arguments = hook_result.modified_args

            tool_start = time.time()
            try:
                # Enforce timeout for tool execution
                result = await asyncio.wait_for(
                    self.tools.execute(tool_call, context),
                    timeout=self.config.timeout_per_tool,
                )
            except asyncio.TimeoutError:
                tool_duration = (time.time() - tool_start) * 1000
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error=f"Tool execution timed out after {self.config.timeout_per_tool}s",
                    tool_name=tool_call.name,
                )
                self._emit_progress(
                    ProgressEventType.ERROR,
                    f"Tool {tool_call.name} timed out",
                    {
                        "tool": tool_call.name,
                        "timeout_seconds": self.config.timeout_per_tool,
                        "duration_ms": tool_duration,
                    },
                )
            tool_duration = (time.time() - tool_start) * 1000

            # Record tool call for step budget (Phase 25)
            if self._step_budget:
                self._step_budget.record_tool_call(tool_call.name)

            # Offload large output if needed (Phase 24)
            if self._offloader and result.success and result.content:
                if self._offloader.should_offload(result.content, session.id):
                    result = self._offloader.create_offloaded_result(result, session.id)
                    self._emit_progress(
                        ProgressEventType.STATE_CHANGE,
                        f"Offloaded large output from {tool_call.name}",
                        {
                            "offloaded": True,
                            "original_size": result.metadata.get("original_size", 0),
                        },
                    )

            # Execute AFTER_TOOL_EXECUTE hooks
            hook_result = await self._hooks.execute_hooks(
                HookPoint.AFTER_TOOL_EXECUTE,
                HookContext(
                    hook_point=HookPoint.AFTER_TOOL_EXECUTE,
                    session_id=session.id,
                    iteration=self._iteration,
                    tool_name=tool_call.name,
                    tool_args=tool_call.arguments,
                    tool_result=result,
                ),
            )
            if hook_result.action == HookAction.INJECT_MESSAGE:
                session.add_message(hook_result.inject_message)
            if hook_result.action == HookAction.MODIFY_RESULT:
                result = hook_result.modified_result

            # Sanitize output
            if self._sanitizer and result.success and result.content:
                result.content = self._sanitizer.sanitize(result.content)

            # Audit log
            if self._audit_logger:
                self._audit_logger.log_tool_call(
                    session_id=session.id,
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    result="success" if result.success else "error",
                    details={"error": result.error} if result.error else None,
                )

            # Record result for circuit breaker
            if self._circuit_breaker:
                if result.success:
                    self._circuit_breaker.record_success()
                else:
                    self._circuit_breaker.record_error()

            # Emit tool result
            status = "success" if result.success else "failed"
            # Create result preview (first 200 chars)
            result_preview = ""
            if result.content:
                result_preview = str(result.content)[:200]
            elif result.error:
                result_preview = str(result.error)[:200]

            self._emit_progress(
                ProgressEventType.TOOL_RESULT,
                f"Tool {tool_call.name}: {status}",
                {
                    "tool": tool_call.name,
                    "tool_call_id": tool_call.id,
                    "success": result.success,
                    "error": result.error if not result.success else None,
                    "result": result_preview,
                    "metadata": result.metadata,  # Include tool result metadata
                },
                duration_ms=tool_duration,
            )

            results.append(result)

        return results

    def interrupt(self) -> None:
        """Interrupt the current loop."""
        self._interrupt_flag = True

    def _check_empty_error_stuck(self, session: Session, iteration: int) -> StuckDetectionResult | None:
        """
        Check for empty/error stuck pattern (zero-cost detection).

        This is the fast path that doesn't require embedding model.

        Args:
            session: Current session with message history
            iteration: Current iteration number

        Returns:
            StuckDetectionResult if stuck detected, None otherwise
        """
        if iteration < self.config.stuck_min_iterations:
            return None

        recent = session.messages[-6:]  # Last 3 rounds
        tool_msgs = [m for m in recent if m.role == "tool"]

        if len(tool_msgs) < self.config.stuck_consecutive_failures:
            return None

        n = self.config.stuck_consecutive_failures

        # Rule 1: consecutive empty results
        empty_count = sum(1 for m in tool_msgs[-n:] if not m.content.strip())
        if empty_count >= n:
            return StuckDetectionResult(
                is_stuck=True,
                reason="empty",
                details={"empty_count": empty_count},
            )

        # Rule 2: consecutive error results
        error_count = sum(1 for m in tool_msgs[-n:] if m.content.startswith("Error:"))
        if error_count >= n:
            return StuckDetectionResult(
                is_stuck=True,
                reason="error",
                details={"error_count": error_count},
            )

        return None

    async def _is_stuck(self, session: Session, iteration: int) -> StuckDetectionResult:
        """
        Detect if the agent is stuck using multiple strategies.

        Detection order (fast to slow):
        1. Empty/error detection (zero-cost)
        2. Semantic similarity detection (if enabled and model available)

        Args:
            session: Current session with message history
            iteration: Current iteration number

        Returns:
            StuckDetectionResult with detection outcome
        """
        # 1. Fast path: check empty/error patterns
        result = self._check_empty_error_stuck(session, iteration)
        if result is not None:
            return result

        # 2. Semantic detection (if enabled)
        if self._stuck_detector and self._stuck_detector.config.enable_semantic:
            result = await self._stuck_detector.check(
                session_id=session.id,
                messages=session.messages[-6:],
                iteration=iteration,
            )
            if result.is_stuck:
                return result

        return StuckDetectionResult(is_stuck=False, reason="no_stuck")

    def _generate_stuck_feedback(
        self,
        feedback_count: int,
        session: Session,
        detection_result: StuckDetectionResult | None = None,
    ) -> str:
        """
        Generate differentiated feedback based on detection result.

        Args:
            feedback_count: Which feedback attempt this is (1-based)
            session: Current session for error analysis
            detection_result: Result from stuck detection (for semantic feedback)

        Returns:
            Feedback message content
        """
        # Generate context-specific feedback
        if detection_result and detection_result.reason == "semantic_repeat":
            similarity = detection_result.similarity or 0.0
            if feedback_count == 1:
                return (
                    f"[循环检测] 检测到重复的输出模式（相似度 {similarity:.0%}）。\n"
                    "你的方法似乎在原地打转，请尝试完全不同的策略。\n"
                    "建议：\n"
                    "1. 换用其他工具或方法\n"
                    "2. 重新审视问题的核心需求\n"
                    "3. 如果已尝试多种方法，可以考虑承认无法解决"
                )
            else:
                return (
                    f"[循环检测 - 最后机会] 重复模式仍在继续（相似度 {similarity:.0%}）。\n"
                    "请立即：\n"
                    "1. 承认无法继续并说明遇到的困难，或\n"
                    "2. 采用根本性不同的方法"
                )

        # Default feedback for empty/error detection
        if feedback_count == 1:
            return (
                "[循环检测] 最近几步操作无进展（工具返回空结果或错误）。\n"
                "请尝试：\n"
                "1. 使用不同的工具或方法\n"
                "2. 调整参数或搜索策略\n"
                "3. 重新评估当前问题是否可解决"
            )

        # 2nd+ feedback: forceful, include error analysis
        error_summary = self._summarize_recent_errors(session)
        return (
            "[循环检测 - 最后机会] 已尝试调整但仍无进展。\n"
            f"观察到的问题：{error_summary}\n"
            "\n请立即：\n"
            "1. 承认无法继续并说明遇到的困难，或\n"
            "2. 采用完全不同的方法（根本性改变策略）"
        )

    def _summarize_recent_errors(self, session: Session) -> str:
        """
        Summarize error patterns in recent tool results.

        Args:
            session: Current session

        Returns:
            Human-readable summary of recent failures
        """
        recent = session.messages[-6:]
        tool_msgs = [m for m in recent if m.role == "tool"]

        parts = []
        empty = sum(1 for m in tool_msgs if not m.content.strip())
        errors = sum(1 for m in tool_msgs if m.content.startswith("Error:"))
        if empty:
            parts.append(f"空结果 {empty} 次")
        if errors:
            parts.append(f"错误 {errors} 次")

        return " | ".join(parts) if parts else "工具调用无进展"

    def create_snapshot(
        self,
        session: Session,
        iteration: int = 0,
        pending_tool_calls: list[ToolCall] | None = None,
        last_llm_response: str | None = None,
    ) -> LoopSnapshot:
        """
        Create a snapshot of the current loop state.

        Args:
            session: Current session
            iteration: Current iteration number
            pending_tool_calls: Tool calls waiting to be executed
            last_llm_response: Last response from LLM

        Returns:
            LoopSnapshot capturing current state
        """
        return LoopSnapshot(
            session_id=session.id,
            messages=session.messages.copy(),
            current_iteration=iteration,
            pending_tool_calls=pending_tool_calls or [],
            last_llm_response=last_llm_response,
        )

    async def resume_from_snapshot(
        self,
        snapshot: LoopSnapshot,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """
        Resume execution from a snapshot.

        Args:
            snapshot: Snapshot to resume from
            tools: Available tools
            on_chunk: Streaming callback
            on_progress: Progress callback

        Returns:
            LoopResult from resumed execution
        """
        # Restore session from snapshot
        session = Session(
            id=snapshot.session_id,
            messages=snapshot.messages.copy(),
        )

        self._on_progress = on_progress
        self._loop_start_time = time.time()
        self._interrupt_flag = False

        # Update cost controller progress callback
        if self._cost_controller:
            self._cost_controller._on_progress = on_progress

        # Emit resume event
        self._emit_progress(
            ProgressEventType.STATE_CHANGE,
            f"Resuming from snapshot at iteration {snapshot.current_iteration}",
            {
                "state": LoopState.BUILDING_CONTEXT.value,
                "snapshot_created_at": snapshot.created_at.isoformat(),
            },
        )

        # Continue from snapshot iteration
        self.state = LoopState.BUILDING_CONTEXT
        iteration = snapshot.current_iteration
        total_usage = session.token_usage
        self._iteration = iteration
        self._circuit_breaker_stop_injected = False  # Reset circuit breaker stop flag

        # Reset circuit breaker when restoring from snapshot
        # Resuming from a saved state is like starting a new task
        if self._circuit_breaker:
            self._circuit_breaker.reset()

        try:
            # Execute pending tool calls if any
            if snapshot.pending_tool_calls:
                self.state = LoopState.EXECUTING_TOOLS
                tool_results = await self._execute_tools(
                    snapshot.pending_tool_calls,
                    session,
                )
                for result in tool_results:
                    content = result.content if result.success else f"Error: {result.error}"
                    tool_msg = Message(
                        role="tool",
                        content=content,
                        metadata={
                            "tool_call_id": result.tool_call_id,
                            "is_error": not result.success,
                        },
                    )
                    session.add_message(tool_msg)
                iteration += 1
                self._iteration = iteration

            # Continue the loop
            while iteration < self.config.max_iterations:
                # Check cost budget
                if self._cost_controller:
                    budget_status = self._cost_controller.check(total_usage, session.id)
                    if not budget_status.is_within_budget:
                        self.state = LoopState.ERROR
                        self._emit_progress(
                            ProgressEventType.ERROR,
                            budget_status.warning_message or "Budget exceeded",
                            {
                                "total_tokens": total_usage.total_tokens,
                                "limit": self._cost_controller.config.max_tokens_per_session,
                            },
                        )
                        raise BudgetExceededError(
                            budget_status.warning_message or "Budget exceeded",
                            usage=total_usage,
                            limit=self._cost_controller.config.max_tokens_per_session,
                        )

                # Check for interruption
                if self._interrupt_flag:
                    self.state = LoopState.INTERRUPTED
                    self._emit_progress(
                        ProgressEventType.LOOP_END,
                        "Loop interrupted",
                        {"status": "interrupted", "iterations": iteration},
                    )
                    return LoopResult(
                        status=LoopState.INTERRUPTED,
                        session=session,
                        iterations=iteration,
                    )

                # Build context
                self.state = LoopState.BUILDING_CONTEXT
                context = self.context.build(session)

                # Call LLM
                self.state = LoopState.CALLING_LLM
                llm_call_start = time.time()
                self._emit_progress(
                    ProgressEventType.LLM_CALL,
                    f"Calling LLM: {self.llm.model_name}",
                    {"model": self.llm.model_name, "message_count": len(context.messages)},
                )

                response = await self.llm.call(
                    messages=context.messages,
                    tools=tools,
                    system=context.system_prompt,
                )

                llm_duration = (time.time() - llm_call_start) * 1000
                self._emit_progress(
                    ProgressEventType.LLM_RESPONSE,
                    f"LLM responded",
                    {
                        "stop_reason": response.stop_reason.value,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                    duration_ms=llm_duration,
                )

                # Update usage
                total_usage.input_tokens += response.usage.input_tokens
                total_usage.output_tokens += response.usage.output_tokens

                # Add assistant message
                assistant_msg = Message(role="assistant", content=response.content)
                session.add_message(assistant_msg)

                # Check if we need tools
                if response.is_tool_use:
                    self.state = LoopState.EXECUTING_TOOLS
                    tool_results = await self._execute_tools(response.tool_calls, session)

                    for result in tool_results:
                        content = result.content if result.success else f"Error: {result.error}"
                        tool_msg = Message(
                            role="tool",
                            content=content,
                            metadata={
                                "tool_call_id": result.tool_call_id,
                                "is_error": not result.success,
                            },
                        )
                        session.add_message(tool_msg)

                    iteration += 1
                    self._iteration = iteration
                    continue

                # Done!
                self.state = LoopState.COMPLETED
                session.token_usage = total_usage

                total_duration = (time.time() - self._loop_start_time) * 1000
                self._emit_progress(
                    ProgressEventType.LOOP_END,
                    "Loop completed successfully",
                    {
                        "status": "completed",
                        "iterations": iteration + 1,
                        "total_tokens": total_usage.total_tokens,
                    },
                    duration_ms=total_duration,
                )

                self._error_handler.reset()

                return LoopResult(
                    status=LoopState.COMPLETED,
                    session=session,
                    messages=session.messages,
                    final_response=response.content,
                    iterations=iteration,
                    token_usage=total_usage,
                )

            # Max iterations reached
            self.state = LoopState.ERROR
            self._emit_progress(
                ProgressEventType.ERROR,
                "Max iterations reached",
                {"iterations": iteration},
            )
            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=iteration,
                error="Max iterations reached",
                token_usage=total_usage,
            )

        except Exception as e:
            error_ctx = ErrorContext(
                error=e,
                iteration=self._iteration,
                context_tokens=total_usage.total_tokens,
            )
            decision = self._error_handler.handle(e, error_ctx)

            self.state = LoopState.ERROR
            self._emit_progress(
                ProgressEventType.ERROR,
                f"Error: {str(e)}",
                {
                    "error": str(e),
                    "type": type(e).__name__,
                    "action": decision.action.value,
                },
            )

            self._error_handler.reset()

            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=self._iteration,
                error=str(e),
                token_usage=total_usage,
            )
