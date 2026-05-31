"""
Sidebar panel with sessions, MCP servers, and skills.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QGroupBox, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction


class SidebarPanel(QWidget):
    """Left sidebar with session list, MCP servers, and skills."""

    # Signals
    work_dir_changed = pyqtSignal(Path)
    mcp_connect_requested = pyqtSignal(str)
    skill_load_requested = pyqtSignal(Path)
    session_delete_requested = pyqtSignal(str)
    session_switch_requested = pyqtSignal(str)
    session_new_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.work_dir = Path.cwd()
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Sessions group
        sessions_group = QGroupBox("📁 会话列表")
        sessions_layout = QVBoxLayout(sessions_group)

        self.session_list = QListWidget()
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._on_session_context_menu)
        self.session_list.itemClicked.connect(self._on_session_clicked)
        sessions_layout.addWidget(self.session_list)

        new_session_btn = QPushButton("➕ 新建会话")
        new_session_btn.clicked.connect(self._on_new_session)
        sessions_layout.addWidget(new_session_btn)

        layout.addWidget(sessions_group)

        # MCP Servers group
        mcp_group = QGroupBox("🔌 MCP 服务器")
        mcp_layout = QVBoxLayout(mcp_group)

        self.mcp_list = QListWidget()
        self.mcp_list.itemDoubleClicked.connect(self._on_mcp_double_click)
        mcp_layout.addWidget(self.mcp_list)

        mcp_btn_layout = QHBoxLayout()
        add_mcp_btn = QPushButton("➕ 添加")
        add_mcp_btn.clicked.connect(self._on_add_mcp)
        mcp_btn_layout.addWidget(add_mcp_btn)

        refresh_mcp_btn = QPushButton("🔄 刷新")
        refresh_mcp_btn.clicked.connect(self._on_refresh_mcp)
        mcp_btn_layout.addWidget(refresh_mcp_btn)

        mcp_layout.addLayout(mcp_btn_layout)
        layout.addWidget(mcp_group)

        # Skills group
        skills_group = QGroupBox("⚡ 技能列表")
        skills_layout = QVBoxLayout(skills_group)

        self.skill_list = QListWidget()
        self.skill_list.itemDoubleClicked.connect(self._on_skill_double_click)
        skills_layout.addWidget(self.skill_list)

        skill_btn_layout = QHBoxLayout()
        load_skill_btn = QPushButton("📂 加载")
        load_skill_btn.clicked.connect(self._on_load_skill)
        skill_btn_layout.addWidget(load_skill_btn)

        new_skill_btn = QPushButton("➕ 新建")
        new_skill_btn.clicked.connect(self._on_new_skill)
        skill_btn_layout.addWidget(new_skill_btn)

        skills_layout.addLayout(skill_btn_layout)
        layout.addWidget(skills_group)

        # Work directory group
        work_group = QGroupBox("📂 工作目录")
        work_layout = QVBoxLayout(work_group)

        self.work_dir_label = QLabel(str(self.work_dir))
        self.work_dir_label.setWordWrap(True)
        self.work_dir_label.setStyleSheet("color: #666; font-size: 11px;")
        work_layout.addWidget(self.work_dir_label)

        change_dir_btn = QPushButton("更改...")
        change_dir_btn.clicked.connect(self._on_change_work_dir)
        work_layout.addWidget(change_dir_btn)

        layout.addWidget(work_group)

        layout.addStretch()

    # === Session List Management ===

    def update_sessions(self, current_session, history_sessions: list):
        """
        Update the session list display.

        Args:
            current_session: Current ClientSession object (or None)
            history_sessions: List of historical ClientSession objects
        """
        self.session_list.clear()

        # Current session (always first)
        if current_session:
            item = QListWidgetItem(f"🔵 {current_session.name}")
            item.setData(Qt.ItemDataRole.UserRole, current_session.id)
            self.session_list.addItem(item)

        # Historical sessions
        for session in history_sessions:
            item = QListWidgetItem(f"📄 {session.name}")
            item.setData(Qt.ItemDataRole.UserRole, session.id)
            self.session_list.addItem(item)

    def _on_new_session(self):
        """Handle new session button click."""
        self.session_new_requested.emit()

    def _on_session_clicked(self, item: QListWidgetItem):
        """Handle session list item click."""
        row = self.session_list.row(item)
        session_id = item.data(Qt.ItemDataRole.UserRole)

        # First item is current session - no action needed
        if row == 0:
            return

        # Switch to this session
        if session_id:
            self.session_switch_requested.emit(session_id)

    def _on_session_context_menu(self, position):
        """Show context menu for session list."""
        item = self.session_list.itemAt(position)
        if not item:
            return

        row = self.session_list.row(item)
        text = item.text()

        # Don't show menu for current session (first item)
        if row == 0:
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        if not session_id:
            return

        menu = QMenu(self)

        delete_action = QAction("🗑️ 删除会话", self)
        delete_action.triggered.connect(lambda: self._on_delete_session(session_id, text))
        menu.addAction(delete_action)

        menu.exec(self.session_list.mapToGlobal(position))

    def _on_delete_session(self, session_id: str, session_name: str):
        """Handle delete session request with confirmation."""
        display_name = session_name.replace("🔵 ", "").replace("📄 ", "")
        if "(" in display_name:
            display_name = display_name.split("(")[0].strip()

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话「{display_name}」吗？\n\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.session_delete_requested.emit(session_id)

    # === MCP Servers ===

    def _on_add_mcp(self):
        """Add MCP server dialog."""
        from harness_client.ui.mcp_panel import MCPServerDialog
        dialog = MCPServerDialog(self)
        if dialog.exec():
            config = dialog.get_config()
            self.mcp_config = config

    def _on_refresh_mcp(self):
        """Refresh MCP server list."""
        pass

    def _on_mcp_double_click(self, item: QListWidgetItem):
        """Handle MCP server double click."""
        text = item.text()
        parts = text.split()
        if len(parts) >= 2:
            server_name = parts[1]
            self.mcp_connect_requested.emit(server_name)

    def add_mcp_server(self, name: str, status: str = "未连接"):
        """Add MCP server to list."""
        icon = "✓" if status == "已连接" else "○"
        self.mcp_list.addItem(f"{icon} {name} ({status})")

    # === Skills ===

    def _on_load_skill(self):
        """Load skills from directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "选择技能目录")
        if dir_path:
            self.skill_load_requested.emit(Path(dir_path))

    def _on_new_skill(self):
        """Create new skill."""
        from harness_client.ui.skill_dialog import SkillEditDialog
        dialog = SkillEditDialog(self)
        if dialog.exec():
            pass

    def _on_skill_double_click(self, item: QListWidgetItem):
        """Handle skill double click."""
        pass

    def add_skill(self, name: str, status: str = "已启用"):
        """Add skill to list."""
        self.skill_list.addItem(f"{name} ({status})")

    # === Work Directory ===

    def _on_change_work_dir(self):
        """Change work directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择工作目录", str(self.work_dir)
        )
        if dir_path:
            self.work_dir = Path(dir_path)
            self.work_dir_label.setText(str(self.work_dir))
            self.work_dir_changed.emit(self.work_dir)

    def update_work_dir(self, path: Path):
        """Update work directory display."""
        self.work_dir = path
        self.work_dir_label.setText(str(path))
