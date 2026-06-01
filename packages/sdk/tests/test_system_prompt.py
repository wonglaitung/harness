"""
Tests for Dynamic System Prompt Assembly.
"""

import tempfile
from pathlib import Path

import pytest

from harness.memory.system_prompt import (
    SystemPromptBuilder,
    SystemPromptConfig,
    SystemPromptSource,
    discover_project_context,
)


class TestSystemPromptSource:
    """Test SystemPromptSource."""

    def test_static_content(self):
        """Test source with static content."""
        source = SystemPromptSource(
            name="test",
            priority=50,
            content="Hello, world!",
        )
        assert source.get_content() == "Hello, world!"

    def test_callable_content(self):
        """Test source with callable content."""
        source = SystemPromptSource(
            name="test",
            priority=50,
            content=lambda: "Dynamic content",
        )
        assert source.get_content() == "Dynamic content"

    def test_file_content(self):
        """Test source from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("File content")
            f.flush()

            source = SystemPromptSource(
                name="test",
                priority=50,
                file_path=Path(f.name),
            )
            assert source.get_content() == "File content"

    def test_missing_file_returns_empty(self):
        """Test that missing file returns empty string."""
        source = SystemPromptSource(
            name="test",
            priority=50,
            file_path=Path("/nonexistent/file.md"),
        )
        assert source.get_content() == ""

    def test_missing_required_file_raises(self):
        """Test that missing required file raises error."""
        source = SystemPromptSource(
            name="test",
            priority=50,
            file_path=Path("/nonexistent/file.md"),
            required=True,
        )
        with pytest.raises(FileNotFoundError):
            source.get_content()


class TestSystemPromptBuilder:
    """Test SystemPromptBuilder."""

    def test_base_prompt_only(self):
        """Test builder with only base prompt."""
        config = SystemPromptConfig(
            base_prompt="You are a helpful assistant.",
        )
        builder = SystemPromptBuilder(config)
        assert builder.build() == "You are a helpful assistant."

    def test_no_prompt_returns_empty(self):
        """Test builder with no sources returns empty."""
        config = SystemPromptConfig()
        builder = SystemPromptBuilder(config)
        assert builder.build() == ""

    def test_custom_separator(self):
        """Test custom section separator."""
        config = SystemPromptConfig(
            base_prompt="Base",
            section_separator="\n\n===\n\n",
        )
        builder = SystemPromptBuilder(config)
        builder.add_source(SystemPromptSource(
            name="extra",
            priority=10,
            content="Extra",
        ))
        result = builder.build()
        assert "Base" in result
        assert "Extra" in result
        assert "\n\n===\n\n" in result

    def test_priority_ordering(self):
        """Test that sources are ordered by priority."""
        config = SystemPromptConfig(base_prompt="Base (priority 100)")
        builder = SystemPromptBuilder(config)

        builder.add_source(SystemPromptSource(
            name="low",
            priority=10,
            content="Low priority",
        ))
        builder.add_source(SystemPromptSource(
            name="high",
            priority=90,
            content="High priority",
        ))

        result = builder.build()
        # High priority should come first
        assert result.index("Base") < result.index("High priority") < result.index("Low priority")

    def test_add_remove_source(self):
        """Test adding and removing sources."""
        config = SystemPromptConfig(base_prompt="Base")
        builder = SystemPromptBuilder(config)

        builder.add_source(SystemPromptSource(
            name="test",
            priority=50,
            content="Test content",
        ))
        assert builder.get_source_content("test") == "Test content"

        removed = builder.remove_source("test")
        assert removed is True
        assert builder.get_source_content("test") is None

    def test_get_available_sources(self):
        """Test getting available sources."""
        config = SystemPromptConfig(base_prompt="Base")
        builder = SystemPromptBuilder(config)

        # Add source with empty content
        builder.add_source(SystemPromptSource(
            name="empty",
            priority=50,
            content="",
        ))

        # Add source with content
        builder.add_source(SystemPromptSource(
            name="has_content",
            priority=50,
            content="Content",
        ))

        available = builder.get_available_sources()
        assert "base" in available
        assert "has_content" in available
        assert "empty" not in available


class TestDiscoverProjectContext:
    """Test discover_project_context function."""

    def test_discovers_agents_md(self):
        """Test discovery of AGENTS.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_path = Path(tmpdir) / "AGENTS.md"
            agents_path.write_text("# Agent Instructions\n\nTest content")

            context = discover_project_context(Path(tmpdir))
            assert "AGENTS.md" in context
            assert "Agent Instructions" in context["AGENTS.md"]

    def test_discovers_memory_md(self):
        """Test discovery of MEMORY.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "MEMORY.md"
            memory_path.write_text("# Memory\n\nKey decisions here")

            context = discover_project_context(Path(tmpdir))
            assert "MEMORY.md" in context

    def test_discovers_claude_md(self):
        """Test discovery of CLAUDE.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_path = Path(tmpdir) / "CLAUDE.md"
            claude_path.write_text("# Claude Instructions")

            context = discover_project_context(Path(tmpdir))
            assert "CLAUDE.md" in context

    def test_no_files_returns_empty(self):
        """Test that empty directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = discover_project_context(Path(tmpdir))
            assert context == {}

    def test_discovers_multiple_files(self):
        """Test discovery of multiple context files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "AGENTS.md").write_text("Agents")
            (Path(tmpdir) / "MEMORY.md").write_text("Memory")
            (Path(tmpdir) / "CLAUDE.md").write_text("Claude")

            context = discover_project_context(Path(tmpdir))
            assert len(context) == 3
            assert context["AGENTS.md"] == "Agents"
            assert context["MEMORY.md"] == "Memory"
            assert context["CLAUDE.md"] == "Claude"
