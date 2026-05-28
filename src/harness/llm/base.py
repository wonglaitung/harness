"""
Base LLM client interface.

Defines the abstract interface that all LLM implementations must follow.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from harness.types import LLMResponse


@dataclass
class LLMConfig:
    """Base configuration for LLM clients."""
    model: str
    max_tokens: int = 4096
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
