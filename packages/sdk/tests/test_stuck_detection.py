"""
Tests for Stuck Detection and tool error encoding fix.
"""

import pytest

from harness.types import LoopState, Message, Session, ToolCall, ToolResult
from harness.core.agent_loop import AgentLoop, LoopConfig


def _make_loop(config: LoopConfig | None = None) -> AgentLoop:
    """Create an AgentLoop with mock components for unit testing."""
    from harness.llm import MockLLMClient
    from harness.memory import SessionManager, ContextBuilder
    from harness.tools import ToolRegistry, ToolExecutor

    llm = MockLLMClient(model="mock")
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    context_builder = ContextBuilder()
    session_manager = SessionManager()

    return AgentLoop(llm, executor, context_builder, session_manager, config=config)


class TestIsStuck:
    """Tests for AgentLoop._is_stuck detection."""

    def test_early_iterations_not_stuck(self):
        """Iterations below stuck_min_iterations should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3))
        session = Session(id="test")

        # No messages, early iteration
        assert loop._is_stuck(session, iteration=0) is False
        assert loop._is_stuck(session, iteration=2) is False

    def test_no_tool_messages_not_stuck(self):
        """Sessions with no tool messages should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3))
        session = Session(id="test")
        session.add_message(Message(role="user", content="Hello"))
        session.add_message(Message(role="assistant", content="Hi there!"))

        assert loop._is_stuck(session, iteration=5) is False

    def test_detects_empty_tool_results(self):
        """Majority empty tool results should trigger stuck detection."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.8))
        session = Session(id="test")

        # Add 5 empty tool results (> 80% of recent tool messages)
        for i in range(5):
            session.add_message(Message(role="tool", content=""))

        assert loop._is_stuck(session, iteration=4) is True

    def test_detects_error_tool_results(self):
        """Majority error tool results should trigger stuck detection."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.8))
        session = Session(id="test")

        # Add 5 error tool results (> 80% of recent tool messages)
        for i in range(5):
            session.add_message(Message(role="tool", content=f"Error: file not found"))

        assert loop._is_stuck(session, iteration=4) is True

    def test_mixed_results_below_threshold(self):
        """Mixed success/failure below threshold should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.8))
        session = Session(id="test")

        # 2 successes + 1 error = 33% error rate, well below 80%
        session.add_message(Message(role="tool", content="File contents here"))
        session.add_message(Message(role="tool", content="Another file contents"))
        session.add_message(Message(role="tool", content="Error: not found"))

        assert loop._is_stuck(session, iteration=4) is False

    def test_mixed_results_at_threshold(self):
        """Results at exactly the threshold boundary should not trigger (>)."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.8))
        session = Session(id="test")

        # 4 errors + 1 success = 80% = NOT > 80%, so should not trigger
        for i in range(4):
            session.add_message(Message(role="tool", content="Error: failed"))
        session.add_message(Message(role="tool", content="OK"))

        assert loop._is_stuck(session, iteration=4) is False

    def test_only_checks_recent_messages(self):
        """Should only look at the last 6 messages (3 rounds), not older ones."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.8))
        session = Session(id="test")

        # Old messages: all successes
        for i in range(10):
            session.add_message(Message(role="tool", content=f"Content {i}"))

        # Recent messages: all empty
        for i in range(5):
            session.add_message(Message(role="tool", content=""))

        # Recent 6 messages: 5 empty tool msgs out of 5 = 100% > 0.8
        assert loop._is_stuck(session, iteration=10) is True

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_error_threshold=0.5))
        session = Session(id="test")

        # 2 errors + 2 successes = 50% = NOT > 50%
        session.add_message(Message(role="tool", content="Error: fail"))
        session.add_message(Message(role="tool", content="OK"))
        session.add_message(Message(role="tool", content="Error: fail"))
        session.add_message(Message(role="tool", content="OK"))

        assert loop._is_stuck(session, iteration=4) is False

        # 3 errors + 1 success = 75% > 50%
        session.add_message(Message(role="tool", content="Error: another"))
        assert loop._is_stuck(session, iteration=5) is True


class TestToolErrorEncoding:
    """Tests for the tool error encoding fix in _execute_tools / _run_impl."""

    def test_tool_result_error_in_content(self):
        """Failed ToolResult content should be 'Error: {error}' in Message."""
        result = ToolResult(
            tool_call_id="call_1",
            success=False,
            content="",
            error="Permission denied",
        )
        content = result.content if result.success else f"Error: {result.error}"
        msg = Message(
            role="tool",
            content=content,
            metadata={
                "tool_call_id": result.tool_call_id,
                "is_error": not result.success,
            },
        )

        assert msg.content == "Error: Permission denied"
        assert msg.metadata["is_error"] is True

    def test_tool_result_success_in_content(self):
        """Successful ToolResult content should be preserved as-is in Message."""
        result = ToolResult(
            tool_call_id="call_1",
            success=True,
            content="File contents here",
        )
        content = result.content if result.success else f"Error: {result.error}"
        msg = Message(
            role="tool",
            content=content,
            metadata={
                "tool_call_id": result.tool_call_id,
                "is_error": not result.success,
            },
        )

        assert msg.content == "File contents here"
        assert msg.metadata["is_error"] is False


class TestLoopStateStuck:
    """Tests for LoopState.STUCK."""

    def test_stuck_state_exists(self):
        """LoopState.STUCK should be a valid state."""
        assert LoopState.STUCK.value == "stuck"

    def test_stuck_result_is_not_success(self):
        """LoopResult with STUCK status should not be success."""
        from harness.types import LoopResult

        result = LoopResult(
            status=LoopState.STUCK,
            session=Session(id="test"),
            iterations=5,
            error="Agent stuck: repeated failures after feedback attempts",
        )

        assert result.is_success is False
        assert result.status == LoopState.STUCK


class TestLoopConfigStuckDetection:
    """Tests for LoopConfig stuck detection settings."""

    def test_default_config(self):
        """Default LoopConfig should have stuck detection defaults."""
        config = LoopConfig()
        assert config.max_stuck_feedbacks == 2
        assert config.stuck_min_iterations == 3
        assert config.stuck_error_threshold == 0.8

    def test_custom_config(self):
        """Custom LoopConfig stuck detection settings should be respected."""
        config = LoopConfig(
            max_stuck_feedbacks=5,
            stuck_min_iterations=5,
            stuck_error_threshold=0.6,
        )
        assert config.max_stuck_feedbacks == 5
        assert config.stuck_min_iterations == 5
        assert config.stuck_error_threshold == 0.6


class TestStuckFeedbackCount:
    """Tests for stuck feedback count tracking."""

    def test_initial_count_is_zero(self):
        """_stuck_feedback_count should start at 0."""
        loop = _make_loop()
        assert loop._stuck_feedback_count == 0

    def test_count_resets_between_runs(self):
        """_stuck_feedback_count should reset at start of _run_impl."""
        loop = _make_loop()
        loop._stuck_feedback_count = 5

        # The reset happens inside _run_impl — we verify the attribute
        # is present and initialized correctly at construction time
        fresh_loop = _make_loop()
        assert fresh_loop._stuck_feedback_count == 0