"""
Skill completer - autocomplete for skill names with '/' prefix.

Features:
- Theme-aware popup styling
- Shows skill name and description
- Case-insensitive matching
- Empty state handling
"""

import logging

from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, QSize
from PyQt6.QtWidgets import QCompleter, QStyledItemDelegate, QStyle, QApplication
from PyQt6.QtGui import QColor, QFont, QFontMetrics

logger = logging.getLogger(__name__)


class SkillListModel(QAbstractListModel):
    """Custom model to store skill name and description."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills: list[dict] = []  # [{name, description}, ...]

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._skills)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._skills):
            return None

        skill = self._skills[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return f"/{skill['name']}"
        elif role == Qt.ItemDataRole.ToolTipRole:
            return skill.get('description', '')
        elif role == Qt.ItemDataRole.UserRole.value:  # Custom role for description
            return skill.get('description', '')

        return None

    def set_skills(self, skills: list[dict]) -> None:
        """Update the skill list."""
        self.beginResetModel()
        self._skills = skills
        self.endResetModel()

    def get_skill_at(self, row: int) -> dict | None:
        """Get skill data at the given row."""
        if 0 <= row < len(self._skills):
            return self._skills[row]
        return None


class SkillItemDelegate(QStyledItemDelegate):
    """Custom delegate to render skill name and description."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = None

    def set_theme(self, theme) -> None:
        """Update the theme for rendering."""
        self._theme = theme

    def paint(self, painter, option, index):
        """Paint the skill item with name and description."""
        from harness_client.themes import get_theme

        theme = self._theme or get_theme()

        # Draw background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(theme.ACCENT))
            text_color = QColor("white")
            desc_color = QColor("rgba(255, 255, 255, 0.7)")
        else:
            painter.fillRect(option.rect, QColor(theme.COMPOSER))
            text_color = QColor(theme.TEXT)
            desc_color = QColor(theme.TEXT_SUBTLE)

        # Get data
        name = index.data(Qt.ItemDataRole.DisplayRole)
        description = index.data(Qt.ItemDataRole.UserRole) or ""

        # Truncate description if too long
        max_desc_width = option.rect.width() - 20
        if description:
            fm = QFontMetrics(option.font)
            description = fm.elidedText(description, Qt.TextElideMode.ElideRight, max_desc_width)

        # Calculate layout
        name_rect = option.rect.adjusted(12, 6, -12, -6)
        desc_rect = name_rect.adjusted(0, name_rect.height() // 2 + 2, 0, 0)

        # Draw name
        painter.setPen(text_color)
        font = QFont(option.font)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, name)

        # Draw description (smaller, secondary color)
        if description:
            painter.setPen(desc_color)
            font = QFont(option.font)
            font.setBold(False)
            font.setPointSize(theme.FONT_SIZE_SM.replace("px", "").replace("pt", "") if hasattr(theme, 'FONT_SIZE_SM') else 11)
            painter.setFont(font)
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, description)

    def sizeHint(self, option, index):
        """Return the size hint for the item."""
        description = index.data(Qt.ItemDataRole.UserRole)
        # Height: name line + description line (if exists) + padding
        base_height = 36
        if description:
            base_height += 18
        return QSize(option.rect.width(), base_height)


class SkillCompleter(QCompleter):
    """
    Custom completer for skill names, activated by '/' prefix.

    Features:
    - Only shows completions when text starts with '/'
    - Case-insensitive matching
    - Shows skill names as '/skill-name' with description
    - Theme-aware styling
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills: dict[str, str] = {}  # name -> description

        # Create custom model
        self._model = SkillListModel(self)
        self.setModel(self._model)

        # Create custom delegate
        self._delegate = SkillItemDelegate(self)
        self.popup().setItemDelegate(self._delegate)

        # Basic settings
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModelSorting(QCompleter.ModelSorting.CaseInsensitivelySortedModel)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setMaxVisibleItems(8)

    def update_skills(self, skills: list[dict]) -> None:
        """
        Update skill list for completion.

        Args:
            skills: List of dicts with 'name' and 'description' keys
        """
        self._skills = {s["name"]: s.get("description", "") for s in skills}
        self._model.set_skills(skills)
        logger.debug(f"[SkillCompleter] update_skills: {len(skills)} items")

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
        return text.startswith("/")

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
        super().complete(rect)

    def _apply_popup_style(self) -> None:
        """Apply theme-aware styling to the popup."""
        from harness_client.themes import get_theme

        theme = get_theme()
        self._delegate.set_theme(theme)

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
                border-radius: {theme.RADIUS_SM};
                margin: 2px 0;
            }}
        """)