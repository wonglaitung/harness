"""
Agent Loop - The core execution engine.

Implements the ReAct-style loop that drives agent behavior.
Includes circuit breaker and error handling for production resilience.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from harness.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from harness.core.cost_controller import CostController
from harness.core.error_handler import ErrorAction, ErrorContext, ErrorDecision, ErrorHandler
from harness.core.observability import (
    SpanBuilder,
    is_tracing,
    record_token_usage,
    traced_operation,
)
from harness.llm.base import LLMClient, ToolDefinition
from harness.memory.context_builder import ContextBuilder
from harness.memory.session import SessionManager
from harness.tools.executor import ToolContext, ToolExecutor
from harness.types import (
    BudgetExceededError,
    CostConfig,
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


@dataclass
class LoopConfig:
    """Configuration for agent loop."""
    max_iterations: int = 100
    timeout_per_tool: float = 30.0
    enable_parallel_tools: bool = True
    retry_on_error: int = 3
    enable_progress: bool = True  # Enable progress events
    enable_circuit_breaker: bool = True  # Enable circuit breaker
    same_tool_threshold: int = 5  # Circuit breaker threshold
    enable_cost_control: bool = True  # Enable cost control
    cost_config: CostConfig | None = None  # Cost control configuration


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

        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                same_tool_threshold=self.config.same_tool_threshold,
            )
        ) if self.config.enable_circuit_breaker else None

        # Initialize error handler
        self._error_handler = ErrorHandler(max_retries=self.config.retry_on_error)

        # Initialize cost controller
        cost_config = self.config.cost_config or CostConfig()
        self._cost_controller = CostController(
            config=cost_config,
            on_progress=None,  # Will be set in run()
        ) if self.config.enable_cost_control else None

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
        prompt: str,
        session: Session,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """
        Run the agent loop.

        Args:
            prompt: User input
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

        self.state = LoopState.BUILDING_CONTEXT
        iteration = 0
        total_usage = session.token_usage
        self._iteration = 0  # Reset for error handler context

        try:
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
                context = self.context.build(session, prompt if iteration == 0 else None)
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
                max_llm_retries = 3
                for llm_attempt in range(max_llm_retries):
                    try:
                        response = await self.llm.call(
                            messages=context.messages,
                            tools=tools,
                            system=context.system_prompt,
                        )
                        break  # Success, exit retry loop
                    except Exception as e:
                        llm_error = e
                        error_ctx = ErrorContext(
                            error=e,
                            iteration=self._iteration,
                            context_tokens=getattr(context, 'token_count', 0),
                        )
                        decision = self._error_handler.handle(e, error_ctx)

                        if decision.action == ErrorAction.RETRY and llm_attempt < max_llm_retries - 1:
                            self._emit_progress(
                                ProgressEventType.ERROR,
                                f"LLM call failed, retrying: {decision.message}",
                                {"error": str(e), "attempt": llm_attempt + 1, "delay": decision.delay_seconds},
                            )
                            if decision.delay_seconds > 0:
                                await asyncio.sleep(decision.delay_seconds)
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

                # Add assistant message
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

                    # Add tool results to session
                    for result in tool_results:
                        tool_msg = Message(
                            role="tool",
                            content=result.content,
                            metadata={"tool_call_id": result.tool_call_id},
                        )
                        session.add_message(tool_msg)

                    iteration += 1
                    self._iteration = iteration
                    continue

                # Done!
                self.state = LoopState.COMPLETED
                session.token_usage = total_usage

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

                # Reset error handler state
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

    async def _execute_tools(
        self,
        tool_calls: list[ToolCall],
        session: Session,
    ) -> list:
        """Execute tool calls with progress tracking and circuit breaker."""
        from harness.tools.permissions import PermissionSet

        context = ToolContext(
            session_id=session.id,
            working_directory=Path(os.getcwd()),
            permissions=PermissionSet.sandbox(os.getcwd()),
        )

        results = []
        for tool_call in tool_calls:
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

            tool_start = time.time()
            result = await self.tools.execute(tool_call, context)
            tool_duration = (time.time() - tool_start) * 1000

            # Record result for circuit breaker
            if self._circuit_breaker:
                if result.success:
                    self._circuit_breaker.record_success()
                else:
                    self._circuit_breaker.record_error()

            # Emit tool result
            status = "success" if result.success else "failed"
            self._emit_progress(
                ProgressEventType.TOOL_RESULT,
                f"Tool {tool_call.name}: {status}",
                {
                    "tool": tool_call.name,
                    "tool_call_id": tool_call.id,
                    "success": result.success,
                    "error": result.error if not result.success else None,
                },
                duration_ms=tool_duration,
            )

            results.append(result)

        return results

    def interrupt(self) -> None:
        """Interrupt the current loop."""
        self._interrupt_flag = True

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

        try:
            # Execute pending tool calls if any
            if snapshot.pending_tool_calls:
                self.state = LoopState.EXECUTING_TOOLS
                tool_results = await self._execute_tools(
                    snapshot.pending_tool_calls,
                    session,
                )
                for result in tool_results:
                    tool_msg = Message(
                        role="tool",
                        content=result.content,
                        metadata={"tool_call_id": result.tool_call_id},
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
                        tool_msg = Message(
                            role="tool",
                            content=result.content,
                            metadata={"tool_call_id": result.tool_call_id},
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
