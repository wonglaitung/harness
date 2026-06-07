"""
Memory controller for managing persistent global memory.
"""

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from harness.memory.memory_file import (
    MemoryCategory,
    MemoryEntry,
    MemoryFileManager,
    MemorySections,
    MemorySource,
)

from harness_client.utils.settings import get_config_dir


class MemoryController(QObject):
    """
    Controller for managing persistent global memory.

    Memory is stored in ~/.harness/MEMORY.md and shared across all projects.
    """

    memory_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Memory file is stored in global config directory
        self._memory_root = get_config_dir()
        self._manager = MemoryFileManager(self._memory_root)

    @property
    def memory_file_path(self) -> Path:
        """Get the path to MEMORY.md file."""
        return self._memory_root / "MEMORY.md"

    def get_sections(self) -> MemorySections:
        """Load all memory sections."""
        return self._manager.load()

    def get_entries(self, category: MemoryCategory) -> list[str]:
        """Get entries for a specific category."""
        return self._manager.get_entries(category)

    def add_entry(self, category: MemoryCategory, content: str) -> None:
        """
        Add a new memory entry.

        Args:
            category: Memory category
            content: Entry content
        """
        entry = MemoryEntry(
            category=category,
            content=content,
            source=MemorySource.USER_INPUT,
        )
        self._manager.add_entry(entry)
        self.memory_changed.emit()

    def update_entry(self, category: MemoryCategory, index: int, content: str) -> bool:
        """
        Update an existing entry.

        Args:
            category: Memory category
            index: Entry index
            content: New content

        Returns:
            True if updated successfully
        """
        sections = self._manager.load()
        section = sections.get_section(category)

        if 0 <= index < len(section):
            section[index] = content
            self._manager.save(sections)
            self.memory_changed.emit()
            return True
        return False

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

    def get_category_display_name(self, category: MemoryCategory) -> str:
        """Get display name for a category in Chinese."""
        names = {
            MemoryCategory.USER_PROFILE: "用户偏好",
            MemoryCategory.KEY_DECISIONS: "关键决策",
            MemoryCategory.LEARNED_PATTERNS: "学习模式",
            MemoryCategory.PROJECT_CONTEXT: "项目上下文",
        }
        return names.get(category, category.value)
