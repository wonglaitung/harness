"""
Token counting utilities for precise token budget management.

Uses tiktoken for accurate token counting across different LLM models.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.types import Message, ToolCall

# Model encoding mapping
MODEL_ENCODING_MAP = {
    # Claude models use cl100k_base
    "claude": "cl100k_base",
    "claude-2": "cl100k_base",
    "claude-3": "cl100k_base",
    "claude-instant": "cl100k_base",
    # GPT-4 models
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-3.5": "cl100k_base",
}

# Default encoding for unknown models
DEFAULT_ENCODING = "cl100k_base"


class TokenCounter:
    """
    Accurate token counter using tiktoken.

    Provides token counting for text, messages, and tool definitions.
    Uses caching for performance.

    Example:
        >>> counter = TokenCounter("claude-sonnet-4-6")
        >>> counter.count("Hello, world!")
        4
        >>> counter.count_messages([Message(role="user", content="Hi")])
        5
    """

    def __init__(self, model: str | None = None):
        """
        Initialize token counter.

        Args:
            model: Model name to determine encoding (e.g., "claude-sonnet-4-6")
        """
        self._encoding_name = self._get_encoding_for_model(model)
        self._encoder = self._get_encoder(self._encoding_name)
        self._cache: dict[str, int] = {}

    def _get_encoding_for_model(self, model: str | None) -> str:
        """Get encoding name for a model."""
        if not model:
            return DEFAULT_ENCODING

        model_lower = model.lower()

        # Check for exact matches first
        for prefix, encoding in MODEL_ENCODING_MAP.items():
            if model_lower.startswith(prefix):
                return encoding

        return DEFAULT_ENCODING

    @staticmethod
    @functools.lru_cache(maxsize=8)
    def _get_encoder(encoding_name: str):
        """Get tiktoken encoder with caching."""
        try:
            import tiktoken
            return tiktoken.get_encoding(encoding_name)
        except ImportError:
            raise ImportError(
                "tiktoken is required for token counting. "
                "Install it with: pip install tiktoken>=0.5.0"
            )

    def count(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Check cache
        if text in self._cache:
            return self._cache[text]

        # Count and cache
        count = len(self._encoder.encode(text))
        self._cache[text] = count
        return count

    def count_messages(self, messages: list[Message]) -> int:
        """
        Count total tokens in a list of messages.

        Includes overhead for message structure (role, formatting).

        Args:
            messages: List of messages to count

        Returns:
            Total token count including overhead
        """
        total = 0

        for msg in messages:
            # Message overhead: role, separators
            # Approximate: 4 tokens per message for structure
            total += 4

            # Count content
            content = msg.content
            if isinstance(content, str):
                total += self.count(content)
            elif isinstance(content, list):
                # Handle multi-part content
                for part in content:
                    if isinstance(part, dict):
                        if "text" in part:
                            total += self.count(part["text"])
                        elif "type" in part:
                            total += 2  # Type field overhead

        # Conversation overhead
        total += 3

        return total

    def estimate_tool_overhead(self, tools: list) -> int:
        """
        Estimate token overhead for tool definitions.

        Args:
            tools: List of tool definitions

        Returns:
            Estimated token count for tool schemas
        """
        if not tools:
            return 0

        total = 0

        for tool in tools:
            # Base overhead per tool
            total += 10

            # Tool name
            if hasattr(tool, "name"):
                total += self.count(tool.name)
            elif isinstance(tool, dict):
                total += self.count(tool.get("name", ""))

            # Tool description
            if hasattr(tool, "description"):
                total += self.count(tool.description or "")
            elif isinstance(tool, dict):
                total += self.count(tool.get("description", ""))

            # Input schema (rough estimate)
            if hasattr(tool, "input_schema"):
                schema = tool.input_schema
            elif isinstance(tool, dict):
                schema = tool.get("input_schema", {})
            else:
                schema = {}

            # Schema overhead: estimate based on properties
            if schema:
                properties = schema.get("properties", {})
                total += len(properties) * 5  # ~5 tokens per property
                total += 20  # Schema structure overhead

        return total

    def estimate_tool_result_overhead(self, tool_results: list) -> int:
        """
        Estimate token overhead for tool results in context.

        Args:
            tool_results: List of tool results

        Returns:
            Estimated token count for tool result formatting
        """
        if not tool_results:
            return 0

        total = 0

        for result in tool_results:
            # Overhead for tool result structure
            total += 8

            # Tool call ID
            if hasattr(result, "tool_call_id"):
                total += len(result.tool_call_id) // 4
            elif isinstance(result, dict):
                tool_id = result.get("tool_call_id", "")
                total += len(tool_id) // 4

            # Result content
            if hasattr(result, "content"):
                total += self.count(result.content or "")
            elif isinstance(result, dict):
                total += self.count(result.get("content", ""))

        return total

    def clear_cache(self) -> None:
        """Clear the token count cache."""
        self._cache.clear()

    def get_budget_allocation(
        self,
        max_tokens: int,
        system_prompt: str | None = None,
        tools: list | None = None,
    ) -> dict[str, int]:
        """
        Calculate token budget allocation.

        Priority: system_prompt > recent_messages > skills > memory

        Args:
            max_tokens: Maximum context tokens (e.g., 200000)
            system_prompt: System prompt text
            tools: Available tools

        Returns:
            Dict with allocated tokens for each component
        """
        # Reserve tokens for response
        response_reserve = 4096

        # Available tokens for input
        available = max_tokens - response_reserve

        allocation = {
            "system_prompt": 0,
            "tools": 0,
            "recent_messages": 0,
            "skills": 0,
            "memory": 0,
            "response_reserve": response_reserve,
            "total_available": available,
        }

        # Allocate system prompt (high priority, exact fit)
        if system_prompt:
            system_tokens = self.count(system_prompt)
            allocation["system_prompt"] = min(system_tokens, available)
            available -= allocation["system_prompt"]

        # Allocate tool overhead
        if tools:
            tool_tokens = self.estimate_tool_overhead(tools)
            allocation["tools"] = min(tool_tokens, available)
            available -= allocation["tools"]

        # Allocate remaining to messages (70%), skills (20%), memory (10%)
        if available > 0:
            allocation["recent_messages"] = int(available * 0.7)
            allocation["skills"] = int(available * 0.2)
            allocation["memory"] = int(available * 0.1)

        return allocation


# Convenience function
def count_tokens(text: str, model: str | None = None) -> int:
    """
    Quick token count for text.

    Args:
        text: Text to count
        model: Optional model name

    Returns:
        Token count
    """
    counter = TokenCounter(model)
    return counter.count(text)
