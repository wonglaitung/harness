"""
Main window for Harness Client - 3-column layout with header bar.
"""

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QFontDatabase, QIcon
from PyQt6.QtSvg import QSvgRenderer
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
from harness_client.controllers.memory_controller import MemoryController
from harness_client.controllers.skill_controller import SkillController
from harness_client.ui.chat_panel import ChatPanel
from harness_client.ui.right_panel import RightPanel
from harness_client.ui.sidebar import SidebarPanel
from harness_client.utils.settings import SettingsManager
from harness_client.themes import register_theme_listener, unregister_theme_listener, get_theme

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

        # Set window icon from SVG
        self._set_window_icon()

        # Initialize controllers
        self.chat_controller = ChatController()
        self.mcp_controller = MCPController()
        self.skill_controller = SkillController()
        self.memory_controller = MemoryController()

        # Connect controller callbacks
        self.mcp_controller.set_change_callback(self._on_mcp_changed)
        self.skill_controller.set_change_callback(self._on_skills_changed)
        self.memory_controller.memory_changed.connect(self._on_memory_changed)
        self.chat_controller.set_tool_call_callback(self._on_tool_call)
        self.chat_controller.set_tool_result_callback(self._on_tool_result)
        self.chat_controller.set_thinking_callback(self._on_thinking)
        self.chat_controller.set_confirm_callback(self._confirm_dangerous_operation)

        # Settings
        self._stream_enabled = True

        # Initialize UI
        self._setup_menubar()
        self._setup_central_widget()
        self._setup_statusbar()

        # State
        self.work_dir = Path.cwd()
        self._is_processing = False
        self.settings_manager = SettingsManager()

        # Update chat controller work dir
        self.chat_controller.work_dir = self.work_dir

        # Update chat panel work dir for file completer
        self.chat_panel.set_work_dir(self.work_dir)

        # Update right panel file tree work dir
        self.right_panel.set_work_dir(self.work_dir)

        # Connect signals
        self.chat_panel.message_sent.connect(self._on_message_sent)
        self.chat_panel.stop_requested.connect(self._on_stop_requested)
        self.chat_panel.clear_chat_requested.connect(self._on_clear_context)
        self.sidebar.session_new_requested.connect(self._on_new_session)
        self.sidebar.session_switch_requested.connect(self._on_session_switch)
        self.sidebar.session_delete_requested.connect(self._on_session_delete)
        self.sidebar.settings_requested.connect(self._on_preferences)
        self.right_panel.work_dir_changed.connect(self._on_work_dir_changed)
        self.right_panel.add_mcp_server_requested.connect(self._on_add_mcp_server)
        self.right_panel.toggle_mcp_server_requested.connect(self._on_toggle_mcp_server)
        self.right_panel.server_double_clicked.connect(self._on_edit_mcp_server)
        self.right_panel.add_skill_requested.connect(self._on_add_skill)
        self.right_panel.skill_double_clicked.connect(self._on_edit_skill)
        self.right_panel.memory_add_requested.connect(self._on_memory_add)
        self.right_panel.memory_edit_requested.connect(self._on_memory_edit)
        self.right_panel.memory_remove_requested.connect(self._on_memory_remove)
        self.right_panel.memory_importance_changed.connect(self._on_memory_importance_changed)

        # Load saved settings
        self._load_saved_settings()

        # Load MCP configuration
        self._load_mcp_config()

        # Load skills from default directories
        self.skill_controller.load_defaults()

        # Load memory display
        self._refresh_memory()

        # Initialize with a new session
        self.chat_controller.new_session()
        self._refresh_session_list()

        # Register theme listener for dynamic theme updates
        self._theme_callback = self._on_theme_changed
        register_theme_listener(self._theme_callback)

    def _set_window_icon(self):
        """Set window icon from SVG file."""
        import sys
        from PyQt6.QtGui import QPixmap, QPainter

        # In PyInstaller bundle, resources are in sys._MEIPASS
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            icon_path = base_path / "resources" / "icons" / "icon.svg"
        else:
            # In development, use relative path from this file
            icon_path = Path(__file__).parent.parent.parent.parent / "resources" / "icons" / "icon.svg"

        if icon_path.exists():
            renderer = QSvgRenderer(str(icon_path))
            if renderer.isValid():
                # Create pixmap at multiple sizes for better quality
                pixmap = QPixmap(64, 64)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                self.setWindowIcon(QIcon(pixmap))

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
        from harness_client.themes import get_theme
        theme = get_theme()

        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {theme.CHROME};
                border-bottom: 1px solid {theme.BORDER};
                color: {theme.TEXT};
                padding: 2px;
            }}
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

    def _setup_central_widget(self):
        """Setup central widget with 3-column splitter layout."""
        theme = get_theme()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create 3-column splitter
        self._central_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._central_splitter.setStyleSheet(f"""
            QSplitter {{
                background-color: {theme.APP_BACKGROUND};
            }}
            QSplitter::handle {{
                background-color: {theme.BORDER};
                width: 1px;
            }}
            QSplitter::handle:hover {{
                background-color: {theme.ACCENT};
            }}
        """)

        # Left sidebar (collapsible navigation)
        self.sidebar = SidebarPanel()
        self._central_splitter.addWidget(self.sidebar)

        # Center chat panel
        self.chat_panel = ChatPanel()
        self._central_splitter.addWidget(self.chat_panel)

        # Right panel (skills, MCP, files)
        self.right_panel = RightPanel()
        self._central_splitter.addWidget(self.right_panel)

        # Set initial sizes: sidebar (160), chat (640), right (200)
        self._central_splitter.setSizes([160, 640, 200])

        # Set stretch factors: sidebar doesn't stretch, chat gets most space, right gets some
        self._central_splitter.setStretchFactor(0, 0)  # Sidebar fixed width
        self._central_splitter.setStretchFactor(1, 1)  # Chat stretches
        self._central_splitter.setStretchFactor(2, 0)  # Right panel fixed width

        layout.addWidget(self._central_splitter)
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        """Setup status bar."""
        from harness_client.themes import get_theme
        theme = get_theme()

        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {theme.ACCENT};
                color: white;
            }}
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
            self.chat_controller.clear_context()
            self.statusbar.showMessage("上下文已清空", 3000)

    # === Message Handling ===

    @asyncSlot(str)
    async def _on_message_sent(self, message: str):
        """Handle message sent from chat panel."""
        logger.info(f"Message sent: {message[:50]}...")

        if self.chat_controller.is_busy():
            self.statusbar.showMessage("正在处理中，请稍候...", 2000)
            return

        self._is_processing = True
        self.chat_panel.set_streaming_state(True)
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
        finally:
            self.chat_panel.set_streaming_state(False)
            self._is_processing = False

    def _on_stop_requested(self):
        """Handle stop button click."""
        if self.chat_controller.stop():
            self.statusbar.showMessage("正在停止...", 2000)
            self.chat_panel.set_streaming_state(False)
            self._is_processing = False
        else:
            self.statusbar.showMessage("没有正在进行的任务", 2000)

    def _on_response_received(self, response: str):
        """Handle response from agent."""
        logger.info(f"Response received: {response[:50] if response else 'EMPTY'}...")

        # Always display full message directly (streaming causes HTML structure issues)
        if response:
            self.chat_panel.append_assistant_message(response)
        else:
            self.chat_panel.append_assistant_message("(无响应)")

        # Refresh session list (name may have changed)
        self._refresh_session_list()

        # Update token usage display
        self._update_token_display()
        self.statusbar.showMessage(f"完成 | Token: {self.chat_controller.get_token_usage()}")
        self.chat_panel.set_streaming_state(False)
        self._is_processing = False

    def _on_error(self, error: str):
        """Handle error from async operation."""
        logger.error(f"Error received: {error}")
        self.chat_panel.append_assistant_message(f"❌ 错误: {error}")
        self.statusbar.showMessage(f"错误: {error}")
        self.chat_panel.set_streaming_state(False)
        self._is_processing = False

    def _update_token_display(self):
        """Update token usage display in chat panel."""
        usage = self.chat_controller.get_token_usage()
        self.chat_panel.set_token_usage(usage)

    # === Progress Callbacks ===

    def _on_tool_call(self, tool_name: str, arguments: dict):
        """Handle tool call event."""
        self.chat_panel.append_tool_call(tool_name, arguments)

    def _on_tool_result(self, tool_name: str, result: str, success: bool = True, metadata: dict = None):
        """Handle tool result event.

        Args:
            tool_name: Name of the tool
            result: Tool result string
            success: Whether the tool call succeeded
            metadata: Optional metadata from tool (e.g., {"refresh_memory": True})
        """
        self.chat_panel.append_tool_result(tool_name, result, success)

        # Check if memory refresh is needed
        if metadata and metadata.get("refresh_memory"):
            self._refresh_memory()

    def _on_thinking(self, message: str):
        """Handle thinking/progress event."""
        self.chat_panel.append_thinking(message)

    def _confirm_dangerous_operation(self, tool_name: str, args: dict) -> "ConfirmationResult":
        """Show confirmation dialog for dangerous operations.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments

        Returns:
            ConfirmationResult with confirmed and trust_session fields
        """
        from harness import ConfirmationResult

        # Format arguments preview
        args_lines = []
        for k, v in list(args.items())[:5]:
            val_str = repr(v)[:100]
            args_lines.append(f"  {k}: {val_str}")
        args_preview = "\n".join(args_lines) if args_lines else "  (无参数)"

        # Build message
        msg_text = f"""AI 请求执行可能危险的操作：

工具: {tool_name}
参数:
{args_preview}

是否允许执行？"""

        # Show confirmation dialog with three buttons
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("确认执行")
        msg.setText(msg_text)

        # Add three custom buttons
        btn_once = msg.addButton("允许一次", QMessageBox.ButtonRole.AcceptRole)
        btn_session = msg.addButton("允许本次会话", QMessageBox.ButtonRole.AcceptRole)
        btn_reject = msg.addButton("拒绝", QMessageBox.ButtonRole.RejectRole)

        msg.setDefaultButton(btn_once)
        msg.exec()

        clicked = msg.clickedButton()

        if clicked == btn_once:
            logger.info(f"User confirmed operation (once): {tool_name}")
            return ConfirmationResult(confirmed=True, trust_session=False)
        elif clicked == btn_session:
            logger.info(f"User confirmed operation (session): {tool_name}")
            return ConfirmationResult(confirmed=True, trust_session=True)
        else:
            logger.info(f"User rejected operation: {tool_name}")
            return ConfirmationResult(confirmed=False, trust_session=False)

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
        dialog.auto_update_memory_check.setChecked(current.auto_update_memory)
        if current.work_dir:
            dialog.work_dir_edit.setText(current.work_dir)
        dialog.remember_dir_check.setChecked(current.remember_dir)
        dialog._set_theme_mode(current.theme_mode)

        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            self._apply_settings(settings)
            self.statusbar.showMessage("设置已保存", 3000)
        elif result == 2:  # Apply clicked
            settings = dialog.get_settings()
            self._apply_settings(settings)
            self.statusbar.showMessage("设置已应用", 3000)
            # Reopen dialog with updated settings
            self._on_preferences()

    def _apply_settings(self, settings: dict):
        """Apply settings to controllers and save to disk."""
        from harness_client.controllers.chat_controller import ChatConfig
        from harness_client.themes import set_theme_mode
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
            auto_update_memory=settings.get("auto_update_memory", True),
            work_dir=settings.get("work_dir", ""),
            remember_dir=settings.get("remember_dir", True),
            theme_mode=settings.get("theme_mode", "auto"),
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
            auto_update_memory=settings.get("auto_update_memory", True),
        )
        self.chat_controller.configure(chat_config)

        if settings.get("work_dir"):
            self.work_dir = Path(settings["work_dir"])
            self.right_panel.set_work_dir(self.work_dir)

        # Apply theme change if needed
        theme_mode = settings.get("theme_mode", "auto")
        from harness_client.themes import set_theme_mode

        set_theme_mode(theme_mode)

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
            auto_update_memory=settings.auto_update_memory,
        )
        self.chat_controller.configure(chat_config)

        if settings.work_dir:
            self.work_dir = Path(settings.work_dir)
            self.chat_controller.work_dir = self.work_dir
            self.chat_panel.set_work_dir(self.work_dir)
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
        self.chat_controller.agent = None  # Force re-initialization with new sandbox_workspace
        self.chat_panel.set_work_dir(path)
        self.statusbar.showMessage(f"工作目录已更改: {path}", 3000)

        # Save work_dir to settings if remember_dir is enabled
        settings = self.settings_manager.get()
        if settings.remember_dir:
            settings.work_dir = str(path)
            self.settings_manager.save(settings)

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

    def _refresh_mcp_list(self):
        """Refresh the MCP server list in right panel."""
        servers = []
        for info in self.mcp_controller.get_server_list():
            servers.append({
                "name": info.name,
                "status": info.status,
                "tools_count": info.tools_count,
            })
        self.right_panel.update_servers(servers)

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
        from harness_client.utils.settings import get_config_dir
        from pathlib import Path

        dialog = SkillEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save to global skill directory (~/.harness/skills/)
            skill_dir = get_config_dir() / "skills"
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

    def _on_edit_mcp_server(self, server_name: str):
        """Handle double-click on MCP server item to edit."""
        from harness_client.ui.mcp_panel import MCPServerDialog

        server_info = self.mcp_controller.servers.get(server_name)
        if not server_info:
            return

        # Get current config from manager
        server_config = self.mcp_controller.manager.get_server_config(server_name)
        if not server_config:
            return

        # Get tools if connected
        tools = self.mcp_controller.manager.get_server_tools(server_name)

        config_dict = {
            "name": server_config.name,
            "transport": server_config.transport,
            "command": server_config.command,
            "args": server_config.args,
            "url": server_config.url,
            "timeout": server_config.timeout,
            "enabled": server_config.enabled,
        }

        dialog = MCPServerDialog(self, config_dict, tools=tools)
        dialog.setWindowTitle("编辑 MCP 服务器")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            # Update configuration
            self.mcp_controller.update_server_config(server_name, new_config)
            self._save_mcp_config()
            self._refresh_mcp_list()

    # === Memory Management ===

    def _refresh_memory(self):
        """Refresh the memory display in right panel."""
        from harness.memory.memory_file import MemoryCategory

        sections = self.memory_controller.get_sections()
        self.right_panel.update_memory(sections)

        # Update with full MemoryEntry objects for importance display
        for category in MemoryCategory:
            entries = self.memory_controller.get_entries(category)
            self.right_panel.update_memory_entries(category, entries)

    def _on_memory_changed(self):
        """Handle memory change event."""
        self._refresh_memory()
        self.statusbar.showMessage("记忆已更新", 3000)

    def _on_memory_add(self, category_name: str):
        """Handle add memory entry request."""
        from harness.memory.memory_file import MemoryCategory
        from harness_client.ui.memory_panel import AddEntryDialog

        # Get display name
        category = MemoryCategory(category_name)
        display_name = self.memory_controller.get_category_display_name(category)

        dialog = AddEntryDialog(display_name, self)
        if dialog.exec() == QMessageBox.StandardButton.Ok:
            content = dialog.get_content()
            importance = dialog.get_importance()
            if content:
                self.memory_controller.add_entry(category, content, importance)

    def _on_memory_edit(self, category_name: str, index: int):
        """Handle edit memory entry request."""
        from harness.memory.memory_file import MemoryCategory
        from harness_client.ui.memory_panel import AddEntryDialog

        category = MemoryCategory(category_name)
        entries = self.memory_controller.get_entries(category)

        if 0 <= index < len(entries):
            entry = entries[index]
            display_name = self.memory_controller.get_category_display_name(category)
            dialog = AddEntryDialog(display_name, self)
            dialog._input.setText(entry.content)
            dialog._importance_slider.setValue(int(entry.importance * 100))

            if dialog.exec() == QMessageBox.StandardButton.Ok:
                content = dialog.get_content()
                importance = dialog.get_importance()
                if content:
                    self.memory_controller.update_entry(category, index, content, importance)

    def _on_memory_remove(self, category_name: str, index: int):
        """Handle remove memory entry request."""
        from harness.memory.memory_file import MemoryCategory

        category = MemoryCategory(category_name)
        entries = self.memory_controller.get_entries(category)

        if 0 <= index < len(entries):
            reply = QMessageBox.question(
                self,
                "删除记忆",
                f"确定要删除此记忆条目吗？\n\n{entries[index].content[:50]}...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.memory_controller.remove_entry(category, index)

    def _on_memory_importance_changed(self, category_name: str, index: int, importance: float):
        """Handle importance slider change."""
        from harness.memory.memory_file import MemoryCategory

        category = MemoryCategory(category_name)
        self.memory_controller.update_importance(category, index, importance)

    def closeEvent(self, event):
        """Handle window close - cleanup resources properly."""
        import asyncio

        # Unregister theme listener
        try:
            unregister_theme_listener(self._theme_callback)
        except Exception:
            pass

        # Stop any ongoing chat
        self.chat_controller.stop()

        # Disconnect all MCP servers synchronously (best effort)
        for name in list(self.mcp_controller.servers.keys()):
            try:
                # Try synchronous disconnect if available
                if hasattr(self.mcp_controller, 'disconnect_server_sync'):
                    self.mcp_controller.disconnect_server_sync(name)
            except Exception:
                pass  # Ignore errors during cleanup

        event.accept()

    def _on_theme_changed(self):
        """Handle theme change - reapply styles to all components."""
        theme = get_theme()

        # Update menubar style
        self.menuBar().setStyleSheet(f"""
            QMenuBar {{
                background-color: {theme.CHROME};
                border-bottom: 1px solid {theme.BORDER};
                color: {theme.TEXT};
                padding: 2px;
            }}
        """)

        # Update splitter style
        self._central_splitter.setStyleSheet(f"""
            QSplitter {{
                background-color: {theme.APP_BACKGROUND};
            }}
            QSplitter::handle {{
                background-color: {theme.BORDER};
                width: 1px;
            }}
            QSplitter::handle:hover {{
                background-color: {theme.ACCENT};
            }}
        """)

        # Update statusbar style
        self.statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {theme.ACCENT};
                color: white;
            }}
        """)

        # Notify child panels to update their styles
        if hasattr(self.sidebar, '_on_theme_changed'):
            self.sidebar._on_theme_changed()
        if hasattr(self.chat_panel, '_on_theme_changed'):
            self.chat_panel._on_theme_changed()
        if hasattr(self.right_panel, '_on_theme_changed'):
            self.right_panel._on_theme_changed()

        # Force repaint of all widgets
        self.update()
