"""
Main window for Harness Client - 3-column layout with header bar.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QFontDatabase, QIcon
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

if TYPE_CHECKING:
    from harness import ConfirmationResult

from harness_client.controllers.chat_controller import ChatController
from harness_client.controllers.mcp_controller import MCPController
from harness_client.controllers.memory_controller import MemoryController
from harness_client.controllers.monitoring_controller import MonitoringController
from harness_client.controllers.schedule_controller import ScheduleController
from harness_client.controllers.skill_controller import SkillController
from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener
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

        # Set window icon from SVG
        self._set_window_icon()

        # Initialize controllers
        self.chat_controller = ChatController()
        self.mcp_controller = MCPController()
        self.skill_controller = SkillController()
        self.memory_controller = MemoryController()
        self.schedule_controller = ScheduleController()
        self.monitoring_controller = MonitoringController()

        # Connect controller callbacks
        self.mcp_controller.set_change_callback(self._on_mcp_changed)
        self.skill_controller.set_change_callback(self._on_skills_changed)
        self.memory_controller.memory_changed.connect(self._on_memory_changed)
        self.chat_controller.set_tool_call_callback(self._on_tool_call)
        self.chat_controller.set_tool_result_callback(self._on_tool_result)
        self.chat_controller.set_thinking_callback(self._on_thinking)
        self.chat_controller.set_confirm_callback(self._confirm_dangerous_operation)
        self.chat_controller.set_progress_callback(self._on_progress_event)
        self.chat_controller.set_mcp_controller(self.mcp_controller)

        # Set callback to start schedule controller when agent is ready
        self.chat_controller._on_agent_ready = self._on_agent_ready

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
        self.chat_panel.browser_close_requested.connect(self._on_browser_close)
        self.sidebar.session_new_requested.connect(self._on_new_session)
        self.sidebar.session_switch_requested.connect(self._on_session_switch)
        self.sidebar.session_delete_requested.connect(self._on_session_delete)
        self.sidebar.settings_requested.connect(self._on_preferences)
        # Right panel signals (including schedule and browser moved from sidebar)
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
        self.right_panel.schedule_requested.connect(self._on_schedule_panel)
        self.right_panel.browser_toggle_requested.connect(self._on_browser_toggle)

        # Load saved settings
        self._load_saved_settings()

        # Load MCP configuration
        self._load_mcp_config()

        # Load schedule configuration
        self._load_schedule_config()

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

        # Initialize agent and start schedule controller on startup
        # Use QTimer to ensure event loop is running
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._initialize_agent_for_schedules)

    def _set_window_icon(self):
        """Set window icon from SVG file."""
        import sys

        from PyQt6.QtGui import QPainter, QPixmap

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
        self.right_panel = RightPanel(monitoring_controller=self.monitoring_controller)
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
        """Setup status bar with monitoring metrics."""
        from PyQt6.QtWidgets import QLabel

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

        # 状态消息标签（左侧）
        self._status_msg_label = QLabel("就绪")
        self._status_msg_label.setStyleSheet("color: white;")
        self.statusbar.addWidget(self._status_msg_label)

        # 分隔符
        self.statusbar.addWidget(QLabel(" | "))

        # Token 标签（右侧）
        self._token_label = QLabel("Token: 0")
        self._token_label.setStyleSheet("color: white; font-weight: bold;")
        self.statusbar.addPermanentWidget(self._token_label)

        # 成本标签
        self._cost_label = QLabel("成本: $0.00")
        self._cost_label.setStyleSheet("color: white;")
        self.statusbar.addPermanentWidget(self._cost_label)

        # API 模型标签
        self._model_label = QLabel("API: -")
        self._model_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        self.statusbar.addPermanentWidget(self._model_label)

        # 延迟标签
        self._latency_label = QLabel("延迟: -")
        self._latency_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        self.statusbar.addPermanentWidget(self._latency_label)

        # 连接监控信号
        self.monitoring_controller.metrics_updated.connect(self._update_statusbar_metrics)
        self.monitoring_controller.session_ended.connect(self._on_session_ended)

    def _update_statusbar_metrics(self):
        """更新状态栏监控指标"""
        metrics = self.monitoring_controller.metrics

        # 更新 Token
        self._token_label.setText(f"Token: {metrics.total_tokens():,}")

        # 更新成本
        self._cost_label.setText(f"成本: ${metrics.cost_usd:.2f}")

        # 更新延迟
        latency = self.monitoring_controller.get_recent_latency_ms()
        if latency:
            self._latency_label.setText(f"延迟: {latency:.0f}ms")

    def _on_session_ended(self):
        """会话结束时的处理"""
        metrics = self.monitoring_controller.metrics
        self._status_msg_label.setText(
            f"完成 | 迭代: {metrics.iterations}, 工具: {metrics.tool_calls}"
        )

    # === Session Management ===

    def _refresh_session_list(self):
        """Refresh the session list in sidebar."""
        current = self.chat_controller.get_current_session()
        history = self.chat_controller.session_manager.get_history_list()
        self.sidebar.update_sessions(current, history)

        # Update session title in header
        if current:
            self.chat_panel.set_session_title(current.name)

    def _on_new_session(self):
        """Create a new session."""
        self.chat_controller.new_session()
        self.chat_panel.clear_chat()
        self.chat_panel.set_session_title("新会话")
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
                        # Multimodal content: extract text and show attachment info
                        text_parts = []
                        attachment_info = []
                        for block in content:
                            if isinstance(block, dict):
                                block_type = block.get("type", "")
                                if block_type == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block_type == "document":
                                    filename = block.get("filename", "文档")
                                    attachment_info.append(f"[文档: {filename}]")
                                elif block_type == "image":
                                    attachment_info.append("[图片]")
                        # Combine text and attachment info
                        display_content = " ".join(text_parts)
                        if attachment_info:
                            display_content += " " + " ".join(attachment_info)
                        content = display_content
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

    @asyncSlot(object, bool)
    async def _on_message_sent(self, message: str | list[dict[str, Any]], goal_mode: bool):
        """Handle message sent from chat panel.

        Args:
            message: User message - can be text (str) or multimodal content (list of dicts)
            goal_mode: If True, use run_goal() for multi-iteration autonomous execution
        """
        # Log message type
        if isinstance(message, list):
            logger.info(f"Multimodal message sent with {len(message)} blocks, goal_mode={goal_mode}")
        else:
            logger.info(f"Message sent: {message[:50]}..., goal_mode={goal_mode}")

        if self.chat_controller.is_busy():
            self.statusbar.showMessage("正在处理中，请稍候...", 2000)
            return

        self._is_processing = True
        self.chat_panel.set_streaming_state(True)

        if goal_mode:
            self.statusbar.showMessage("执行任务中...")
        else:
            self.statusbar.showMessage("正在思考...")

        config = self.chat_controller.config
        logger.info(f"Current config: provider={config.provider}, model={config.model}")

        try:
            response = ""
            async for chunk in self.chat_controller.send_message(message, goal_mode=goal_mode):
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
        usage = self.chat_controller.get_token_usage()
        self.statusbar.showMessage(f"完成 | Token: {usage.get('input', 0)} 输入, {usage.get('output', 0)} 输出")
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

    def _on_progress_event(self, event):
        """Handle SDK ProgressEvent for monitoring."""
        self.monitoring_controller.handle_progress_event(event)

        # 更新状态栏消息（开始/结束事件）
        event_type = event.type.value
        if event_type == "loop_start":
            self._status_msg_label.setText("执行中...")
        elif event_type == "loop_end":
            self._status_msg_label.setText("完成")

    def _initialize_agent_for_schedules(self):
        """Initialize agent on startup to enable scheduled tasks."""
        # Only initialize if there are enabled schedules
        enabled_schedules = [s for s in self.schedule_controller.get_schedule_list() if s.enabled]
        if not enabled_schedules:
            logger.info("No enabled schedules, skipping early agent initialization")
            return

        # Check if API key is configured
        settings = self.settings_manager.get()
        if not settings.api_key:
            logger.warning("API key not configured, scheduled tasks will not run")
            return

        logger.info(f"Found {len(enabled_schedules)} enabled schedule(s), initializing agent...")

        async def init_and_start():
            try:
                # Initialize agent
                await self.chat_controller.initialize()

                # ScheduleController will be started via _on_agent_ready callback
                logger.info("Agent initialized for scheduled tasks")
            except Exception as e:
                logger.error(f"Failed to initialize agent for schedules: {e}", exc_info=True)

        try:
            asyncio.create_task(init_and_start())
        except RuntimeError:
            logger.warning("Event loop not ready, schedules will start on first message")

    def _on_agent_ready(self, agent):
        """Handle agent ready - start schedule controller and load MCP/Skill configs."""
        logger.info("Agent ready, initializing controllers...")

        self.schedule_controller.set_agent(agent)

        # Set agent to skill and MCP controllers
        self.skill_controller.set_agent(agent)
        self.mcp_controller.set_agent(agent)

        # Sync cached MCP configs to SDK's MCPManager
        # (Configs were cached during startup before agent was available)
        for name, info in self.mcp_controller.servers.items():
            config = self.mcp_controller.get_server_config(name)
            if config and agent._mcp_manager:
                # Check if server already exists in manager
                existing = agent._mcp_manager.get_server_config(name)
                if not existing:
                    logger.info(f"Syncing cached MCP config '{name}' to SDK")
                    agent._mcp_manager.add_server(config)
                else:
                    logger.info(f"MCP config '{name}' already in SDK, skipping")

        # Load skills now that agent is available
        logger.info("Loading skills after agent ready...")
        skills_loaded = self.skill_controller.load_defaults()
        logger.info(f"Loaded {skills_loaded} skills")

        # Auto-connect enabled MCP servers
        self._auto_connect_mcp_servers()

        # Start schedule controller in background
        async def start_schedule_controller():
            try:
                await self.schedule_controller.start()
                logger.info("ScheduleController started successfully")
            except Exception as e:
                logger.error(f"Failed to start schedule controller: {e}", exc_info=True)

        # Schedule the start on the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(start_schedule_controller())
            else:
                loop.run_until_complete(start_schedule_controller())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(start_schedule_controller())

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
        # Browser settings
        dialog.browser_type_combo.setCurrentText(getattr(current, "browser_type", "msedge"))
        dialog.browser_headless_check.setChecked(getattr(current, "browser_headless", False))
        dialog.browser_screenshot_check.setChecked(getattr(current, "browser_screenshot", True))
        dialog.browser_timeout_spin.setValue(getattr(current, "browser_timeout", 30000))

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

    @asyncSlot()
    async def _on_browser_toggle(self):
        """Toggle browser on/off."""
        browser_ctrl = self.chat_controller.browser_controller

        # Check if playwright is available
        if not browser_ctrl.is_available():
            QMessageBox.warning(
                self,
                "浏览器不可用",
                "Playwright 未安装。\n\n请运行:\npip install playwright\nplaywright install",
            )
            return

        if browser_ctrl.is_active():
            # Stop browser
            success, message = await browser_ctrl.stop_browser()
            if success:
                self.statusbar.showMessage(message, 3000)
                self.right_panel.update_browser_status(False)
                self.chat_panel.set_browser_active(False)
                # Reset agent to remove browser tools
                self.chat_controller.refresh_browser_tools()
            else:
                QMessageBox.warning(self, "关闭浏览器失败", message)
        else:
            # Start browser
            success, message = browser_ctrl.start_browser()
            if success:
                self.statusbar.showMessage(message, 3000)
                self.right_panel.update_browser_status(True, browser_ctrl.get_config().browser_type)
                self.chat_panel.set_browser_active(True, len(browser_ctrl.get_browser_tools()))
                # Reset agent to add browser tools
                self.chat_controller.refresh_browser_tools()
            else:
                QMessageBox.warning(self, "启动浏览器失败", message)

    def _on_browser_close(self):
        """Handle browser close request from chat panel status bar."""
        # Trigger the toggle which will close the browser
        self._on_browser_toggle()

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
            # Browser settings
            browser_type=settings.get("browser_type", "msedge"),
            browser_headless=settings.get("browser_headless", False),
            browser_screenshot=settings.get("browser_screenshot", True),
            browser_timeout=settings.get("browser_timeout", 30000),
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
            # Routing settings
            enable_routing=settings.get("enable_routing", False),
            high_model=settings.get("high_model", ""),
            low_model=settings.get("low_model", ""),
            router_model_path=settings.get("router_model_path", ""),
            router_url=settings.get("router_url", ""),
        )
        self.chat_controller.configure(chat_config)

        # 更新监控控制器模型名称
        model = settings.get("model", "claude-sonnet-4-6")
        self.monitoring_controller.set_model(model)
        self._model_label.setText(f"API: {model}")

        if settings.get("work_dir"):
            self.work_dir = Path(settings["work_dir"])
            self.right_panel.set_work_dir(self.work_dir)

        # Apply theme change if needed
        theme_mode = settings.get("theme_mode", "auto")

        set_theme_mode(theme_mode)

        # Apply browser settings
        from harness_client.controllers.browser_controller import BrowserConfig
        browser_config = BrowserConfig(
            browser_type=settings.get("browser_type", "msedge"),
            headless=settings.get("browser_headless", False),
            auto_screenshot=settings.get("browser_screenshot", True),
            default_timeout=settings.get("browser_timeout", 30000),
        )
        self.chat_controller.browser_controller.configure(browser_config)

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
            # Routing settings
            enable_routing=getattr(settings, "enable_routing", False),
            high_model=getattr(settings, "high_model", ""),
            low_model=getattr(settings, "low_model", ""),
            router_model_path=getattr(settings, "router_model_path", ""),
            router_url=getattr(settings, "router_url", ""),
        )
        self.chat_controller.configure(chat_config)

        # 初始化监控控制器模型名称
        self.monitoring_controller.set_model(settings.model)
        self._model_label.setText(f"API: {settings.model}")

        # Load browser settings
        from harness_client.controllers.browser_controller import BrowserConfig
        browser_config = BrowserConfig(
            browser_type=getattr(settings, "browser_type", "msedge"),
            headless=getattr(settings, "browser_headless", False),
            auto_screenshot=getattr(settings, "browser_screenshot", True),
            default_timeout=getattr(settings, "browser_timeout", 30000),
        )
        self.chat_controller.browser_controller.configure(browser_config)

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
        for server_config in self.mcp_controller.list_server_configs():
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
            # Note: Auto-connect is handled in _on_agent_ready() after agent is initialized

    def _auto_connect_mcp_servers(self):
        """Auto-connect to enabled MCP servers."""
        import logging
        logger = logging.getLogger(__name__)

        # Check if agent is available
        if not self.chat_controller.agent:
            logger.info("Agent not ready, skipping auto-connect (will retry when agent is initialized)")
            return

        for name, info in self.mcp_controller.servers.items():
            config = self.mcp_controller.get_server_config(name)
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

        # Get current config (works even before agent is initialized)
        server_config = self.mcp_controller.get_server_config(server_name)
        if not server_config:
            return

        # Get tools if connected (only available after agent is initialized)
        tools = None
        if self.mcp_controller.manager:
            tools = self.mcp_controller.manager.get_server_tools(server_name)

        config_dict = {
            "name": server_config.name,
            "transport": server_config.transport,
            "command": server_config.command,
            "args": server_config.args,
            "url": server_config.url,
            "env": server_config.env,
            "headers": server_config.headers,
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

    # === Schedule Management ===

    def _on_schedule_panel(self):
        """Show schedule management dialog."""
        from harness_client.ui.schedule_panel import ScheduleSection

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("排程管理")
        dialog.setMinimumSize(500, 500)

        layout = QVBoxLayout(dialog)

        # Create schedule section
        self._schedule_section = ScheduleSection()
        self._refresh_schedule_list()

        # Connect signals
        self._schedule_section.add_requested.connect(lambda: self._on_add_schedule(dialog))
        self._schedule_section.edit_requested.connect(lambda sid: self._on_edit_schedule(sid, dialog))
        self._schedule_section.delete_requested.connect(lambda sid: self._on_delete_schedule(sid, dialog))
        self._schedule_section.toggle_requested.connect(lambda sid: self._on_toggle_schedule(sid, dialog))

        layout.addWidget(self._schedule_section)

        # Close button
        from PyQt6.QtWidgets import QPushButton
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def _refresh_schedule_list(self):
        """Refresh the schedule list in the dialog."""
        if hasattr(self, '_schedule_section') and self._schedule_section:
            schedules = self.schedule_controller.get_schedule_list()
            self._schedule_section.update_schedules([s.to_dict() for s in schedules])

    def _on_add_schedule(self, parent_dialog):
        """Handle add schedule request."""
        from harness_client.ui.schedule_panel import ScheduleDialog

        dialog = ScheduleDialog(parent_dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_schedule_data()
            if not data.get("name") or not data.get("goal"):
                QMessageBox.warning(parent_dialog, "错误", "请填写名称和目标")
                return

            from harness_client.controllers.schedule_controller import ScheduleConfig
            config = ScheduleConfig(
                id=f"schedule_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                name=data["name"],
                goal=data["goal"],
                trigger_type=data["trigger_type"],
                trigger_value=data["trigger_value"],
                max_iterations=data.get("max_iterations", 50),
                timeout_seconds=data.get("timeout_seconds", 3600),
            )

            if self.schedule_controller.add_schedule(config):
                self.statusbar.showMessage(f"排程「{config.name}」已创建", 3000)
                self._save_schedule_config()
                self._refresh_schedule_list()
            else:
                QMessageBox.warning(parent_dialog, "错误", "创建排程失败")

    def _on_edit_schedule(self, schedule_id: str, parent_dialog):
        """Handle edit schedule request."""
        from harness_client.ui.schedule_panel import ScheduleDialog

        config = self.schedule_controller.get_schedule(schedule_id)
        if not config:
            return

        dialog = ScheduleDialog(parent_dialog, config.to_dict())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_schedule_data()
            if self.schedule_controller.update_schedule(schedule_id, data):
                self.statusbar.showMessage("排程已更新", 3000)
                self._save_schedule_config()
                self._refresh_schedule_list()

    def _on_delete_schedule(self, schedule_id: str, parent_dialog):
        """Handle delete schedule request."""
        config = self.schedule_controller.get_schedule(schedule_id)
        if not config:
            return

        reply = QMessageBox.question(
            parent_dialog,
            "删除排程",
            f"确定要删除排程「{config.name}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.schedule_controller.delete_schedule(schedule_id):
                self.statusbar.showMessage("排程已删除", 3000)
                self._save_schedule_config()
                self._refresh_schedule_list()

    def _on_toggle_schedule(self, schedule_id: str, parent_dialog):
        """Handle toggle schedule enabled state."""
        if self.schedule_controller.toggle_schedule(schedule_id):
            config = self.schedule_controller.get_schedule(schedule_id)
            if config:
                state = "已启用" if config.enabled else "已暂停"
                self.statusbar.showMessage(f"排程「{config.name}」{state}", 3000)
            self._save_schedule_config()
            self._refresh_schedule_list()

    def _save_schedule_config(self):
        """Save schedule configuration to file."""
        from harness_client.utils.settings import get_config_dir
        self.schedule_controller.save_to_file(get_config_dir() / "schedules.json")

    def _load_schedule_config(self):
        """Load schedule configuration from file."""
        from harness_client.utils.settings import get_config_dir
        config_path = get_config_dir() / "schedules.json"
        self.schedule_controller.load_from_file(config_path)

    def closeEvent(self, event):
        """Handle window close - cleanup resources properly."""

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
