"""
Tool executor for running tools safely.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

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

    **治理判定在本类内**（设计稿 §7.1 / §7.2）：所有工具调用都从这里过，
    校验发生在**参数最终态**之后（Hook 的 MODIFY_ARGS 已生效）。
    治理校验放在 Hook 里会被"首个非 CONTINUE 即返回"跳过（`core/hooks.py`），
    且放行的是改写前的参数——因此不放在 Hook。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        config: ExecutorConfig | None = None,
    ):
        self.registry = registry
        self.config = config or ExecutorConfig()
        #: 治理网关（strict 下由 `AgentHarness` 注入）。None 表示治理未启用。
        self.governance: Any | None = None

    def _governance_context(self, context: ToolContext) -> Any:
        """取本次 run 的治理上下文（随 `ToolContext.metadata` 送达，§4.4）。"""
        return context.metadata.get("governance_context")

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
        # 治理判定（流水线第 1-9 步）。校验对象是**参数最终态**。
        # 放在注册表查询**之前**：白名单判定要同时覆盖"未登记"与"不在治理块内"
        # （§7.2 第 2 步），未登记的工具不能走到执行路径。
        gov_ctx = None
        if self.governance is not None:
            gov_ctx = self._governance_context(context)
            if gov_ctx is None:
                # 运行上下文缺失 → fail-closed（§4.4：上下文是治理判定的前提）
                return ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error="治理网关拒绝：本次调用缺少运行上下文（fail-closed）",
                    tool_name=tool_call.name,
                )
            decision = self.governance.check(
                gov_ctx, tool_call.name, tool_call.arguments
            )
            if not decision.allowed:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error=f"治理网关拒绝：{decision.reason}（{decision.rule}）",
                    tool_name=tool_call.name,
                )

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
        started = time.monotonic()
        try:
            result = await asyncio.wait_for(
                tool.execute(tool_call.arguments, context),
                timeout=self.config.timeout,
            )
            # Ensure the tool_call_id and tool_name are set
            result.tool_call_id = tool_call.id
            result.tool_name = tool_call.name
            self._record_governance_result(
                gov_ctx, tool_call.name, result, started
            )
            return result

        except TimeoutError:
            self._record_governance_result(
                gov_ctx, tool_call.name, None, started, error="工具执行超时"
            )
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Tool execution timed out after {self.config.timeout}s",
                tool_name=tool_call.name,
            )

        except Exception as e:
            self._record_governance_result(
                gov_ctx, tool_call.name, None, started, error=str(e)
            )
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Tool execution failed: {str(e)}",
                tool_name=tool_call.name,
            )

    def _record_governance_result(
        self,
        gov_ctx: Any,
        tool_name: str,
        result: ToolResult | None,
        started: float,
        *,
        error: str | None = None,
    ) -> None:
        """流水线第 11 步：结果事件 + step 状态推进。"""
        if self.governance is None or gov_ctx is None:
            return
        duration_ms = int((time.monotonic() - started) * 1000)
        success = result is not None and result.success
        metadata = result.metadata if result is not None else {}
        self.governance.record_result(
            gov_ctx,
            tool_name,
            success=success,
            duration_ms=duration_ms,
            metadata=metadata,
            error=error or (result.error if result is not None else None),
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
        tasks = [self.execute(call, context) for call in tool_calls]

        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        async def run_with_semaphore(task: Any) -> Any:
            async with semaphore:
                return await task

        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to error results
        processed: list[ToolResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(
                    ToolResult(
                        tool_call_id=tool_calls[i].id,
                        success=False,
                        content="",
                        error=f"Execution failed: {str(result)}",
                        tool_name=tool_calls[i].name,
                    )
                )
            elif isinstance(result, ToolResult):
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
