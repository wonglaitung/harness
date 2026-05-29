"""
Tests for Context Compression system.
"""

import pytest

from harness.memory.compressor import (
    CompressionConfig,
    CompressionResult,
    ContextCompressor,
    IncrementalTokenCounter,
)
from harness.memory.token_counter import TokenCounter
from harness.types import Message


class TestCompressionConfig:
    """Tests for CompressionConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = CompressionConfig()

        assert config.min_messages_before_compress == 10
        assert config.keep_recent_messages == 5
        assert config.keep_system_messages is True
        assert config.summary_max_tokens == 500
        assert config.compression_ratio == 0.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = CompressionConfig(
            min_messages_before_compress=5,
            keep_recent_messages=3,
            summary_max_tokens=1000,
        )

        assert config.min_messages_before_compress == 5
        assert config.keep_recent_messages == 3
        assert config.summary_max_tokens == 1000


class TestCompressionResult:
    """Tests for CompressionResult."""

    def test_compression_saved(self):
        """Test compression saved calculation."""
        result = CompressionResult(
            original_messages=[Message(role="user", content="test")] * 10,
            compressed_messages=[Message(role="user", content="test")] * 5,
            tokens_before=1000,
            tokens_after=500,
            messages_removed=5,  # Explicitly set
        )

        assert result.compression_saved == 500
        assert result.messages_removed == 5

    def test_no_compression(self):
        """Test result when no compression needed."""
        messages = [Message(role="user", content="test")]
        result = CompressionResult(
            original_messages=messages,
            compressed_messages=messages,
            tokens_before=100,
            tokens_after=100,
        )

        assert result.compression_saved == 0
        assert result.messages_removed == 0


class TestContextCompressor:
    """Tests for ContextCompressor."""

    @pytest.fixture
    def compressor(self):
        """Create a compressor instance."""
        token_counter = TokenCounter()
        return ContextCompressor(token_counter)

    def test_init(self, compressor):
        """Test initialization."""
        assert compressor.config is not None
        assert compressor.token_counter is not None

    def test_no_compression_needed(self, compressor):
        """Test when compression not needed."""
        messages = [Message(role="user", content="Hello")]

        result = compressor.compress(messages, target_tokens=10000)

        assert len(result.compressed_messages) == len(messages)
        assert result.summary is None

    def test_compression_below_threshold(self, compressor):
        """Test that compression doesn't happen below message threshold."""
        # Fewer than min_messages_before_compress
        messages = [
            Message(role="user", content=f"Message {i}")
            for i in range(5)
        ]

        result = compressor.compress(messages, target_tokens=10)

        # Should not compress because too few messages
        assert len(result.compressed_messages) == len(messages)

    def test_compression_keeps_recent(self, compressor):
        """Test that compression keeps recent messages."""
        # Create more than min_messages_before_compress
        messages = [
            Message(role="user", content=f"This is a longer message number {i}" * 10)
            for i in range(15)
        ]

        result = compressor.compress(messages, target_tokens=100)

        # Should have fewer messages
        assert len(result.compressed_messages) < len(messages)

        # Should keep recent messages
        recent_content = messages[-1].content
        assert any(recent_content in m.content for m in result.compressed_messages)

    def test_compression_generates_summary(self, compressor):
        """Test that compression generates summary."""
        messages = [
            Message(role="user", content=f"User request {i}")
            for i in range(20)
        ]

        result = compressor.compress(messages, target_tokens=50)

        # Should generate a summary
        assert result.summary is not None
        assert len(result.summary) > 0

    def test_should_compress_false(self, compressor):
        """Test should_compress returns False when not needed."""
        messages = [Message(role="user", content="test")]

        should = compressor.should_compress(messages, current_tokens=100, max_tokens=1000)

        assert should is False

    def test_should_compress_true(self, compressor):
        """Test should_compress returns True when needed."""
        messages = [
            Message(role="user", content=f"Message {i}")
            for i in range(20)
        ]

        should = compressor.should_compress(messages, current_tokens=10000, max_tokens=1000)

        assert should is True

    def test_should_compress_too_few_messages(self, compressor):
        """Test should_compress returns False with too few messages."""
        messages = [Message(role="user", content="test")] * 5

        should = compressor.should_compress(messages, current_tokens=10000, max_tokens=1000)

        # Too few messages, won't compress
        assert should is False

    def test_generate_summary_empty(self, compressor):
        """Test summary generation with empty messages."""
        summary = compressor._generate_summary([])

        assert summary == ""

    def test_generate_summary_with_messages(self, compressor):
        """Test summary generation with messages."""
        messages = [
            Message(role="user", content="What is Python?"),
            Message(role="assistant", content="Python is a programming language."),
            Message(role="user", content="How do I install it?"),
        ]

        summary = compressor._generate_summary(messages)

        assert "User" in summary or "Python" in summary

    def test_compression_truncates_long_summary(self):
        """Test that long summaries are truncated."""
        config = CompressionConfig(summary_max_tokens=50)
        token_counter = TokenCounter()
        compressor = ContextCompressor(token_counter, config)

        # Create many messages to generate long summary
        messages = [
            Message(role="user", content="X" * 500)  # Long message
            for i in range(20)
        ]

        result = compressor.compress(messages, target_tokens=100)

        # Summary should be truncated
        if result.summary:
            # Approximate token count (4 chars per token)
            estimated_tokens = len(result.summary) // 4
            assert estimated_tokens <= config.summary_max_tokens * 1.5  # Allow some margin


class TestIncrementalTokenCounter:
    """Tests for IncrementalTokenCounter."""

    @pytest.fixture
    def counter(self):
        """Create an incremental counter."""
        token_counter = TokenCounter()
        return IncrementalTokenCounter(token_counter)

    def test_init(self, counter):
        """Test initialization."""
        assert counter.token_counter is not None
        assert len(counter._cache) == 0

    def test_count_caches_result(self, counter):
        """Test that count caches results."""
        content = "Hello, world!"

        # First count
        count1 = counter.count(content)
        assert count1 > 0

        # Should be cached
        assert len(counter._cache) == 1

        # Second count should use cache
        count2 = counter.count(content)
        assert count2 == count1

    def test_count_empty(self, counter):
        """Test counting empty content."""
        count = counter.count("")

        assert count == 0

    def test_count_messages(self, counter):
        """Test counting messages."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        total = counter.count_messages(messages)

        assert total > 0

    def test_cache_size_limit(self, counter):
        """Test that cache respects size limit."""
        counter._cache_size = 10

        # Add more entries than cache size
        for i in range(20):
            counter.count(f"Unique content {i}")

        # Cache should be trimmed
        assert len(counter._cache) <= counter._cache_size

    def test_clear_cache(self, counter):
        """Test clearing cache."""
        counter.count("Some content")
        assert len(counter._cache) > 0

        counter.clear_cache()
        assert len(counter._cache) == 0
