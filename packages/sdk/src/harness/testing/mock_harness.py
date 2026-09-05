"""
Mock Harness for testing.

Provides a fully mocked agent harness for unit testing without real LLM calls.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.types import (
    LLMResponse,
    LoopResult,
    LoopState,
    Message,
    Session,
    StopReason,
    TokenUsage,
    ToolCall,
)

if TYPE_CHECKING:
    from harness.loop.types import GoalConfig, GoalResult
    from harness.tools.base import Tool

logger = logging.getLogger(__name__)


@dataclass
class MockResponse:
    """A mock LLM response for testing."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    input_tokens: int = 100
    output_tokens: int = 50

    def to_llm_response(self) -> LLMResponse:
        """Convert to LLMResponse."""
        return LLMResponse(
            content=self.content,
            tool_calls=self.tool_calls,
            stop_reason=self.stop_reason,
            usage=TokenUsage(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        )


@dataclass
class MockHarnessConfig:
    """Configuration for MockHarness."""

    responses: list[MockResponse] = field(default_factory=list)
    auto_tool_results: dict[str, str] = field(default_factory=dict)
    record_mode: bool = False
    recording_path: Path | None = None
    default_input_tokens: int = 100
    default_output_tokens: int = 50


class MockHarness:
    """
    A fully mocked agent harness for testing.

    Allows testing agent behavior without real LLM API calls.
    Supports:
    - Predefined responses
    - Automatic tool result handling
    - Recording/playback mode
    - Deterministic testing

    Example:
        >>> # Simple usage
        >>> mock = MockHarness(responses=[
        ...     MockResponse(content="Hello!"),
        ... ])
        >>> result = await mock.run("Say hello")
        >>> assert result.content == "Hello!"

        >>> # With tool calls
        >>> mock = MockHarness(responses=[
        ...     MockResponse(
        ...         tool_calls=[ToolCall(id="1", name="read", arguments={"path": "/test"})],
        ...         stop_reason=StopReason.TOOL_USE,
        ...     ),
        ...     MockResponse(content="File contents: ..."),
        ... ])
        >>> # Add mock tool result
        >>> mock.add_tool_result("read", "test file content")
        >>> result = await mock.run("Read the file")
    """

    def __init__(
        self,
        config: MockHarnessConfig | None = None,
        responses: list[MockResponse] | None = None,
        tools: list[Tool] | None = None,
    ):
        self.config = config or MockHarnessConfig()
        if responses:
            self.config.responses = responses

        self._tools = tools or []
        self._response_index = 0
        self._tool_results: dict[str, str] = self.config.auto_tool_results.copy()
        self._recordings: list[dict[str, Any]] = []
        self._sessions: dict[str, Session] = {}

    def add_response(self, response: MockResponse) -> None:
        """Add a mock response."""
        self.config.responses.append(response)

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """
        Add automatic tool result for a tool.

        When the agent calls this tool, the mock will automatically
        return this result instead of executing the real tool.

        Args:
            tool_name: Tool name
            result: Result content
        """
        self._tool_results[tool_name] = result

    def set_responses(self, responses: list[MockResponse]) -> None:
        """Set all responses."""
        self.config.responses = responses
        self._response_index = 0

    async def run(
        self,
        prompt: str,
        session_id: str | None = None,
        max_iterations: int = 10,
    ) -> LoopResult:
        """
        Run the mock harness.

        Args:
            prompt: User input
            session_id: Optional session ID
            max_iterations: Maximum iterations

        Returns:
            LoopResult
        """
        session_id = session_id or "mock-session"
        self._response_index = 0

        # Create or get session
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(id=session_id)

        session = self._sessions[session_id]
        session.add_message(Message(role="user", content=prompt))

        iteration = 0
        total_usage = TokenUsage()

        try:
            while iteration < max_iterations and self._response_index < len(self.config.responses):
                # Get next response
                mock_response = self.config.responses[self._response_index]
                self._response_index += 1

                response = mock_response.to_llm_response()

                # Update usage
                total_usage.input_tokens += response.usage.input_tokens
                total_usage.output_tokens += response.usage.output_tokens

                # Add assistant message
                session.add_message(Message(role="assistant", content=response.content))

                # Record if in record mode
                if self.config.record_mode:
                    self._recordings.append(
                        {
                            "type": "llm_response",
                            "iteration": iteration,
                            "response": {
                                "content": response.content,
                                "tool_calls": [tc.to_dict() for tc in response.tool_calls],
                                "stop_reason": response.stop_reason.value,
                            },
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                # Handle tool calls
                if response.is_tool_use:
                    for tool_call in response.tool_calls:
                        # Check for mock tool result
                        if tool_call.name in self._tool_results:
                            result_content = self._tool_results[tool_call.name]
                        else:
                            # Use default mock result
                            result_content = f"Mock result for {tool_call.name}"

                        session.add_message(
                            Message(
                                role="tool",
                                content=result_content,
                                metadata={"tool_call_id": tool_call.id},
                            )
                        )

                        # Record
                        if self.config.record_mode:
                            self._recordings.append(
                                {
                                    "type": "tool_result",
                                    "tool_name": tool_call.name,
                                    "tool_call_id": tool_call.id,
                                    "result": result_content,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

                    iteration += 1
                    continue

                # Done
                session.token_usage = total_usage
                return LoopResult(
                    status=LoopState.COMPLETED,
                    session=session,
                    messages=session.messages,
                    final_response=response.content,
                    iterations=iteration,
                    token_usage=total_usage,
                )

            # Max iterations reached
            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=iteration,
                error="Max iterations reached or responses exhausted",
                token_usage=total_usage,
            )

        except Exception as e:
            return LoopResult(
                status=LoopState.ERROR,
                session=session,
                messages=session.messages,
                iterations=iteration,
                error=str(e),
                token_usage=total_usage,
            )

    async def run_goal(
        self,
        goal: str | GoalConfig,
        **kwargs,
    ) -> GoalResult:
        """
        Mock implementation of run_goal for testing.

        Returns a successful GoalResult for testing purposes.

        Args:
            goal: Goal description or GoalConfig
            **kwargs: Additional arguments (ignored)

        Returns:
            GoalResult with ACHIEVED status
        """
        from harness.loop.types import GoalConfig, GoalResult, GoalStatus

        # Extract goal description
        description = goal.description if isinstance(goal, GoalConfig) else goal

        # Return mock successful result
        return GoalResult(
            goal=description,
            status=GoalStatus.ACHIEVED,
            total_iterations=1,
            context_resets=0,
            total_tokens={"input": 100, "output": 50},
            duration_seconds=0.1,
            final_response=f"Mock goal achieved: {description}",
            verification_log=[],
        )

    def activate_skill(self, skill_name: str) -> None:
        """Mock skill activation (does nothing)."""
        pass

    def get_recordings(self) -> list[dict[str, Any]]:
        """Get all recordings."""
        return self._recordings.copy()

    def save_recording(self, path: Path) -> None:
        """Save recordings to file."""
        if not self._recordings:
            logger.warning("No recordings to save")
            return

        with open(path, "w") as f:
            json.dump(
                {
                    "recordings": self._recordings,
                    "config": {
                        "responses_count": len(self.config.responses),
                        "tool_results": self._tool_results,
                    },
                },
                f,
                indent=2,
            )

        logger.info(f"Saved recording to {path}")

    def load_recording(self, path: Path) -> None:
        """Load recording from file for playback."""
        with open(path) as f:
            data = json.load(f)

        # Convert recordings back to responses
        responses = []
        for rec in data["recordings"]:
            if rec["type"] == "llm_response":
                resp_data = rec["response"]
                responses.append(
                    MockResponse(
                        content=resp_data["content"],
                        tool_calls=[
                            ToolCall.from_dict(tc) for tc in resp_data.get("tool_calls", [])
                        ],
                        stop_reason=StopReason(resp_data["stop_reason"]),
                    )
                )

        self.set_responses(responses)

        if "config" in data and "tool_results" in data["config"]:
            self._tool_results = data["config"]["tool_results"]

        logger.info(f"Loaded recording from {path}")

    def reset(self) -> None:
        """Reset mock state."""
        self._response_index = 0
        self._recordings.clear()
        self._sessions.clear()

    @property
    def current_response_index(self) -> int:
        """Current response index."""
        return self._response_index

    @property
    def responses_remaining(self) -> int:
        """Number of responses remaining."""
        return len(self.config.responses) - self._response_index
