"""
Memory controller for managing persistent global memory.

Supports memory scoring with importance levels for intelligent archival.
"""

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from harness.memory.memory_file import (
    MemoryCategory,
    MemoryEntry,
    MemoryFileManager,
    MemoryScoringConfig,
    MemorySections,
    MemorySource,
)

from harness_client.utils.settings import get_config_dir


class MemoryController(QObject):
    """
    Controller for managing persistent global memory.

    Memory is stored in ~/.harness/MEMORY.md and shared across all projects.

    Features:
    - Add/update/remove memory entries with importance levels
    - Importance-based visual indication (high/medium/low)
    - Retrieval Strength calculation for display
    """

    memory_changed = pyqtSignal()

    def __init__(self, scoring_config: MemoryScoringConfig | None = None):
        super().__init__()
        # Memory file is stored in global config directory
        self._memory_root = get_config_dir()
        self._scoring_config = scoring_config or MemoryScoringConfig()
        self._manager = MemoryFileManager(self._memory_root, self._scoring_config)

    @property
    def memory_file_path(self) -> Path:
        """Get the path to MEMORY.md file."""
        return self._memory_root / "MEMORY.md"

    @property
    def archive_file_path(self) -> Path:
        """Get the path to MEMORY_ARCHIVE.md file."""
        return self._memory_root / "MEMORY_ARCHIVE.md"

    def get_sections(self) -> MemorySections:
        """Load all memory sections."""
        return self._manager.load()

    def get_entries(self, category: MemoryCategory) -> list[MemoryEntry]:
        """
        Get entries for a specific category with full metadata.

        Returns:
            List of MemoryEntry objects with importance and access_count.
        """
        return self._manager._load_entries_with_metadata(category)

    def get_entry_strings(self, category: MemoryCategory) -> list[str]:
        """
        Get entry content strings for a specific category.

        This is kept for backward compatibility.
        """
        return self._manager.get_entries(category)

    def add_entry(
        self,
        category: MemoryCategory,
        content: str,
        importance: float = 1.0,
    ) -> None:
        """
        Add a new memory entry with importance level.

        Args:
            category: Memory category
            content: Entry content
            importance: Importance level (0.0-1.0)
                - 0.8-1.0: High importance (core preferences)
                - 0.5-0.8: Medium importance (useful patterns)
                - 0.0-0.5: Low importance (temporary info)
        """
        entry = MemoryEntry(
            category=category,
            content=content,
            source=MemorySource.USER_INPUT,
            importance=importance,
        )
        self._manager.add_entry(entry)
        self.memory_changed.emit()

    def update_entry(
        self,
        category: MemoryCategory,
        index: int,
        content: str,
        importance: float | None = None,
    ) -> bool:
        """
        Update an existing entry.

        Args:
            category: Memory category
            index: Entry index
            content: New content
            importance: Optional new importance level

        Returns:
            True if updated successfully
        """
        entries = self._manager._load_entries_with_metadata(category)

        if 0 <= index < len(entries):
            entry = entries[index]
            entry.content = content
            if importance is not None:
                entry.importance = importance

            # Rebuild and save
            sections = self._manager.load()
            section = sections.get_section(category)
            section[index] = entry.to_markdown_line().replace("- ", "", 1).split(" <!-- ")[0]
            self._manager.save(sections)
            self.memory_changed.emit()
            return True
        return False

    def update_importance(
        self,
        category: MemoryCategory,
        index: int,
        importance: float,
    ) -> bool:
        """
        Update importance level of an entry.

        Args:
            category: Memory category
            index: Entry index
            importance: New importance level (0.0-1.0)

        Returns:
            True if updated successfully
        """
        entries = self._manager._load_entries_with_metadata(category)

        if 0 <= index < len(entries):
            entries[index].importance = importance

            # Rebuild file with updated importance
            self._save_entries_with_metadata(category, entries)
            self.memory_changed.emit()
            return True
        return False

    def _save_entries_with_metadata(
        self,
        category: MemoryCategory,
        entries: list[MemoryEntry],
    ) -> None:
        """Save entries with full metadata."""
        sections = self._manager.load()
        section = sections.get_section(category)
        section.clear()
        for entry in entries:
            # Store with metadata
            section.append(entry.to_markdown_line().replace("- ", "", 1))
        self._manager.save(sections)

    def remove_entry(self, category: MemoryCategory, index: int) -> bool:
        """
        Remove an entry from a category.

        Args:
            category: Memory category
            index: Entry index

        Returns:
            True if removed successfully
        """
        success = self._manager.remove_entry(category, index)
        if success:
            self.memory_changed.emit()
        return success

    def clear_all(self) -> None:
        """Clear all memory."""
        self._manager.clear()
        self.memory_changed.emit()

    def to_context_string(self) -> str:
        """Get memory formatted for LLM context."""
        return self._manager.to_context_string()

    def exists(self) -> bool:
        """Check if MEMORY.md exists."""
        return self._manager.exists()

    def check_capacity(self) -> tuple[bool, int]:
        """
        Check if Core Memory exceeds capacity.

        Returns:
            Tuple of (is_over_limit, current_tokens)
        """
        return self._manager.check_capacity()

    def get_importance_level(self, importance: float) -> str:
        """
        Get importance level name for display.

        Args:
            importance: Importance value (0.0-1.0)

        Returns:
            Level name: "high", "medium", or "low"
        """
        if importance >= 0.8:
            return "high"
        elif importance >= 0.5:
            return "medium"
        else:
            return "low"

    def get_category_display_name(self, category: MemoryCategory) -> str:
        """Get display name for a category in Chinese."""
        names = {
            MemoryCategory.USER_PROFILE: "用户偏好",
            MemoryCategory.KEY_DECISIONS: "关键决策",
            MemoryCategory.LEARNED_PATTERNS: "学习模式",
            MemoryCategory.PROJECT_CONTEXT: "项目上下文",
        }
        return names.get(category, category.value)
