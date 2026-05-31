"""
Main window for Harness Client.
"""

import asyncio
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QSplitter, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from qasync import asyncSlot

from harness_client.ui.chat_panel import ChatPanel
from harness_client.ui.sidebar import SidebarPanel
from harness_client.controllers.chat_controller import ChatController
from harness_client.controllers.mcp_controller import MCPController
from harness_client.controllers.skill_controller import SkillController
from harness_client.utils.settings import SettingsManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

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
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()

        # State
        self.work_dir = Path.cwd()
        self._is_processing = False
        self.settings_manager = SettingsManager()

        # Connect signals
        self.chat_panel.message_sent.connect(self._on_message_sent)

        # Load saved settings
        self._load_saved_settings()

        # Initialize with a new session
        self.chat_controller.new_session()
        self._refresh_session_list()

    def _setup_menubar(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        from PyQt6.QtGui import QAction

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

        settings_menu = menubar.addMenu("设置(&S)")

        preferences_action = QAction("首选项(&P)...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self._on_preferences)
        settings_menu.addAction(preferences_action)

        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup toolbar."""
        from PyQt6.QtGui import QAction
        from PyQt6.QtCore import QSize

        toolbar = self.addToolBar("Main")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)

        new_session_action = QAction("新建会话", self)
        new_session_action.triggered.connect(self._on_new_session)
        toolbar.addAction(new_session_action)

        toolbar.addSeparator()

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._on_preferences)
        toolbar.addAction(settings_action)

    def _setup_central_widget(self):
        """Setup central widget with splitter layout."""
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = SidebarPanel()
        self.sidebar.setMaximumWidth(280)
        self.sidebar.work_dir_changed.connect(self._on_work_dir_changed)
        self.sidebar.session_delete_requested.connect(self._on_session_delete)
        self.sidebar.session_switch_requested.connect(self._on_session_switch)
        self.sidebar.session_new_requested.connect(self._on_new_session)

        self.chat_panel = ChatPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.chat_panel)
        splitter.setSizes([250, 950])

        layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
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

            self.statusbar.showMessage(f"已切换到会话", 3000)

    def _on_session_delete(self, session_id: str):
        """Delete a session."""
        self.chat_controller.delete_session(session_id)
        self._refresh_session_list()
        self.statusbar.showMessage("会话已删除", 3000)

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

        self.statusbar.showMessage(
            f"完成 | Token: {self.chat_controller.get_token_usage()}"
        )
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
        chunk = self._stream_buffer[self._stream_pos:end]
        self._stream_pos = end

        self.chat_panel.append_streaming_chunk(chunk)

    def _on_error(self, error: str):
        """Handle error from async operation."""
        logger.error(f"Error received: {error}")
        self.chat_panel.append_assistant_message(f"❌ 错误: {error}")
        self.statusbar.showMessage(f"错误: {error}")
        self._is_processing = False

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
            max_iterations=settings.get("max_iterations", 20),
        )
        self.chat_controller.configure(chat_config)

        if settings.get("work_dir"):
            self.work_dir = Path(settings["work_dir"])

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
            max_iterations=settings.max_iterations,
        )
        self.chat_controller.configure(chat_config)

        if settings.work_dir:
            self.work_dir = Path(settings.work_dir)

    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "关于 Harness Client",
            "Harness Client v0.1.0\n\n"
            "Windows 桌面客户端\n"
            "基于 Harness AI Agent SDK\n\n"
            "© 2024 Harness Team"
        )

    def _on_work_dir_changed(self, path: Path):
        """Handle work directory change."""
        self.work_dir = path
        self.chat_controller.work_dir = path
        self.statusbar.showMessage(f"工作目录已更改: {path}", 3000)

    def _on_mcp_changed(self):
        """Handle MCP server list change."""
        self.sidebar.mcp_list.clear()
        for server in self.mcp_controller.get_server_list():
            status_icon = "✓" if server.status == "已连接" else "○"
            self.sidebar.mcp_list.addItem(f"{status_icon} {server.name} ({server.status})")

    def _on_skills_changed(self):
        """Handle skill list change."""
        self.sidebar.skill_list.clear()
        for skill in self.skill_controller.get_skill_list():
            status = "已启用" if skill.enabled else "已禁用"
            self.sidebar.skill_list.addItem(f"{skill.name} ({status})")

    def closeEvent(self, event):
        """Handle window close."""
        event.accept()
