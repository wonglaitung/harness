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

        # Eagerly initialize the client to catch import errors early
        # This is especially important on Windows with qasync
        logger.info(f"OpenAIClient.__init__: api_key={'*' * 8 if self._api_key else 'None'}, base_url={self._base_url}")
        # Pre-import openai module
        import openai
        logger.info(f"OpenAI module pre-imported, version: {openai.__version__}")

    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            logger.info("Creating OpenAI client instance...")
            import openai

            client_kwargs = {"api_key": self._api_key}
            if self._base_url:
                client_kwargs["base_url"] = self._base_url

            # Use synchronous client to avoid issues with qasync on Windows
            self._client = openai.OpenAI(**client_kwargs)
            logger.info("OpenAI client created (sync mode for compatibility)")
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
        logger.info(f"OpenAI call starting: model={self.config.model}, base_url={self._base_url}")

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

        logger.info(f"OpenAI API request: messages={len(formatted_messages)}, tools={len(tools) if tools else 0}")

        # Use separate thread pool + async polling to avoid qasync/Windows issues
        import concurrent.futures

        def sync_call():
            logger.info("sync_call: Starting API request")
            client = self._get_client()  # Returns sync client
            result = client.chat.completions.create(**params)
            logger.info("sync_call: API request completed")
            return result

        try:
            # Use independent thread pool, completely separate from asyncio
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(sync_call)

                # Async polling to check if Future is done, avoiding run_in_executor entirely
                while not future.done():
                    await asyncio.sleep(0.02)  # Release control, keep UI responsive

                # Get result directly (already completed, non-blocking)
                response = future.result()

            logger.info(f"OpenAI response received: finish_reason={response.choices[0].finish_reason if response.choices else 'no choices'}")
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

        Uses a sync client in a separate thread with a queue to avoid
        qasync/Windows compatibility issues.
        """
        from harness.core import StreamingConfig, StreamingHandler
        import queue
        import threading

        client = self._get_client()

        streaming_config = self.config.streaming_config or StreamingConfig()
        handler = StreamingHandler(
            config=streaming_config,
            on_progress=on_progress,
        )

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

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

        # Use sync queue to bridge thread (producer) -> coroutine (consumer)
        chunk_queue = queue.Queue()
        exception_holder = {}

        def sync_stream_worker():
            try:
                logger.info("sync_stream_worker: Starting stream request")
                response_stream = client.chat.completions.create(**params)
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        chunk_queue.put(text)
            except Exception as e:
                logger.exception("Error in sync_stream_worker")
                exception_holder["exception"] = e
            finally:
                # Sentinel to signal end of stream
                chunk_queue.put(None)

        # Start pure native thread for streaming request
        worker_thread = threading.Thread(target=sync_stream_worker, daemon=True)
        worker_thread.start()

        # Consume queue in async coroutine
        while True:
            if "exception" in exception_holder:
                raise exception_holder["exception"]

            if not chunk_queue.empty():
                text = chunk_queue.get_nowait()
                if text is None:  # Sentinel received, stream ended
                    break

                stream_chunk = Chunk(type=ChunkType.TEXT, content=text)
                await handler.handle(stream_chunk)

                if handler.should_pause:
                    await asyncio.sleep(0.01)

                if on_chunk:
                    on_chunk(text)

                yield text
            else:
                # Queue empty, release control to prevent CPU spin
                await asyncio.sleep(0.01)

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
