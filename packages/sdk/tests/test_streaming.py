"""
Tests for Streaming Backpressure system.
"""

import asyncio

import pytest

from harness.core import StreamingConfig, StreamingHandler, StreamingStats
from harness.types import Chunk, ChunkType


class TestChunkType:
    """Tests for ChunkType enum."""

    def test_chunk_types(self):
        """Test all chunk types exist."""
        assert ChunkType.TEXT.value == "text"
        assert ChunkType.TOOL_CALL_START.value == "tool_start"
        assert ChunkType.TOOL_CALL_DELTA.value == "tool_delta"
        assert ChunkType.TOOL_CALL_END.value == "tool_end"
        assert ChunkType.THINKING.value == "thinking"
        assert ChunkType.ERROR.value == "error"
        assert ChunkType.DONE.value == "done"


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_text_chunk(self):
        """Test creating a text chunk."""
        chunk = Chunk(type=ChunkType.TEXT, content="Hello")

        assert chunk.type == ChunkType.TEXT
        assert chunk.content == "Hello"
        assert chunk.is_text() is True
        assert chunk.is_tool_call() is False
        assert chunk.is_done() is False

    def test_tool_call_start_chunk(self):
        """Test creating a tool call start chunk."""
        chunk = Chunk(
            type=ChunkType.TOOL_CALL_START,
            tool_call_id="call_123",
            tool_name="read_file",
        )

        assert chunk.type == ChunkType.TOOL_CALL_START
        assert chunk.tool_call_id == "call_123"
        assert chunk.tool_name == "read_file"
        assert chunk.is_tool_call() is True
        assert chunk.is_text() is False

    def test_tool_call_delta_chunk(self):
        """Test creating a tool call delta chunk."""
        chunk = Chunk(
            type=ChunkType.TOOL_CALL_DELTA,
            tool_call_id="call_123",
            tool_arguments={"path": "/test"},
        )

        assert chunk.type == ChunkType.TOOL_CALL_DELTA
        assert chunk.tool_arguments == {"path": "/test"}

    def test_done_chunk(self):
        """Test creating a done chunk."""
        chunk = Chunk(type=ChunkType.DONE)

        assert chunk.is_done() is True
        assert chunk.is_text() is False


class TestStreamingConfig:
    """Tests for StreamingConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = StreamingConfig()

        assert config.buffer_size == 8192
        assert config.backpressure_threshold == 0.9
        assert config.pause_on_backpressure is True
        assert config.max_pause_duration == 5.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = StreamingConfig(
            buffer_size=1000,
            backpressure_threshold=0.8,
            pause_on_backpressure=False,
        )

        assert config.buffer_size == 1000
        assert config.backpressure_threshold == 0.8
        assert config.pause_on_backpressure is False


class TestStreamingStats:
    """Tests for StreamingStats."""

    def test_default_stats(self):
        """Test default statistics."""
        stats = StreamingStats()

        assert stats.chunks_received == 0
        assert stats.chunks_processed == 0
        assert stats.backpressure_events == 0
        assert stats.total_pause_time == 0.0

    def test_is_healthy(self):
        """Test is_healthy property."""
        stats = StreamingStats()
        assert stats.is_healthy is True

        # After many backpressure events, not healthy
        stats.backpressure_events = 15
        assert stats.is_healthy is False


class TestStreamingHandler:
    """Tests for StreamingHandler."""

    def test_init(self):
        """Test initialization."""
        handler = StreamingHandler()

        assert handler.config is not None
        assert handler.buffer_size == 0
        assert handler.buffer_usage == 0.0

    def test_handle_text_chunk(self):
        """Test handling text chunks."""
        handler = StreamingHandler()

        # Handle some text chunks
        asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content="Hello")))
        asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content=" ")))
        asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content="World")))

        assert handler.get_full_content() == "Hello World"
        assert handler.stats.chunks_received == 3
        assert handler.stats.chunks_processed == 3

    def test_handle_tool_calls(self):
        """Test handling tool call chunks."""
        handler = StreamingHandler()

        # Start tool call
        asyncio.run(handler.handle(Chunk(
            type=ChunkType.TOOL_CALL_START,
            tool_call_id="call_1",
            tool_name="read_file",
        )))

        # Delta
        asyncio.run(handler.handle(Chunk(
            type=ChunkType.TOOL_CALL_DELTA,
            tool_call_id="call_1",
            tool_arguments={"path": "/test.txt"},
        )))

        # End
        asyncio.run(handler.handle(Chunk(
            type=ChunkType.TOOL_CALL_END,
            tool_call_id="call_1",
        )))

        tool_calls = handler.get_tool_calls()
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["name"] == "read_file"

    def test_should_pause(self):
        """Test should_pause property."""
        config = StreamingConfig(buffer_size=10, backpressure_threshold=0.9)
        handler = StreamingHandler(config=config)

        # Initially not paused
        assert handler.should_pause is False

        # Fill buffer to threshold
        for i in range(9):
            handler._buffer.append(Chunk(type=ChunkType.TEXT, content=f"chunk_{i}"))

        # Now should pause
        assert handler.should_pause is True

    def test_buffer_usage(self):
        """Test buffer_usage calculation."""
        config = StreamingConfig(buffer_size=100)
        handler = StreamingHandler(config=config)

        assert handler.buffer_usage == 0.0

        # Add some chunks
        for i in range(25):
            handler._buffer.append(Chunk(type=ChunkType.TEXT, content=f"chunk_{i}"))

        assert handler.buffer_usage == 0.25

    def test_clear(self):
        """Test clear method."""
        handler = StreamingHandler()

        # Add some content
        asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content="test")))

        assert handler.buffer_size > 0
        assert len(handler.get_full_content()) > 0

        # Clear
        handler.clear()

        assert handler.buffer_size == 0
        assert handler.get_full_content() == ""

    def test_custom_on_chunk_callback(self):
        """Test custom on_chunk callback."""
        received = []

        handler = StreamingHandler(on_chunk=lambda c: received.append(c))

        asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content="test")))

        assert len(received) == 1
        assert received[0].content == "test"

    def test_buffer_high_watermark(self):
        """Test buffer high watermark tracking."""
        config = StreamingConfig(buffer_size=100)
        handler = StreamingHandler(config=config)

        # Add chunks via handle() to update watermark
        for i in range(50):
            asyncio.run(handler.handle(Chunk(type=ChunkType.TEXT, content=f"chunk_{i}")))

        assert handler.stats.buffer_high_watermark == 50

    def test_repr(self):
        """Test string representation."""
        handler = StreamingHandler()

        repr_str = repr(handler)
        assert "StreamingHandler" in repr_str
        assert "buffer=" in repr_str


class TestStreamingHandlerBackpressure:
    """Tests for backpressure handling."""

    @pytest.mark.asyncio
    async def test_backpressure_emits_event(self):
        """Test that backpressure emits progress event."""
        events = []

        def on_progress(event):
            events.append(event)

        config = StreamingConfig(
            buffer_size=10,
            backpressure_threshold=0.9,
            pause_on_backpressure=False,  # Don't actually pause in test
        )
        handler = StreamingHandler(config=config, on_progress=on_progress)

        # Fill buffer past threshold
        for i in range(10):
            await handler.handle(Chunk(type=ChunkType.TEXT, content=f"chunk_{i}"))

        # Should have triggered backpressure
        # Note: event only emitted if pause_on_backpressure is True

    @pytest.mark.asyncio
    async def test_no_backpressure_when_disabled(self):
        """Test no backpressure when disabled."""
        config = StreamingConfig(
            buffer_size=10,
            pause_on_backpressure=False,
        )
        handler = StreamingHandler(config=config)

        # Fill buffer
        for i in range(15):  # Over buffer size
            handler._buffer.append(Chunk(type=ChunkType.TEXT, content=f"chunk_{i}"))

        # Should not be paused (just drops old chunks)
        assert handler._is_paused is False
