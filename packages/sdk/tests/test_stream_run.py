"""
Tests for AgentLoop streaming support (Phase 1).

Tests the stream_run() method that uses llm.stream_with_tools() for
real token-level streaming.
"""

import asyncio

import pytest

from harness.core.agent_loop import AgentLoop, LoopConfig
from harness.llm.mock import MockLLMClient, MockResponse
from harness.memory.context_builder import ContextBuilder, ContextConfig
from harness.memory.session import SessionManager
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.types import (
    Chunk,
    ChunkType,
    LoopState,
    Message,
    Session,
    StopReason,
    TokenUsage,
    ToolCall,
)


def _create_loop(llm_client, tools=None):
    """Helper to create an AgentLoop with mock dependencies."""
    session_store = type("MockStore", (), {"load": lambda s, id: None, "save": lambda s, s_: None})()
    session_manager = SessionManager(session_store)
    context_builder = ContextBuilder(config=ContextConfig(max_tokens=100000))

    tool_registry = ToolRegistry()
    tool_executor = ToolExecutor(tool_registry)

    config = LoopConfig(max_iterations=5, enable_progress=False)

    loop = AgentLoop(
        llm_client=llm_client,
        tool_executor=tool_executor,
        context_builder=context_builder,
        session_manager=session_manager,
        config=config,
    )
    return loop


@pytest.mark.asyncio
async def test_stream_run_simple_text():
    """Test streaming with simple text response (no tools)."""
    llm = MockLLMClient(
        responses=[
            MockResponse(content="Hello world", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    chunks = []
    async for chunk in loop.stream_run(
        prompt="Say hello",
        session=session,
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "Hello world" in full_text

    assert loop._stream_result is not None
    assert loop._stream_result.status == LoopState.COMPLETED
    assert loop._stream_result.final_response == "Hello world"


@pytest.mark.asyncio
async def test_stream_run_with_tool_calls():
    """Test streaming with tool calls (tool execution is blocking)."""
    llm = MockLLMClient(
        responses=[
            MockResponse(
                content="",
                tool_calls=[{"id": "tc_1", "name": "read", "arguments": {"path": "/test"}}],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(content="File contents: test", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    chunks = []
    async for chunk in loop.stream_run(
        prompt="Read the file",
        session=session,
    ):
        chunks.append(chunk)

    assert loop._stream_result is not None
    assert loop._stream_result.status == LoopState.COMPLETED
    assert loop._stream_result.iterations == 1

    full_text = "".join(chunks)
    assert "File contents: test" in full_text


@pytest.mark.asyncio
async def test_stream_run_yields_strings():
    """Test that stream_run yields plain strings, not objects."""
    llm = MockLLMClient(
        responses=[
            MockResponse(content="Test response", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    async for chunk in loop.stream_run(
        prompt="Test",
        session=session,
    ):
        assert isinstance(chunk, str)


@pytest.mark.asyncio
async def test_stream_run_on_chunk_callback():
    """Test that on_chunk callback is called for each text chunk."""
    llm = MockLLMClient(
        responses=[
            MockResponse(content="Hello world", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    received_chunks = []

    async for chunk in loop.stream_run(
        prompt="Test",
        session=session,
        on_chunk=lambda c: received_chunks.append(c),
    ):
        pass

    assert len(received_chunks) > 0
    assert "".join(received_chunks) == "Hello world"


@pytest.mark.asyncio
async def test_stream_run_max_iterations():
    """Test that stream_run respects max_iterations."""
    llm = MockLLMClient(
        responses=[
            MockResponse(
                content="",
                tool_calls=[{"id": "tc_1", "name": "read", "arguments": {}}],
                stop_reason=StopReason.TOOL_USE,
            ),
        ]
        * 10  # More responses than max_iterations
    )

    config = LoopConfig(max_iterations=2, enable_progress=False)
    loop = _create_loop(llm)
    loop.config = config
    session = Session(id="test")

    chunks = []
    async for chunk in loop.stream_run(
        prompt="Test",
        session=session,
    ):
        chunks.append(chunk)

    assert loop._stream_result is not None
    assert loop._stream_result.status == LoopState.ERROR
    assert "Max iterations" in loop._stream_result.error


@pytest.mark.asyncio
async def test_stream_run_stores_session():
    """Test that stream_run updates session with messages."""
    llm = MockLLMClient(
        responses=[
            MockResponse(content="Response", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    async for _ in loop.stream_run(
        prompt="Test prompt",
        session=session,
    ):
        pass

    assert loop._stream_result is not None
    result_session = loop._stream_result.session

    user_msgs = [m for m in result_session.messages if m.role == "user"]
    assistant_msgs = [m for m in result_session.messages if m.role == "assistant"]

    assert len(user_msgs) >= 1
    assert len(assistant_msgs) >= 1
    assert assistant_msgs[-1].content == "Response"


@pytest.mark.asyncio
async def test_stream_run_tool_results_in_session():
    """Test that tool results are added to session during streaming."""
    llm = MockLLMClient(
        responses=[
            MockResponse(
                content="",
                tool_calls=[{"id": "tc_1", "name": "read", "arguments": {"path": "/test"}}],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(content="Done", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    async for _ in loop.stream_run(
        prompt="Read file",
        session=session,
    ):
        pass

    result_session = loop._stream_result.session
    tool_msgs = [m for m in result_session.messages if m.role == "tool"]
    assert len(tool_msgs) >= 1


@pytest.mark.asyncio
async def test_stream_run_empty_response():
    """Test streaming with empty response."""
    llm = MockLLMClient(
        responses=[
            MockResponse(content="", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    chunks = []
    async for chunk in loop.stream_run(
        prompt="Test",
        session=session,
    ):
        chunks.append(chunk)

    assert loop._stream_result is not None
    assert loop._stream_result.status == LoopState.COMPLETED
    assert loop._stream_result.final_response == ""


@pytest.mark.asyncio
async def test_stream_run_multiple_iterations():
    """Test streaming across multiple iterations with tool calls."""
    llm = MockLLMClient(
        responses=[
            MockResponse(
                content="Step 1",
                tool_calls=[{"id": "tc_1", "name": "tool_a", "arguments": {}}],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(
                content="Step 2",
                tool_calls=[{"id": "tc_2", "name": "tool_b", "arguments": {}}],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(content="Final answer", stop_reason=StopReason.END_TURN),
        ]
    )

    loop = _create_loop(llm)
    session = Session(id="test")

    chunks = []
    async for chunk in loop.stream_run(
        prompt="Multi-step task",
        session=session,
    ):
        chunks.append(chunk)

    assert loop._stream_result is not None
    assert loop._stream_result.status == LoopState.COMPLETED
    assert loop._stream_result.iterations == 2

    full_text = "".join(chunks)
    assert "Final answer" in full_text
