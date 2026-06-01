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

        assert loop._is_stuck(session, iteration=0) is False
        assert loop._is_stuck(session, iteration=2) is False

    def test_no_tool_messages_not_stuck(self):
        """Sessions with no tool messages should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3))
        session = Session(id="test")
        session.add_message(Message(role="user", content="Hello"))
        session.add_message(Message(role="assistant", content="Hi there!"))

        assert loop._is_stuck(session, iteration=5) is False

    def test_too_few_tool_messages_not_stuck(self):
        """Fewer tool messages than stuck_consecutive_failures should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")
        # Only 2 tool messages, need 3 consecutive
        session.add_message(Message(role="tool", content=""))
        session.add_message(Message(role="tool", content=""))

        assert loop._is_stuck(session, iteration=4) is False

    def test_detects_empty_tool_results(self):
        """Consecutive empty tool results should trigger stuck detection."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        # 3 consecutive empty results
        for i in range(3):
            session.add_message(Message(role="tool", content=""))

        assert loop._is_stuck(session, iteration=4) is True

    def test_detects_error_tool_results(self):
        """Consecutive error tool results should trigger stuck detection."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        # 3 consecutive error results
        for i in range(3):
            session.add_message(Message(role="tool", content="Error: file not found"))

        assert loop._is_stuck(session, iteration=4) is True

    def test_short_but_nonempty_not_stuck(self):
        """Short but non-empty content (e.g. 'True', 'OK') should NOT trigger empty rule."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        # "True" and "OK" are legitimate short results
        session.add_message(Message(role="tool", content="True"))
        session.add_message(Message(role="tool", content="OK"))
        session.add_message(Message(role="tool", content="No results found"))

        assert loop._is_stuck(session, iteration=4) is False

    def test_mixed_success_and_failure_not_stuck(self):
        """Mixed success/failure without consecutive failures should not trigger."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        # Alternating: not consecutive
        session.add_message(Message(role="tool", content="Error: fail"))
        session.add_message(Message(role="tool", content="File contents"))
        session.add_message(Message(role="tool", content="Error: fail"))

        assert loop._is_stuck(session, iteration=4) is False

    def test_only_checks_last_n(self):
        """Should only check the last N tool messages, ignoring older ones."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        # Old messages: all successes
        for i in range(10):
            session.add_message(Message(role="tool", content=f"Content {i}"))

        # Recent 3: all empty
        for i in range(3):
            session.add_message(Message(role="tool", content=""))

        assert loop._is_stuck(session, iteration=10) is True

    def test_custom_consecutive_failures(self):
        """Custom stuck_consecutive_failures should be respected."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=5))
        session = Session(id="test")

        # 3 errors not enough for threshold of 5
        for i in range(3):
            session.add_message(Message(role="tool", content="Error: fail"))

        assert loop._is_stuck(session, iteration=4) is False

        # 5 errors triggers
        session.add_message(Message(role="tool", content="Error: fail"))
        session.add_message(Message(role="tool", content="Error: fail"))

        assert loop._is_stuck(session, iteration=5) is True

    def test_whitespace_only_counts_as_empty(self):
        """Whitespace-only content should count as empty."""
        loop = _make_loop(LoopConfig(stuck_min_iterations=3, stuck_consecutive_failures=3))
        session = Session(id="test")

        session.add_message(Message(role="tool", content="   "))
        session.add_message(Message(role="tool", content="\n\t"))
        session.add_message(Message(role="tool", content="  "))

        assert loop._is_stuck(session, iteration=4) is True


class TestToolErrorEncoding:
    """Tests for the tool error encoding fix."""

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
        assert config.stuck_consecutive_failures == 3

    def test_custom_config(self):
        """Custom LoopConfig stuck detection settings should be respected."""
        config = LoopConfig(
            max_stuck_feedbacks=5,
            stuck_min_iterations=5,
            stuck_consecutive_failures=5,
        )
        assert config.max_stuck_feedbacks == 5
        assert config.stuck_min_iterations == 5
        assert config.stuck_consecutive_failures == 5


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

        fresh_loop = _make_loop()
        assert fresh_loop._stuck_feedback_count == 0


class TestGenerateStuckFeedback:
    """Tests for differentiated feedback generation."""

    def test_first_feedback_is_gentle(self):
        """First feedback should be a gentle suggestion."""
        loop = _make_loop()
        session = Session(id="test")
        feedback = loop._generate_stuck_feedback(1, session)

        assert "循环检测" in feedback
        assert "请尝试" in feedback
        assert "最后机会" not in feedback

    def test_second_feedback_is_forceful(self):
        """Second feedback should be forceful with error analysis."""
        loop = _make_loop()
        session = Session(id="test")
        # Add some error tool messages for the summary
        for i in range(3):
            session.add_message(Message(role="tool", content="Error: not found"))

        feedback = loop._generate_stuck_feedback(2, session)

        assert "最后机会" in feedback
        assert "承认无法继续" in feedback or "承认困难" in feedback

    def test_third_feedback_same_as_second(self):
        """Third+ feedback should use same forceful template."""
        loop = _make_loop()
        session = Session(id="test")
        feedback = loop._generate_stuck_feedback(3, session)

        assert "最后机会" in feedback


class TestSummarizeRecentErrors:
    """Tests for error pattern summarization."""

    def test_empty_results_counted(self):
        """Empty tool results should be counted in summary."""
        loop = _make_loop()
        session = Session(id="test")
        for i in range(3):
            session.add_message(Message(role="tool", content=""))

        summary = loop._summarize_recent_errors(session)
        assert "空结果" in summary
        assert "3 次" in summary

    def test_error_results_counted(self):
        """Error tool results should be counted in summary."""
        loop = _make_loop()
        session = Session(id="test")
        for i in range(2):
            session.add_message(Message(role="tool", content="Error: permission denied"))

        summary = loop._summarize_recent_errors(session)
        assert "错误" in summary
        assert "2 次" in summary

    def test_mixed_errors_summarized(self):
        """Both empty and error results should appear in summary."""
        loop = _make_loop()
        session = Session(id="test")
        session.add_message(Message(role="tool", content=""))
        session.add_message(Message(role="tool", content="Error: not found"))

        summary = loop._summarize_recent_errors(session)
        assert "空结果" in summary
        assert "错误" in summary

    def test_no_tool_messages_default(self):
        """No tool messages should return default summary."""
        loop = _make_loop()
        session = Session(id="test")

        summary = loop._summarize_recent_errors(session)
        assert summary == "工具调用无进展"

    def test_all_successful_results(self):
        """Successful results should return default summary."""
        loop = _make_loop()
        session = Session(id="test")
        session.add_message(Message(role="tool", content="File contents here"))

        summary = loop._summarize_recent_errors(session)
        assert summary == "工具调用无进展"


class TestFeedbackMetadata:
    """Tests for feedback message metadata."""

    def test_feedback_has_metadata(self):
        """Injected feedback messages should have stuck_feedback metadata."""
        msg = Message(
            role="user",
            content="[循环检测] test",
            metadata={"type": "stuck_feedback", "injected": True},
        )

        assert msg.metadata["type"] == "stuck_feedback"
        assert msg.metadata["injected"] is True
