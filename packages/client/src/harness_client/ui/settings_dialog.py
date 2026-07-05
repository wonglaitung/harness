"""
Settings dialog for API configuration and preferences.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from harness_client.themes import get_theme


class SettingsDialog(QDialog):
    """Settings dialog for configuring the client."""

    # Signal to notify theme change
    theme_changed = None  # Will be connected in main_window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        theme = get_theme()
        layout = QVBoxLayout(self)

        # Tabs
        tabs = QTabWidget()

        # API tab
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["anthropic", "openai"])
        api_layout.addRow("Provider:", self.provider_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("或设置环境变量")
        api_layout.addRow("API Key:", self.api_key_edit)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("留空使用官方 API")
        api_layout.addRow("Base URL:", self.base_url_edit)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # 允许自定义输入
        self.model_combo.addItems(
            [
                "claude-sonnet-4-6",
                "claude-opus-4-6",
                "claude-haiku-4-5",
                "gpt-4o",
                "gpt-4-turbo",
                "glm-4",
                "glm-5",
                "deepseek-chat",
                "deepseek-coder",
                "qwen-max",
                "qwen-plus",
            ]
        )
        self.model_combo.setCurrentText("claude-sonnet-4-6")
        self.model_combo.lineEdit().setPlaceholderText("选择或输入模型名称")
        api_layout.addRow("Model:", self.model_combo)

        self.context_window_combo = QComboBox()
        self.context_window_combo.setEditable(True)  # 允许自定义输入
        self.context_window_combo.addItems(
            [
                "auto",
                "32k",
                "64k",
                "128k",
                "200k",
            ]
        )
        self.context_window_combo.setCurrentText("auto")
        self.context_window_combo.lineEdit().setPlaceholderText("选择或输入上下文长度")
        api_layout.addRow("Context:", self.context_window_combo)

        # Compatibility mode for proxy APIs that don't support "tool" role
        # Only relevant for Anthropic provider
        self.tool_role_combo = QComboBox()
        self.tool_role_combo.addItems(["tool", "user"])
        self.tool_role_combo.setCurrentText("tool")
        self.tool_role_combo.setToolTip(
            "某些 Anthropic 代理 API 不支持原生的 tool role。\n"
            "如果遇到 'invalid role: tool' 错误，请选择 'user'。"
        )
        self.tool_role_label = QLabel("工具结果角色:")
        self.tool_role_row = api_layout.addRow(self.tool_role_label, self.tool_role_combo)

        # Explanation label for tool role
        self.tool_role_help = QLabel(
            "• tool: Anthropic 原生格式\n"
            "• user: 兼容模式（代理 API 不支持 tool role 时使用）"
        )
        self.tool_role_help.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}; margin-left: 20px;")
        self.tool_role_help.setWordWrap(True)
        self.tool_role_help_row = api_layout.addRow(self.tool_role_help)

        # Connect provider change to update tool role visibility
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)

        tabs.addTab(api_tab, "API")

        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        # Theme selection (外观 - 用户最常调整)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["自动", "亮色", "深色"])
        self.theme_combo.setToolTip(
            "自动: 跟随系统设置\n亮色: 强制使用亮色主题\n深色: 强制使用深色主题"
        )
        general_layout.addRow("主题:", self.theme_combo)

        # Stream output (基础行为)
        self.stream_check = QCheckBox("启用流式输出")
        self.stream_check.setChecked(True)
        general_layout.addRow(self.stream_check)

        # Auto save (基础行为)
        self.auto_save_check = QCheckBox("自动保存对话")
        self.auto_save_check.setChecked(True)
        general_layout.addRow(self.auto_save_check)

        # Auto update memory (功能开关)
        self.auto_update_memory_check = QCheckBox("允许 Agent 自主更新记忆")
        self.auto_update_memory_check.setChecked(True)  # Enabled by default
        self.auto_update_memory_check.setToolTip(
            "启用后，Agent 可以自主判断并将用户偏好、项目约定等保存到长期记忆。\n"
            "禁用后，Agent 将无法调用 update_core_memory 工具。"
        )
        general_layout.addRow(self.auto_update_memory_check)

        # Temperature slider (模型参数 - 高级设置)
        self.temperature_label = QLabel("Temperature: 0.3")
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)  # 0-100 maps to 0.0-1.0
        self.temperature_slider.setValue(30)  # Default 0.3 for stability
        self.temperature_slider.valueChanged.connect(self._on_temperature_changed)
        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.temperature_slider)
        temp_help = QLabel("低值(0.1-0.3)更稳定，高值(0.7-1.0)更有创造性")
        temp_help.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS};")
        temp_layout.addWidget(temp_help)
        general_layout.addRow(self.temperature_label, temp_layout)

        # Max iterations (高级限制)
        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(1, 100)
        self.max_iterations_spin.setValue(10)  # 业界标准默认值（与 SDK 一致）
        general_layout.addRow("最大迭代次数:", self.max_iterations_spin)

        tabs.addTab(general_tab, "常规")

        # Directories tab
        dir_tab = QWidget()
        dir_layout = QFormLayout(dir_tab)

        self.work_dir_edit = QLineEdit()
        self.work_dir_edit.setText(str(Path.cwd()))
        work_btn = QPushButton("浏览...")
        work_btn.clicked.connect(self._browse_work_dir)
        work_layout = QHBoxLayout()
        work_layout.addWidget(self.work_dir_edit)
        work_layout.addWidget(work_btn)
        dir_layout.addRow("工作目录:", work_layout)

        self.remember_dir_check = QCheckBox("记住上次目录")
        self.remember_dir_check.setChecked(True)
        dir_layout.addRow(self.remember_dir_check)

        tabs.addTab(dir_tab, "目录")

        # Routing tab (智能路由配置)
        routing_tab = QWidget()
        routing_layout = QFormLayout(routing_tab)

        # Enable routing checkbox
        self.enable_routing_check = QCheckBox("启用智能路由")
        self.enable_routing_check.setToolTip(
            "使用 CPU 模型自动选择最合适的 LLM，降低 API 成本。\n"
            "简单请求使用低成本模型，复杂请求使用高能力模型。"
        )
        routing_layout.addRow(self.enable_routing_check)

        # High model selection
        self.high_model_combo = QComboBox()
        self.high_model_combo.setEditable(True)
        self.high_model_combo.addItems([
            "gpt-4o",
            "gpt-4-turbo",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
            "deepseek-chat",
            "qwen-max",
        ])
        self.high_model_combo.setCurrentText("")
        self.high_model_combo.lineEdit().setPlaceholderText("选择或输入高级模型名称")
        routing_layout.addRow("高级模型:", self.high_model_combo)

        # Low model selection
        self.low_model_combo = QComboBox()
        self.low_model_combo.setEditable(True)
        self.low_model_combo.addItems([
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "claude-haiku-4-5",
            "deepseek-chat",
            "qwen-plus",
        ])
        self.low_model_combo.setCurrentText("")
        self.low_model_combo.lineEdit().setPlaceholderText("选择或输入基础模型名称")
        routing_layout.addRow("基础模型:", self.low_model_combo)

        # Router model path (local GGUF)
        self.router_path_edit = QLineEdit()
        self.router_path_edit.setPlaceholderText("本地 GGUF 模型文件路径")
        router_path_btn = QPushButton("浏览...")
        router_path_btn.clicked.connect(self._browse_router_path)
        router_path_layout = QHBoxLayout()
        router_path_layout.addWidget(self.router_path_edit)
        router_path_layout.addWidget(router_path_btn)
        routing_layout.addRow("路由器模型:", router_path_layout)

        # Router URL (HTTP service)
        self.router_url_edit = QLineEdit()
        self.router_url_edit.setPlaceholderText("或使用 HTTP 服务 (如 http://localhost:8080)")
        routing_layout.addRow("路由服务 URL:", self.router_url_edit)

        # Help text
        routing_help = QLabel(
            "💡 路由功能说明：\n"
            "• 简单请求（问答、查询、翻译）→ 基础模型\n"
            "• 复杂请求（推理、代码生成、分析）→ 高级模型\n"
            "• 需要准备路由器模型（如 Qwen2.5-1.5B GGUF 文件）"
        )
        routing_help.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS};")
        routing_help.setWordWrap(True)
        routing_layout.addRow(routing_help)

        tabs.addTab(routing_tab, "路由")

        # Browser tab
        browser_tab = QWidget()
        browser_layout = QFormLayout(browser_tab)

        # Browser type selection
        self.browser_type_combo = QComboBox()
        self.browser_type_combo.addItems([
            "msedge",  # Microsoft Edge (default for Windows enterprise)
            "chrome",  # Google Chrome
            "chromium",  # Playwright bundled
            "firefox",  # Playwright bundled
        ])
        self.browser_type_combo.setToolTip(
            "msedge/chrome: 使用系统浏览器，无需下载\n"
            "chromium/firefox: Playwright 自带，需要运行 playwright install"
        )
        browser_layout.addRow("浏览器类型:", self.browser_type_combo)

        # Headless mode
        self.browser_headless_check = QCheckBox("无头模式 (后台运行)")
        self.browser_headless_check.setChecked(False)
        self.browser_headless_check.setToolTip(
            "勾选后浏览器在后台运行，不显示窗口。\n"
            "适合自动化任务，但无法手动干预。"
        )
        browser_layout.addRow(self.browser_headless_check)

        # Auto screenshot
        self.browser_screenshot_check = QCheckBox("自动截图 (审计)")
        self.browser_screenshot_check.setChecked(True)
        self.browser_screenshot_check.setToolTip(
            "每次操作后自动截图，用于审计和调试。"
        )
        browser_layout.addRow(self.browser_screenshot_check)

        # Timeout
        self.browser_timeout_spin = QSpinBox()
        self.browser_timeout_spin.setRange(5000, 120000)
        self.browser_timeout_spin.setValue(30000)
        self.browser_timeout_spin.setSuffix(" ms")
        self.browser_timeout_spin.setToolTip("等待页面加载的超时时间")
        browser_layout.addRow("超时时间:", self.browser_timeout_spin)

        # Help text
        browser_help = QLabel(
            "浏览器控制允许 Agent 自动操作浏览器。\n\n"
            "• Microsoft Edge: Windows 系统自带，推荐内网使用\n"
            "• Chrome: 需要安装 Google Chrome\n"
            "• Chromium/Firefox: Playwright 自带浏览器"
        )
        browser_help.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS};")
        browser_help.setWordWrap(True)
        browser_layout.addRow(browser_help)

        tabs.addTab(browser_tab, "浏览器")

        layout.addWidget(tabs)

        # Config save location info
        self.save_location_label = QLabel()
        self.save_location_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_MUTED};
                font-size: {theme.FONT_SIZE_XS};
                padding: 4px;
            }}
        """)
        self._update_save_location()
        layout.addWidget(self.save_location_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self._on_button_clicked)
        layout.addWidget(buttons)

    def _on_button_clicked(self, button):
        """Handle button clicks including Apply."""
        from PyQt6.QtWidgets import QDialogButtonBox

        dialog_buttons = self.findChild(QDialogButtonBox)
        if dialog_buttons and button == dialog_buttons.button(QDialogButtonBox.StandardButton.Apply):
            # Apply button clicked - emit signal with current settings
            self._apply_clicked()

    def _apply_clicked(self):
        """Handle Apply button click - notify parent to apply settings."""
        # Store settings temporarily so parent can read them
        self._pending_settings = self.get_settings()
        # Accept the dialog temporarily to trigger parent's apply logic
        # Then reopen the dialog
        self.done(2)  # Custom result for Apply

    def _browse_work_dir(self):
        """Browse for work directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录", self.work_dir_edit.text())
        if dir_path:
            self.work_dir_edit.setText(dir_path)

    def _browse_router_path(self):
        """Browse for router model file (GGUF)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择路由器模型文件",
            self.router_path_edit.text(),
            "GGUF Files (*.gguf);;All Files (*)",
        )
        if file_path:
            self.router_path_edit.setText(file_path)

    def _update_save_location(self):
        """Update the save location label."""
        from harness_client.utils.settings import get_config_dir

        config_dir = get_config_dir()
        self.save_location_label.setText(f"保存位置: {config_dir / 'settings.json'}")

    def _on_provider_changed(self, provider: str):
        """Update UI based on provider selection."""
        # Tool result role only relevant for Anthropic provider
        is_anthropic = provider == "anthropic"
        self.tool_role_label.setVisible(is_anthropic)
        self.tool_role_combo.setVisible(is_anthropic)
        self.tool_role_help.setVisible(is_anthropic)

    def _on_temperature_changed(self, value: int):
        """Update temperature label when slider changes."""
        temp = value / 100.0
        self.temperature_label.setText(f"Temperature: {temp:.1f}")

    def get_settings(self) -> dict:
        """Get current settings."""
        provider = self.provider_combo.currentText()

        # Tool result role only applies to Anthropic provider
        # For OpenAI, always use native "tool" role
        tool_result_role = self.tool_role_combo.currentText()
        if provider == "openai":
            tool_result_role = "tool"

        temperature = self.temperature_slider.value() / 100.0

        return {
            "provider": provider,
            "api_key": self.api_key_edit.text(),
            "base_url": self.base_url_edit.text(),
            "model": self.model_combo.currentText(),
            "context_window": self.context_window_combo.currentText(),
            "tool_result_role": tool_result_role,
            "temperature": temperature,
            "auto_save": self.auto_save_check.isChecked(),
            "stream": self.stream_check.isChecked(),
            "max_iterations": self.max_iterations_spin.value(),
            "auto_update_memory": self.auto_update_memory_check.isChecked(),
            "work_dir": self.work_dir_edit.text(),
            "theme_mode": self._get_theme_mode(),
            # Routing settings
            "enable_routing": self.enable_routing_check.isChecked(),
            "high_model": self.high_model_combo.currentText(),
            "low_model": self.low_model_combo.currentText(),
            "router_model_path": self.router_path_edit.text(),
            "router_url": self.router_url_edit.text(),
            # Browser settings
            "browser_type": self.browser_type_combo.currentText(),
            "browser_headless": self.browser_headless_check.isChecked(),
            "browser_screenshot": self.browser_screenshot_check.isChecked(),
            "browser_timeout": self.browser_timeout_spin.value(),
        }

    def _get_theme_mode(self) -> str:
        """Get theme mode from combo selection."""
        index = self.theme_combo.currentIndex()
        modes = ["auto", "light", "dark"]
        return modes[index] if 0 <= index < len(modes) else "auto"

    def _set_theme_mode(self, mode: str):
        """Set combo selection from theme mode."""
        modes = ["auto", "light", "dark"]
        if mode in modes:
            self.theme_combo.setCurrentIndex(modes.index(mode))

    def set_settings(self, settings: dict):
        """Set dialog settings from saved values."""
        if "provider" in settings:
            self.provider_combo.setCurrentText(settings["provider"])
        if "api_key" in settings:
            self.api_key_edit.setText(settings["api_key"])
        if "base_url" in settings:
            self.base_url_edit.setText(settings["base_url"])
        if "model" in settings:
            self.model_combo.setCurrentText(settings["model"])
        if "context_window" in settings:
            self.context_window_combo.setCurrentText(settings["context_window"])
        if "tool_result_role" in settings:
            self.tool_role_combo.setCurrentText(settings["tool_result_role"])
        if "temperature" in settings:
            temp_value = int(settings["temperature"] * 100)
            self.temperature_slider.setValue(temp_value)
        if "auto_save" in settings:
            self.auto_save_check.setChecked(settings["auto_save"])
        if "stream" in settings:
            self.stream_check.setChecked(settings["stream"])
        if "max_iterations" in settings:
            self.max_iterations_spin.setValue(settings["max_iterations"])
        if "auto_update_memory" in settings:
            self.auto_update_memory_check.setChecked(settings["auto_update_memory"])
        if "work_dir" in settings:
            self.work_dir_edit.setText(settings["work_dir"])
        if "theme_mode" in settings:
            self._set_theme_mode(settings["theme_mode"])
        # Routing settings
        if "enable_routing" in settings:
            self.enable_routing_check.setChecked(settings["enable_routing"])
        if "high_model" in settings:
            self.high_model_combo.setCurrentText(settings["high_model"])
        if "low_model" in settings:
            self.low_model_combo.setCurrentText(settings["low_model"])
        if "router_model_path" in settings:
            self.router_path_edit.setText(settings["router_model_path"])
        if "router_url" in settings:
            self.router_url_edit.setText(settings["router_url"])
        # Browser settings
        if "browser_type" in settings:
            self.browser_type_combo.setCurrentText(settings["browser_type"])
        if "browser_headless" in settings:
            self.browser_headless_check.setChecked(settings["browser_headless"])
        if "browser_screenshot" in settings:
            self.browser_screenshot_check.setChecked(settings["browser_screenshot"])
        if "browser_timeout" in settings:
            self.browser_timeout_spin.setValue(settings["browser_timeout"])

        # Update UI visibility based on provider
        self._on_provider_changed(self.provider_combo.currentText())
