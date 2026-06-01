"""
MEMORY.md Standard - Persistent memory file management.

MEMORY.md files store persistent context across sessions:
- User Profile: Role, preferences, response style
- Key Decisions: Important architectural choices
- Learned Patterns: User preferences discovered over time
- Project Context: Project-specific conventions

Usage:
    from harness.memory.memory_file import MemoryFileManager, MemoryEntry

    manager = MemoryFileManager(project_root=Path("/path/to/project"))

    # Load existing memory
    sections = manager.load()

    # Add new entry
    manager.add_entry(MemoryEntry(
        category="key_decisions",
        content="Chose SQLite for session storage",
        source="agent_observation",
    ))

    # Save changes
    manager.save(sections)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryCategory(Enum):
    """Categories for memory entries."""
    USER_PROFILE = "user_profile"
    KEY_DECISIONS = "key_decisions"
    LEARNED_PATTERNS = "learned_patterns"
    PROJECT_CONTEXT = "project_context"


class MemorySource(Enum):
    """Source of memory entry."""
    USER_INPUT = "user_input"
    AGENT_OBSERVATION = "agent_observation"
    EXPLICIT_SAVE = "explicit_save"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    category: MemoryCategory
    content: str
    source: MemorySource
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown_line(self) -> str:
        """Convert to markdown list item."""
        if self.category == MemoryCategory.KEY_DECISIONS:
            date_str = self.created_at.strftime("%Y-%m-%d")
            return f"- {date_str}: {self.content}"
        return f"- {self.content}"

    @classmethod
    def from_markdown_line(
        cls,
        line: str,
        category: MemoryCategory,
        source: MemorySource = MemorySource.AGENT_OBSERVATION,
    ) -> MemoryEntry | None:
        """Parse from markdown list item."""
        line = line.strip()
        if not line.startswith("-"):
            return None

        # Remove leading dash
        content = line[1:].strip()

        # Check for date prefix (YYYY-MM-DD:)
        date_match = re.match(r"(\d{4}-\d{2}-\d{2}):\s*(.+)", content)
        if date_match:
            try:
                created_at = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                content = date_match.group(2)
            except ValueError:
                pass

        if not content:
            return None

        return cls(
            category=category,
            content=content,
            source=source,
        )


@dataclass
class MemorySections:
    """All memory sections."""

    user_profile: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)
    learned_patterns: list[str] = field(default_factory=list)
    project_context: list[str] = field(default_factory=list)

    def get_section(self, category: MemoryCategory) -> list[str]:
        """Get a section by category."""
        mapping = {
            MemoryCategory.USER_PROFILE: self.user_profile,
            MemoryCategory.KEY_DECISIONS: self.key_decisions,
            MemoryCategory.LEARNED_PATTERNS: self.learned_patterns,
            MemoryCategory.PROJECT_CONTEXT: self.project_context,
        }
        return mapping.get(category, [])

    def set_section(self, category: MemoryCategory, entries: list[str]) -> None:
        """Set a section by category."""
        mapping = {
            MemoryCategory.USER_PROFILE: "user_profile",
            MemoryCategory.KEY_DECISIONS: "key_decisions",
            MemoryCategory.LEARNED_PATTERNS: "learned_patterns",
            MemoryCategory.PROJECT_CONTEXT: "project_context",
        }
        attr_name = mapping.get(category)
        if attr_name:
            setattr(self, attr_name, entries)


class MemoryFileManager:
    """
    Manager for MEMORY.md files.

    Handles reading, writing, and updating memory files in the standard format.

    Example:
        manager = MemoryFileManager(Path.cwd())

        # Check if exists
        if manager.exists():
            sections = manager.load()

            # Access specific section
            for pattern in sections.learned_patterns:
                print(f"Pattern: {pattern}")

        # Add new entry
        manager.add_entry(MemoryEntry(
            category=MemoryCategory.KEY_DECISIONS,
            content="Use qasync for PyQt integration",
            source=MemorySource.AGENT_OBSERVATION,
        ))
    """

    FILE_NAME = "MEMORY.md"

    # Standard section headers
    SECTION_HEADERS = {
        "User Profile": MemoryCategory.USER_PROFILE,
        "Key Decisions": MemoryCategory.KEY_DECISIONS,
        "Learned Patterns": MemoryCategory.LEARNED_PATTERNS,
        "Project Context": MemoryCategory.PROJECT_CONTEXT,
    }

    def __init__(self, project_root: Path | None = None):
        """
        Initialize the memory file manager.

        Args:
            project_root: Project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.memory_file = self.project_root / self.FILE_NAME

    def exists(self) -> bool:
        """Check if MEMORY.md exists."""
        return self.memory_file.exists()

    def load(self) -> MemorySections:
        """
        Load MEMORY.md content.

        Returns:
            MemorySections with all parsed entries
        """
        sections = MemorySections()

        if not self.exists():
            return sections

        content = self.memory_file.read_text(encoding="utf-8")
        return self._parse_content(content)

    def _parse_content(self, content: str) -> MemorySections:
        """Parse MEMORY.md content into sections."""
        sections = MemorySections()
        current_category: MemoryCategory | None = None

        for line in content.split("\n"):
            # Check for section header
            if line.startswith("## "):
                header = line[3:].strip()
                current_category = self.SECTION_HEADERS.get(header)
                continue

            # Parse entry
            if current_category and line.strip().startswith("-"):
                entry = MemoryEntry.from_markdown_line(line, current_category)
                if entry:
                    section = sections.get_section(current_category)
                    section.append(entry.content)

        return sections

    def save(self, sections: MemorySections) -> None:
        """
        Save sections to MEMORY.md.

        Args:
            sections: MemorySections to save
        """
        content = self._build_content(sections)
        self.memory_file.write_text(content, encoding="utf-8")
        logger.info(f"Saved memory to {self.memory_file}")

    def _build_content(self, sections: MemorySections) -> str:
        """Build MEMORY.md content from sections."""
        lines = ["# MEMORY.md\n"]

        # User Profile
        if sections.user_profile:
            lines.append("## User Profile")
            for entry in sections.user_profile:
                lines.append(f"- {entry}")
            lines.append("")

        # Key Decisions
        if sections.key_decisions:
            lines.append("## Key Decisions")
            for entry in sections.key_decisions:
                # Check if already has date prefix
                if not re.match(r"\d{4}-\d{2}-\d{2}:", entry):
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    lines.append(f"- {date_str}: {entry}")
                else:
                    lines.append(f"- {entry}")
            lines.append("")

        # Learned Patterns
        if sections.learned_patterns:
            lines.append("## Learned Patterns")
            for entry in sections.learned_patterns:
                lines.append(f"- {entry}")
            lines.append("")

        # Project Context
        if sections.project_context:
            lines.append("## Project Context")
            for entry in sections.project_context:
                lines.append(f"- {entry}")
            lines.append("")

        return "\n".join(lines)

    def add_entry(self, entry: MemoryEntry) -> None:
        """
        Add a new entry to MEMORY.md.

        Args:
            entry: MemoryEntry to add
        """
        sections = self.load()
        section = sections.get_section(entry.category)
        section.append(entry.content)
        self.save(sections)

    def remove_entry(self, category: MemoryCategory, index: int) -> bool:
        """
        Remove an entry from a section.

        Args:
            category: Category to remove from
            index: Index of entry to remove

        Returns:
            True if removed, False if index out of bounds
        """
        sections = self.load()
        section = sections.get_section(category)

        if 0 <= index < len(section):
            section.pop(index)
            self.save(sections)
            return True

        return False

    def get_entries(self, category: MemoryCategory) -> list[str]:
        """Get all entries in a category."""
        sections = self.load()
        return sections.get_section(category)

    def to_context_string(self) -> str:
        """
        Format memory as context string for LLM.

        Returns:
            Formatted string for injection into context
        """
        sections = self.load()

        if not any([
            sections.user_profile,
            sections.key_decisions,
            sections.learned_patterns,
            sections.project_context,
        ]):
            return ""

        lines = ["# Project Memory\n"]

        if sections.user_profile:
            lines.append("## User Profile")
            for entry in sections.user_profile:
                lines.append(f"- {entry}")
            lines.append("")

        if sections.key_decisions:
            lines.append("## Key Decisions")
            for entry in sections.key_decisions:
                lines.append(f"- {entry}")
            lines.append("")

        if sections.learned_patterns:
            lines.append("## Learned Patterns")
            for entry in sections.learned_patterns:
                lines.append(f"- {entry}")
            lines.append("")

        if sections.project_context:
            lines.append("## Project Context")
            for entry in sections.project_context:
                lines.append(f"- {entry}")
            lines.append("")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all memory by deleting MEMORY.md."""
        if self.exists():
            self.memory_file.unlink()
            logger.info(f"Deleted {self.memory_file}")


def create_default_memory(project_root: Path | None = None) -> None:
    """
    Create a default MEMORY.md template.

    Args:
        project_root: Project root directory
    """
    manager = MemoryFileManager(project_root)

    sections = MemorySections(
        user_profile=[
            "Role: Software Developer",
            "Preferred Language: Python",
        ],
        key_decisions=[],
        learned_patterns=[],
        project_context=[
            "Add project-specific conventions here",
        ],
    )

    manager.save(sections)
