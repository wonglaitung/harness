"""Tests for core types."""

import pytest
from datetime import datetime

from harness.types import (
    Message,
    Session,
    ToolCall,
    ToolResult,
    LLMResponse,
    LoopState,
    StopReason,
    TokenUsage,
    LoopResult,
)


class TestMessage:
    """Tests for Message class."""

    def test_create_user_message(self):
        """Test creating a user message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_invalid_role_raises(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError):
            Message(role="invalid", content="test")

    def test_to_api_format(self):
        """Test API format conversion."""
        msg = Message(role="user", content="test")
        api = msg.to_api_format()
        assert api["role"] == "user"
        assert api["content"] == "test"

    def test_tool_message_includes_metadata(self):
        """Test that tool messages include metadata in API format."""
        msg = Message(
            role="tool",
            content="file contents",
            metadata={"tool_call_id": "toolu_123", "tool_name": "read_file"},
        )
        api = msg.to_api_format()
        assert api["role"] == "tool"
        assert api["content"] == "file contents"
        assert "metadata" in api
        assert api["metadata"]["tool_call_id"] == "toolu_123"
        assert api["metadata"]["tool_name"] == "read_file"

    def test_user_message_excludes_metadata(self):
        """Test that non-tool messages don't include metadata."""
        msg = Message(role="user", content="test", metadata={"extra": "data"})
        api = msg.to_api_format()
        assert "metadata" not in api


class TestSession:
    """Tests for Session class."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session(id="test-123")
        assert session.id == "test-123"
        assert len(session.messages) == 0

    def test_add_message(self):
        """Test adding messages to session."""
        session = Session(id="test")
        msg = Message(role="user", content="Hello")
        session.add_message(msg)

        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"

    def test_get_last_n_messages(self):
        """Test getting last N messages."""
        session = Session(id="test")
        for i in range(5):
            session.add_message(Message(role="user", content=str(i)))

        last_3 = session.get_last_n_messages(3)
        assert len(last_3) == 3
        assert last_3[0].content == "2"
        assert last_3[2].content == "4"


class TestToolCall:
    """Tests for ToolCall class."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        tc = ToolCall(
            id="call_123",
            name="read",
            arguments={"file_path": "/tmp/test.txt"},
        )
        assert tc.id == "call_123"
        assert tc.name == "read"
        assert tc.arguments["file_path"] == "/tmp/test.txt"


class TestToolResult:
    """Tests for ToolResult class."""

    def test_success_result(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_call_id="call_123",
            success=True,
            content="file contents",
        )
        assert result.success
        assert result.content == "file contents"
        assert result.error is None

    def test_error_result(self):
        """Test error tool result."""
        result = ToolResult(
            tool_call_id="call_123",
            success=False,
            content="",
            error="File not found",
        )
        assert not result.success
        assert result.error == "File not found"

    def test_tool_result_with_name(self):
        """Test tool result with tool name."""
        result = ToolResult(
            tool_call_id="call_123",
            success=True,
            content="file contents",
            tool_name="read_file",
        )
        assert result.tool_name == "read_file"


class TestLLMResponse:
    """Tests for LLMResponse class."""

    def test_text_response(self):
        """Test a simple text response."""
        response = LLMResponse(
            content="Hello, how can I help?",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
        )
        assert response.content == "Hello, how can I help?"
        assert response.is_complete
        assert not response.is_tool_use

    def test_tool_use_response(self):
        """Test a tool use response."""
        response = LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="call_1", name="read", arguments={})
            ],
            stop_reason=StopReason.TOOL_USE,
        )
        assert response.is_tool_use
        assert not response.is_complete


class TestTokenUsage:
    """Tests for TokenUsage class."""

    def test_token_usage(self):
        """Test token usage tracking."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
        )
        assert usage.total_tokens == 150


class TestLoopResult:
    """Tests for LoopResult class."""

    def test_successful_result(self):
        """Test a successful loop result."""
        session = Session(id="test")
        result = LoopResult(
            status=LoopState.COMPLETED,
            session=session,
            final_response="Done!",
            iterations=3,
        )
        assert result.is_success
        assert result.content == "Done!"
        assert result.iterations == 3

    def test_error_result(self):
        """Test an error loop result."""
        session = Session(id="test")
        result = LoopResult(
            status=LoopState.ERROR,
            session=session,
            error="Something went wrong",
        )
        assert not result.is_success
        assert result.error == "Something went wrong"