"""
Skill completer - autocomplete for skill names with '/' prefix.

Features:
- Theme-aware popup styling
- Case-insensitive matching
- Empty state handling
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
    - Theme-aware styling
    """

    def __init__(self, parent=None):
        super().__init__([], parent)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModelSorting(QCompleter.ModelSorting.CaseInsensitivelySortedModel)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        # Use popup completion mode
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._skills: dict[str, str] = {}  # name -> description
        self._max_visible_items = 10

    def update_skills(self, skills: list[dict]) -> None:
        """
        Update skill list for completion.

        Args:
            skills: List of dicts with 'name' and 'description' keys
        """
        self._skills = {s["name"]: s.get("description", "") for s in skills}
        # Format: "/skill-name"
        items = [f"/{name}" for name in self._skills.keys()]
        logger.debug(f"[SkillCompleter] update_skills: {len(items)} items: {items[:5]}...")
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
            True if text starts with '/'
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

    def complete(self, rect=None):
        """Override to apply theme styling before showing popup."""
        self._apply_popup_style()
        count = self.completionCount()
        logger.debug(f"[SkillCompleter] complete() called, completionCount={count}")
        super().complete(rect)

    def _apply_popup_style(self) -> None:
        """Apply theme-aware styling to the popup."""
        from harness_client.themes import get_theme

        theme = get_theme()

        # Apply popup frame style
        self.popup().setStyleSheet(f"""
            QListView {{
                background-color: {theme.COMPOSER};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                padding: 4px;
                outline: none;
            }}
            QListView::item {{
                padding: 6px 12px;
                color: {theme.TEXT};
                border-radius: {theme.RADIUS_SM};
            }}
            QListView::item:selected {{
                background-color: {theme.ACCENT};
                color: white;
            }}
            QListView::item:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)