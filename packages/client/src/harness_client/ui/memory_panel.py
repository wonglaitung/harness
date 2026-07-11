"""
Memory panel for managing persistent global memory entries.

Features:
- Display memory entries with importance indicator (high/medium/low)
- Adjust importance level via slider
- Add/edit/remove entries with importance support
"""

from PyQt6.QtCore import QAbstractAnimation, Qt, pyqtSignal, QRectF, QPointF, QPropertyAnimation, QParallelAnimationGroup
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QFrame,
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
from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener
from harness_client.ui.right_panel import CollapsibleSection
from harness_client.ui.dialog_styles import get_muted_label_stylesheet

# Maximum content height for memory section when expanded
# 50% larger than MoreToolsSection (350 * 1.5 ≈ 525)
MEMORY_MAX_CONTENT_HEIGHT = 525


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
        # Register theme listener
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

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

        self._name_label = QLabel(self._display_name)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(self._name_label)

        header_layout.addStretch()

        self._add_btn = QPushButton("+")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM};
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                color: {theme.ACCENT};
            }}
        """)
        self._add_btn.setToolTip("添加记忆条目")
        self._add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(self._add_btn)

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

        # Content label - save as widget property for theme updates
        content_label = QLabel(entry.content)
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_XS};
            }}
        """)
        content_label.setWordWrap(True)
        content_label.setProperty("isContentLabel", True)  # Mark for theme updates
        layout.addWidget(content_label, 1)

        # Importance slider (custom painted)
        importance_slider = ImportanceSlider(entry.importance)
        importance_slider.valueChanged.connect(
            lambda value: self._on_importance_changed(index, value)
        )
        layout.addWidget(importance_slider)

        # Remove button - save as widget property for theme updates
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
        remove_btn.setProperty("isRemoveButton", True)  # Mark for theme updates
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

    def _on_theme_changed(self):
        """Handle theme change - update all child widgets."""
        theme = get_theme()
        # Update header elements
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM};
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                color: {theme.ACCENT};
            }}
        """)
        # Update entry widgets and their children
        for widget in self._entry_widgets:
            # Update widget background
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme.APP_BACKGROUND};
                    border-radius: {theme.RADIUS_SM};
                }}
            """)
            # Find and update content labels using property
            for label in widget.findChildren(QLabel):
                if label.property("isContentLabel"):
                    label.setStyleSheet(f"""
                        QLabel {{
                            color: {theme.TEXT};
                            font-size: {theme.FONT_SIZE_XS};
                        }}
                    """)
            # Find and update remove buttons using property
            for btn in widget.findChildren(QPushButton):
                if btn.property("isRemoveButton"):
                    btn.setStyleSheet(f"""
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
            # Find and update ImportanceSlider
            for child in widget.findChildren(ImportanceSlider):
                child.update()
        # Update placeholder label
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 6px;
            }}
        """)


class MemorySection(CollapsibleSection):
    """Section for managing global memory entries with importance support.

    Caps its expanded height to prevent overflow in the right panel.
    """

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
        super().__init__("记忆", parent=parent)
        self._capped_content_height = 0
        self._collapsed_header_height = 0
        self._setup_content()
        # Connect animation finished signal to lock height after animation
        self.toggle_animation.finished.connect(self._on_animation_finished)
        # Note: Theme listener is registered in CollapsibleSection.__init__

    def _on_toggle(self, checked: bool):
        """Override to cap animation values before starting animation."""
        self._is_collapsed = not checked

        # Update button arrow
        if checked:  # Expanded
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Forward)
        else:  # Collapsed
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Backward)

        # Get current content height
        content_widget = self.content_area.widget()
        content_height = content_widget.sizeHint().height() if content_widget else 0
        collapsed_height = self.toggle_button.sizeHint().height()

        # Cap the height
        capped_height = min(content_height, MEMORY_MAX_CONTENT_HEIGHT)

        # Set animation values with cap
        for i in range(self.toggle_animation.animationCount() - 1):
            anim = self.toggle_animation.animationAt(i)
            anim.setDuration(self._animation_duration)
            anim.setStartValue(collapsed_height)
            anim.setEndValue(collapsed_height + capped_height)

        content_anim = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_anim.setDuration(self._animation_duration)
        content_anim.setStartValue(0)
        content_anim.setEndValue(capped_height)

        # Store capped height for use after animation
        self._capped_content_height = capped_height if checked else 0
        self._collapsed_header_height = collapsed_height

        self.toggle_animation.start()

    def _on_animation_finished(self):
        """Lock the height after animation completes to prevent resizing."""
        if self._collapsed_header_height <= 0:
            return

        if self._is_collapsed:
            # Collapsed state - lock to header height only
            self.setMaximumHeight(self._collapsed_header_height)
            self.content_area.setMaximumHeight(0)
        else:
            # Expanded state - lock to capped height
            total_height = self._collapsed_header_height + self._capped_content_height
            self.setMaximumHeight(total_height)
            self.content_area.setMaximumHeight(self._capped_content_height)

    def set_collapsed(self, collapsed: bool, animate: bool = True):
        """Override to cap expanded content height."""
        if self._is_collapsed == collapsed:
            return
        self._is_collapsed = collapsed

        # Update button state
        self.toggle_button.setChecked(not collapsed)

        if collapsed:
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Backward)
        else:
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Forward)

        if animate:
            # Cap the animation end value
            collapsed_height = self.toggle_button.sizeHint().height()
            for i in range(self.toggle_animation.animationCount() - 1):
                anim = self.toggle_animation.animationAt(i)
                anim.setEndValue(collapsed_height + MEMORY_MAX_CONTENT_HEIGHT)
            content_anim = self.toggle_animation.animationAt(
                self.toggle_animation.animationCount() - 1
            )
            content_anim.setEndValue(MEMORY_MAX_CONTENT_HEIGHT)
            self.toggle_animation.start()
        else:
            collapsed_height = self.toggle_button.sizeHint().height()
            content_widget = self.content_area.widget()
            content_height = (
                min(content_widget.sizeHint().height(), MEMORY_MAX_CONTENT_HEIGHT)
                if content_widget
                else 0
            )

            if collapsed:
                self.setMinimumHeight(collapsed_height)
                self.setMaximumHeight(collapsed_height)
                self.content_area.setMaximumHeight(0)
            else:
                self.setMinimumHeight(collapsed_height + content_height)
                self.setMaximumHeight(collapsed_height + content_height)
                self.content_area.setMaximumHeight(content_height)

    def _setup_content(self):
        """Setup the memory section content."""
        theme = get_theme()
        # Scroll area for all categories
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"""
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
        self.add_widget(self._scroll, 1)

        # Container for categories
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(10)
        self._scroll.setWidget(container)

        # Info label with importance legend
        self._info_label = QLabel(
            "全局记忆存储在 ~/.harness/MEMORY.md\n"
            "● 绿色=高重要 · ● 橙色=中重要 · ● 灰色=低重要"
        )
        self._info_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 6px;
            }}
        """)
        self._container_layout.addWidget(self._info_label)

        # Create category sections
        self._category_sections: dict[MemoryCategory, CategorySection] = {}

        categories = [
            MemoryCategory.USER_PROFILE,
            MemoryCategory.KEY_DECISIONS,
            MemoryCategory.LEARNED_PATTERNS,
            MemoryCategory.PROJECT_CONTEXT,
        ]

        for i, category in enumerate(categories):
            display_name = self.CATEGORY_NAMES.get(category, category.value)
            section = CategorySection(category, display_name)
            section.add_clicked.connect(self._on_add_clicked)
            section.entry_double_clicked.connect(self._on_edit_clicked)
            section.remove_clicked.connect(self._on_remove_clicked)
            section.importance_changed.connect(self._on_importance_changed)
            self._container_layout.addWidget(section)
            self._category_sections[category] = section

            # Add separator between categories (not after the last one)
            if i < len(categories) - 1:
                separator = QWidget()
                separator.setFixedHeight(1)
                separator.setStyleSheet(f"""
                    QWidget {{
                        background-color: {theme.BORDER};
                    }}
                """)
                self._container_layout.addWidget(separator)

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

    def _on_theme_changed(self):
        """Handle theme change - update all category sections."""
        super()._on_theme_changed()  # Update CollapsibleSection header
        theme = get_theme()
        # Update scroll area
        self._scroll.setStyleSheet(f"""
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
        # Update info label
        self._info_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 6px;
            }}
        """)
        # Update all category sections
        for section in self._category_sections.values():
            section._on_theme_changed()


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
        self._input.setMinimumWidth(300)
        layout = self.layout()
        layout.addWidget(self._input, 1, 0, 1, layout.columnCount())

        # Importance slider (0-100)
        self._importance_slider = QSlider(Qt.Orientation.Horizontal)
        self._importance_slider.setMinimum(0)
        self._importance_slider.setMaximum(100)
        self._importance_slider.setValue(50)  # Default: medium importance

        # Add importance label
        importance_label = QLabel("重要性:")
        importance_label.setStyleSheet(get_muted_label_stylesheet())
        layout.addWidget(importance_label, 2, 0)
        layout.addWidget(self._importance_slider, 3, 0, 1, layout.columnCount())

    def get_content(self) -> str:
        """Get the entered content."""
        return self._input.text().strip()

    def get_importance(self) -> float:
        """Get the importance level (0.0-1.0)."""
        return self._importance_slider.value() / 100.0