"""
Embedded Llama client using-cpp-python.

Provides CPU-based inference for GGUF models (e.g., Qwen2.5-1.5B)
for use as a routing classifier.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import LLMResponse, StopReason, TokenUsage

logger = logging.getLogger(__name__)

# Global thread pool for llama.cpp calls (avoid creating per-request)
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool for llama.cpp calls."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llama-cpp")
    return _executor


class EmbeddedLlamaClient(LLMClient):
    """
    Embedded LLM client using llama-cpp-python.

    Loads a GGUF model directly in-process for CPU inference.
    Ideal for routing decisions where low latency is required.

    Usage:
        client = EmbeddedLlamaClient(
            model_path="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            n_ctx=2048,
        )
        response = await client.call([{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,  # 0 = CPU only
        config: LLMConfig | None = None,
        **kwargs,
    ):
        if config is None:
            config = LLMConfig(model=model_path, max_tokens=10)
        super().__init__(config)

        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._model = None

        # Lazy load - don't load model until first call
        self._loaded = False

    def _load_model(self):
        """Load the GGUF model (lazy loading)."""
        if self._loaded:
            return

        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise ImportError(
                "llama-cpp-python is required for embedded inference. "
                "Install with: pip install llama-cpp-python"
            ) from e

        logger.info(f"Loading GGUF model: {self._model_path}")

        self._model = Llama(
            model_path=self._model_path,
            n_ctx=self._n_ctx,
            n_gpu_layers=self._n_gpu_layers,
            verbose=False,
        )

        self._loaded = True
        logger.info(f"Model loaded successfully: {self._model_path}")

    @property
    def model_name(self) -> str:
        """Return the model path as the model name."""
        return self._model_path

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Make a call to the embedded model.

        Note: llama-cpp-python is synchronous, so we run in a thread pool.
        """
        # Lazy load on first call
        if not self._loaded:
            self._load_model()

        # Build messages for llama.cpp format
        formatted_messages = []

        if system:
            formatted_messages.append({"role": "system", "content": system})

        formatted_messages.extend(messages)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        executor = _get_executor()

        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        def sync_call():
            return self._model.create_chat_completion(
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=kwargs.get("temperature", 0.0),  # Deterministic for routing
            )

        try:
            response = await loop.run_in_executor(executor, sync_call)
        except Exception as e:
            logger.error(f"Embedded LLM call failed: {e}")
            raise

        return self._parse_response(response)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Any = None,
        **kwargs,
    ):
        """
        Stream response from the embedded model.

        Note: For routing, we typically don't need streaming.
        This is a simplified implementation.
        """
        # For routing, just use the sync call
        response = await self.call(messages, tools, system, **kwargs)

        if response.content:
            if on_chunk:
                on_chunk(response.content)
            yield response.content

    def _parse_response(self, response: dict) -> LLMResponse:
        """Parse llama.cpp response into our format."""
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        content = message.get("content", "")

        # Map finish_reason
        finish_reason = choice.get("finish_reason", "stop")
        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "length": StopReason.MAX_TOKENS,
        }
        stop_reason = stop_reason_map.get(finish_reason, StopReason.END_TURN)

        # Parse usage
        usage_data = response.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMResponse(
            content=content,
            tool_calls=[],
            stop_reason=stop_reason,
            usage=usage,
        )
