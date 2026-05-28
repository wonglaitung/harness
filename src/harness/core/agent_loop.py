"""
Agent Loop - The core execution engine.

Implements the ReAct-style loop that drives agent behavior.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from harness.llm.base import LLMClient, ToolDefinition
from harness.memory.context_builder import ContextBuilder
from harness.memory.session import SessionManager
from harness.tools.executor import ToolContext, ToolExecutor
from harness.types import (
    LoopResult,
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
        self._on_progress = on_progress
        self._loop_start_time = time.time()
        self._interrupt_flag = False

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

        try:
            while iteration < self.config.max_iterations:
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
            self.state = LoopState.ERROR
            self._emit_progress(
                ProgressEventType.ERROR,
                f"Error: {str(e)}",
                {"error": str(e), "type": type(e).__name__},
            )
            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=iteration,
                error=str(e),
                token_usage=total_usage,
            )

    async def _execute_tools(
        self,
        tool_calls: list[ToolCall],
        session: Session,
    ) -> list:
        """Execute tool calls with progress tracking."""
        from harness.tools.permissions import PermissionSet

        context = ToolContext(
            session_id=session.id,
            working_directory=Path(os.getcwd()),
            permissions=PermissionSet.sandbox(os.getcwd()),
        )

        results = []
        for tool_call in tool_calls:
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
