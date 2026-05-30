"""
MCP server configuration dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QDialogButtonBox, QGroupBox,
    QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt


class MCPServerDialog(QDialog):
    """Dialog for adding/editing MCP server configuration."""

    def __init__(self, parent=None, server_config: dict = None):
        super().__init__(parent)
        self.setWindowTitle("添加 MCP 服务器")
        self.setMinimumWidth(450)
        self._setup_ui()

        if server_config:
            self._load_config(server_config)

    def _setup_ui(self):
        """Setup UI components."""
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

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        buttons.addButton(test_btn, QDialogButtonBox.ButtonRole.ActionRole)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initial state
        self._on_transport_changed("stdio")

    def _on_transport_changed(self, transport: str):
        """Handle transport type change."""
        is_stdio = transport == "stdio"
        self.stdio_group.setVisible(is_stdio)
        self.http_group.setVisible(not is_stdio)

    def _test_connection(self):
        """Test MCP server connection."""
        # TODO: Implement actual connection test
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "测试连接", "连接测试功能待实现")

    def _load_config(self, config: dict):
        """Load existing configuration."""
        self.name_edit.setText(config.get("name", ""))
        self.transport_combo.setCurrentText(config.get("transport", "stdio"))
        self.command_edit.setText(config.get("command", ""))
        self.args_edit.setText(", ".join(config.get("args", [])))
        self.url_edit.setText(config.get("url", ""))

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
                config["env"] = dict(
                    e.split("=", 1) for e in self.env_edit.text().split(",") if "=" in e
                )
        else:
            config["url"] = self.url_edit.text()
            if self.headers_edit.text():
                config["headers"] = dict(
                    h.split(":", 1) for h in self.headers_edit.text().split(",") if ":" in h
                )

        return config
