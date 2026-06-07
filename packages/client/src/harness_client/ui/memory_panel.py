"""
Memory panel for managing persistent global memory entries.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from harness.memory.memory_file import MemoryCategory

from harness_client.ui.right_panel import CollapsibleSection


class CategorySection(QWidget):
    """A sub-section for a single memory category."""

    add_clicked = pyqtSignal(str)  # category name
    entry_double_clicked = pyqtSignal(str, int)  # category, index
    remove_clicked = pyqtSignal(str, int)  # category, index

    def __init__(self, category: MemoryCategory, display_name: str, parent=None):
        super().__init__(parent)
        self._category = category
        self._display_name = display_name
        self._entries: list[str] = []
        self._entry_widgets: list[QWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the category section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with category name and add button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        name_label = QLabel(self._display_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        add_btn = QPushButton("+")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                color: #d4d4d4;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3e3e42;
                border-color: #007acc;
            }
        """)
        add_btn.setToolTip("添加记忆条目")
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)

        layout.addWidget(header)

        # Entries container
        self.entries_widget = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_widget)
        self.entries_layout.setContentsMargins(4, 4, 4, 4)
        self.entries_layout.setSpacing(2)
        layout.addWidget(self.entries_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无记忆条目")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
                padding: 4px;
            }
        """)
        self.entries_layout.addWidget(self.placeholder_label)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self._category.value)

    def update_entries(self, entries: list[str]):
        """Update the entries display."""
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

    def _create_entry_item(self, content: str, index: int) -> QWidget:
        """Create an entry item widget."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Content label
        content_label = QLabel(content)
        content_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-size: 11px;
            }
        """)
        content_label.setWordWrap(True)
        layout.addWidget(content_label, 1)

        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #808080;
                font-size: 14px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton:hover {
                color: #f14c4c;
            }
        """)
        remove_btn.setToolTip("删除此条目")
        remove_btn.clicked.connect(lambda checked: self._on_remove_clicked(index))
        layout.addWidget(remove_btn)

        # Double-click to edit
        widget.mouseDoubleClickEvent = lambda event: self._on_double_click(index)

        return widget

    def _on_remove_clicked(self, index: int):
        """Handle remove button click."""
        self.remove_clicked.emit(self._category.value, index)

    def _on_double_click(self, index: int):
        """Handle double-click on entry."""
        self.entry_double_clicked.emit(self._category.value, index)


class MemorySection(CollapsibleSection):
    """Section for managing global memory entries."""

    add_entry_requested = pyqtSignal(str)  # category name
    edit_entry_requested = pyqtSignal(str, int)  # category, index
    remove_entry_requested = pyqtSignal(str, int)  # category, index

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
        # Scroll area for all categories
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #252526;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #3e3e42;
                border-radius: 4px;
            }
        """)
        self.add_widget(scroll, 1)

        # Container for categories
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(8)
        scroll.setWidget(container)

        # Info label
        info_label = QLabel("全局记忆存储在 ~/.harness/MEMORY.md")
        info_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
                padding: 4px;
            }
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

    def update_memory(self, sections):
        """
        Update memory display from MemorySections.

        Args:
            sections: MemorySections from MemoryController
        """
        # Update each category
        self._category_sections[MemoryCategory.USER_PROFILE].update_entries(
            sections.user_profile
        )
        self._category_sections[MemoryCategory.KEY_DECISIONS].update_entries(
            sections.key_decisions
        )
        self._category_sections[MemoryCategory.LEARNED_PATTERNS].update_entries(
            sections.learned_patterns
        )
        self._category_sections[MemoryCategory.PROJECT_CONTEXT].update_entries(
            sections.project_context
        )


class AddEntryDialog(QMessageBox):
    """Simple dialog for adding a new memory entry."""

    def __init__(self, category_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"添加记忆 - {category_name}")
        self.setText("请输入记忆内容:")
        self.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        # Add input field
        self._input = QLineEdit()
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 8px;
                color: #d4d4d4;
            }
        """)
        self._input.setMinimumWidth(300)
        # QMessageBox uses QGridLayout; add input below the text label
        # The default layout has: row 0 = text, row 1 = buttons
        # We insert our input at row 1, shifting buttons to row 2
        layout = self.layout()
        layout.addWidget(self._input, 1, 0, 1, layout.columnCount())

    def get_content(self) -> str:
        """Get the entered content."""
        return self._input.text().strip()