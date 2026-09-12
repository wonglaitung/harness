"""
Tests for StreamEvent type and stream_with_tools() method.
"""

import pytest

from harness.llm.mock import MockLLMClient, MockResponse
from harness.types import (
    Chunk,
    ChunkType,
    StreamEvent,
    StopReason,
    TokenUsage,
    ToolCall,
)


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_text_event(self):
        """Test creating a text event."""
        event = StreamEvent(type="text", text="Hello")
        assert event.type == "text"
        assert event.text == "Hello"
        assert event.tool_calls == []
        assert event.error is None
        # New envelope fields have sensible defaults
        assert event.source == "agent"
        assert event.category == "text"
        assert event.seq == 0

    def test_done_event(self):
        """Test creating a done event."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        tool_calls = [ToolCall(id="tc_1", name="read", arguments={})]
        event = StreamEvent(
            type="done",
            tool_calls=tool_calls,
            usage=usage,
        )
        assert event.type == "done"
        assert len(event.tool_calls) == 1
        assert event.usage.input_tokens == 100

    def test_error_event(self):
        """Test creating an error event."""
        event = StreamEvent(type="error", error="Something went wrong")
        assert event.type == "error"
        assert event.error == "Something went wrong"

    def test_envelope_fields(self):
        """Test structured envelope fields (source/category/seq/event_id/parent_id)."""
        event = StreamEvent(
            type="text", text="chunk",
            source="agent", category="text",
            seq=42, event_id="evt-1", parent_id="evt-0",
        )
        assert event.source == "agent"
        assert event.category == "text"
        assert event.seq == 42
        assert event.event_id == "evt-1"
        assert event.parent_id == "evt-0"

    def test_goal_event_fields(self):
        """Test goal-specific fields."""
        event = StreamEvent(
            type="goal_iteration",
            source="goal_loop", category="lifecycle",
            seq=5, iteration=3, achieved=False,
        )
        assert event.type == "goal_iteration"
        assert event.iteration == 3
        assert event.achieved is False


class TestMockLLMStreamWithTools:
    """Tests for MockLLMClient.stream_with_tools()."""

    @pytest.mark.asyncio
    async def test_stream_with_tools_text_only(self):
        """Test streaming text-only response."""
        llm = MockLLMClient(
            responses=[
                MockResponse(content="Hello world", stop_reason=StopReason.END_TURN),
            ]
        )

        chunks = []
        async for chunk in llm.stream_with_tools(messages=[{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        done_chunks = [c for c in chunks if c.type == ChunkType.DONE]

        assert len(text_chunks) > 0
        assert "".join(c.content for c in text_chunks) == "Hello world"
        assert len(done_chunks) == 1
        assert done_chunks[0].metadata["tool_calls"] == []

    @pytest.mark.asyncio
    async def test_stream_with_tools_tool_calls(self):
        """Test streaming response with tool calls."""
        llm = MockLLMClient(
            responses=[
                MockResponse(
                    content="Let me read that",
                    tool_calls=[
                        {"id": "tc_1", "name": "read", "arguments": {"path": "/test"}}
                    ],
                    stop_reason=StopReason.TOOL_USE,
                ),
            ]
        )

        chunks = []
        async for chunk in llm.stream_with_tools(messages=[{"role": "user", "content": "Read file"}]):
            chunks.append(chunk)

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        tool_chunks = [c for c in chunks if c.type == ChunkType.TOOL_CALL_START]
        done_chunks = [c for c in chunks if c.type == ChunkType.DONE]

        assert len(text_chunks) > 0
        assert len(tool_chunks) == 1
        assert tool_chunks[0].tool_name == "read"
        assert tool_chunks[0].tool_arguments == {"path": "/test"}
        assert len(done_chunks) == 1

    @pytest.mark.asyncio
    async def test_stream_with_tools_empty_content(self):
        """Test streaming with empty content and tool calls."""
        llm = MockLLMClient(
            responses=[
                MockResponse(
                    content="",
                    tool_calls=[
                        {"id": "tc_1", "name": "bash", "arguments": {"command": "ls"}}
                    ],
                    stop_reason=StopReason.TOOL_USE,
                ),
            ]
        )

        chunks = []
        async for chunk in llm.stream_with_tools(messages=[{"role": "user", "content": "Run ls"}]):
            chunks.append(chunk)

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        tool_chunks = [c for c in chunks if c.type == ChunkType.TOOL_CALL_START]

        assert len(text_chunks) == 0  # Empty content
        assert len(tool_chunks) == 1
        assert tool_chunks[0].tool_name == "bash"
