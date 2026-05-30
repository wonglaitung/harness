"""
Tests for LLM streaming with backpressure integration.
"""

import pytest

from harness.llm.base import LLMConfig
from harness.core import StreamingConfig, StreamingHandler
from harness.types import Chunk, ChunkType, ProgressEvent, ProgressEventType


class TestLLMConfigStreaming:
    """Tests for LLMConfig streaming configuration."""

    def test_default_streaming_config_is_none(self):
        """Test that streaming_config is None by default."""
        config = LLMConfig(model="test-model")

        assert config.streaming_config is None

    def test_custom_streaming_config(self):
        """Test custom streaming config."""
        streaming_config = StreamingConfig(
            buffer_size=1000,
            backpressure_threshold=0.8,
        )
        config = LLMConfig(
            model="test-model",
            streaming_config=streaming_config,
        )

        assert config.streaming_config is not None
        assert config.streaming_config.buffer_size == 1000
        assert config.streaming_config.backpressure_threshold == 0.8


class TestStreamingIntegration:
    """Tests for streaming integration patterns."""

    def test_handler_initialization_pattern(self):
        """Test the pattern used in LLM stream() methods."""
        # This tests the initialization pattern we use
        streaming_config = StreamingConfig(buffer_size=100)
        handler = StreamingHandler(config=streaming_config)

        assert handler.config.buffer_size == 100

    @pytest.mark.asyncio
    async def test_chunk_processing_pattern(self):
        """Test the chunk processing pattern used in stream() methods."""
        handler = StreamingHandler()
        collected = []

        # Simulate streaming pattern
        async def process_stream():
            texts = ["Hello", " ", "World"]
            for text in texts:
                chunk = Chunk(type=ChunkType.TEXT, content=text)
                await handler.handle(chunk)

                if handler.should_pause:
                    import asyncio
                    await asyncio.sleep(0.01)

                collected.append(text)

        await process_stream()

        assert collected == ["Hello", " ", "World"]
        assert handler.get_full_content() == "Hello World"

    @pytest.mark.asyncio
    async def test_progress_callback_pattern(self):
        """Test progress callback pattern."""
        events = []

        def on_progress(event: ProgressEvent):
            events.append(event)

        config = StreamingConfig(
            buffer_size=10,
            backpressure_threshold=0.9,
        )
        handler = StreamingHandler(config=config, on_progress=on_progress)

        # Fill buffer to trigger backpressure
        for i in range(10):
            chunk = Chunk(type=ChunkType.TEXT, content=f"chunk_{i}")
            handler._buffer.append(chunk)

        # Check should_pause
        assert handler.should_pause is True

    @pytest.mark.asyncio
    async def test_backpressure_with_on_chunk(self):
        """Test combined on_chunk and backpressure handling."""
        chunks_received = []
        handler = StreamingHandler(
            on_chunk=lambda c: chunks_received.append(c),
        )

        # Simulate stream processing
        for text in ["a", "b", "c"]:
            chunk = Chunk(type=ChunkType.TEXT, content=text)
            await handler.handle(chunk)

        assert len(chunks_received) == 3
        assert handler.get_full_content() == "abc"


class TestStreamingConfigVariations:
    """Tests for different streaming configurations."""

    def test_small_buffer_config(self):
        """Test configuration with small buffer for testing."""
        config = StreamingConfig(
            buffer_size=10,
            backpressure_threshold=0.8,
            pause_on_backpressure=True,
            max_pause_duration=1.0,
        )

        handler = StreamingHandler(config=config)

        assert handler.config.buffer_size == 10
        assert handler.should_pause is False

        # Fill to threshold
        for i in range(8):
            handler._buffer.append(Chunk(type=ChunkType.TEXT, content=str(i)))

        assert handler.should_pause is True

    def test_no_pause_config(self):
        """Test configuration that doesn't pause on backpressure."""
        config = StreamingConfig(
            buffer_size=10,
            pause_on_backpressure=False,
        )

        handler = StreamingHandler(config=config)

        # Fill over capacity
        for i in range(15):
            handler._buffer.append(Chunk(type=ChunkType.TEXT, content=str(i)))

        # Should not pause, just drops old chunks
        assert handler._is_paused is False


class TestStreamingStatsIntegration:
    """Tests for streaming statistics during integration."""

    @pytest.mark.asyncio
    async def test_stats_tracking_during_stream(self):
        """Test that stats are correctly tracked during streaming."""
        handler = StreamingHandler()

        # Process some chunks
        for i in range(5):
            chunk = Chunk(type=ChunkType.TEXT, content=f"text_{i}")
            await handler.handle(chunk)

        assert handler.stats.chunks_received == 5
        assert handler.stats.chunks_processed == 5
        assert handler.stats.buffer_high_watermark > 0

    @pytest.mark.asyncio
    async def test_healthy_stream(self):
        """Test healthy stream detection."""
        handler = StreamingHandler()

        # Process chunks without backpressure
        for i in range(10):
            chunk = Chunk(type=ChunkType.TEXT, content=f"text_{i}")
            await handler.handle(chunk)

        assert handler.stats.is_healthy is True
