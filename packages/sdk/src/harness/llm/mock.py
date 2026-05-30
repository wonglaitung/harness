"""
Mock LLM client for testing without real API calls.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import LLMResponse, StopReason, TokenUsage, ToolCall


@dataclass
class MockResponse:
    """Predefined mock response."""
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing.

    This client returns predefined responses without making real API calls.
    Useful for unit tests and development.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        responses: list[MockResponse] | None = None,
        model: str = "mock-model",
    ):
        if config is None:
            config = LLMConfig(model=model)
        super().__init__(config)

        self.responses = responses or []
        self._response_index = 0
        self._call_count = 0
        self._last_messages: list[dict[str, Any]] | None = None
        self._last_tools: list[ToolDefinition] | None = None

    def set_responses(self, responses: list[MockResponse]) -> None:
        """Set predefined responses."""
        self.responses = responses
        self._response_index = 0

    def add_response(self, response: MockResponse) -> None:
        """Add a response to the queue."""
        self.responses.append(response)

    @property
    def model_name(self) -> str:
        """Return the mock model name."""
        return self.config.model

    @property
    def call_count(self) -> int:
        """Return number of calls made."""
        return self._call_count

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Return a mock response."""
        self._call_count += 1
        self._last_messages = messages
        self._last_tools = tools

        # Get next predefined response or create a default one
        if self.responses and self._response_index < len(self.responses):
            mock = self.responses[self._response_index]
            self._response_index += 1
        else:
            # Default response
            mock = MockResponse(
                content="This is a mock response.",
                tool_calls=[],
                stop_reason=StopReason.END_TURN,
            )

        # Convert mock response to LLMResponse
        tool_calls = []
        for tc in mock.tool_calls:
            tool_calls.append(ToolCall(
                id=tc.get("id", f"mock_tool_{len(tool_calls)}"),
                name=tc.get("name", "unknown"),
                arguments=tc.get("arguments", {}),
            ))

        return LLMResponse(
            content=mock.content,
            tool_calls=tool_calls,
            stop_reason=mock.stop_reason,
            usage=TokenUsage(
                input_tokens=len(str(messages)) // 4,  # Rough estimate
                output_tokens=len(mock.content) // 4,
            ),
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a mock response."""
        # Get response content
        response = await self.call(messages, tools, system, **kwargs)

        # Stream in chunks
        words = response.content.split()
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            if on_chunk:
                on_chunk(chunk)
            yield chunk
            # Small delay to simulate streaming
            # await asyncio.sleep(0.01)  # Optional: uncomment for realistic streaming

    def reset(self) -> None:
        """Reset the mock client state."""
        self._response_index = 0
        self._call_count = 0
        self._last_messages = None
        self._last_tools = None


def create_tool_use_mock(
    tool_name: str,
    tool_args: dict[str, Any],
    final_response: str = "Done",
) -> list[MockResponse]:
    """
    Helper to create mock responses that simulate tool use.

    Args:
        tool_name: Name of the tool to call
        tool_args: Arguments for the tool
        final_response: Response after tool execution

    Returns:
        List of MockResponse objects
    """
    return [
        MockResponse(
            content="",  # Empty content when tool use
            tool_calls=[
                {
                    "id": "mock_tool_call_1",
                    "name": tool_name,
                    "arguments": tool_args,
                }
            ],
            stop_reason=StopReason.TOOL_USE,
        ),
        MockResponse(
            content=final_response,
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
        ),
    ]
