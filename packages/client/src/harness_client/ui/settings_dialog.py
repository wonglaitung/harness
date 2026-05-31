"""
Settings dialog for API configuration and preferences.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Settings dialog for configuring the client."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
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

        tabs.addTab(api_tab, "API")

        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.auto_save_check = QCheckBox("自动保存对话")
        self.auto_save_check.setChecked(True)
        general_layout.addRow(self.auto_save_check)

        self.stream_check = QCheckBox("启用流式输出")
        self.stream_check.setChecked(True)
        general_layout.addRow(self.stream_check)

        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(1, 100)
        self.max_iterations_spin.setValue(20)
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

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_work_dir(self):
        """Browse for work directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录", self.work_dir_edit.text())
        if dir_path:
            self.work_dir_edit.setText(dir_path)

    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            "provider": self.provider_combo.currentText(),
            "api_key": self.api_key_edit.text(),
            "base_url": self.base_url_edit.text(),
            "model": self.model_combo.currentText(),
            "context_window": self.context_window_combo.currentText(),
            "auto_save": self.auto_save_check.isChecked(),
            "stream": self.stream_check.isChecked(),
            "max_iterations": self.max_iterations_spin.value(),
            "work_dir": self.work_dir_edit.text(),
        }
