"""
Context compressor for managing long conversations.

Implements automatic compression strategies to keep context within budget.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from harness.types import Message

if TYPE_CHECKING:
    from harness.memory.token_counter import TokenCounter

logger = logging.getLogger(__name__)


@dataclass
class CompressionConfig:
    """Configuration for context compression."""
    min_messages_before_compress: int = 10  # Minimum messages before considering compression
    keep_recent_messages: int = 5  # Always keep this many recent messages
    keep_system_messages: bool = True  # Keep system messages
    summary_max_tokens: int = 500  # Max tokens for generated summary
    compression_ratio: float = 0.5  # Target ratio after compression


@dataclass
class CompressionResult:
    """Result of context compression."""
    original_messages: list[Message]
    compressed_messages: list[Message]
    summary: str | None = None
    tokens_before: int = 0
    tokens_after: int = 0
    messages_removed: int = 0

    @property
    def compression_saved(self) -> int:
        """Tokens saved by compression."""
        return self.tokens_before - self.tokens_after


class ContextCompressor:
    """
    Compresses conversation context to fit within token budget.

    Strategies (in order):
    1. Remove old messages beyond keep_recent_messages
    2. Generate summary of removed messages
    3. Truncate long tool results

    Example:
        >>> compressor = ContextCompressor(token_counter)
        >>> result = compressor.compress(messages, target_tokens=50000)
        >>> compressed_messages = result.compressed_messages
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        config: CompressionConfig | None = None,
    ):
        self.token_counter = token_counter
        self.config = config or CompressionConfig()

    def compress(
        self,
        messages: list[Message],
        target_tokens: int,
        system_messages: list[Message] | None = None,
    ) -> CompressionResult:
        """
        Compress messages to fit within target tokens.

        Args:
            messages: All messages to potentially compress
            target_tokens: Target token count
            system_messages: Optional separate system messages (preserved)

        Returns:
            CompressionResult with compressed messages and metadata
        """
        if len(messages) < self.config.min_messages_before_compress:
            return CompressionResult(
                original_messages=messages,
                compressed_messages=messages,
                tokens_before=self._count_tokens(messages),
                tokens_after=self._count_tokens(messages),
            )

        tokens_before = self._count_tokens(messages)

        if tokens_before <= target_tokens:
            return CompressionResult(
                original_messages=messages,
                compressed_messages=messages,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
            )

        # Strategy 1: Keep recent messages, summarize older ones
        compressed, summary = self._compress_with_summary(messages, target_tokens)

        tokens_after = self._count_tokens(compressed)

        return CompressionResult(
            original_messages=messages,
            compressed_messages=compressed,
            summary=summary,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            messages_removed=len(messages) - len(compressed),
        )

    def _compress_with_summary(
        self,
        messages: list[Message],
        target_tokens: int,
    ) -> tuple[list[Message], str | None]:
        """
        Compress by keeping recent messages and summarizing older ones.

        Args:
            messages: Messages to compress
            target_tokens: Target token count

        Returns:
            Tuple of (compressed_messages, summary)
        """
        keep_count = self.config.keep_recent_messages

        # Always keep the most recent messages
        recent_messages = messages[-keep_count:] if len(messages) > keep_count else messages
        old_messages = messages[:-keep_count] if len(messages) > keep_count else []

        if not old_messages:
            return messages, None

        # Generate summary of old messages
        summary = self._generate_summary(old_messages)

        # Check if we're within budget
        summary_msg = Message(
            role="system",
            content=f"[Previous conversation summary]\n{summary}",
        ) if summary else None

        compressed = []
        if summary_msg:
            compressed.append(summary_msg)
        compressed.extend(recent_messages)

        return compressed, summary

    def _generate_summary(self, messages: list[Message]) -> str:
        """
        Generate a summary of messages.

        Uses simple heuristic summarization (not LLM-based for MVP).
        For production, this could be enhanced to use LLM summarization.

        Args:
            messages: Messages to summarize

        Returns:
            Summary string
        """
        if not messages:
            return ""

        summary_parts = []

        # Track key information
        user_requests = []
        assistant_actions = []
        tool_calls = []
        key_decisions = []

        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else ""

            if msg.role == "user":
                # Capture user requests (truncate long ones)
                preview = content[:200] + "..." if len(content) > 200 else content
                user_requests.append(f"- User asked: {preview}")

            elif msg.role == "assistant":
                # Capture assistant responses
                preview = content[:200] + "..." if len(content) > 200 else content
                assistant_actions.append(f"- Assistant: {preview}")

            elif msg.role == "tool":
                # Note tool usage
                tool_name = msg.metadata.get("tool_name", "unknown")
                tool_calls.append(f"- Tool: {tool_name}")

        # Build summary
        if user_requests:
            summary_parts.append("### User Requests")
            summary_parts.extend(user_requests[-5:])  # Keep last 5

        if assistant_actions:
            summary_parts.append("\n### Key Actions")
            summary_parts.extend(assistant_actions[-5:])

        if tool_calls:
            summary_parts.append("\n### Tools Used")
            summary_parts.extend(tool_calls[-10:])

        summary = "\n".join(summary_parts)

        # Truncate if too long
        max_summary_chars = self.config.summary_max_tokens * 4  # Rough char estimate
        if len(summary) > max_summary_chars:
            summary = summary[:max_summary_chars] + "\n... (truncated)"

        return summary

    def _count_tokens(self, messages: list[Message]) -> int:
        """Count total tokens in messages."""
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else ""
            total += self.token_counter.count(content)
            total += 4  # Message format overhead
        return total

    def should_compress(
        self,
        messages: list[Message],
        current_tokens: int,
        max_tokens: int,
    ) -> bool:
        """
        Determine if compression is needed.

        Args:
            messages: Current messages
            current_tokens: Current token count
            max_tokens: Maximum allowed tokens

        Returns:
            True if compression is recommended
        """
        if len(messages) < self.config.min_messages_before_compress:
            return False

        return current_tokens > max_tokens


class IncrementalTokenCounter:
    """
    Token counter with caching for better performance.

    Caches token counts for message content to avoid recomputation.
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        cache_size: int = 1000,
    ):
        self.token_counter = token_counter
        self._cache: dict[str, int] = {}
        self._cache_size = cache_size

    def count(self, content: str) -> int:
        """
        Count tokens with caching.

        Args:
            content: Content to count

        Returns:
            Token count
        """
        if not content:
            return 0

        # Use hash for cache key
        cache_key = self._hash_content(content)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Count and cache
        count = self.token_counter.count(content)

        # Manage cache size
        if len(self._cache) >= self._cache_size:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._cache.keys())[:self._cache_size // 4]
            for key in keys_to_remove:
                del self._cache[key]

        self._cache[cache_key] = count
        return count

    def count_messages(self, messages: list[Message]) -> int:
        """
        Count tokens in messages with caching.

        Args:
            messages: Messages to count

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else ""
            total += self.count(content)
            total += 4  # Message overhead
        return total

    def _hash_content(self, content: str) -> str:
        """Create hash key for content."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the token count cache."""
        self._cache.clear()
