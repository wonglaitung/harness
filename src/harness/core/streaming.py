"""
Streaming handler with backpressure control.

Manages streaming output from LLM with buffer management and backpressure.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from harness.types import Chunk, ChunkType, ProgressEventType

if TYPE_CHECKING:
    from harness.types import ProgressCallback, ProgressEvent

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for streaming handler."""
    buffer_size: int = 8192  # Max chunks in buffer
    backpressure_threshold: float = 0.9  # Trigger backpressure at 90% capacity
    pause_on_backpressure: bool = True  # Pause upstream on backpressure
    max_pause_duration: float = 5.0  # Max seconds to pause (seconds)


@dataclass
class StreamingStats:
    """Statistics for streaming session."""
    chunks_received: int = 0
    chunks_processed: int = 0
    backpressure_events: int = 0
    total_pause_time: float = 0.0
    buffer_high_watermark: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if streaming is healthy (no excessive backpressure)."""
        return self.backpressure_events < 10


class StreamingHandler:
    """
    Handles streaming output with buffer management and backpressure control.

    Features:
    - Buffer management with configurable size
    - Backpressure detection and handling
    - Progress event emission on backpressure
    - Support for different chunk types

    Example:
        >>> handler = StreamingHandler(on_progress=my_callback)
        >>> async for chunk in llm.stream(messages):
        ...     await handler.handle(chunk)
        ...     if handler.should_pause:
        ...         await asyncio.sleep(0.1)
        >>> content = handler.get_full_content()
    """

    def __init__(
        self,
        config: StreamingConfig | None = None,
        on_progress: "ProgressCallback | None" = None,
        on_chunk: Callable[[Chunk], None] | None = None,
    ):
        self.config = config or StreamingConfig()
        self._on_progress = on_progress
        self._on_chunk = on_chunk

        # Buffer for chunks
        self._buffer: deque[Chunk] = deque(maxlen=self.config.buffer_size)

        # State
        self._is_paused = False
        self._stats = StreamingStats()

        # Accumulated content
        self._text_content: list[str] = []
        self._tool_calls: dict[str, dict[str, Any]] = {}

    @property
    def buffer_size(self) -> int:
        """Current buffer size."""
        return len(self._buffer)

    @property
    def buffer_usage(self) -> float:
        """Buffer usage ratio (0.0 to 1.0)."""
        return len(self._buffer) / self.config.buffer_size

    @property
    def should_pause(self) -> bool:
        """Check if upstream should pause due to backpressure."""
        return self._is_paused or self.buffer_usage >= self.config.backpressure_threshold

    @property
    def stats(self) -> StreamingStats:
        """Get streaming statistics."""
        return self._stats

    async def handle(self, chunk: Chunk) -> None:
        """
        Handle an incoming chunk.

        Args:
            chunk: The chunk to process
        """
        self._stats.chunks_received += 1

        # Add to buffer
        self._buffer.append(chunk)

        # Update high watermark
        if len(self._buffer) > self._stats.buffer_high_watermark:
            self._stats.buffer_high_watermark = len(self._buffer)

        # Check for backpressure
        if self.config.pause_on_backpressure and self.should_pause:
            await self._apply_backpressure()

        # Process chunk
        self._process_chunk(chunk)

        # Call custom handler
        if self._on_chunk:
            self._on_chunk(chunk)

        self._stats.chunks_processed += 1

    def _process_chunk(self, chunk: Chunk) -> None:
        """Process a chunk based on its type."""
        if chunk.type == ChunkType.TEXT:
            self._text_content.append(chunk.content)

        elif chunk.type == ChunkType.TOOL_CALL_START:
            self._tool_calls[chunk.tool_call_id or ""] = {
                "name": chunk.tool_name,
                "arguments": {},
            }

        elif chunk.type == ChunkType.TOOL_CALL_DELTA:
            if chunk.tool_call_id in self._tool_calls:
                self._tool_calls[chunk.tool_call_id]["arguments"].update(
                    chunk.tool_arguments
                )

        elif chunk.type == ChunkType.ERROR:
            logger.error(f"Stream error: {chunk.content}")

    async def _apply_backpressure(self) -> None:
        """Apply backpressure by pausing."""
        self._is_paused = True
        self._stats.backpressure_events += 1

        # Emit progress event
        if self._on_progress:
            from harness.types import ProgressEvent
            self._on_progress(ProgressEvent(
                type=ProgressEventType.STREAM_BACKPRESSURE,
                message=f"Backpressure applied: buffer at {self.buffer_usage:.0%}",
                data={
                    "buffer_size": len(self._buffer),
                    "buffer_max": self.config.buffer_size,
                    "usage": self.buffer_usage,
                },
            ))

        # Wait for buffer to drain
        pause_start = asyncio.get_event_loop().time()

        while self.buffer_usage > self.config.backpressure_threshold * 0.5:
            await asyncio.sleep(0.01)

            # Check max pause duration
            elapsed = asyncio.get_event_loop().time() - pause_start
            if elapsed > self.config.max_pause_duration:
                logger.warning("Max pause duration exceeded, resuming")
                break

        self._stats.total_pause_time += asyncio.get_event_loop().time() - pause_start
        self._is_paused = False

    def get_full_content(self) -> str:
        """
        Get accumulated text content.

        Returns:
            All text content received so far
        """
        return "".join(self._text_content)

    def get_tool_calls(self) -> list[dict[str, Any]]:
        """
        Get accumulated tool calls.

        Returns:
            List of tool call dictionaries with name and arguments
        """
        return [
            {"id": id_, **data}
            for id_, data in self._tool_calls.items()
        ]

    def clear(self) -> None:
        """Clear buffer and accumulated content."""
        self._buffer.clear()
        self._text_content.clear()
        self._tool_calls.clear()
        self._is_paused = False

    def __repr__(self) -> str:
        return (
            f"<StreamingHandler buffer={len(self._buffer)}/{self.config.buffer_size} "
            f"usage={self.buffer_usage:.0%}>"
        )
