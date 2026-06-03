"""
Right panel with collapsible sections for skills, MCP servers, and file tree.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """A collapsible section widget with header and content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._is_collapsed = False
        self._title = title
        self._setup_ui()

    def _setup_ui(self):
        """Setup the collapsible section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header button
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
        layout.addWidget(self.header_btn)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 4, 8, 8)
        self.content_layout.setSpacing(4)
        layout.addWidget(self.content_widget, 1)  # stretch=1 to fill section

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

    def __init__(self, parent=None):
        super().__init__("技能", parent)
        self._setup_content()

    def _setup_content(self):
        """Setup skills list content."""
        # Skills list
        self.skills_list = QLabel("暂无已加载的技能")
        self.skills_list.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 12px;
                padding: 4px;
            }
        """)
        self.skills_list.setWordWrap(True)
        self.add_widget(self.skills_list)

    def update_skills(self, skills: list):
        """Update the skills list display.

        Args:
            skills: List of dicts with 'name' and 'enabled' keys
        """
        if not skills:
            self.skills_list.setText("暂无已加载的技能")
            return

        # Build skills display
        lines = []
        for skill in skills:
            status = "✓" if skill.get("enabled", True) else "○"
            lines.append(f"{status} {skill.get('name', 'Unknown')}")
        self.skills_list.setText("\n".join(lines))


class MCPServersSection(CollapsibleSection):
    """Section displaying MCP server status."""

    server_double_clicked = pyqtSignal(str)  # server name
    add_server_requested = pyqtSignal()  # request to add server
    toggle_server_requested = pyqtSignal(str)  # server name to connect/disconnect

    def __init__(self, parent=None):
        super().__init__("MCP 服务器", parent)
        self._setup_content()

    def _setup_content(self):
        """Setup MCP servers list content."""
        # Add server button
        self.add_btn = QPushButton("+ 添加服务器")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px 12px;
                color: #d4d4d4;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3e3e42;
                border-color: #007acc;
            }
        """)
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.add_widget(self.add_btn)

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
    """Section displaying workspace file tree with lazy loading."""

    file_clicked = pyqtSignal(Path)
    work_dir_changed = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__("工作区", parent)
        self._work_dir = Path.cwd()
        self._setup_content()

    def _setup_content(self):
        """Setup file tree content."""
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

        # File tree view
        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["文件"])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #171717;
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
                background-color: #2a2a2a;
            }
        """)
        self.tree_view.clicked.connect(self._on_item_clicked)
        self.tree_view.expanded.connect(self._on_item_expanded)
        self.add_widget(self.tree_view, 1)  # stretch=1 to fill space

        # Change directory button
        change_btn = QPushButton("更改工作目录...")
        change_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px 12px;
                color: #d4d4d4;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3e3e42;
            }
        """)
        change_btn.clicked.connect(self._on_change_dir)
        self.add_widget(change_btn)

        # Initialize with current directory
        self._load_root()

    def set_work_dir(self, path: Path):
        """Set the work directory."""
        self._work_dir = path
        self.work_dir_label.setText(path.name if path.name else str(path))
        self._load_root()

    def _load_root(self):
        """Load the root directory contents."""
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(["文件"])

        if not self._work_dir.exists():
            return

        root_item = QStandardItem(f"📁 {self._work_dir.name}")
        root_item.setData(str(self._work_dir), Qt.ItemDataRole.UserRole)
        root_item.setSelectable(False)

        # Load immediate children
        self._load_directory_contents(root_item, self._work_dir)
        self.tree_model.appendRow(root_item)

        # Expand root by default
        self.tree_view.expand(root_item.index())

    def _load_directory_contents(self, parent_item: QStandardItem, directory: Path):
        """Load directory contents into the tree item (non-recursive for lazy loading)."""
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            error_item = QStandardItem("⚠️ 权限不足")
            error_item.setForeground(Qt.GlobalColor.red)
            parent_item.appendRow(error_item)
            return

        for entry in entries[:50]:  # Limit to 50 entries for performance
            if entry.is_dir():
                # Folder - add placeholder for lazy loading
                folder_item = QStandardItem(f"📁 {entry.name}")
                folder_item.setData(str(entry), Qt.ItemDataRole.UserRole)
                # Add placeholder child to indicate expandable
                placeholder = QStandardItem("...")
                placeholder.setData("__placeholder__", Qt.ItemDataRole.UserRole)
                folder_item.appendRow(placeholder)
                parent_item.appendRow(folder_item)
            else:
                # File
                icon = self._get_file_icon(entry)
                file_item = QStandardItem(f"{icon} {entry.name}")
                file_item.setData(str(entry), Qt.ItemDataRole.UserRole)
                parent_item.appendRow(file_item)

    def _get_file_icon(self, path: Path) -> str:
        """Get an icon character for a file based on its extension."""
        ext = path.suffix.lower()
        icon_map = {
            ".py": "🐍",
            ".js": "📜",
            ".ts": "📜",
            ".json": "📋",
            ".yaml": "📋",
            ".yml": "📋",
            ".md": "📝",
            ".txt": "📄",
            ".html": "🌐",
            ".css": "🎨",
            ".sql": "🗃️",
            ".csv": "📊",
            ".xlsx": "📊",
            ".pdf": "📕",
            ".png": "🖼️",
            ".jpg": "🖼️",
            ".gif": "🖼️",
            ".zip": "📦",
            ".tar": "📦",
            ".gz": "📦",
        }
        return icon_map.get(ext, "📄")

    def _on_item_clicked(self, index):
        """Handle item click."""
        item = self.tree_model.itemFromIndex(index)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data != "__placeholder__":
                path = Path(data)
                if path.is_file():
                    self.file_clicked.emit(path)

    def _on_item_expanded(self, index):
        """Handle item expansion - lazy load children."""
        item = self.tree_model.itemFromIndex(index)
        if not item:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or data == "__placeholder__":
            return

        path = Path(data)
        if not path.is_dir():
            return

        # Check if we have a placeholder child (first child)
        first_child = item.child(0)
        if first_child and first_child.data(Qt.ItemDataRole.UserRole) == "__placeholder__":
            # Remove placeholder and load actual contents
            item.removeRow(0)
            self._load_directory_contents(item, path)

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
        self._load_root()


class RightPanel(QWidget):
    """Right panel with collapsible sections for skills, MCP, and files."""

    # Signals
    skill_double_clicked = pyqtSignal(str)
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

        # Skills section
        self.skills_section = SkillsSection()
        self.skills_section.skill_double_clicked.connect(self.skill_double_clicked)
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
