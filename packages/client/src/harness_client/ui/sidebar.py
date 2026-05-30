"""
Sidebar panel with sessions, MCP servers, and skills.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal


class SidebarPanel(QWidget):
    """Left sidebar with session list, MCP servers, and skills."""

    # Signals
    work_dir_changed = pyqtSignal(Path)

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
        sessions_group = QGroupBox("会话列表")
        sessions_layout = QVBoxLayout(sessions_group)

        self.session_list = QListWidget()
        self.session_list.addItem("当前会话")
        sessions_layout.addWidget(self.session_list)

        new_session_btn = QPushButton("新建会话")
        sessions_layout.addWidget(new_session_btn)

        layout.addWidget(sessions_group)

        # MCP Servers group
        mcp_group = QGroupBox("MCP 服务器")
        mcp_layout = QVBoxLayout(mcp_group)

        self.mcp_list = QListWidget()
        self.mcp_list.addItem("filesystem (已连接)")
        self.mcp_list.addItem("github (已连接)")
        mcp_layout.addWidget(self.mcp_list)

        mcp_btn_layout = QHBoxLayout()
        add_mcp_btn = QPushButton("添加")
        add_mcp_btn.clicked.connect(self._on_add_mcp)
        mcp_btn_layout.addWidget(add_mcp_btn)

        refresh_mcp_btn = QPushButton("刷新")
        mcp_btn_layout.addWidget(refresh_mcp_btn)

        mcp_layout.addLayout(mcp_btn_layout)
        layout.addWidget(mcp_group)

        # Skills group
        skills_group = QGroupBox("技能列表")
        skills_layout = QVBoxLayout(skills_group)

        self.skill_list = QListWidget()
        self.skill_list.addItem("code-review (已启用)")
        self.skill_list.addItem("translator (已启用)")
        skills_layout.addWidget(self.skill_list)

        skill_btn_layout = QHBoxLayout()
        load_skill_btn = QPushButton("加载")
        load_skill_btn.clicked.connect(self._on_load_skill)
        skill_btn_layout.addWidget(load_skill_btn)

        new_skill_btn = QPushButton("新建")
        skill_btn_layout.addWidget(new_skill_btn)

        skills_layout.addLayout(skill_btn_layout)
        layout.addWidget(skills_group)

        # Work directory group
        work_group = QGroupBox("工作目录")
        work_layout = QVBoxLayout(work_group)

        self.work_dir_label = QLabel(str(self.work_dir))
        self.work_dir_label.setWordWrap(True)
        work_layout.addWidget(self.work_dir_label)

        change_dir_btn = QPushButton("更改...")
        change_dir_btn.clicked.connect(self._on_change_work_dir)
        work_layout.addWidget(change_dir_btn)

        layout.addWidget(work_group)

        # Stretch
        layout.addStretch()

    def _on_add_mcp(self):
        """Add MCP server dialog."""
        from harness_client.ui.mcp_panel import MCPServerDialog
        dialog = MCPServerDialog(self)
        dialog.exec()

    def _on_load_skill(self):
        """Load skills from directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "选择技能目录")
        if dir_path:
            # TODO: Load skills using SDK
            self.skill_list.addItem(f"从 {Path(dir_path).name} 加载")

    def _on_change_work_dir(self):
        """Change work directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择工作目录", str(self.work_dir)
        )
        if dir_path:
            self.work_dir = Path(dir_path)
            self.work_dir_label.setText(str(self.work_dir))
            self.work_dir_changed.emit(self.work_dir)

    def add_mcp_server(self, name: str, status: str = "未连接"):
        """Add MCP server to list."""
        self.mcp_list.addItem(f"{name} ({status})")

    def add_skill(self, name: str, status: str = "已启用"):
        """Add skill to list."""
        self.skill_list.addItem(f"{name} ({status})")
