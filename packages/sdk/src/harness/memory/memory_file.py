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
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

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
class MemoryScoringConfig:
    """Memory scoring configuration for Retrieval Strength calculation."""
    decay_lambda: float = 0.05            # Decay speed (higher = faster decay)
    min_retrieval_strength: float = 0.3   # Minimum retrieval strength (floor)
    max_core_memory_tokens: int = 2000    # Core Memory token limit
    enable_llm_evaluation: bool = False   # Enable LLM importance evaluation
    archive_fallback: Literal["file", "delete", "none"] = "file"
    # file: Archive to MEMORY_ARCHIVE.md (default, no data loss)
    # delete: Delete directly (not recommended)
    # none: Disable archiving, Core Memory grows indefinitely


@dataclass
class MemoryEntry:
    """A single memory entry."""

    category: MemoryCategory
    content: str
    source: MemorySource
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    # New fields for scoring (backward compatible with defaults)
    importance: float = 1.0           # Storage Strength (used for archive decision)
    last_accessed: datetime | None = None  # Last access time
    access_count: int = 0             # Access count

    def calculate_retrieval_strength(
        self,
        decay_lambda: float = 0.05,
        min_strength: float = 0.3,
    ) -> float:
        """
        Calculate Retrieval Strength (only for Retrieved Memory).

        Based on Bjork's New Theory of Disuse:
        - Time decay: older memories decay but never below min_strength
        - Access bonus: frequently accessed memories get bonus

        Returns:
            Retrieval strength value (min_strength to ~2.5)
        """
        # Calculate days idle
        if self.last_accessed:
            days_idle = (datetime.now() - self.last_accessed).days
        else:
            days_idle = (datetime.now() - self.created_at).days

        # Time decay factor (never below min_strength)
        time_decay = min_strength + (1 - min_strength) * math.exp(-decay_lambda * days_idle)

        # Access bonus factor
        access_bonus = 1 + 0.5 * math.log(1 + self.access_count)

        return time_decay * access_bonus

    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def to_markdown_line(self) -> str:
        """Convert to markdown list item."""
        if self.category == MemoryCategory.KEY_DECISIONS:
            date_str = self.created_at.strftime("%Y-%m-%d")
            base = f"- {date_str}: {self.content}"
        else:
            base = f"- {self.content}"

        # Add metadata as HTML comment if non-default
        if self.importance != 1.0 or self.access_count > 0:
            meta = f" <!-- importance={self.importance:.2f}, accesses={self.access_count} -->"
            return base + meta

        return base

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

        # Extract metadata from HTML comment if present
        importance = 1.0
        access_count = 0
        meta_match = re.search(r"<!-- importance=(\d+\.\d+), accesses=(\d+) -->", content)
        if meta_match:
            importance = float(meta_match.group(1))
            access_count = int(meta_match.group(2))
            content = content[:meta_match.start()].strip()

        # Check for date prefix (YYYY-MM-DD:)
        created_at = datetime.now()
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
            created_at=created_at,
            importance=importance,
            access_count=access_count,
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

    def total_entries(self) -> int:
        """Count total entries across all sections."""
        return (
            len(self.user_profile) +
            len(self.key_decisions) +
            len(self.learned_patterns) +
            len(self.project_context)
        )


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
    ARCHIVE_FILE_NAME = "MEMORY_ARCHIVE.md"

    # Standard section headers
    SECTION_HEADERS = {
        "User Profile": MemoryCategory.USER_PROFILE,
        "Key Decisions": MemoryCategory.KEY_DECISIONS,
        "Learned Patterns": MemoryCategory.LEARNED_PATTERNS,
        "Project Context": MemoryCategory.PROJECT_CONTEXT,
    }

    def __init__(
        self,
        project_root: Path | None = None,
        scoring_config: MemoryScoringConfig | None = None,
    ):
        """
        Initialize the memory file manager.

        Args:
            project_root: Project root directory. If None, uses current directory.
            scoring_config: Memory scoring configuration.
        """
        self.project_root = project_root or Path.cwd()
        self.memory_file = self.project_root / self.FILE_NAME
        self.archive_file = self.project_root / self.ARCHIVE_FILE_NAME
        self.scoring_config = scoring_config or MemoryScoringConfig()

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

    def add_entry(self, entry: MemoryEntry, check_duplicate: bool = True) -> bool:
        """
        Add a new entry to MEMORY.md.

        Args:
            entry: MemoryEntry to add
            check_duplicate: If True, check for similar existing entries and skip if duplicate

        Returns:
            True if entry was added, False if skipped as duplicate
        """
        sections = self.load()
        section = sections.get_section(entry.category)

        if check_duplicate:
            # Check for similar existing entries
            for existing in section:
                similarity = self._calculate_similarity(entry.content, existing)
                if similarity > 0.7:  # Similarity threshold (0.7 = 70% similar)
                    logger.info(
                        f"Skipping duplicate memory: '{entry.content}' "
                        f"similar to existing '{existing}' (similarity={similarity:.2f})"
                    )
                    return False

        section.append(entry.content)
        self.save(sections)
        return True

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using character-level Jaccard similarity.

        Supports both Chinese and English text without requiring word segmentation.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize: lowercase
        text1 = text1.lower()
        text2 = text2.lower()

        if not text1 or not text2:
            return 0.0

        # Use character-level comparison for mixed Chinese/English
        # For Chinese text, use bigrams (2-character sequences)
        def get_ngrams(text: str, n: int = 2) -> set[str]:
            """Get character n-grams from text."""
            if len(text) < n:
                return {text}
            return {text[i : i + n] for i in range(len(text) - n + 1)}

        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)

        # Jaccard similarity: intersection / union
        intersection = ngrams1 & ngrams2
        union = ngrams1 | ngrams2

        return len(intersection) / len(union)

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

    # ==================== Capacity Management ====================

    def check_capacity(self) -> tuple[bool, int]:
        """
        Check if Core Memory exceeds token limit.

        Returns:
            Tuple of (is_over_limit, current_tokens)
        """
        content = self.to_context_string()
        tokens = self._estimate_tokens(content)
        return (tokens > self.scoring_config.max_core_memory_tokens, tokens)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Simple estimation: ~4 characters per token for English text.
        """
        return len(text) // 4

    def _load_entries_with_metadata(self, category: MemoryCategory) -> list[MemoryEntry]:
        """
        Load entries with full metadata for a category.

        Returns:
            List of MemoryEntry objects with importance and access_count.
        """
        if not self.exists():
            return []

        content = self.memory_file.read_text(encoding="utf-8")
        entries = []
        in_section = False

        for line in content.split("\n"):
            # Check for section header
            if line.startswith("## "):
                header = line[3:].strip()
                in_section = (self.SECTION_HEADERS.get(header) == category)
                continue

            # Parse entry if in target section
            if in_section and line.strip().startswith("-"):
                entry = MemoryEntry.from_markdown_line(line, category)
                if entry:
                    entries.append(entry)

        return entries

    def _load_all_entries_with_metadata(self) -> list[dict[str, Any]]:
        """
        Load all entries with metadata across all sections.

        Returns:
            List of dicts with 'category', 'index', 'entry' keys.
        """
        all_entries = []
        for category in MemoryCategory:
            entries = self._load_entries_with_metadata(category)
            for i, entry in enumerate(entries):
                all_entries.append({
                    "category": category,
                    "index": i,
                    "entry": entry,
                })
        return all_entries

    async def archive_low_importance(
        self,
        archive_callback: Any = None,
    ) -> int:
        """
        Archive low-importance entries when capacity exceeded.

        Entry-level archival: only archives lowest importance entries,
        not entire sections.

        Args:
            archive_callback: Optional async callback to archive entry to Retrieved Memory.
                              If None, archives to MEMORY_ARCHIVE.md file.

        Returns:
            Number of entries archived.
        """
        is_over, current_tokens = self.check_capacity()
        if not is_over:
            return 0

        # Collect all entries with metadata
        all_entries = self._load_all_entries_with_metadata()

        # Sort by importance (lowest first)
        all_entries.sort(key=lambda x: x["entry"].importance)

        archived_count = 0
        for item in all_entries:
            entry = item["entry"]
            category = item["category"]

            # Archive the entry
            if archive_callback:
                # Use callback (e.g., to VectorMemoryStore)
                await archive_callback(entry)
            else:
                # Fallback: archive to file
                self._archive_to_file(entry)

            # Remove from Core Memory
            self.remove_entry(category, item["index"] - archived_count)
            archived_count += 1

            # Check if we've freed enough space (keep 20% buffer)
            is_over, new_tokens = self.check_capacity()
            if not is_over and new_tokens <= self.scoring_config.max_core_memory_tokens * 0.8:
                break

        logger.info(f"Archived {archived_count} entries from Core Memory")
        return archived_count

    def _archive_to_file(self, entry: MemoryEntry) -> None:
        """
        Archive entry to MEMORY_ARCHIVE.md file.

        This is the fallback when no vector store is configured.
        """
        # Parse existing archive file or create new
        archive_sections = self._load_archive_sections()

        # Add entry to appropriate section
        section_map = {
            MemoryCategory.USER_PROFILE: "user_profile",
            MemoryCategory.KEY_DECISIONS: "key_decisions",
            MemoryCategory.LEARNED_PATTERNS: "learned_patterns",
            MemoryCategory.PROJECT_CONTEXT: "project_context",
        }
        section_name = section_map.get(entry.category, "project_context")
        if section_name not in archive_sections:
            archive_sections[section_name] = []

        archive_sections[section_name].append({
            "content": entry.content,
            "importance": entry.importance,
            "archived_at": datetime.now(),
        })

        # Save archive file
        self._save_archive_sections(archive_sections)
        logger.info(f"Archived entry to {self.archive_file}: {entry.content[:50]}...")

    def _load_archive_sections(self) -> dict[str, list[dict[str, Any]]]:
        """Load MEMORY_ARCHIVE.md content."""
        sections: dict[str, list[dict[str, Any]]] = {}

        if not self.archive_file.exists():
            return sections

        content = self.archive_file.read_text(encoding="utf-8")
        current_section: str | None = None

        for line in content.split("\n"):
            if line.startswith("## "):
                current_section = line[3:].strip().lower().replace(" ", "_")
                sections[current_section] = []
                continue

            if current_section and line.strip().startswith("-"):
                # Parse archive entry: - [YYYY-MM-DD, importance=X] content
                match = re.match(r"- \[(\d{4}-\d{2}-\d{2}), importance=(\d+\.\d+)\] (.+)", line[2:])
                if match:
                    sections[current_section].append({
                        "archived_at": datetime.strptime(match.group(1), "%Y-%m-%d"),
                        "importance": float(match.group(2)),
                        "content": match.group(3),
                    })

        return sections

    def _save_archive_sections(self, sections: dict[str, list[dict[str, Any]]]) -> None:
        """Save to MEMORY_ARCHIVE.md file."""
        header_names = {
            "user_profile": "User Profile",
            "key_decisions": "Key Decisions",
            "learned_patterns": "Learned Patterns",
            "project_context": "Project Context",
        }

        lines = [
            "# Archived Memory",
            "",
            "> 以下记忆已从 Core Memory 归档。可通过全文搜索查找。",
            "",
        ]

        for section_key, entries in sections.items():
            if entries:
                section_name = header_names.get(section_key, section_key.title())
                lines.append(f"## {section_name}")
                for entry in entries:
                    archived_at = entry.get("archived_at", datetime.now())
                    if isinstance(archived_at, str):
                        archived_at = datetime.fromisoformat(archived_at)
                    date_str = archived_at.strftime("%Y-%m-%d")
                    importance = entry.get("importance", 1.0)
                    content = entry.get("content", "")
                    lines.append(f"- [{date_str}, importance={importance:.2f}] {content}")
                lines.append("")

        self.archive_file.write_text("\n".join(lines), encoding="utf-8")


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
