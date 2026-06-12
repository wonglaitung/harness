"""
File completer - autocomplete for file names with '@' prefix.
"""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtWidgets import QCompleter

logger = logging.getLogger(__name__)

# Directories to ignore when scanning
IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "env",
    ".env",
    ".tox",
    ".nox",
}

# Maximum number of files to scan
MAX_FILES = 500

# Maximum directory depth to scan
MAX_DEPTH = 5


class FileCompleter(QCompleter):
    """
    Custom completer for file names, activated by '@' prefix.

    Features:
    - Only shows completions when text starts with '@'
    - Case-insensitive matching
    - Shows file and directory paths relative to work directory
    - Limits results to 10 items for performance
    """

    def __init__(self, parent=None):
        super().__init__([], parent)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModelSorting(QCompleter.ModelSorting.CaseInsensitivelySortedModel)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        # Use popup completion mode
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        # Limit to 10 items in popup
        self.setMaxVisibleItems(10)
        self._work_dir: Path = Path.cwd()
        self._files: list[str] = []  # Relative paths

    def set_work_dir(self, path: Path) -> None:
        """
        Set the work directory and scan files.

        Args:
            path: Path to the work directory
        """
        self._work_dir = path
        logger.debug(f"[FileCompleter] set_work_dir: {path}")
        self._scan_files()

    def _scan_files(self) -> None:
        """Scan work directory for files and directories."""
        self._files = []
        count = 0

        try:
            for item in self._work_dir.rglob("*"):
                if count >= MAX_FILES:
                    break

                # Skip hidden files/dirs (starting with .)
                if any(part.startswith(".") for part in item.parts):
                    continue

                # Skip ignored directories
                try:
                    relative = item.relative_to(self._work_dir)
                    if any(part in IGNORE_DIRS for part in relative.parts):
                        continue
                except ValueError:
                    continue

                # Check depth
                depth = len(relative.parts)
                if depth > MAX_DEPTH:
                    continue

                # Add relative path as string
                self._files.append(str(relative))
                count += 1

        except PermissionError:
            logger.warning(f"Permission denied scanning {self._work_dir}")
        except Exception as e:
            logger.error(f"Error scanning files: {e}")

        logger.debug(f"[FileCompleter] Scanned {len(self._files)} files from {self._work_dir}")
        self.setModel(QStringListModel(self._files))

    def should_complete(self, text: str) -> bool:
        """
        Check if completer should show suggestions.

        Args:
            text: Current input text

        Returns:
            True if text starts with '@'
        """
        return text.startswith("@")

    def get_completion_prefix(self, text: str) -> str:
        """
        Get the completion prefix from text.

        Args:
            text: Current input text

        Returns:
            The prefix to match (e.g., "te" for "@te" input)
        """
        if text.startswith("@"):
            return text[1:]  # Remove @ for matching
        return ""

    def refresh(self) -> None:
        """Refresh the file list by re-scanning."""
        self._scan_files()
