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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMetaObject, Q_ARG

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


class AsyncWorker(QThread):
    """Worker thread for async operations with proper event loop handling."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self.coro = coro

    def run(self):
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the coroutine
            result = loop.run_until_complete(self.coro)

            # Clean up
            try:
                # Cancel all running tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Wait for all tasks to be cancelled
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()

            logger.info(f"AsyncWorker finished with result: {result[:50] if result else 'None'}...")
            self.finished.emit(result or "")
        except Exception as e:
            logger.exception(f"AsyncWorker error: {e}")
            self.error.emit(f"{type(e).__name__}: {str(e)}")


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

        # Connect chat controller callbacks for progress display
        self.chat_controller.set_tool_call_callback(self._on_tool_call)
        self.chat_controller.set_tool_result_callback(self._on_tool_result)
        self.chat_controller.set_thinking_callback(self._on_thinking)

        # Settings
        self._stream_enabled = True  # Will be loaded from settings

        # Initialize UI
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()

        # State
        self.work_dir = Path.cwd()
        self._current_worker = None
        self.settings_manager = SettingsManager()

        # Connect chat panel signals
        self.chat_panel.message_sent.connect(self._on_message_sent)

        # Load saved settings
        self._load_saved_settings()

    def _setup_menubar(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")

        from PyQt6.QtGui import QAction

        new_session_action = QAction("新建会话(&N)", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self._on_new_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("设置(&S)")

        preferences_action = QAction("首选项(&P)...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self._on_preferences)
        settings_menu.addAction(preferences_action)

        # Help menu
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

        # Left sidebar
        self.sidebar = SidebarPanel()
        self.sidebar.setMaximumWidth(280)
        self.sidebar.work_dir_changed.connect(self._on_work_dir_changed)
        self.sidebar.session_delete_requested.connect(self._on_session_delete)
        self.sidebar.session_switch_requested.connect(self._on_session_switch)
        self.sidebar.session_new_requested.connect(self._on_new_session)

        # Right chat panel
        self.chat_panel = ChatPanel()

        # Splitter
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

    def _on_new_session(self):
        """Create new session."""
        # Get current session ID before creating new one
        old_session_id = self.chat_controller.state.session_id

        # Create new session
        self.chat_controller.new_session()
        new_session_id = self.chat_controller.state.session_id

        # Add old session to sidebar history (if not the default empty session)
        if old_session_id and old_session_id != "default":
            self.sidebar.add_session(old_session_id, f"会话 {old_session_id[:8]}")

        # Clear chat panel
        self.chat_panel.clear_chat()

        # Update sidebar to show new session as current
        self.sidebar.update_current_session(f"会话 {new_session_id[:8]}", new_session_id)

        self.statusbar.showMessage("新会话已创建", 3000)

    def _on_session_switch(self, session_id: str):
        """Handle session switch request."""
        # Get current session ID
        current_session_id = self.chat_controller.state.session_id

        # Switch to the new session
        self.chat_controller.state.session_id = session_id
        self.chat_controller.agent = None  # Force re-initialization

        # Update sidebar (switch_to_session handles the swap)
        self.sidebar.switch_to_session(session_id, f"会话 {session_id[:8]}")

        # Clear chat panel and load session history
        self.chat_panel.clear_chat()
        messages = self.chat_controller.get_session_messages(session_id)
        for msg in messages:
            if msg.role == "user":
                self.chat_panel.append_user_message(msg.content)
            elif msg.role == "assistant":
                self.chat_panel.append_assistant_message(msg.content)

        self.statusbar.showMessage(f"已切换到会话 {session_id[:8]}", 3000)

    def _on_session_delete(self, session_id: str):
        """Handle session delete request."""
        # For now, just show a message since we don't have persistent sessions
        # In the future, this would delete the session from storage
        self.sidebar.remove_session(session_id)
        self.statusbar.showMessage(f"会话已删除", 3000)

    def _on_preferences(self):
        """Open preferences dialog."""
        from harness_client.ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)

        # Populate with current settings
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

        # Create and save settings
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

        # Update stream setting
        self._stream_enabled = settings.get("stream", True)

        # Apply to chat controller
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

        # Store stream setting
        self._stream_enabled = settings.stream

        # Apply to chat controller
        chat_config = ChatConfig(
            provider=settings.provider,
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            max_iterations=settings.max_iterations,
        )
        self.chat_controller.configure(chat_config)

        # Apply work directory
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

    def _on_message_sent(self, message: str):
        """Handle message sent from chat panel."""
        logger.info(f"Message sent: {message[:50]}...")

        if self.chat_controller.is_busy():
            self.statusbar.showMessage("正在处理中，请稍候...", 2000)
            return

        # User message is already shown by chat_panel._on_send()
        self.statusbar.showMessage("正在思考...")

        # Log current config
        config = self.chat_controller.config
        logger.info(f"Current config: provider={config.provider}, model={config.model}, api_key={'*' * 8 if config.api_key else 'NOT SET'}")

        # Start async worker
        async def send_and_receive():
            response = ""
            async for chunk in self.chat_controller.send_message(message):
                response = chunk
            return response

        self._current_worker = AsyncWorker(send_and_receive())
        self._current_worker.finished.connect(self._on_response_received)
        self._current_worker.error.connect(self._on_error)
        logger.info("Starting AsyncWorker...")
        self._current_worker.start()

    def _on_response_received(self, response: str):
        """Handle response from agent."""
        logger.info(f"Response received: {response[:50] if response else 'EMPTY'}...")
        if response:
            # Check if streaming is enabled
            settings = self.settings_manager.get()
            if settings.stream and len(response) > 50:
                # Simulate streaming for better UX
                self._simulate_streaming(response)
            else:
                self.chat_panel.append_assistant_message(response)
        else:
            self.chat_panel.append_assistant_message("(无响应)")
        self.statusbar.showMessage(
            f"完成 | Token: {self.chat_controller.get_token_usage()}"
        )
        self._current_worker = None

    def _simulate_streaming(self, text: str):
        """Simulate streaming output for better UX."""
        from PyQt6.QtCore import QTimer

        self.chat_panel.start_streaming()
        self._stream_buffer = text
        self._stream_pos = 0
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self._stream_next_chunk)

        # Calculate chunk size and interval based on text length
        chunk_size = max(1, len(text) // 100)  # ~100 chunks
        interval = max(10, 1500 // 100)  # ~1.5 seconds total

        self._stream_chunk_size = chunk_size
        self._stream_timer.start(interval)

    def _stream_next_chunk(self):
        """Stream the next chunk of text."""
        if self._stream_pos >= len(self._stream_buffer):
            self._stream_timer.stop()
            self.chat_panel.finish_streaming()
            return

        # Get next chunk
        end = min(self._stream_pos + self._stream_chunk_size, len(self._stream_buffer))
        chunk = self._stream_buffer[self._stream_pos:end]
        self._stream_pos = end

        # Append chunk
        self.chat_panel.append_streaming_chunk(chunk)

    def _on_error(self, error: str):
        """Handle error from async operation."""
        logger.error(f"Error received: {error}")
        self.chat_panel.append_assistant_message(f"❌ 错误: {error}")
        self.statusbar.showMessage(f"错误: {error}")
        self._current_worker = None

    def _on_tool_call(self, tool_name: str, arguments: dict):
        """Handle tool call event."""
        self.chat_panel.append_tool_call(tool_name, arguments)

    def _on_tool_result(self, tool_name: str, result: str, success: bool = True):
        """Handle tool result event."""
        self.chat_panel.append_tool_result(tool_name, result, success)

    def _on_thinking(self, message: str):
        """Handle thinking/progress event."""
        self.chat_panel.append_thinking(message)

    def _on_work_dir_changed(self, path: Path):
        """Handle work directory change."""
        self.work_dir = path
        self.chat_controller.work_dir = path
        self.statusbar.showMessage(f"工作目录已更改: {path}", 3000)

    def _on_mcp_changed(self):
        """Handle MCP server list change."""
        # Update sidebar
        self.sidebar.mcp_list.clear()
        for server in self.mcp_controller.get_server_list():
            status_icon = "✓" if server.status == "已连接" else "○"
            self.sidebar.mcp_list.addItem(f"{status_icon} {server.name} ({server.status})")

    def _on_skills_changed(self):
        """Handle skill list change."""
        # Update sidebar
        self.sidebar.skill_list.clear()
        for skill in self.skill_controller.get_skill_list():
            status = "已启用" if skill.enabled else "已禁用"
            self.sidebar.skill_list.addItem(f"{skill.name} ({status})")

    def closeEvent(self, event):
        """Handle window close."""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.wait()
        event.accept()
