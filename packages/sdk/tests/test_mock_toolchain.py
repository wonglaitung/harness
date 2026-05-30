"""
Tests for Mock Testing Toolchain.
"""

import pytest
from pathlib import Path
import tempfile
import json

from harness.testing import MockHarness, MockHarnessConfig, RecordingHarness, RecordingConfig
from harness.testing.mock_harness import MockResponse
from harness.types import StopReason, ToolCall, LoopState


class TestMockResponse:
    """Tests for MockResponse."""

    def test_default_response(self):
        """Test default mock response."""
        response = MockResponse()

        assert response.content == ""
        assert response.tool_calls == []
        assert response.stop_reason == StopReason.END_TURN

    def test_custom_response(self):
        """Test custom response."""
        response = MockResponse(
            content="Hello, world!",
            input_tokens=50,
            output_tokens=25,
        )

        assert response.content == "Hello, world!"
        assert response.input_tokens == 50
        assert response.output_tokens == 25

    def test_to_llm_response(self):
        """Test conversion to LLMResponse."""
        mock = MockResponse(content="Test")
        llm_response = mock.to_llm_response()

        assert llm_response.content == "Test"
        assert llm_response.usage.input_tokens == 100
        assert llm_response.usage.output_tokens == 50


class TestMockHarnessConfig:
    """Tests for MockHarnessConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = MockHarnessConfig()

        assert config.responses == []
        assert config.auto_tool_results == {}
        assert config.record_mode is False
        assert config.default_input_tokens == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = MockHarnessConfig(
            responses=[MockResponse(content="test")],
            auto_tool_results={"read": "file content"},
            record_mode=True,
        )

        assert len(config.responses) == 1
        assert config.auto_tool_results["read"] == "file content"
        assert config.record_mode is True


class TestMockHarness:
    """Tests for MockHarness."""

    def test_init(self):
        """Test initialization."""
        harness = MockHarness()

        assert harness.config is not None
        assert harness.responses_remaining == 0

    def test_init_with_responses(self):
        """Test initialization with responses."""
        responses = [MockResponse(content="Hello")]
        harness = MockHarness(responses=responses)

        assert harness.responses_remaining == 1

    def test_add_response(self):
        """Test adding response."""
        harness = MockHarness()
        harness.add_response(MockResponse(content="Hi"))

        assert harness.responses_remaining == 1

    def test_set_responses(self):
        """Test setting responses."""
        harness = MockHarness()
        harness.set_responses([
            MockResponse(content="First"),
            MockResponse(content="Second"),
        ])

        assert harness.responses_remaining == 2

    def test_add_tool_result(self):
        """Test adding tool result."""
        harness = MockHarness()
        harness.add_tool_result("read", "file content")

        assert harness._tool_results["read"] == "file content"

    @pytest.mark.asyncio
    async def test_run_simple(self):
        """Test simple run."""
        harness = MockHarness(responses=[
            MockResponse(content="Hello!"),
        ])

        result = await harness.run("Say hello")

        assert result.status == LoopState.COMPLETED
        assert result.content == "Hello!"

    @pytest.mark.asyncio
    async def test_run_with_tool_call(self):
        """Test run with tool calls."""
        harness = MockHarness(responses=[
            MockResponse(
                tool_calls=[ToolCall(id="call_1", name="read", arguments={"path": "/test"})],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(content="File contents: test data"),
        ])
        harness.add_tool_result("read", "test data")

        result = await harness.run("Read the file")

        assert result.status == LoopState.COMPLETED
        assert "File contents" in result.content

    @pytest.mark.asyncio
    async def test_run_multiple_iterations(self):
        """Test multiple iterations."""
        harness = MockHarness(responses=[
            MockResponse(
                tool_calls=[ToolCall(id="call_1", name="read", arguments={})],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(
                tool_calls=[ToolCall(id="call_2", name="write", arguments={})],
                stop_reason=StopReason.TOOL_USE,
            ),
            MockResponse(content="Done"),
        ])

        result = await harness.run("Do things", max_iterations=10)

        assert result.status == LoopState.COMPLETED
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_run_exhausts_responses(self):
        """Test when responses run out."""
        harness = MockHarness(responses=[
            MockResponse(content="Only one response"),
        ])

        # First run succeeds
        result = await harness.run("First")
        assert result.status == LoopState.COMPLETED

        # Reset and run again
        harness.reset()
        harness.add_response(MockResponse(content="Second"))
        result = await harness.run("Second")
        assert result.status == LoopState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_records_interactions(self):
        """Test recording mode."""
        harness = MockHarness(config=MockHarnessConfig(record_mode=True))
        harness.add_response(MockResponse(content="Test response"))

        await harness.run("Test")

        recordings = harness.get_recordings()
        assert len(recordings) > 0
        assert recordings[0]["type"] == "llm_response"

    def test_reset(self):
        """Test reset."""
        harness = MockHarness(responses=[MockResponse(content="Test")])
        harness.add_tool_result("read", "data")

        harness.reset()

        assert harness.current_response_index == 0
        assert len(harness._sessions) == 0


class TestMockHarnessRecording:
    """Tests for MockHarness recording functionality."""

    def test_get_recordings(self):
        """Test getting recordings."""
        harness = MockHarness(config=MockHarnessConfig(record_mode=True))
        harness.add_response(MockResponse(content="Test"))

        recordings = harness.get_recordings()
        assert isinstance(recordings, list)

    def test_save_and_load_recording(self):
        """Test saving and loading recordings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_recording.json"

            # Create and save
            harness = MockHarness(config=MockHarnessConfig(record_mode=True))
            harness.add_response(MockResponse(content="Test response"))

            # Run to create recording
            import asyncio
            asyncio.run(harness.run("Test prompt"))

            harness.save_recording(path)

            assert path.exists()

            # Load into new harness
            new_harness = MockHarness()
            new_harness.load_recording(path)

            assert new_harness.responses_remaining >= 1


class TestRecordingHarness:
    """Tests for RecordingHarness."""

    def test_init(self):
        """Test initialization."""
        # Use MockHarness as the underlying harness
        mock = MockHarness()
        recorder = RecordingHarness(mock)

        assert recorder.harness is mock
        assert recorder.config is not None

    def test_start_recording(self):
        """Test starting recording."""
        mock = MockHarness()
        recorder = RecordingHarness(mock)

        recorder.start_recording("test-session")

        assert recorder._current_session_id == "test-session"

    def test_get_recording_summary(self):
        """Test getting recording summary."""
        mock = MockHarness()
        recorder = RecordingHarness(mock)

        summary = recorder.get_recording_summary()

        assert "total_interactions" in summary

    def test_clear_recording(self):
        """Test clearing recording."""
        mock = MockHarness()
        recorder = RecordingHarness(mock)

        recorder.start_recording("test")
        recorder.clear_recording()

        assert recorder._current_session_id is None
        assert len(recorder._interactions) == 0


class TestRecordingConfig:
    """Tests for RecordingConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RecordingConfig()

        assert config.auto_save is True
        assert config.include_metadata is True
        assert config.max_recording_size == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = RecordingConfig(
            auto_save=False,
            max_recording_size=50,
        )

        assert config.auto_save is False
        assert config.max_recording_size == 50
