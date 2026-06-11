"""
Skill completer - autocomplete for skill names with '/' prefix.
"""

import logging

from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtWidgets import QCompleter

logger = logging.getLogger(__name__)


class SkillCompleter(QCompleter):
    """
    Custom completer for skill names, activated by '/' prefix.

    Features:
    - Only shows completions when text starts with '/'
    - Case-insensitive matching
    - Shows skill names as '/skill-name'
    """

    def __init__(self, parent=None):
        super().__init__([], parent)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModelSorting(QCompleter.ModelSorting.CaseInsensitivelySortedModel)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        # Use popup completion mode
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._skills: dict[str, str] = {}  # name -> description

    def update_skills(self, skills: list[dict]) -> None:
        """
        Update skill list for completion.

        Args:
            skills: List of dicts with 'name' and 'description' keys
        """
        self._skills = {s["name"]: s.get("description", "") for s in skills}
        # Format: "/skill-name"
        items = [f"/{name}" for name in self._skills.keys()]
        logger.debug(f"[SkillCompleter] update_skills: {len(items)} items: {items}")
        self.setModel(QStringListModel(items))

    def get_skill_description(self, name: str) -> str:
        """
        Get description for a skill.

        Args:
            name: Skill name (with or without '/' prefix)

        Returns:
            Skill description or empty string
        """
        return self._skills.get(name.lstrip("/"), "")

    def should_complete(self, text: str) -> bool:
        """
        Check if completer should show suggestions.

        Args:
            text: Current input text

        Returns:
            True if text starts with '/' and has at least one character
        """
        return text.startswith("/") and len(text) >= 1

    def get_completion_prefix(self, text: str) -> str:
        """
        Get the completion prefix from text.

        Args:
            text: Current input text

        Returns:
            The prefix to match (e.g., "/cl" for "/cl" input)
        """
        if text.startswith("/"):
            return text
        return ""
