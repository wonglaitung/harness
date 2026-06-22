"""
Embedded Llama client using llama-cpp-python.

Provides CPU-based inference for GGUF models (e.g., Qwen2.5-1.5B)
for use as a routing classifier.

Reuses model_presets.py design pattern for context_window="auto" support.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.model_presets import DEFAULT_PRESET, parse_context_window
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

    Reuses model_presets.py design:
    - context_window="auto" infers from model name in file path
    - Falls back to 2048 for unknown models (sufficient for routing)

    Usage:
        client = EmbeddedLlamaClient(
            model_path="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            context_window="auto",  # Infers from filename
        )
        response = await client.call([{"role": "user", "content": "Hello"}])
    """

    # GGUF filename patterns to strip when extracting model name
    QUANTIZATION_SUFFIXES = [
        "-q4_k_m", "-q4_k_s", "-q4_0", "-q5_k_m", "-q5_k_s", "-q5_0",
        "-q6_k", "-q8_0", "-f16", "-bf16",
    ]
    OTHER_SUFFIXES = ["-instruct", "-chat"]

    def __init__(
        self,
        model_path: str,
        context_window: int | str = "auto",  # "auto" or explicit int
        n_gpu_layers: int = 0,  # 0 = CPU only
        config: LLMConfig | None = None,
        **kwargs,
    ):
        if config is None:
            config = LLMConfig(model=model_path, max_tokens=10)
        super().__init__(config)

        self._model_path = model_path
        self._n_gpu_layers = n_gpu_layers
        self._model = None
        self._loaded = False

        # Parse context_window using model_presets pattern
        model_name = self._extract_model_name(model_path)
        parsed_ctx = parse_context_window(context_window, model_name)

        # For router models, use smaller default than DEFAULT_PRESET (64k)
        # Routing tasks typically need ~500-800 tokens, 2048 is sufficient
        if parsed_ctx == DEFAULT_PRESET.context_window:
            self._n_ctx = 2048
            logger.debug(f"Unknown model '{model_name}', using default ctx=2048 for routing")
        else:
            self._n_ctx = parsed_ctx
            logger.debug(f"Model '{model_name}' context_window={self._n_ctx}")

    def _extract_model_name(self, model_path: str) -> str:
        """
        Extract model name from GGUF file path.

        Example: "models/qwen3.5-0.8b-instruct-q4_k_m.gguf" → "qwen3.5-0.8b"
        """
        filename = Path(model_path).stem  # Remove .gguf extension

        # Strip quantization suffixes
        for suffix in self.QUANTIZATION_SUFFIXES:
            filename = filename.replace(suffix, "")

        # Strip other common suffixes
        for suffix in self.OTHER_SUFFIXES:
            filename = filename.replace(suffix, "")

        # Clean up any remaining artifacts
        filename = filename.strip("-_")

        return filename

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

        logger.info(f"Loading GGUF model: {self._model_path} (n_ctx={self._n_ctx})")

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
