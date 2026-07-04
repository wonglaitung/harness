"""
OpenAI LLM client implementation.
"""

import asyncio
import concurrent.futures
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

        # Global thread pool for this client, avoid frequent create/destroy
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="HarnessOpenAI"
        )

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

        # Convert multimodal content to OpenAI format
        for msg in messages:
            converted_msg = msg.copy()
            content = msg.get("content")

            # If content is a list (multimodal), convert format
            if isinstance(content, list):
                converted_msg["content"] = self._convert_multimodal_content(content)

            formatted_messages.append(converted_msg)

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

        def sync_call():
            logger.info("sync_call: Starting API request")
            client = self._get_client()  # Returns sync client
            result = client.chat.completions.create(**params)
            logger.info("sync_call: API request completed")
            return result

        try:
            # Use instance's thread pool directly (no 'with' to avoid shutdown issues)
            future = self._executor.submit(sync_call)

            # Async polling to check if Future is done, avoiding run_in_executor entirely
            while not future.done():
                await asyncio.sleep(0.02)  # Release control, keep UI responsive

            # Get result directly (already completed, non-blocking)
            response = future.result()

            # Handle non-standard API responses (some APIs return string on error)
            if isinstance(response, str):
                logger.error(f"OpenAI API returned string instead of response object: {response[:200]}")
                raise ValueError(f"API returned non-standard response: {response[:200]}")

            logger.info(f"OpenAI response received: finish_reason={response.choices[0].finish_reason if response.choices else 'no choices'}")

        except Exception as e:
            error_str = str(e)

            # Check if error is about unsupported content type (file type)
            # This happens with OpenAI-compatible APIs that don't support documents
            if "content type" in error_str and ("file" in error_str or "must be text" in error_str):
                logger.warning(f"API doesn't support 'file' content type, retrying with text conversion: {error_str}")

                # Check if we have document content in original messages
                has_documents = False
                for msg in messages:
                    content = msg.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "document":
                                has_documents = True
                                break

                if has_documents:
                    # Convert documents to text and retry
                    converted_messages = []
                    for msg in messages:
                        converted_msg = msg.copy()
                        content = msg.get("content")
                        if isinstance(content, list):
                            converted_msg["content"] = self._convert_documents_to_text(content)
                        converted_messages.append(converted_msg)

                    # Rebuild formatted messages
                    formatted_messages = []
                    if system:
                        formatted_messages.append({"role": "system", "content": system})
                    formatted_messages.extend(converted_messages)
                    params["messages"] = formatted_messages

                    logger.info(f"Retrying with converted messages: {len(formatted_messages)} messages")

                    # Retry the call
                    try:
                        future = self._executor.submit(sync_call)
                        while not future.done():
                            await asyncio.sleep(0.02)
                        response = future.result()

                        if isinstance(response, str):
                            raise ValueError(f"API returned non-standard response: {response[:200]}")

                        logger.info(f"Retry successful: finish_reason={response.choices[0].finish_reason if response.choices else 'no choices'}")

                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        raise retry_error
                else:
                    raise e
            else:
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

    def supports_vision(self) -> bool:
        """Check if the client supports vision/image inputs."""
        # GPT-4o, GPT-4-turbo, and later models support vision
        model_name = self.config.model.lower()
        return any(v in model_name for v in ["gpt-4o", "gpt-4-turbo", "gpt-4-vision", "gpt-4-1106", "gpt-4-0125"])

    def _convert_multimodal_content(self, content: list[dict]) -> list[dict]:
        """
        Convert Anthropic-style multimodal content to OpenAI format.

        Anthropic format:
            {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
            {"type": "document", "source": {"type": "base64", "media_type": "...", "data": "..."}}

        OpenAI format:
            {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}
            {"type": "file", "file": {"filename": "...", "file_data": "data:...;base64,..."}}
        """
        converted = []
        for block in content:
            block_type = block.get("type", "")

            if block_type == "image":
                # Convert image block
                source = block.get("source", {})
                media_type = source.get("media_type", "image/png")
                data = source.get("data", "")
                converted.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{data}"}
                })

            elif block_type == "document":
                # Convert document block (OpenAI supports file type)
                source = block.get("source", {})
                media_type = source.get("media_type", "application/pdf")
                data = source.get("data", "")
                filename = block.get("filename", "document.pdf")
                converted.append({
                    "type": "file",
                    "file": {
                        "filename": filename,
                        "file_data": f"data:{media_type};base64,{data}"
                    }
                })

            else:
                # Keep text and other blocks unchanged
                converted.append(block)

        return converted

    def _convert_documents_to_text(self, content: list[dict]) -> list[dict]:
        """
        Convert document blocks to text for APIs that don't support file type.

        This is a fallback for OpenAI-compatible APIs that don't support the
        'file' content type (e.g., GLM, Qwen, other local models).

        Args:
            content: Original multimodal content list

        Returns:
            Content list with documents converted to text blocks (does NOT modify original)
        """
        import base64

        converted = []
        document_texts = []

        for block in content:
            block_type = block.get("type", "")

            if block_type == "document":
                # Decode document and add as text
                source = block.get("source", {})
                data = source.get("data", "")
                filename = block.get("filename", "document")
                media_type = source.get("media_type", "text/plain")

                try:
                    decoded_content = base64.b64decode(data).decode("utf-8", errors="replace")
                    file_info = f"\n\n--- Attached File: {filename} ---\n{decoded_content}\n--- End of File ---\n"
                    document_texts.append(file_info)
                    logger.info(f"Document '{filename}' converted to text ({len(decoded_content)} chars)")
                except Exception as e:
                    logger.warning(f"Failed to decode document '{filename}': {e}")
                    document_texts.append(f"\n\n[Attached file: {filename} - content could not be decoded]\n")

            elif block_type == "image":
                # Keep image blocks unchanged (copy to avoid modifying original)
                source = block.get("source", {})
                media_type = source.get("media_type", "image/png")
                data = source.get("data", "")
                converted.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{data}"}
                })

            else:
                # Copy other blocks (especially text) to avoid modifying original content
                if block_type == "text":
                    converted.append({
                        "type": "text",
                        "text": block.get("text", "")
                    })
                else:
                    converted.append(block.copy())

        # Append document texts to the last text block or create new one
        if document_texts:
            for i in range(len(converted) - 1, -1, -1):
                if converted[i].get("type") == "text":
                    converted[i]["text"] += "".join(document_texts)
                    break
            else:
                converted.append({
                    "type": "text",
                    "text": "".join(document_texts)
                })

        return converted

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
