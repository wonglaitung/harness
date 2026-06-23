"""
Memory panel for managing persistent global memory entries.

Features:
- Display memory entries with importance indicator (high/medium/low)
- Adjust importance level via slider
- Add/edit/remove entries with importance support
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from harness.memory.memory_file import MemoryCategory, MemoryEntry, MemorySource
from harness_client.themes import get_theme
from harness_client.ui.right_panel import CollapsibleSection


class ImportanceSlider(QWidget):
    """
    Custom painted importance slider with visual feedback.

    Features:
    - Colored track based on importance level
    - Circular handle with hover enlargement
    - Tooltip showing current value
    - Mouse drag interaction
    """

    valueChanged = pyqtSignal(float)  # 0.0 to 1.0

    def __init__(self, initial_value: float = 0.5, parent=None):
        super().__init__(parent)
        self._value = initial_value
        self._hover = False
        self._dragging = False

        # Fixed size
        self.setFixedHeight(20)
        self.setMinimumWidth(60)
        self.setMaximumWidth(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def value(self) -> float:
        """Get the current value (0.0 to 1.0)."""
        return self._value

    def setValue(self, value: float):
        """Set the value (0.0 to 1.0)."""
        value = max(0.0, min(1.0, value))
        if self._value != value:
            self._value = value
            self.valueChanged.emit(self._value)
            self.update()

    def _get_color_for_value(self) -> str:
        """Get color based on importance value."""
        if self._value >= 0.8:
            return "#22c55e"  # green - high
        elif self._value >= 0.5:
            return "#f59e0b"  # orange - medium
        else:
            return "#6b7280"  # gray - low

    def _get_handle_rect(self) -> QRectF:
        """Calculate handle rectangle based on value and hover state."""
        handle_size = 16 if self._hover or self._dragging else 14
        track_width = self.width() - handle_size
        x = self._value * track_width

        return QRectF(
            x,
            (self.height() - handle_size) / 2,
            handle_size,
            handle_size
        )

    def paintEvent(self, event):
        """Paint the slider with track, fill, and handle."""
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track dimensions
        track_height = 4
        track_y = (self.height() - track_height) / 2
        track_rect = QRectF(0, track_y, self.width(), track_height)

        # Draw background track
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.CHROME)))
        painter.drawRoundedRect(track_rect, 2, 2)

        # Draw filled portion
        fill_color = QColor(self._get_color_for_value())
        fill_width = self._value * self.width()
        fill_rect = QRectF(0, track_y, fill_width, track_height)
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(fill_rect, 2, 2)

        # Draw handle
        handle_rect = self._get_handle_rect()
        handle_color = QColor(theme.ACCENT)
        painter.setBrush(QBrush(handle_color))
        painter.drawEllipse(handle_rect)

        painter.end()

    def enterEvent(self, event):
        """Handle mouse enter - enlarge handle."""
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave - shrink handle."""
        self._hover = False
        self.update()
        # Hide tooltip
        QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press - start dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_value_from_pos(event.position().x())
            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move - update value while dragging."""
        if self._dragging:
            self._update_value_from_pos(event.position().x())
        else:
            # Show tooltip on hover
            self._show_tooltip()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.update()

    def _update_value_from_pos(self, x: float):
        """Update value based on mouse position."""
        handle_size = 14
        track_width = self.width() - handle_size
        value = (x - handle_size / 2) / track_width
        self.setValue(max(0.0, min(1.0, value)))

    def _show_tooltip(self):
        """Show tooltip with current importance level."""
        if self._value >= 0.8:
            level = "高"
        elif self._value >= 0.5:
            level = "中"
        else:
            level = "低"
        QToolTip.showText(
            self.mapToGlobal(self.rect().bottomLeft()),
            f"重要性: {level} ({self._value:.0%})",
            self
        )


class CategorySection(QWidget):
    """A sub-section for a single memory category."""

    add_clicked = pyqtSignal(str)  # category name
    entry_double_clicked = pyqtSignal(str, int)  # category, index
    remove_clicked = pyqtSignal(str, int)  # category, index
    importance_changed = pyqtSignal(str, int, float)  # category, index, new_importance

    def __init__(self, category: MemoryCategory, display_name: str, parent=None):
        super().__init__(parent)
        self._category = category
        self._display_name = display_name
        self._entries: list[MemoryEntry] = []
        self._entry_widgets: list[QWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the category section UI."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header with category name and add button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        name_label = QLabel(self._display_name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        add_btn = QPushButton("+")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                min-width: 22px;
                max-width: 22px;
                min-height: 22px;
                max-height: 22px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.ACCENT};
            }}
        """)
        add_btn.setToolTip("添加记忆条目")
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)

        layout.addWidget(header)

        # Entries container
        self.entries_widget = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_widget)
        self.entries_layout.setContentsMargins(6, 6, 6, 6)
        self.entries_layout.setSpacing(4)
        layout.addWidget(self.entries_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无记忆条目")
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 6px;
            }}
        """)
        self.entries_layout.addWidget(self.placeholder_label)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self._category.value)

    def update_entries(self, entries: list[MemoryEntry]):
        """Update the entries display with MemoryEntry objects."""
        # Clear existing widgets
        for widget in self._entry_widgets:
            widget.deleteLater()
        self._entry_widgets.clear()

        self._entries = entries

        if not entries:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        for i, entry in enumerate(entries):
            item_widget = self._create_entry_item(entry, i)
            self.entries_layout.addWidget(item_widget)
            self._entry_widgets.append(item_widget)

    def _get_importance_color(self, importance: float) -> str:
        """Get color for importance level."""
        if importance >= 0.8:
            return "#22c55e"  # green - high importance
        elif importance >= 0.5:
            return "#f59e0b"  # orange - medium importance
        else:
            return "#6b7280"  # gray - low importance

    def _get_importance_name(self, importance: float) -> str:
        """Get display name for importance level."""
        if importance >= 0.8:
            return "高"
        elif importance >= 0.5:
            return "中"
        else:
            return "低"

    def _create_entry_item(self, entry: MemoryEntry, index: int) -> QWidget:
        """Create an entry item widget with importance indicator."""
        theme = get_theme()
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Importance indicator (colored dot)
        importance_color = self._get_importance_color(entry.importance)
        importance_indicator = QLabel("●")
        importance_indicator.setStyleSheet(f"""
            QLabel {{
                color: {importance_color};
                font-size: 12px;
            }}
        """)
        importance_indicator.setToolTip(f"重要性: {self._get_importance_name(entry.importance)} ({entry.importance:.0%})")
        layout.addWidget(importance_indicator)

        # Content label
        content_label = QLabel(entry.content)
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_XS};
            }}
        """)
        content_label.setWordWrap(True)
        layout.addWidget(content_label, 1)

        # Importance slider (custom painted)
        importance_slider = ImportanceSlider(entry.importance)
        importance_slider.valueChanged.connect(
            lambda value: self._on_importance_changed(index, value)
        )
        layout.addWidget(importance_slider)

        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_MD};
                min-width: 22px;
                max-width: 22px;
            }}
            QPushButton:hover {{
                color: {theme.DANGER};
            }}
        """)
        remove_btn.setToolTip("删除此条目")
        remove_btn.clicked.connect(lambda checked: self._on_remove_clicked(index))
        layout.addWidget(remove_btn)

        # Double-click to edit
        widget.mouseDoubleClickEvent = lambda event: self._on_double_click(index)

        return widget

    def _on_importance_changed(self, index: int, importance: float):
        """Handle importance slider change."""
        self.importance_changed.emit(self._category.value, index, importance)

    def _on_remove_clicked(self, index: int):
        """Handle remove button click."""
        self.remove_clicked.emit(self._category.value, index)

    def _on_double_click(self, index: int):
        """Handle double-click on entry."""
        self.entry_double_clicked.emit(self._category.value, index)


class MemorySection(CollapsibleSection):
    """Section for managing global memory entries with importance support."""

    add_entry_requested = pyqtSignal(str)  # category name
    edit_entry_requested = pyqtSignal(str, int)  # category, index
    remove_entry_requested = pyqtSignal(str, int)  # category, index
    importance_changed = pyqtSignal(str, int, float)  # category, index, importance

    # Category display names in Chinese
    CATEGORY_NAMES = {
        MemoryCategory.USER_PROFILE: "用户偏好",
        MemoryCategory.KEY_DECISIONS: "关键决策",
        MemoryCategory.LEARNED_PATTERNS: "学习模式",
        MemoryCategory.PROJECT_CONTEXT: "项目上下文",
    }

    def __init__(self, parent=None):
        super().__init__("记忆", parent)
        self._setup_content()

    def _setup_content(self):
        """Setup the memory section content."""
        theme = get_theme()
        # Scroll area for all categories
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.BORDER};
                border-radius: 3px;
            }}
        """)
        self.add_widget(scroll, 1)

        # Container for categories
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(10)
        scroll.setWidget(container)

        # Info label with importance legend
        info_label = QLabel(
            "全局记忆存储在 ~/.harness/MEMORY.md\n"
            "● 绿色=高重要 · ● 橙色=中重要 · ● 灰色=低重要"
        )
        info_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 6px;
            }}
        """)
        self._container_layout.addWidget(info_label)

        # Create category sections
        self._category_sections: dict[MemoryCategory, CategorySection] = {}

        for category in [
            MemoryCategory.USER_PROFILE,
            MemoryCategory.KEY_DECISIONS,
            MemoryCategory.LEARNED_PATTERNS,
            MemoryCategory.PROJECT_CONTEXT,
        ]:
            display_name = self.CATEGORY_NAMES.get(category, category.value)
            section = CategorySection(category, display_name)
            section.add_clicked.connect(self._on_add_clicked)
            section.entry_double_clicked.connect(self._on_edit_clicked)
            section.remove_clicked.connect(self._on_remove_clicked)
            section.importance_changed.connect(self._on_importance_changed)
            self._container_layout.addWidget(section)
            self._category_sections[category] = section

        # Spacer
        self._container_layout.addStretch()

    def _on_add_clicked(self, category_name: str):
        """Handle add button click from category section."""
        self.add_entry_requested.emit(category_name)

    def _on_edit_clicked(self, category_name: str, index: int):
        """Handle double-click on entry."""
        self.edit_entry_requested.emit(category_name, index)

    def _on_remove_clicked(self, category_name: str, index: int):
        """Handle remove button click."""
        self.remove_entry_requested.emit(category_name, index)

    def _on_importance_changed(self, category_name: str, index: int, importance: float):
        """Handle importance slider change."""
        self.importance_changed.emit(category_name, index, importance)

    def update_memory(self, sections):
        """
        Update memory display from MemorySections.

        Args:
            sections: MemorySections from MemoryController
        """
        # Update each category with entries (need to fetch with metadata)
        # Note: This expects the controller to provide list[MemoryEntry]
        # For now, we'll use the string entries from sections
        # The actual MemoryEntry list comes from controller.get_entries()

        # Convert string lists to MemoryEntry (with default importance)
        for category in [
            MemoryCategory.USER_PROFILE,
            MemoryCategory.KEY_DECISIONS,
            MemoryCategory.LEARNED_PATTERNS,
            MemoryCategory.PROJECT_CONTEXT,
        ]:
            section = sections.get_section(category)
            # Create MemoryEntry from strings (backward compatible)
            entries = []
            for content in section:
                entries.append(MemoryEntry(
                    category=category,
                    content=content,
                    source=MemorySource.USER_INPUT,
                ))
            self._category_sections[category].update_entries(entries)

    def update_memory_with_entries(
        self,
        category: MemoryCategory,
        entries: list[MemoryEntry],
    ):
        """
        Update memory display with full MemoryEntry objects.

        Args:
            category: Memory category
            entries: List of MemoryEntry with importance metadata
        """
        self._category_sections[category].update_entries(entries)


class AddEntryDialog(QMessageBox):
    """Dialog for adding a new memory entry with importance setting."""

    def __init__(self, category_name: str, parent=None):
        super().__init__(parent)
        theme = get_theme()
        self.setWindowTitle(f"添加记忆 - {category_name}")
        self.setText("请输入记忆内容和重要性:")
        self.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        # Content input field
        self._input = QLineEdit()
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.COMPOSER};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                padding: 10px;
                color: {theme.TEXT};
                min-width: 300px;
            }}
        """)
        layout = self.layout()
        layout.addWidget(self._input, 1, 0, 1, layout.columnCount())

        # Importance slider (0-100)
        self._importance_slider = QSlider(Qt.Orientation.Horizontal)
        self._importance_slider.setMinimum(0)
        self._importance_slider.setMaximum(100)
        self._importance_slider.setValue(50)  # Default: medium importance
        self._importance_slider.setStyleSheet(f"""
            QSlider {{
                background-color: {theme.COMPOSER};
                border-radius: {theme.RADIUS_SM};
                padding: 5px;
            }}
        """)
        # Add importance label
        importance_label = QLabel("重要性:")
        importance_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
            }}
        """)
        layout.addWidget(importance_label, 2, 0)
        layout.addWidget(self._importance_slider, 3, 0, 1, layout.columnCount())

    def get_content(self) -> str:
        """Get the entered content."""
        return self._input.text().strip()

    def get_importance(self) -> float:
        """Get the importance level (0.0-1.0)."""
        return self._importance_slider.value() / 100.0