"""
Anthropic Claude LLM client implementation.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import Chunk, ChunkType, LLMResponse, StopReason, TokenUsage, ToolCall

if TYPE_CHECKING:
    from harness.core import StreamingConfig
    from harness.types import ProgressCallback


class AnthropicClient(LLMClient):
    """
    LLM client for Anthropic Claude models.

    This client wraps the official Anthropic SDK and provides
    a consistent interface for the Harness framework.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        **kwargs,
    ):
        if config is None:
            config = LLMConfig(model=model, **kwargs)
        super().__init__(config)

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        # Lazy import to avoid dependency issues
        self._client = None

    def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self.config.model

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Make a call to Claude."""
        client = self._get_client()

        # Convert messages if using compatibility mode
        messages = self._convert_messages(messages)

        # Build request parameters
        params = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": messages,
        }

        if system:
            params["system"] = system

        if tools:
            params["tools"] = [t.to_api_format() for t in tools]

        # Add temperature if specified
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]
        elif self.config.temperature != 1.0:
            params["temperature"] = self.config.temperature

        # Make the API call
        response = await client.messages.create(**params)

        # Parse response
        return self._parse_response(response)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: "ProgressCallback | None" = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream response from Claude with backpressure control.

        Args:
            messages: Conversation messages
            tools: Available tools
            system: System prompt
            on_chunk: Callback for each text chunk
            on_progress: Callback for progress events (including backpressure)
            **kwargs: Additional parameters

        Yields:
            Text chunks from the response
        """
        from harness.core import StreamingConfig, StreamingHandler

        client = self._get_client()

        # Initialize streaming handler with backpressure control
        streaming_config = self.config.streaming_config or StreamingConfig()
        handler = StreamingHandler(
            config=streaming_config,
            on_progress=on_progress,
        )

        # Convert messages if using compatibility mode
        messages = self._convert_messages(messages)

        # Build request parameters
        params = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": messages,
        }

        if system:
            params["system"] = system

        if tools:
            params["tools"] = [t.to_api_format() for t in tools]

        # Stream the response with backpressure handling
        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                # Create chunk and process through handler
                chunk = Chunk(type=ChunkType.TEXT, content=text)
                await handler.handle(chunk)

                # Apply backpressure if needed
                if handler.should_pause:
                    await asyncio.sleep(0.01)

                if on_chunk:
                    on_chunk(text)

                yield text

    def _parse_response(self, response) -> LLMResponse:
        """Parse Anthropic response into our format."""
        # Extract content
        content = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif hasattr(block, "name"):
                # Tool use block
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if hasattr(block, "input") else {},
                ))

        # Map stop reason
        stop_reason_map = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.STOP_SEQUENCE,
        }
        stop_reason = stop_reason_map.get(
            response.stop_reason,
            StopReason.END_TURN
        )

        # Parse usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert messages to Anthropic API format.

        Anthropic API expects tool results as:
        - role: "user"
        - content: [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]

        Our SDK internally uses role: "tool" which needs to be converted.
        For proxy APIs that don't support tool_result blocks, use compatibility mode.

        Args:
            messages: Original messages

        Returns:
            Converted messages in Anthropic API format
        """
        converted = []
        for msg in messages:
            role = msg.get("role", "")

            if role == "tool":
                # Tool results must be sent as user messages with tool_result blocks
                tool_call_id = msg.get("metadata", {}).get("tool_call_id", "")
                content = msg.get("content", "")
                is_error = msg.get("metadata", {}).get("is_error", False)

                if self.config.tool_result_role == "tool":
                    # Native Anthropic format: user message with tool_result block
                    tool_result_block = {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": content,
                    }
                    if is_error:
                        tool_result_block["is_error"] = True

                    converted_msg = {
                        "role": "user",
                        "content": [tool_result_block],
                    }
                else:
                    # Compatibility mode for proxy APIs: plain text user message
                    converted_msg = {
                        "role": "user",
                        "content": (
                            f"[TOOL RESULT]\n"
                            f"This is the result of your tool call. "
                            f"Use this information to complete the user's original request.\n\n"
                            f"{content}"
                        ),
                    }
                converted.append(converted_msg)
            else:
                converted.append(msg)

        return converted
