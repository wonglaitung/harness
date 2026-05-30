"""
Chat panel for displaying conversation.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    # Signals
    message_sent = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _get_font(self) -> QFont:
        """Get a suitable font for the system."""
        font = QFont()
        font.setPointSize(10)
        # Try common fonts in order
        for family in ["Microsoft YaHei", "Segoe UI", "SimHei", "Arial"]:
            font.setFamily(family)
            if QFontDatabase.families().count(family) > 0 or family in QFontDatabase.families():
                break
        return font

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setFont(self._get_font())
        self.chat_display.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.chat_display.setPlaceholderText("开始对话...")

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息... (Enter 发送)")
        self.input_field.setFont(self._get_font())
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self._on_send)

        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setMinimumWidth(80)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(self.chat_display)
        layout.addLayout(input_layout)

        # Welcome message
        self._append_message("assistant",
            "你好！我是基于 Harness SDK 的 AI 助手。\n\n"
            "我可以帮助你：\n"
            "- 读取和分析文件\n"
            "- 执行命令\n"
            "- 搜索网络\n"
            "- 管理项目\n\n"
            "请配置左侧的 MCP 服务器和技能以解锁更多功能。"
        )

    def _on_send(self):
        """Handle send button click."""
        text = self.input_field.text().strip()
        if not text:
            return

        # Display user message
        self._append_message("user", text)

        # Clear input
        self.input_field.clear()

        # Emit signal
        self.message_sent.emit(text)

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display."""
        if role == "user":
            html = f'''
            <div style="margin: 8px 0; text-align: right;">
                <div style="display: inline-block; background-color: #0078d4; color: white;
                            padding: 8px 12px; border-radius: 12px; max-width: 70%;">
                    <b>你:</b> {self._escape_html(content)}
                </div>
            </div>
            '''
        else:
            html = f'''
            <div style="margin: 8px 0;">
                <div style="display: inline-block; background-color: #f0f0f0; color: #333;
                            padding: 8px 12px; border-radius: 12px; max-width: 70%;">
                    <b>🤖 助手:</b><br>{self._escape_html(content)}
                </div>
            </div>
            '''
        self.chat_display.append(html)

        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _escape_html(self, text: str) -> str:
        """Escape HTML characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def append_assistant_message(self, content: str):
        """Append an assistant message."""
        self._append_message("assistant", content)

    def append_user_message(self, content: str):
        """Append a user message."""
        self._append_message("user", content)

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()
