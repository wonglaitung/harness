"""
Tests for MEMORY.md Standard.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from harness.memory.memory_file import (
    MemoryCategory,
    MemoryEntry,
    MemoryFileManager,
    MemorySections,
    MemorySource,
    create_default_memory,
)


class TestMemoryEntry:
    """Test MemoryEntry."""

    def test_create_entry(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(
            category=MemoryCategory.KEY_DECISIONS,
            content="Use SQLite for storage",
            source=MemorySource.AGENT_OBSERVATION,
        )
        assert entry.category == MemoryCategory.KEY_DECISIONS
        assert entry.content == "Use SQLite for storage"

    def test_to_markdown_line_key_decision(self):
        """Test markdown formatting for key decision."""
        entry = MemoryEntry(
            category=MemoryCategory.KEY_DECISIONS,
            content="Use SQLite",
            source=MemorySource.AGENT_OBSERVATION,
            created_at=datetime(2026, 6, 1),
        )
        line = entry.to_markdown_line()
        assert "2026-06-01" in line
        assert "Use SQLite" in line

    def test_to_markdown_line_pattern(self):
        """Test markdown formatting for learned pattern."""
        entry = MemoryEntry(
            category=MemoryCategory.LEARNED_PATTERNS,
            content="User prefers concise responses",
            source=MemorySource.AGENT_OBSERVATION,
        )
        line = entry.to_markdown_line()
        assert line == "- User prefers concise responses"

    def test_from_markdown_line(self):
        """Test parsing from markdown line."""
        entry = MemoryEntry.from_markdown_line(
            "- Test content",
            MemoryCategory.USER_PROFILE,
        )
        assert entry is not None
        assert entry.content == "Test content"
        assert entry.category == MemoryCategory.USER_PROFILE

    def test_from_markdown_line_with_date(self):
        """Test parsing markdown line with date."""
        entry = MemoryEntry.from_markdown_line(
            "- 2026-06-01: Important decision",
            MemoryCategory.KEY_DECISIONS,
        )
        assert entry is not None
        assert entry.content == "Important decision"

    def test_from_markdown_line_invalid(self):
        """Test parsing invalid line."""
        entry = MemoryEntry.from_markdown_line(
            "Not a list item",
            MemoryCategory.USER_PROFILE,
        )
        assert entry is None


class TestMemorySections:
    """Test MemorySections."""

    def test_empty_sections(self):
        """Test empty sections."""
        sections = MemorySections()
        assert sections.user_profile == []
        assert sections.key_decisions == []

    def test_get_section(self):
        """Test getting section by category."""
        sections = MemorySections(
            user_profile=["Role: Developer"],
            key_decisions=["Decision 1"],
        )

        profile = sections.get_section(MemoryCategory.USER_PROFILE)
        assert profile == ["Role: Developer"]

        decisions = sections.get_section(MemoryCategory.KEY_DECISIONS)
        assert decisions == ["Decision 1"]

    def test_set_section(self):
        """Test setting section by category."""
        sections = MemorySections()
        sections.set_section(MemoryCategory.USER_PROFILE, ["New entry"])

        assert sections.user_profile == ["New entry"]


class TestMemoryFileManager:
    """Test MemoryFileManager."""

    def test_exists_false(self):
        """Test exists returns False for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))
            assert manager.exists() is False

    def test_exists_true(self):
        """Test exists returns True for existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "MEMORY.md").write_text("# MEMORY.md\n")

            manager = MemoryFileManager(root)
            assert manager.exists() is True

    def test_load_empty(self):
        """Test loading non-existent file returns empty sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))
            sections = manager.load()

            assert sections.user_profile == []
            assert sections.key_decisions == []

    def test_save_and_load(self):
        """Test saving and loading memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            sections = MemorySections(
                user_profile=["Role: Developer", "Language: Python"],
                key_decisions=["Use SQLite"],
                learned_patterns=["Prefer concise responses"],
            )

            manager.save(sections)

            # Load and verify
            loaded = manager.load()
            assert len(loaded.user_profile) == 2
            assert len(loaded.key_decisions) == 1
            assert "Use SQLite" in loaded.key_decisions[0]

    def test_add_entry(self):
        """Test adding an entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            entry = MemoryEntry(
                category=MemoryCategory.KEY_DECISIONS,
                content="Use qasync for PyQt",
                source=MemorySource.AGENT_OBSERVATION,
            )

            manager.add_entry(entry)

            loaded = manager.load()
            assert len(loaded.key_decisions) == 1
            assert "Use qasync for PyQt" in loaded.key_decisions[0]

    def test_remove_entry(self):
        """Test removing an entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            sections = MemorySections(
                user_profile=["Entry 1", "Entry 2", "Entry 3"],
            )
            manager.save(sections)

            # Remove middle entry
            result = manager.remove_entry(MemoryCategory.USER_PROFILE, 1)
            assert result is True

            loaded = manager.load()
            assert len(loaded.user_profile) == 2
            assert "Entry 1" in loaded.user_profile
            assert "Entry 3" in loaded.user_profile

    def test_remove_entry_invalid_index(self):
        """Test removing with invalid index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            sections = MemorySections(user_profile=["Entry 1"])
            manager.save(sections)

            result = manager.remove_entry(MemoryCategory.USER_PROFILE, 99)
            assert result is False

    def test_get_entries(self):
        """Test getting entries by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            sections = MemorySections(
                key_decisions=["Decision 1", "Decision 2"],
            )
            manager.save(sections)

            entries = manager.get_entries(MemoryCategory.KEY_DECISIONS)
            assert len(entries) == 2

    def test_to_context_string(self):
        """Test formatting as context string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))

            sections = MemorySections(
                user_profile=["Role: Developer"],
                key_decisions=["Use SQLite"],
            )
            manager.save(sections)

            context = manager.to_context_string()

            assert "# Project Memory" in context
            assert "## User Profile" in context
            assert "## Key Decisions" in context
            assert "Role: Developer" in context

    def test_to_context_string_empty(self):
        """Test empty context string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryFileManager(Path(tmpdir))
            context = manager.to_context_string()
            assert context == ""

    def test_clear(self):
        """Test clearing memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = MemoryFileManager(root)

            # Create file
            sections = MemorySections(user_profile=["Test"])
            manager.save(sections)
            assert manager.exists() is True

            # Clear
            manager.clear()
            assert manager.exists() is False

    def test_parse_existing_file(self):
        """Test parsing an existing MEMORY.md file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content = """# MEMORY.md

## User Profile
- Role: Software Developer
- Preferred Language: Python

## Key Decisions
- 2026-06-01: Use SQLite for session storage
- 2026-05-30: Use qasync for PyQt integration

## Learned Patterns
- User prefers concise responses

## Project Context
- Monorepo structure with sdk and client packages
"""
            (root / "MEMORY.md").write_text(content)

            manager = MemoryFileManager(root)
            sections = manager.load()

            assert len(sections.user_profile) == 2
            assert len(sections.key_decisions) == 2
            assert len(sections.learned_patterns) == 1
            assert len(sections.project_context) == 1


class TestCreateDefaultMemory:
    """Test create_default_memory function."""

    def test_create_default(self):
        """Test creating default memory file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            create_default_memory(Path(tmpdir))

            manager = MemoryFileManager(Path(tmpdir))
            sections = manager.load()

            assert len(sections.user_profile) == 2
            assert len(sections.project_context) == 1


class TestMemoryCategory:
    """Test MemoryCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert MemoryCategory.USER_PROFILE.value == "user_profile"
        assert MemoryCategory.KEY_DECISIONS.value == "key_decisions"
        assert MemoryCategory.LEARNED_PATTERNS.value == "learned_patterns"
        assert MemoryCategory.PROJECT_CONTEXT.value == "project_context"


class TestMemorySource:
    """Test MemorySource enum."""

    def test_source_values(self):
        """Test source enum values."""
        assert MemorySource.USER_INPUT.value == "user_input"
        assert MemorySource.AGENT_OBSERVATION.value == "agent_observation"
        assert MemorySource.EXPLICIT_SAVE.value == "explicit_save"
