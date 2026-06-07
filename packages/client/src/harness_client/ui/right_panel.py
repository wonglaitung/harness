"""
Right panel with collapsible sections for skills, MCP servers, and file tree.
"""

from pathlib import Path

from PyQt6.QtCore import QDir, Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFileIconProvider,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class CustomFileIconProvider(QFileIconProvider):
    """Custom icon provider that uses Qt built-in icons for files and folders."""

    def __init__(self):
        super().__init__()
        style = QApplication.style()
        self._folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._folder_open_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self._file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def icon(self, info):
        """Return appropriate icon based on file type.

        Args:
            info: QFileInfo object

        Returns:
            QIcon for the file/folder
        """
        if info.isDir():
            return self._folder_icon
        return self._file_icon


class CollapsibleSection(QWidget):
    """A collapsible section widget with header and content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._is_collapsed = False
        self._title = title
        self._header_buttons: list[QPushButton] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the collapsible section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header container
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        # Header button (fold/unfold)
        self.header_btn = QPushButton(f"▼ {self._title}")
        self.header_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d30;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                text-align: left;
                color: #d4d4d4;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3e3e42;
            }
        """)
        self.header_btn.clicked.connect(self._toggle_collapsed)
        header_layout.addWidget(self.header_btn, 1)  # stretch=1 to take remaining space

        # Container for extra header buttons (e.g., "+")
        self.header_buttons_widget = QWidget()
        self.header_buttons_layout = QHBoxLayout(self.header_buttons_widget)
        self.header_buttons_layout.setContentsMargins(0, 0, 8, 0)  # right margin
        self.header_buttons_layout.setSpacing(4)
        header_layout.addWidget(self.header_buttons_widget)

        layout.addWidget(header_widget)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 4, 8, 8)
        self.content_layout.setSpacing(4)
        layout.addWidget(self.content_widget, 1)  # stretch=1 to fill section

    def add_header_button(self, text: str, callback, tooltip: str = "") -> QPushButton:
        """Add a button to the header row.

        Args:
            text: Button text (e.g., "+")
            callback: Function to call on click
            tooltip: Optional tooltip text

        Returns:
            The created QPushButton
        """
        btn = QPushButton(text)
        btn.setStyleSheet("""
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
        if tooltip:
            btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        self.header_buttons_layout.addWidget(btn)
        self._header_buttons.append(btn)
        return btn

    def _toggle_collapsed(self):
        """Toggle collapsed state."""
        self._is_collapsed = not self._is_collapsed
        self.content_widget.setVisible(not self._is_collapsed)
        arrow = "▶" if self._is_collapsed else "▼"
        self.header_btn.setText(f"{arrow} {self._title}")

    def add_widget(self, widget: QWidget, stretch: int = 0):
        """Add a widget to the content area.

        Args:
            widget: Widget to add
            stretch: Stretch factor (0 = no stretch, >0 = proportional stretch)
        """
        self.content_layout.addWidget(widget, stretch)

    def set_collapsed(self, collapsed: bool):
        """Set collapsed state."""
        self._is_collapsed = collapsed
        self.content_widget.setVisible(not collapsed)
        arrow = "▶" if collapsed else "▼"
        self.header_btn.setText(f"{arrow} {self._title}")


class SkillsSection(CollapsibleSection):
    """Section displaying loaded skills."""

    skill_double_clicked = pyqtSignal(str)  # skill name
    add_skill_requested = pyqtSignal()  # request to add new skill

    def __init__(self, parent=None):
        super().__init__("技能", parent)
        # Add "+" button in header
        self.add_header_button("+", self._on_add_clicked, "新建技能")
        self._setup_content()

    def _setup_content(self):
        """Setup skills list content."""
        # Skills list container
        self.skills_list_widget = QWidget()
        self.skills_list_layout = QVBoxLayout(self.skills_list_widget)
        self.skills_list_layout.setContentsMargins(0, 4, 0, 0)
        self.skills_list_layout.setSpacing(4)
        self.add_widget(self.skills_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无已加载的技能")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 12px;
                padding: 4px;
            }
        """)
        self.skills_list_layout.addWidget(self.placeholder_label)

        # Store skill item widgets
        self._skill_items: dict[str, QWidget] = {}

    def _on_add_clicked(self):
        """Handle add skill button click."""
        self.add_skill_requested.emit()

    def update_skills(self, skills: list):
        """Update the skills list display.

        Args:
            skills: List of dicts with 'name' and 'enabled' keys
        """
        # Clear existing items
        for item in self._skill_items.values():
            item.deleteLater()
        self._skill_items.clear()

        if not skills:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        for skill in skills:
            name = skill.get("name", "Unknown")
            enabled = skill.get("enabled", True)

            # Create skill item widget
            item_widget = self._create_skill_item(name, enabled)
            self.skills_list_layout.addWidget(item_widget)
            self._skill_items[name] = item_widget

    def _create_skill_item(self, name: str, enabled: bool) -> QWidget:
        """Create a skill item widget."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Status indicator
        indicator_color = "#50c878" if enabled else "#808080"
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {indicator_color}; font-size: 12px;")
        layout.addWidget(indicator)

        # Skill name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #d4d4d4; font-size: 12px;")
        layout.addWidget(name_label)

        layout.addStretch()

        # Double-click to edit
        widget.mouseDoubleClickEvent = lambda event, n=name: self._on_double_click(n)

        return widget

    def _on_double_click(self, name: str):
        """Handle double-click on skill item."""
        self.skill_double_clicked.emit(name)


class MCPServersSection(CollapsibleSection):
    """Section displaying MCP server status."""

    server_double_clicked = pyqtSignal(str)  # server name
    add_server_requested = pyqtSignal()  # request to add server
    toggle_server_requested = pyqtSignal(str)  # server name to connect/disconnect

    def __init__(self, parent=None):
        super().__init__("MCP 服务器", parent)
        # Add "+" button in header
        self.add_header_button("+", self._on_add_clicked, "添加服务器")
        self._setup_content()

    def _setup_content(self):
        """Setup MCP servers list content."""
        # Server list container
        self.server_list_widget = QWidget()
        self.server_list_layout = QVBoxLayout(self.server_list_widget)
        self.server_list_layout.setContentsMargins(0, 4, 0, 0)
        self.server_list_layout.setSpacing(4)
        self.add_widget(self.server_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无 MCP 服务器")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 12px;
                padding: 4px;
            }
        """)
        self.server_list_layout.addWidget(self.placeholder_label)

        # Store server item widgets
        self._server_items: dict[str, QWidget] = {}

    def _on_add_clicked(self):
        """Handle add server button click."""
        self.add_server_requested.emit()

    def update_servers(self, servers: list):
        """Update the MCP servers list display.

        Args:
            servers: List of dicts with 'name', 'status', and 'tools_count' keys
        """
        # Clear existing items
        for item in self._server_items.values():
            item.deleteLater()
        self._server_items.clear()

        if not servers:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        for server in servers:
            name = server.get("name", "Unknown")
            status = server.get("status", "未连接")
            tools_count = server.get("tools_count", 0)

            # Create server item widget
            item_widget = self._create_server_item(name, status, tools_count)
            self.server_list_layout.addWidget(item_widget)
            self._server_items[name] = item_widget

    def _create_server_item(self, name: str, status: str, tools_count: int) -> QWidget:
        """Create a server item widget."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Status indicator
        is_connected = status == "已连接"
        indicator_color = "#50c878" if is_connected else "#808080"
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {indicator_color}; font-size: 12px;")
        layout.addWidget(indicator)

        # Server name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #d4d4d4; font-size: 12px;")
        layout.addWidget(name_label)

        # Status text
        if is_connected:
            status_text = f"已连接 ({tools_count} 工具)"
            status_color = "#50c878"
        elif status == "连接中...":
            status_text = status
            status_color = "#dcdcaa"
        elif status == "错误":
            status_text = status
            status_color = "#f14c4c"
        else:
            status_text = status
            status_color = "#808080"

        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        layout.addWidget(status_label)

        layout.addStretch()

        # Connect/Disconnect button
        action_btn = QPushButton()
        if is_connected:
            action_btn.setText("断开")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5a1d1d;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    color: #f14c4c;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #6a2d2d;
                }
            """)
        else:
            action_btn.setText("连接")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1d3a5a;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    color: #4fc1ff;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2d4a6a;
                }
            """)

        action_btn.clicked.connect(lambda checked, n=name: self._on_toggle_server(n))
        layout.addWidget(action_btn)

        # Double-click to toggle
        widget.mouseDoubleClickEvent = lambda event, n=name: self._on_double_click(n)

        return widget

    def _on_toggle_server(self, name: str):
        """Handle connect/disconnect button click."""
        self.toggle_server_requested.emit(name)

    def _on_double_click(self, name: str):
        """Handle double-click on server item."""
        self.server_double_clicked.emit(name)


class FileTreeSection(CollapsibleSection):
    """Section displaying workspace file tree using QFileSystemModel."""

    file_clicked = pyqtSignal(Path)
    work_dir_changed = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__("工作区", parent)
        self._work_dir = Path.cwd()
        # Add folder button in header for changing directory
        self.add_header_button("📁", self._on_change_dir, "更改工作目录")
        self._setup_content()

    def _setup_content(self):
        """Setup file tree content."""
        from PyQt6.QtCore import QDir

        # Work directory name (editable)
        self.work_dir_label = QLabel(str(self._work_dir.name))
        self.work_dir_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-size: 12px;
                font-weight: bold;
                padding: 4px;
            }
        """)
        self.add_widget(self.work_dir_label)

        # File tree view with QFileSystemModel
        self.tree_view = QTreeView()
        self.fs_model = QFileSystemModel()
        self.fs_model.setIconProvider(CustomFileIconProvider())
        self.fs_model.setRootPath(str(self._work_dir))
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(str(self._work_dir)))

        # Hide size, type, date columns - only show name
        for col in [1, 2, 3]:
            self.tree_view.setColumnHidden(col, True)

        self.tree_view.setHeaderHidden(True)
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                color: #d4d4d4;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:selected {
                background-color: #094771;
            }
            QTreeView::item:hover {
                background-color: #3e3e42;
            }
            QTreeView::branch {
                background-color: #252526;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                background-color: #252526;
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                background-color: #252526;
            }
        """)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self.add_widget(self.tree_view, 1)  # stretch=1 to fill space

    def set_work_dir(self, path: Path):
        """Set the work directory."""
        self._work_dir = path
        self.work_dir_label.setText(path.name if path.name else str(path))
        self.fs_model.setRootPath(str(path))
        self.tree_view.setRootIndex(self.fs_model.index(str(path)))

    def _on_item_double_clicked(self, index):
        """Handle item double-click - open file."""
        path_str = self.fs_model.filePath(index)
        path = Path(path_str)
        if path.is_file():
            self.file_clicked.emit(path)

    def _on_change_dir(self):
        """Handle change directory button click."""
        from PyQt6.QtWidgets import QFileDialog

        dir_path = QFileDialog.getExistingDirectory(
            self, "选择工作目录", str(self._work_dir)
        )
        if dir_path:
            self.set_work_dir(Path(dir_path))
            self.work_dir_changed.emit(Path(dir_path))

    def refresh(self):
        """Refresh the file tree."""
        self.fs_model.setRootPath("")  # Force refresh
        self.fs_model.setRootPath(str(self._work_dir))
        self.tree_view.setRootIndex(self.fs_model.index(str(self._work_dir)))


class RightPanel(QWidget):
    """Right panel with collapsible sections for memory, skills, MCP, and files."""

    # Signals
    memory_add_requested = pyqtSignal(str)  # category name
    memory_edit_requested = pyqtSignal(str, int)  # category, index
    memory_remove_requested = pyqtSignal(str, int)  # category, index
    skill_double_clicked = pyqtSignal(str)
    add_skill_requested = pyqtSignal()
    server_double_clicked = pyqtSignal(str)
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)
    file_clicked = pyqtSignal(Path)
    work_dir_changed = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the right panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Memory section (first, before Skills)
        from harness_client.ui.memory_panel import MemorySection
        self.memory_section = MemorySection()
        self.memory_section.add_entry_requested.connect(self.memory_add_requested)
        self.memory_section.edit_entry_requested.connect(self.memory_edit_requested)
        self.memory_section.remove_entry_requested.connect(self.memory_remove_requested)
        layout.addWidget(self.memory_section)

        # Skills section
        self.skills_section = SkillsSection()
        self.skills_section.skill_double_clicked.connect(self.skill_double_clicked)
        self.skills_section.add_skill_requested.connect(self.add_skill_requested)
        layout.addWidget(self.skills_section)

        # MCP servers section
        self.mcp_section = MCPServersSection()
        self.mcp_section.server_double_clicked.connect(self.server_double_clicked)
        self.mcp_section.add_server_requested.connect(self.add_mcp_server_requested)
        self.mcp_section.toggle_server_requested.connect(self.toggle_mcp_server_requested)
        layout.addWidget(self.mcp_section)

        # File tree section
        self.file_section = FileTreeSection()
        self.file_section.file_clicked.connect(self.file_clicked)
        self.file_section.work_dir_changed.connect(self.work_dir_changed)
        layout.addWidget(self.file_section, 1)  # stretch=1 to fill remaining space

        # Set collapsed state for sections (default all expanded)
        # Users can click to collapse

    def update_memory(self, sections):
        """Update memory display."""
        self.memory_section.update_memory(sections)

    def update_skills(self, skills: list):
        """Update skills list."""
        self.skills_section.update_skills(skills)

    def update_servers(self, servers: list):
        """Update MCP servers list."""
        self.mcp_section.update_servers(servers)

    def set_work_dir(self, path: Path):
        """Set work directory for file tree."""
        self.file_section.set_work_dir(path)

    def refresh_files(self):
        """Refresh file tree."""
        self.file_section.refresh()
