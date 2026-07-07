"""
MCP server configuration dialog.
"""

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from harness_client.themes import get_theme


class TestConnectionThread(QThread):
    """Thread for testing MCP server connection."""

    success = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self):
        """Run the connection test in a separate thread with its own event loop."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._test_connection())
                if result:
                    self.success.emit()
                else:
                    self.failed.emit("连接失败")
            finally:
                loop.close()
        except Exception as e:
            self.failed.emit(str(e))

    async def _test_connection(self) -> bool:
        """Test the MCP server connection."""
        from harness import MCPServerConfig
        from harness.mcp.client import MCPClient
        from harness.mcp.transport import HTTPTransport, StdioTransport

        config = self.config
        server_config = MCPServerConfig(
            name="_test_",
            transport=config["transport"],
            command=config.get("command"),
            args=config.get("args", []),
            url=config.get("url"),
            env=config.get("env", {}),
            headers=config.get("headers", {}),
            timeout=config.get("timeout", 30),
        )

        # Create transport
        if server_config.transport == "stdio":
            if not server_config.command:
                raise ValueError("Stdio transport requires command")
            transport = StdioTransport(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env,
            )
        else:
            if not server_config.url:
                raise ValueError("HTTP transport requires URL")
            transport = HTTPTransport(
                url=server_config.url,
                headers=server_config.headers,
                timeout=server_config.timeout,
            )

        # Create client and test connection
        client = MCPClient(transport)
        await client.connect()

        # Check if we got tools
        if client.tools:
            return True

        await client.disconnect()
        return True  # Still success if no tools, just no tools available


class MCPServerDialog(QDialog):
    """Dialog for adding/editing MCP server configuration."""

    def __init__(self, parent=None, server_config: dict = None, tools: list = None):
        super().__init__(parent)
        self._tools = tools or []
        self.setWindowTitle("添加 MCP 服务器")
        self.setMinimumWidth(450)
        self._setup_ui()

        if server_config:
            self._load_config(server_config)

    def _setup_ui(self):
        """Setup UI components."""
        theme = get_theme()
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: filesystem")
        form.addRow("名称:", self.name_edit)

        # Transport
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["stdio", "http"])
        self.transport_combo.currentTextChanged.connect(self._on_transport_changed)
        form.addRow("传输方式:", self.transport_combo)

        layout.addLayout(form)

        # Stdio config
        self.stdio_group = QGroupBox("Stdio 配置")
        stdio_layout = QFormLayout(self.stdio_group)

        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("例如: npx")
        stdio_layout.addRow("命令:", self.command_edit)

        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("例如: -y, @anthropic/mcp-server-filesystem, /path")
        stdio_layout.addRow("参数:", self.args_edit)

        self.env_edit = QLineEdit()
        self.env_edit.setPlaceholderText("例如: DEBUG=1, PATH=/usr/bin")
        stdio_layout.addRow("环境变量:", self.env_edit)

        layout.addWidget(self.stdio_group)

        # HTTP config
        self.http_group = QGroupBox("HTTP 配置")
        http_layout = QFormLayout(self.http_group)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如: http://localhost:8080/mcp")
        http_layout.addRow("URL:", self.url_edit)

        self.headers_edit = QLineEdit()
        self.headers_edit.setPlaceholderText("例如: Authorization: Bearer xxx")
        http_layout.addRow("Headers:", self.headers_edit)

        self.http_group.setVisible(False)
        layout.addWidget(self.http_group)

        # Common settings
        common_layout = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        common_layout.addRow("超时 (秒):", self.timeout_spin)

        self.enabled_check = QCheckBox("启用此服务器")
        self.enabled_check.setChecked(True)
        common_layout.addRow(self.enabled_check)

        layout.addLayout(common_layout)

        # Tools section (only shown if tools exist)
        self.tools_group = QGroupBox("已发现工具")
        tools_layout = QVBoxLayout(self.tools_group)

        if self._tools:
            for tool in self._tools:
                # tool is MCPToolWrapper object
                desc = tool.description or ""
                desc_preview = desc[:60] + "..." if len(desc) > 60 else desc
                tool_label = QLabel(f"• {tool.original_name}")
                tool_label.setStyleSheet(f"font-weight: bold; color: {theme.ACCENT_LIGHT};")
                tools_layout.addWidget(tool_label)
                if desc_preview:
                    desc_label = QLabel(f"  {desc_preview}")
                    desc_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS};")
                    desc_label.setWordWrap(True)
                    tools_layout.addWidget(desc_label)
        else:
            no_tools_label = QLabel("未连接或无工具")
            no_tools_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
            tools_layout.addWidget(no_tools_label)

        layout.addWidget(self.tools_group)

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

        # Connect name change to update save location
        self.name_edit.textChanged.connect(self._update_save_location)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        buttons.addButton(test_btn, QDialogButtonBox.ButtonRole.ActionRole)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initial state
        self._on_transport_changed("stdio")

    def _update_save_location(self):
        """Update the save location label."""
        from pathlib import Path
        from harness_client.utils.settings import get_config_dir

        config_dir = get_config_dir()
        name = self.name_edit.text().strip()
        if name:
            self.save_location_label.setText(f"保存位置: {config_dir / 'mcp.json'} → mcpServers.{name}")
        else:
            self.save_location_label.setText(f"保存位置: {config_dir / 'mcp.json'}")

    def _on_transport_changed(self, transport: str):
        """Handle transport type change."""
        is_stdio = transport == "stdio"
        self.stdio_group.setVisible(is_stdio)
        self.http_group.setVisible(not is_stdio)

    def _test_connection(self):
        """Test MCP server connection."""
        config = self.get_config()
        if not config.get("name"):
            QMessageBox.warning(self, "测试连接", "请先输入服务器名称")
            return

        if config["transport"] == "stdio" and not config.get("command"):
            QMessageBox.warning(self, "测试连接", "请输入命令")
            return

        if config["transport"] == "http" and not config.get("url"):
            QMessageBox.warning(self, "测试连接", "请输入 URL")
            return

        # Disable button during test
        self._test_btn = self.sender()
        self._test_btn.setEnabled(False)
        self._test_btn.setText("测试中...")

        # Run test in background thread
        self._test_thread = TestConnectionThread(config, self)
        self._test_thread.success.connect(self._on_test_success)
        self._test_thread.failed.connect(self._on_test_failed)
        self._test_thread.finished.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_success(self):
        """Handle successful test connection."""
        QMessageBox.information(self, "测试连接", "连接成功！")

    def _on_test_failed(self, error: str):
        """Handle failed test connection."""
        QMessageBox.critical(self, "测试连接", f"连接失败：\n{error}")

    def _on_test_finished(self):
        """Clean up after test connection."""
        if hasattr(self, '_test_btn') and self._test_btn:
            self._test_btn.setEnabled(True)
            self._test_btn.setText("测试连接")

    def _load_config(self, config: dict):
        """Load existing configuration."""
        self.name_edit.setText(config.get("name", ""))
        self.transport_combo.setCurrentText(config.get("transport", "stdio"))
        self.command_edit.setText(config.get("command", ""))
        self.args_edit.setText(", ".join(config.get("args", [])))
        self.url_edit.setText(config.get("url", ""))

        # Load environment variables
        env = config.get("env", {})
        if env:
            self.env_edit.setText(", ".join(f"{k}={v}" for k, v in env.items()))

        # Load headers
        headers = config.get("headers", {})
        if headers:
            self.headers_edit.setText(", ".join(f"{k}: {v}" for k, v in headers.items()))

    def get_config(self) -> dict:
        """Get server configuration."""
        config = {
            "name": self.name_edit.text(),
            "transport": self.transport_combo.currentText(),
            "timeout": self.timeout_spin.value(),
            "enabled": self.enabled_check.isChecked(),
        }

        if config["transport"] == "stdio":
            config["command"] = self.command_edit.text()
            config["args"] = [a.strip() for a in self.args_edit.text().split(",") if a.strip()]
            if self.env_edit.text():
                env_dict = {}
                for e in self.env_edit.text().split(","):
                    if "=" in e:
                        key, value = e.split("=", 1)
                        env_dict[key.strip()] = value.strip()
                config["env"] = env_dict
        else:
            config["url"] = self.url_edit.text()
            if self.headers_edit.text():
                headers_dict = {}
                for h in self.headers_edit.text().split(","):
                    if ":" in h:
                        key, value = h.split(":", 1)
                        headers_dict[key.strip()] = value.strip()
                config["headers"] = headers_dict

        return config
