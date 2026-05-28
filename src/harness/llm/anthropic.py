"""
Anthropic Claude LLM client implementation.
"""

import os
from collections.abc import AsyncIterator, Callable
from typing import Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import LLMResponse, StopReason, TokenUsage, ToolCall


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
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response from Claude."""
        client = self._get_client()

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

        # Stream the response
        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
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
