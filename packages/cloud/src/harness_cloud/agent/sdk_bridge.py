"""
SDKBridge - Integration layer between WebSocket and Harness SDK.

This module provides the core functionality to:
1. Receive WebSocket messages
2. Convert to SDK call parameters
3. Execute SDK in thread pool (avoid blocking event loop)
4. Convert ProgressEvent to WebSocket messages

Reference: packages/cloud/docs/02-agent.md
"""

from __future__ import annotations

import asyncio
import logging
import queue
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING

from harness import (
    AgentHarness,
    HarnessConfig,
    ProgressEvent,
    ProgressEventType,
    ReadTool,
    WriteTool,
    GlobTool,
    GrepTool,
    BashTool,
)

from harness_cloud.agent.config import AgentConfig
from harness_cloud.common.messages import (
    MessageType,
    MergedRequest,
    RunResult,
    StreamChunk,
    ToolCallEvent,
    ToolResultEvent,
    ProgressEventData,
    ErrorEvent,
    create_message,
)

if TYPE_CHECKING:
    from harness import LoopResult

logger = logging.getLogger(__name__)


class SDKBridge:
    """
    Bridge between WebSocket and Harness SDK.

    Core responsibilities:
    1. Receive WebSocket messages
    2. Convert to SDK call parameters
    3. Execute SDK in thread pool (avoid blocking event loop)
    4. Convert ProgressEvent to WebSocket messages
    """

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.workspace = Path(self.config.workspace)
        self.agent: AgentHarness | None = None
        self._interrupt_flag = False
        self._current_session_id: str | None = None

    def _create_agent(self, request: MergedRequest) -> AgentHarness:
        """
        Create AgentHarness instance based on request configuration.

        Args:
            request: Merged request with configuration

        Returns:
            Configured AgentHarness instance
        """
        config = HarnessConfig(
            model=request.model,
            api_key=request.api_key,
            provider=request.provider,
            base_url=request.base_url,
            max_iterations=request.max_iterations,
            temperature=request.temperature,
            system_prompt=request.system_prompt,
            sandbox_workspace=str(self.workspace),
            tool_result_role=request.tool_result_role,
        )

        tools = [
            ReadTool(),
            WriteTool(),
            GlobTool(),
            GrepTool(),
            BashTool(),
        ]

        return AgentHarness(config=config, tools=tools)

    async def run_stream(self, request: MergedRequest) -> AsyncIterator[dict[str, Any]]:
        """
        Execute task and stream events.

        Uses asyncio.to_thread() + sync queue to avoid event loop deadlocks.

        Args:
            request: Merged request with final configuration

        Yields:
            WebSocket message dictionaries
        """
        self.agent = self._create_agent(request)
        self._current_session_id = request.session_id
        self._interrupt_flag = False

        # Use sync queue (thread-safe)
        events_queue: queue.Queue = queue.Queue()

        def on_progress(event: ProgressEvent) -> None:
            """SDK progress callback - sync method."""
            events_queue.put(event)

        def run_agent_sync() -> None:
            """Sync execute agent (runs in thread pool)."""
            try:
                result = self.agent.run(  # type: ignore[misc]
                    prompt=request.prompt,
                    session_id=request.session_id,
                    on_progress=on_progress,
                )
                events_queue.put(("result", result))
            except MemoryError:
                events_queue.put(("error", "MEMORY_LIMIT"))
            except Exception as e:
                events_queue.put(("error", str(e)))

        # Run sync SDK in thread pool
        agent_task = asyncio.create_task(asyncio.to_thread(run_agent_sync))

        # Stream events
        try:
            while True:
                # Non-blocking queue check
                try:
                    item = events_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)  # Brief yield
                    continue

                if isinstance(item, tuple):
                    if item[0] == "result":
                        yield create_message(
                            MessageType.RUN_RESULT,
                            self._result_to_payload(item[1]),
                        )
                        break
                    elif item[0] == "error":
                        if item[1] == "MEMORY_LIMIT":
                            yield create_message(
                                MessageType.ERROR,
                                ErrorEvent(
                                    error="内存不足：任务需要超过限制，请减少数据量",
                                    error_code="MEMORY_LIMIT",
                                ),
                            )
                        else:
                            yield create_message(
                                MessageType.ERROR,
                                ErrorEvent(error=str(item[1])),
                            )
                        break
                else:
                    # ProgressEvent
                    yield self._translate_event(item)

        finally:
            await agent_task

    def _translate_event(self, event: ProgressEvent) -> dict[str, Any]:
        """
        Convert SDK ProgressEvent to WebSocket message.

        Args:
            event: SDK progress event

        Returns:
            WebSocket message dictionary
        """
        if event.type == ProgressEventType.TOOL_CALL:
            return create_message(
                MessageType.TOOL_CALL,
                ToolCallEvent(
                    tool_name=event.data.get("tool", ""),
                    tool_call_id=event.data.get("tool_call_id", ""),
                    arguments=event.data.get("arguments", {}),
                ),
            )

        elif event.type == ProgressEventType.TOOL_RESULT:
            result_text = event.data.get("result", "")
            # Truncate long results
            if len(result_text) > self.config.tool_result_max_length:
                result_text = result_text[: self.config.tool_result_max_length] + "..."

            return create_message(
                MessageType.TOOL_RESULT,
                ToolResultEvent(
                    tool_name=event.data.get("tool", ""),
                    success=event.data.get("success", True),
                    result=result_text,
                    error=event.data.get("error"),
                ),
            )

        elif event.type == ProgressEventType.TEXT_CHUNK:
            return create_message(
                MessageType.STREAM_CHUNK,
                StreamChunk(content=event.data.get("text", "")),
            )

        else:
            return create_message(
                MessageType.PROGRESS,
                ProgressEventData(
                    event_type=event.type.value,
                    message=event.message,
                    data=event.data,
                ),
            )

    def _result_to_payload(self, result: LoopResult) -> RunResult:
        """
        Convert LoopResult to RunResult payload.

        Args:
            result: SDK loop result

        Returns:
            RunResult payload
        """
        status = "completed"
        if result.status.value == "interrupted":
            status = "interrupted"
        elif result.status.value == "error":
            status = "error"

        return RunResult(
            status=status,
            content=result.content,
            iterations=result.iterations,
            token_usage={
                "input": result.token_usage.input_tokens,
                "output": result.token_usage.output_tokens,
            },
            error=result.error,
        )

    def interrupt(self) -> None:
        """Request execution interrupt."""
        self._interrupt_flag = True
        if self.agent:
            self.agent.interrupt()
