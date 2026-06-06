"""
Main window for Harness Client - 3-column layout with header bar.
"""

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from harness_client.controllers.chat_controller import ChatController
from harness_client.controllers.mcp_controller import MCPController
from harness_client.controllers.skill_controller import SkillController
from harness_client.ui.chat_panel import ChatPanel
from harness_client.ui.right_panel import RightPanel
from harness_client.ui.sidebar import SidebarPanel
from harness_client.utils.settings import SettingsManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with 3-column layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harness Client")
        self.setMinimumSize(1200, 800)

        # Initialize controllers
        self.chat_controller = ChatController()
        self.mcp_controller = MCPController()
        self.skill_controller = SkillController()

        # Connect controller callbacks
        self.mcp_controller.set_change_callback(self._on_mcp_changed)
        self.skill_controller.set_change_callback(self._on_skills_changed)
        self.chat_controller.set_tool_call_callback(self._on_tool_call)
        self.chat_controller.set_tool_result_callback(self._on_tool_result)
        self.chat_controller.set_thinking_callback(self._on_thinking)

        # Settings
        self._stream_enabled = True

        # Initialize UI
        self._setup_menubar()
        self._setup_header_bar()
        self._setup_central_widget()
        self._setup_statusbar()

        # State
        self.work_dir = Path.cwd()
        self._is_processing = False
        self.settings_manager = SettingsManager()

        # Update chat controller work dir
        self.chat_controller.work_dir = self.work_dir

        # Connect signals
        self.chat_panel.message_sent.connect(self._on_message_sent)
        self.sidebar.session_new_requested.connect(self._on_new_session)
        self.sidebar.session_switch_requested.connect(self._on_session_switch)
        self.sidebar.session_delete_requested.connect(self._on_session_delete)
        self.sidebar.settings_requested.connect(self._on_preferences)
        self.right_panel.work_dir_changed.connect(self._on_work_dir_changed)
        self.right_panel.add_mcp_server_requested.connect(self._on_add_mcp_server)
        self.right_panel.toggle_mcp_server_requested.connect(self._on_toggle_mcp_server)
        self.right_panel.server_double_clicked.connect(self._on_toggle_mcp_server)
        self.right_panel.add_skill_requested.connect(self._on_add_skill)
        self.right_panel.skill_double_clicked.connect(self._on_edit_skill)

        # Load saved settings
        self._load_saved_settings()

        # Load MCP configuration
        self._load_mcp_config()

        # Load skills from default directories
        self.skill_controller.load_defaults()

        # Initialize with a new session
        self.chat_controller.new_session()
        self._refresh_session_list()

    def _get_font(self) -> QFont:
        """Get a suitable font for the system."""
        font = QFont()
        font.setPointSize(10)
        for family in ["Microsoft YaHei", "Segoe UI", "SimHei", "Arial"]:
            font.setFamily(family)
            if QFontDatabase.families().count(family) > 0 or family in QFontDatabase.families():
                break
        return font

    def _setup_menubar(self):
        """Setup minimal menu bar."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d30;
                border-bottom: 1px solid #3e3e42;
                color: #d4d4d4;
                padding: 2px;
            }
        """)

        file_menu = menubar.addMenu("文件(&F)")

        new_session_action = QAction("新建会话(&N)", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self._on_new_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_header_bar(self):
        """Setup slim header bar with logo and quick actions (~36px)."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 2, 8, 2)

        header_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3e3e42;
            }
        """)
        header_widget.setMaximumHeight(36)

        # Logo icon
        logo_label = QLabel("A")
        logo_label.setStyleSheet("""
            QLabel {
                background-color: #007acc;
                color: white;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
            }
        """)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)

        # App name (single line, no subtitle)
        app_name = QLabel("Harness Client")
        app_name.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-size: 12px;
                font-weight: bold;
                margin-left: 8px;
            }
        """)
        header_layout.addWidget(app_name)

        header_layout.addStretch()

        # Clear context button
        clear_btn = QPushButton("清空上下文")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px 10px;
                color: #d4d4d4;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                border-color: #505050;
            }
        """)
        clear_btn.clicked.connect(self._on_clear_context)
        header_layout.addWidget(clear_btn)

        self.header_widget = header_widget

    def _setup_central_widget(self):
        """Setup central widget with 3-column splitter layout."""
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add header bar at top
        layout.addWidget(self.header_widget)

        # Create 3-column splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter {
                background-color: #1e1e1e;
            }
            QSplitter::handle {
                background-color: #3e3e42;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #007acc;
            }
        """)

        # Left sidebar (collapsible navigation)
        self.sidebar = SidebarPanel()
        splitter.addWidget(self.sidebar)

        # Center chat panel
        self.chat_panel = ChatPanel()
        splitter.addWidget(self.chat_panel)

        # Right panel (skills, MCP, files)
        self.right_panel = RightPanel()
        splitter.addWidget(self.right_panel)

        # Set initial sizes: sidebar (160), chat (640), right (200)
        splitter.setSizes([160, 640, 200])

        # Set stretch factors: sidebar doesn't stretch, chat gets most space, right gets some
        splitter.setStretchFactor(0, 0)  # Sidebar fixed width
        splitter.setStretchFactor(1, 1)  # Chat stretches
        splitter.setStretchFactor(2, 0)  # Right panel fixed width

        layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #007acc;
                color: #ffffff;
            }
        """)
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    # === Session Management ===

    def _refresh_session_list(self):
        """Refresh the session list in sidebar."""
        current = self.chat_controller.get_current_session()
        history = self.chat_controller.session_manager.get_history_list()
        self.sidebar.update_sessions(current, history)

    def _on_new_session(self):
        """Create a new session."""
        self.chat_controller.new_session()
        self.chat_panel.clear_chat()
        self._refresh_session_list()
        self.statusbar.showMessage("新会话已创建", 3000)

    def _on_session_switch(self, session_id: str):
        """Switch to a different session."""
        if self.chat_controller.switch_session(session_id):
            # Update sidebar
            self._refresh_session_list()

            # Load session messages into chat panel
            self.chat_panel.clear_chat()
            session = self.chat_controller.session_manager.get(session_id)
            if session:
                for msg in session.messages:
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            block.get("text", "")
                            for block in content
                            if isinstance(block, dict) and "text" in block
                        )
                    if msg.get("role") == "user":
                        self.chat_panel.append_user_message(content)
                    elif msg.get("role") == "assistant":
                        self.chat_panel.append_assistant_message(content)

            self.statusbar.showMessage("已切换到会话", 3000)

    def _on_session_delete(self, session_id: str):
        """Delete a session."""
        self.chat_controller.delete_session(session_id)
        self._refresh_session_list()
        self.statusbar.showMessage("会话已删除", 3000)

    def _on_clear_context(self):
        """Clear the current chat context."""
        reply = QMessageBox.question(
            self,
            "清空上下文",
            "确定要清空当前对话上下文吗？\n\n此操作会清除当前会话的所有消息。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_panel.clear_chat()
            self.chat_controller.new_session()
            self._refresh_session_list()
            self.statusbar.showMessage("上下文已清空", 3000)

    # === Message Handling ===

    @asyncSlot(str)
    async def _on_message_sent(self, message: str):
        """Handle message sent from chat panel."""
        logger.info(f"Message sent: {message[:50]}...")

        if self.chat_controller.is_busy():
            self.statusbar.showMessage("正在处理中，请稍候...", 2000)
            return

        self.statusbar.showMessage("正在思考...")

        config = self.chat_controller.config
        logger.info(f"Current config: provider={config.provider}, model={config.model}")

        try:
            response = ""
            async for chunk in self.chat_controller.send_message(message):
                response = chunk
            self._on_response_received(response)
        except Exception as e:
            logger.exception(f"Error in _on_message_sent: {e}")
            self._on_error(f"{type(e).__name__}: {str(e)}")

    def _on_response_received(self, response: str):
        """Handle response from agent."""
        logger.info(f"Response received: {response[:50] if response else 'EMPTY'}...")

        if response:
            settings = self.settings_manager.get()
            if settings.stream and len(response) > 50:
                self._simulate_streaming(response)
            else:
                self.chat_panel.append_assistant_message(response)
        else:
            self.chat_panel.append_assistant_message("(无响应)")

        # Refresh session list (name may have changed)
        self._refresh_session_list()

        # Update token usage display
        self._update_token_display()
        self.statusbar.showMessage(f"完成 | Token: {self.chat_controller.get_token_usage()}")
        self._is_processing = False

    def _simulate_streaming(self, text: str):
        """Simulate streaming output for better UX."""
        from PyQt6.QtCore import QTimer

        self.chat_panel.start_streaming()
        self._stream_buffer = text
        self._stream_pos = 0
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self._stream_next_chunk)

        chunk_size = max(1, len(text) // 100)
        interval = max(10, 1500 // 100)

        self._stream_chunk_size = chunk_size
        self._stream_timer.start(interval)

    def _stream_next_chunk(self):
        """Stream the next chunk of text."""
        if self._stream_pos >= len(self._stream_buffer):
            self._stream_timer.stop()
            self.chat_panel.finish_streaming()
            return

        end = min(self._stream_pos + self._stream_chunk_size, len(self._stream_buffer))
        chunk = self._stream_buffer[self._stream_pos : end]
        self._stream_pos = end

        self.chat_panel.append_streaming_chunk(chunk)

    def _on_error(self, error: str):
        """Handle error from async operation."""
        logger.error(f"Error received: {error}")
        self.chat_panel.append_assistant_message(f"❌ 错误: {error}")
        self.statusbar.showMessage(f"错误: {error}")
        self._is_processing = False

    def _update_token_display(self):
        """Update token usage display in chat panel."""
        usage = self.chat_controller.get_token_usage()
        self.chat_panel.set_token_usage(usage)

    # === Progress Callbacks ===

    def _on_tool_call(self, tool_name: str, arguments: dict):
        """Handle tool call event."""
        self.chat_panel.append_tool_call(tool_name, arguments)

    def _on_tool_result(self, tool_name: str, result: str, success: bool = True):
        """Handle tool result event."""
        self.chat_panel.append_tool_result(tool_name, result, success)

    def _on_thinking(self, message: str):
        """Handle thinking/progress event."""
        self.chat_panel.append_thinking(message)

    # === Settings ===

    def _on_preferences(self):
        """Open preferences dialog."""
        from harness_client.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)

        current = self.settings_manager.get()
        dialog.provider_combo.setCurrentText(current.provider)
        dialog.api_key_edit.setText(current.api_key)
        dialog.base_url_edit.setText(current.base_url)
        dialog.model_combo.setCurrentText(current.model)
        dialog.context_window_combo.setCurrentText(current.context_window)
        dialog.tool_role_combo.setCurrentText(current.tool_result_role)
        dialog.auto_save_check.setChecked(current.auto_save)
        dialog.stream_check.setChecked(current.stream)
        dialog.max_iterations_spin.setValue(current.max_iterations)
        if current.work_dir:
            dialog.work_dir_edit.setText(current.work_dir)
        dialog.remember_dir_check.setChecked(current.remember_dir)

        if dialog.exec():
            settings = dialog.get_settings()
            self._apply_settings(settings)
            self.statusbar.showMessage("设置已保存", 3000)

    def _apply_settings(self, settings: dict):
        """Apply settings to controllers and save to disk."""
        from harness_client.controllers.chat_controller import ChatConfig
        from harness_client.utils.settings import AppSettings

        app_settings = AppSettings(
            provider=settings.get("provider", "anthropic"),
            api_key=settings.get("api_key", ""),
            base_url=settings.get("base_url", ""),
            model=settings.get("model", "claude-sonnet-4-6"),
            context_window=settings.get("context_window", "auto"),
            tool_result_role=settings.get("tool_result_role", "tool"),
            auto_save=settings.get("auto_save", True),
            stream=settings.get("stream", True),
            max_iterations=settings.get("max_iterations", 20),
            work_dir=settings.get("work_dir", ""),
            remember_dir=settings.get("remember_dir", True),
        )
        self.settings_manager.save(app_settings)

        self._stream_enabled = settings.get("stream", True)

        chat_config = ChatConfig(
            provider=settings.get("provider", "anthropic"),
            api_key=settings.get("api_key", ""),
            base_url=settings.get("base_url", ""),
            model=settings.get("model", "claude-sonnet-4-6"),
            context_window=settings.get("context_window", "auto"),
            max_iterations=settings.get("max_iterations", 20),
            tool_result_role=settings.get("tool_result_role", "tool"),
        )
        self.chat_controller.configure(chat_config)

        if settings.get("work_dir"):
            self.work_dir = Path(settings["work_dir"])
            self.right_panel.set_work_dir(self.work_dir)

    def _load_saved_settings(self):
        """Load and apply saved settings on startup."""
        from harness_client.controllers.chat_controller import ChatConfig

        settings = self.settings_manager.get()
        self._stream_enabled = settings.stream

        chat_config = ChatConfig(
            provider=settings.provider,
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            context_window=settings.context_window,
            max_iterations=settings.max_iterations,
            temperature=settings.temperature,
            tool_result_role=settings.tool_result_role,
        )
        self.chat_controller.configure(chat_config)

        if settings.work_dir:
            self.work_dir = Path(settings.work_dir)
            self.right_panel.set_work_dir(self.work_dir)

    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "关于 Harness Client",
            "Harness Client v0.1.0\n\n"
            "Windows 桌面客户端\n"
            "基于 Harness AI Agent SDK\n\n"
            "© 2026 Harness Team",
        )

    def _on_work_dir_changed(self, path: Path):
        """Handle work directory change from right panel."""
        self.work_dir = path
        self.chat_controller.work_dir = path
        self.statusbar.showMessage(f"工作目录已更改: {path}", 3000)

    def _on_mcp_changed(self):
        """Handle MCP server list change."""
        servers = []
        for server in self.mcp_controller.get_server_list():
            servers.append({
                "name": server.name,
                "status": server.status,
                "tools_count": getattr(server, "tools_count", 0),
            })
        self.right_panel.update_servers(servers)

        # Sync MCP tools to chat controller
        mcp_tools = self.mcp_controller.get_all_tools()
        self.chat_controller.set_mcp_tools(mcp_tools)

    def _on_add_mcp_server(self):
        """Open dialog to add a new MCP server."""
        from harness_client.ui.mcp_panel import MCPServerDialog

        dialog = MCPServerDialog(self)
        if dialog.exec():
            config = dialog.get_config()
            if not config.get("name"):
                QMessageBox.warning(self, "错误", "请输入服务器名称")
                return

            # Add to controller
            from harness import MCPServerConfig
            server_config = MCPServerConfig(
                name=config["name"],
                transport=config["transport"],
                command=config.get("command"),
                args=config.get("args", []),
                url=config.get("url"),
                env=config.get("env", {}),
                headers=config.get("headers", {}),
                enabled=config.get("enabled", True),
                timeout=config.get("timeout", 30),
            )
            self.mcp_controller.add_server_config(server_config)

            # Save configuration
            self._save_mcp_config()

            # Auto-connect if enabled - use asyncSlot for proper async handling
            if config.get("enabled", True):
                # Schedule the connection after dialog closes
                import asyncio
                asyncio.ensure_future(self._connect_mcp_server(config["name"]))

    @asyncSlot(str)
    async def _on_toggle_mcp_server(self, name: str):
        """Handle connect/disconnect toggle for MCP server."""
        server_info = self.mcp_controller.servers.get(name)
        if not server_info:
            return

        if server_info.status == "已连接":
            await self._disconnect_mcp_server(name)
        else:
            await self._connect_mcp_server_async(name)

    async def _connect_mcp_server(self, name: str) -> bool:
        """Connect to an MCP server."""
        self.statusbar.showMessage(f"正在连接 {name}...")
        success = await self.mcp_controller.connect_server(name)
        if success:
            self.statusbar.showMessage(f"{name} 已连接", 3000)
            # Reset agent to pick up new tools
            self.chat_controller.agent = None
        else:
            server_info = self.mcp_controller.servers.get(name)
            error_msg = server_info.error_message if server_info else "未知错误"
            self.statusbar.showMessage(f"连接失败: {error_msg}", 5000)
        return success

    async def _connect_mcp_server_async(self, name: str):
        """Async wrapper for connecting MCP server."""
        await self._connect_mcp_server(name)

    async def _disconnect_mcp_server(self, name: str):
        """Disconnect from an MCP server."""
        self.statusbar.showMessage(f"正在断开 {name}...")
        success = await self.mcp_controller.disconnect_server(name)
        if success:
            self.statusbar.showMessage(f"{name} 已断开", 3000)
            # Reset agent to update tools
            self.chat_controller.agent = None
        else:
            self.statusbar.showMessage("断开失败", 3000)

    def _save_mcp_config(self):
        """Save MCP server configuration to file."""
        import json

        from harness_client.utils.settings import get_config_dir

        config_dir = get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "mcp.json"

        config = {"mcpServers": {}}
        for server_config in self.mcp_controller.manager.list_server_configs():
            config["mcpServers"][server_config.name] = server_config.to_dict()

        config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_mcp_config(self):
        """Load MCP server configuration from file."""
        import logging
        logger = logging.getLogger(__name__)

        from harness_client.utils.settings import get_config_dir

        config_dir = get_config_dir()
        config_file = config_dir / "mcp.json"

        logger.info(f"Loading MCP config from: {config_file}")
        logger.info(f"Config file exists: {config_file.exists()}")

        if config_file.exists():
            self.mcp_controller.load_from_file(config_file)
            logger.info(f"Loaded {len(self.mcp_controller.servers)} MCP servers")

            # Auto-connect enabled servers after UI is ready
            # Use QTimer to ensure event loop is running
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._auto_connect_mcp_servers)

    def _auto_connect_mcp_servers(self):
        """Auto-connect to enabled MCP servers."""
        import asyncio
        import logging
        logger = logging.getLogger(__name__)

        for name, info in self.mcp_controller.servers.items():
            config = self.mcp_controller.manager.get_server_config(name)
            if config and config.enabled:
                logger.info(f"Auto-connecting to MCP server: {name}")
                asyncio.ensure_future(self._connect_mcp_server(name))

    def _on_skills_changed(self):
        """Handle skill list change."""
        skills = []
        for skill in self.skill_controller.get_skill_list():
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "enabled": skill.enabled,
            })
        self.right_panel.update_skills(skills)
        # Update chat panel skill completer
        self.chat_panel.set_skills(skills)

    def _on_add_skill(self):
        """Handle add skill button click."""
        from harness_client.ui.skill_dialog import SkillEditDialog
        from pathlib import Path

        dialog = SkillEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save to default skill directory
            skill_dir = Path(".agent/skills")
            skill_dir.mkdir(parents=True, exist_ok=True)

            data = dialog.get_skill_data()
            if data["name"]:
                skill_path = skill_dir / f"{data['name']}.md"
                if dialog.save_to_file(skill_path):
                    self.skill_controller.load_from_file(skill_path)

    def _on_edit_skill(self, skill_name: str):
        """Handle double-click on skill item to edit."""
        from harness_client.ui.skill_dialog import SkillEditDialog

        skill_info = self.skill_controller.get_skill(skill_name)
        if skill_info and skill_info.source_path:
            skill_path = Path(skill_info.source_path)
            dialog = SkillEditDialog(self, skill_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.save_to_file(skill_path):
                    self.skill_controller.load_from_file(skill_path)

    def closeEvent(self, event):
        """Handle window close."""
        event.accept()
