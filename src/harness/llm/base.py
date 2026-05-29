"""
Base LLM client interface.

Defines the abstract interface that all LLM implementations must follow.
Includes retry logic with exponential backoff for resilient API calls.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from harness.types import LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Base configuration for LLM clients."""
    model: str
    max_tokens: int = 16384  # Output tokens (reasonable for 64K context models)
    temperature: float = 1.0
    timeout: float = 120.0
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM."""
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.

    All LLM implementations (Anthropic, OpenAI, local models) must inherit
    from this class and implement its abstract methods.
    """

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Make a synchronous call to the LLM.

        Args:
            messages: List of messages in conversation
            tools: Available tools for the LLM to use
            system: System prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse: The response from the LLM
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream response from the LLM.

        Args:
            messages: List of messages in conversation
            tools: Available tools for the LLM to use
            system: System prompt
            on_chunk: Callback for each chunk
            **kwargs: Additional provider-specific parameters

        Yields:
            str: Each chunk of the response
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass

    def supports_tools(self) -> bool:
        """Check if the client supports tool use."""
        return True

    def supports_vision(self) -> bool:
        """Check if the client supports vision/image inputs."""
        return False

    async def call_with_retry(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Call the LLM with automatic retry on transient errors.

        Uses exponential backoff for rate limits and network errors.

        Args:
            messages: List of messages in conversation
            tools: Available tools for the LLM to use
            system: System prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse: The response from the LLM

        Raises:
            Exception: If all retries are exhausted
        """
        last_error: Exception | None = None

        for attempt in range(self.config.retry_count):
            try:
                return await self.call(messages, tools, system, **kwargs)

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_message = str(e).lower()

                # Check if we should retry
                should_retry = self._should_retry(error_type, error_message)

                if not should_retry or attempt == self.config.retry_count - 1:
                    raise

                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{self.config.retry_count}): "
                    f"{error_type}: {e}. Retrying in {delay:.1f}s..."
                )

                await asyncio.sleep(delay)

        # Should not reach here, but for type safety
        raise last_error or RuntimeError("Unexpected retry loop exit")

    def _should_retry(self, error_type: str, error_message: str) -> bool:
        """Determine if an error should be retried."""
        # Retry on rate limits
        if any(indicator in error_message for indicator in [
            "ratelimit", "rate_limit", "429", "too many requests"
        ]):
            return True

        # Retry on network errors
        if any(indicator in error_message for indicator in [
            "connection", "network", "socket", "timeout", "timed out"
        ]):
            return True

        # Retry on 5xx server errors
        if "500" in error_message or "502" in error_message or "503" in error_message:
            return True

        # Don't retry on client errors (4xx except 429)
        if "400" in error_message or "401" in error_message or "403" in error_message:
            return False

        # Don't retry on context length errors
        if "context" in error_message and "length" in error_message:
            return False

        # Default: don't retry unknown errors
        return False

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        base_delay = self.config.retry_delay
        max_delay = 60.0

        # Exponential backoff: delay * 2^attempt
        delay = base_delay * (2 ** attempt)

        # Cap at max delay
        delay = min(delay, max_delay)

        # Add jitter (±10%)
        import random
        jitter = delay * 0.1 * random.random()
        delay = delay + jitter

        return delay
