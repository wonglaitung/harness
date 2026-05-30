"""
Tests for Interrupt/Recovery system.
"""

import pytest
from datetime import datetime

from harness.types import LoopSnapshot, Message, ToolCall
from harness.core.agent_loop import AgentLoop, LoopConfig


class TestLoopSnapshot:
    """Tests for LoopSnapshot."""

    def test_init(self):
        """Test initialization."""
        snapshot = LoopSnapshot(
            session_id="test-session",
            messages=[Message(role="user", content="Hello")],
            current_iteration=5,
        )

        assert snapshot.session_id == "test-session"
        assert len(snapshot.messages) == 1
        assert snapshot.current_iteration == 5
        assert snapshot.pending_tool_calls == []
        assert snapshot.last_llm_response is None

    def test_with_tool_calls(self):
        """Test with pending tool calls."""
        tool_call = ToolCall(id="call_1", name="read_file", arguments={"path": "/test"})
        snapshot = LoopSnapshot(
            session_id="test-session",
            current_iteration=3,
            pending_tool_calls=[tool_call],
            last_llm_response="I will read the file",
        )

        assert len(snapshot.pending_tool_calls) == 1
        assert snapshot.pending_tool_calls[0].name == "read_file"
        assert snapshot.last_llm_response == "I will read the file"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        snapshot = LoopSnapshot(
            session_id="test-session",
            messages=[Message(role="user", content="Hello")],
            current_iteration=5,
        )

        data = snapshot.to_dict()

        assert data["session_id"] == "test-session"
        assert data["current_iteration"] == 5
        assert "messages" in data
        assert "created_at" in data

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "session_id": "test-session",
            "messages": [{"role": "user", "content": "Hello"}],
            "current_iteration": 5,
            "pending_tool_calls": [],
            "last_llm_response": "response",
            "created_at": datetime.now().isoformat(),
        }

        snapshot = LoopSnapshot.from_dict(data)

        assert snapshot.session_id == "test-session"
        assert len(snapshot.messages) == 1
        assert snapshot.current_iteration == 5

    def test_serialization_roundtrip(self):
        """Test serialization roundtrip."""
        original = LoopSnapshot(
            session_id="test-session",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi!"),
            ],
            current_iteration=10,
            pending_tool_calls=[
                ToolCall(id="call_1", name="read", arguments={"path": "/test"})
            ],
            last_llm_response="Reading file",
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = LoopSnapshot.from_dict(data)

        assert restored.session_id == original.session_id
        assert len(restored.messages) == len(original.messages)
        assert restored.current_iteration == original.current_iteration
        assert len(restored.pending_tool_calls) == len(original.pending_tool_calls)


class TestToolCallSerialization:
    """Tests for ToolCall serialization."""

    def test_to_dict(self):
        """Test ToolCall.to_dict."""
        tool_call = ToolCall(id="call_1", name="read_file", arguments={"path": "/test"})

        data = tool_call.to_dict()

        assert data["id"] == "call_1"
        assert data["name"] == "read_file"
        assert data["arguments"] == {"path": "/test"}

    def test_from_dict(self):
        """Test ToolCall.from_dict."""
        data = {
            "id": "call_1",
            "name": "read_file",
            "arguments": {"path": "/test"},
        }

        tool_call = ToolCall.from_dict(data)

        assert tool_call.id == "call_1"
        assert tool_call.name == "read_file"
        assert tool_call.arguments == {"path": "/test"}


class TestAgentLoopInterrupt:
    """Tests for AgentLoop interrupt method."""

    def test_interrupt(self):
        """Test interrupt method."""
        from harness.llm import MockLLMClient
        from harness.memory import SessionManager, ContextBuilder
        from harness.tools import ToolRegistry, ToolExecutor

        llm = MockLLMClient(model="mock")
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        context_builder = ContextBuilder()
        session_manager = SessionManager()

        loop = AgentLoop(llm, executor, context_builder, session_manager)

        # Initially not interrupted
        assert loop._interrupt_flag is False

        # Interrupt
        loop.interrupt()

        assert loop._interrupt_flag is True


class TestAgentLoopSnapshot:
    """Tests for AgentLoop snapshot methods."""

    def test_create_snapshot(self):
        """Test creating snapshot from AgentLoop."""
        from harness.llm import MockLLMClient
        from harness.memory import SessionManager, ContextBuilder
        from harness.tools import ToolRegistry, ToolExecutor
        from harness.types import Session

        # Setup mock components
        llm = MockLLMClient(model="mock")
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        context_builder = ContextBuilder()
        session_manager = SessionManager()

        loop = AgentLoop(llm, executor, context_builder, session_manager)

        # Create session
        session = Session(id="test-session")
        session.add_message(Message(role="user", content="Hello"))

        # Create snapshot
        snapshot = loop.create_snapshot(session, iteration=3)

        assert snapshot.session_id == "test-session"
        assert len(snapshot.messages) == 1
        assert snapshot.current_iteration == 3

    def test_create_snapshot_with_tool_calls(self):
        """Test creating snapshot with pending tool calls."""
        from harness.llm import MockLLMClient
        from harness.memory import SessionManager, ContextBuilder
        from harness.tools import ToolRegistry, ToolExecutor
        from harness.types import Session

        llm = MockLLMClient(model="mock")
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        context_builder = ContextBuilder()
        session_manager = SessionManager()

        loop = AgentLoop(llm, executor, context_builder, session_manager)

        session = Session(id="test-session")
        tool_call = ToolCall(id="call_1", name="read", arguments={"path": "/test"})

        snapshot = loop.create_snapshot(
            session,
            iteration=5,
            pending_tool_calls=[tool_call],
            last_llm_response="I'll read that file",
        )

        assert len(snapshot.pending_tool_calls) == 1
        assert snapshot.last_llm_response == "I'll read that file"