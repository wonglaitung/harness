"""
Agent Loop - The core execution engine.

Implements the ReAct-style loop that drives agent behavior.
"""

from collections.abc import Callable
from dataclasses import dataclass

from harness.llm.base import LLMClient, ToolDefinition
from harness.memory.context_builder import ContextBuilder
from harness.memory.session import SessionManager
from harness.tools.executor import ToolContext, ToolExecutor
from harness.types import (
    LoopResult,
    LoopState,
    Message,
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

    async def run(
        self,
        prompt: str,
        session: Session,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> LoopResult:
        """
        Run the agent loop.

        Args:
            prompt: User input
            session: Current session
            tools: Available tools
            on_chunk: Streaming callback

        Returns:
            LoopResult: Final result
        """
        self.state = LoopState.BUILDING_CONTEXT
        self._interrupt_flag = False

        iteration = 0
        total_usage = session.token_usage

        try:
            while iteration < self.config.max_iterations:
                # Check for interruption
                if self._interrupt_flag:
                    self.state = LoopState.INTERRUPTED
                    return LoopResult(
                        status=LoopState.INTERRUPTED,
                        session=session,
                        iterations=iteration,
                    )

                # Build context
                self.state = LoopState.BUILDING_CONTEXT
                context = self.context.build(session, prompt if iteration == 0 else None)

                # Call LLM
                self.state = LoopState.CALLING_LLM
                response = await self.llm.call(
                    messages=context.messages,
                    tools=tools,
                    system=context.system_prompt,
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
        """Execute tool calls."""
        context = ToolContext(
            session_id=session.id,
            working_directory=self.tools.registry.get("__working_directory__")
            or self.tools.registry._tools.get("read", None)
            and self.tools.registry.get("read")._working_directory
            or None
            or type('obj', (object,), {})(),  # Placeholder
        )

        # Get working directory from config or use cwd
        import os
        from pathlib import Path

        from harness.tools.permissions import PermissionSet

        context = ToolContext(
            session_id=session.id,
            working_directory=Path(os.getcwd()),
            permissions=PermissionSet.sandbox(os.getcwd()),
        )

        return await self.tools.execute_batch(tool_calls, context)

    def interrupt(self) -> None:
        """Interrupt the current loop."""
        self._interrupt_flag = True
