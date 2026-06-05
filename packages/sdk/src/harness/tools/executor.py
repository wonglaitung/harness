"""
Tool executor for running tools safely.
"""

import asyncio
from dataclasses import dataclass

from harness.tools.base import ToolContext
from harness.tools.registry import ToolRegistry
from harness.types import ToolCall, ToolResult


@dataclass
class ExecutorConfig:
    """Configuration for tool executor."""
    timeout: float = 30.0
    max_parallel: int = 10
    fail_fast: bool = False  # Stop on first failure


class ToolExecutor:
    """
    Executes tools with safety checks and timeout handling.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        config: ExecutorConfig | None = None,
    ):
        self.registry = registry
        self.config = config or ExecutorConfig()

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolContext,
    ) -> ToolResult:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call to execute
            context: Execution context

        Returns:
            ToolResult: Result of execution
        """
        tool = self.registry.get(tool_call.name)

        if tool is None:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Unknown tool: {tool_call.name}",
                tool_name=tool_call.name,
            )

        # Validate arguments
        is_valid, error = tool.validate_arguments(tool_call.arguments)
        if not is_valid:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Invalid arguments: {error}",
                tool_name=tool_call.name,
            )

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                tool.execute(tool_call.arguments, context),
                timeout=self.config.timeout,
            )
            # Ensure the tool_call_id and tool_name are set
            result.tool_call_id = tool_call.id
            result.tool_name = tool_call.name
            return result

        except TimeoutError:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Tool execution timed out after {self.config.timeout}s",
                tool_name=tool_call.name,
            )

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Tool execution failed: {str(e)}",
                tool_name=tool_call.name,
            )

    async def execute_batch(
        self,
        tool_calls: list[ToolCall],
        context: ToolContext,
    ) -> list[ToolResult]:
        """
        Execute multiple tool calls in parallel.

        Args:
            tool_calls: List of tool calls
            context: Execution context

        Returns:
            List of ToolResult objects
        """
        if not tool_calls:
            return []

        # Create tasks for parallel execution
        tasks = [
            self.execute(call, context)
            for call in tool_calls
        ]

        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        async def run_with_semaphore(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to error results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(ToolResult(
                    tool_call_id=tool_calls[i].id,
                    success=False,
                    content="",
                    error=f"Execution failed: {str(result)}",
                    tool_name=tool_calls[i].name,
                ))
            else:
                processed.append(result)

        return processed

    async def execute_sequential(
        self,
        tool_calls: list[ToolCall],
        context: ToolContext,
    ) -> list[ToolResult]:
        """
        Execute tool calls sequentially (one after another).

        Useful when tools have dependencies.

        Args:
            tool_calls: List of tool calls
            context: Execution context

        Returns:
            List of ToolResult objects
        """
        results = []
        for call in tool_calls:
            result = await self.execute(call, context)
            results.append(result)

            # Stop on failure if configured
            if self.config.fail_fast and not result.success:
                break

        return results
