"""
pytest plugin for Harness testing.

Provides fixtures and utilities for testing Harness agents.
"""

from pathlib import Path

import pytest

from harness.testing.mock_harness import MockHarness, MockHarnessConfig, MockResponse
from harness.testing.recording import RecordingConfig
from harness.types import StopReason, ToolCall


# Fixtures
@pytest.fixture
def mock_harness():
    """Create a basic mock harness."""
    return MockHarness()


@pytest.fixture
def mock_harness_with_responses():
    """Create a mock harness with default responses."""
    responses = [
        MockResponse(content="Hello! I'm a test agent."),
    ]
    return MockHarness(responses=responses)


@pytest.fixture
def mock_harness_config():
    """Create a mock harness configuration."""
    return MockHarnessConfig(
        responses=[MockResponse(content="Default response")],
        default_input_tokens=100,
        default_output_tokens=50,
    )


@pytest.fixture
def mock_response():
    """Create a single mock response."""
    return MockResponse(content="Test response")


@pytest.fixture
def mock_tool_call():
    """Create a mock tool call."""
    return ToolCall(id="test_call_1", name="read", arguments={"path": "/test.txt"})


@pytest.fixture
def recording_config():
    """Create a recording configuration."""
    return RecordingConfig(
        recording_dir=Path(".test_recordings"),
        auto_save=False,
    )


# Helpers
def create_mock_sequence(responses: list[str]) -> MockHarness:
    """
    Create a mock harness with a sequence of text responses.

    Args:
        responses: List of response texts

    Returns:
        MockHarness configured with the sequence
    """
    return MockHarness(responses=[MockResponse(content=r) for r in responses])


def create_mock_with_tools(
    tool_sequence: list[tuple[str, dict, str]],
    final_response: str = "Done",
) -> MockHarness:
    """
    Create a mock harness with tool calls.

    Args:
        tool_sequence: List of (tool_name, arguments, mock_result) tuples
        final_response: Final response after tools

    Returns:
        MockHarness configured with tool calls
    """
    responses = []
    tool_results = {}

    for tool_name, arguments, result in tool_sequence:
        call_id = f"call_{tool_name}"
        responses.append(
            MockResponse(
                tool_calls=[ToolCall(id=call_id, name=tool_name, arguments=arguments)],
                stop_reason=StopReason.TOOL_USE,
            )
        )
        tool_results[tool_name] = result

    responses.append(MockResponse(content=final_response))

    harness = MockHarness(responses=responses)
    for name, result in tool_results.items():
        harness.add_tool_result(name, result)

    return harness


# pytest hooks
def pytest_configure(config):
    """Register the plugin."""
    config.addinivalue_line(
        "markers",
        "harness_recording: mark test to save recording after execution",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to save recordings after test."""
    outcome = yield
    outcome.get_result()

    # Check if test is marked for recording
    if (
        "harness_recording" in item.keywords
        and call.when == "call"
        and "mock_harness" in item.funcargs
    ):
        # Look for mock_harness fixture
        harness = item.funcargs["mock_harness"]
        if hasattr(harness, "_recordings") and harness._recordings:
            # Save recording
            name = f"{item.name}_recording"
            recording_dir = Path(".pytest_recordings")
            recording_dir.mkdir(exist_ok=True)
            harness.save_recording(recording_dir / f"{name}.json")


# Plugin registration
# This file should be placed in the project root or tests directory
# Add to pyproject.toml:
# [tool.pytest.ini_options]
# plugins = ["pytest_harness"]
