"""
OpenAI LLM client implementation.
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import Chunk, ChunkType, LLMResponse, StopReason, TokenUsage, ToolCall

if TYPE_CHECKING:
    from harness.core import StreamingConfig
    from harness.types import ProgressCallback

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """
    LLM client for OpenAI models.

    This client wraps the official OpenAI SDK and provides
    a consistent interface for the Harness framework.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o",
        base_url: str | None = None,
        **kwargs,
    ):
        if config is None:
            config = LLMConfig(model=model, **kwargs)
        super().__init__(config)

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._client = None

    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            import openai

            client_kwargs = {"api_key": self._api_key}
            if self._base_url:
                client_kwargs["base_url"] = self._base_url

            self._client = openai.AsyncOpenAI(**client_kwargs)
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
        """Make a call to OpenAI."""
        client = self._get_client()

        # Build messages with system prompt
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        # Build request parameters
        params: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": formatted_messages,
        }

        # Add temperature if specified
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]
        elif self.config.temperature != 1.0:
            params["temperature"] = self.config.temperature

        # Add tools if provided
        if tools:
            params["tools"] = [self._format_tool(t) for t in tools]
            params["tool_choice"] = "auto"

        logger.info(f"OpenAI call: model={self.config.model}, base_url={self._base_url}, messages={len(formatted_messages)}, tools={len(tools) if tools else 0}")

        # Make the API call
        try:
            response = await client.chat.completions.create(**params)
            logger.info(f"OpenAI response: finish_reason={response.choices[0].finish_reason if response.choices else 'no choices'}")
        except Exception as e:
            logger.exception(f"OpenAI API error: {type(e).__name__}: {e}")
            raise

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
        Stream response from OpenAI with backpressure control.

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

        # Build messages with system prompt
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        # Build request parameters
        params: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": formatted_messages,
            "stream": True,
        }

        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]
        elif self.config.temperature != 1.0:
            params["temperature"] = self.config.temperature

        if tools:
            params["tools"] = [self._format_tool(t) for t in tools]
            params["tool_choice"] = "auto"

        # Stream the response with backpressure handling
        stream = await client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content

                # Create chunk and process through handler
                stream_chunk = Chunk(type=ChunkType.TEXT, content=text)
                await handler.handle(stream_chunk)

                # Apply backpressure if needed
                if handler.should_pause:
                    await asyncio.sleep(0.01)

                if on_chunk:
                    on_chunk(text)

                yield text

    def _format_tool(self, tool: ToolDefinition) -> dict[str, Any]:
        """Format tool for OpenAI API."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    def _parse_response(self, response) -> LLMResponse:
        """Parse OpenAI response into our format."""
        choice = response.choices[0]
        message = choice.message

        # Extract content
        content = message.content or ""

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                import json

                args = {}
                if tc.function.arguments:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        # Map stop reason
        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
            "content_filter": StopReason.END_TURN,
        }
        stop_reason = stop_reason_map.get(
            choice.finish_reason,
            StopReason.END_TURN
        )

        # Parse usage
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )
