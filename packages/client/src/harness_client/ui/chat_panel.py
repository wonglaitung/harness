"""
Chat panel for displaying conversation.
"""

import markdown
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

    def _render_markdown(self, text: str) -> str:
        """Render markdown to HTML."""
        # Configure markdown extensions
        extensions = [
            'fenced_code',
            'codehilite',
            'tables',
            'toc',
            'nl2br',
        ]
        return markdown.markdown(text, extensions=extensions)

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display."""
        # Render markdown for assistant messages
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message with blue background and white text
            html = f'''
            <div style="margin: 8px 0; text-align: right;">
                <table style="display: inline-table; background-color: #0078d4;
                              border-radius: 12px; max-width: 70%;" cellpadding="8" cellspacing="0">
                    <tr><td style="color: white;">
                        <b style="color: white;">你:</b> <span style="color: white;">{rendered_content}</span>
                    </td></tr>
                </table>
            </div>
            '''
        else:
            # Assistant message with light gray background
            html = f'''
            <div style="margin: 8px 0;">
                <table style="display: inline-table; background-color: #f5f5f5;
                              border-radius: 12px; max-width: 90%;" cellpadding="8" cellspacing="0">
                    <tr><td style="color: #333;">
                        <b style="color: #333;">🤖 助手:</b><br>
                        <div style="margin-top: 4px; color: #333;">{rendered_content}</div>
                    </td></tr>
                </table>
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

    def append_tool_call(self, tool_name: str, arguments: dict):
        """Append a tool call indicator."""
        args_str = ", ".join(f"{k}={v}" for k, v in list(arguments.items())[:3])
        if len(arguments) > 3:
            args_str += "..."
        html = f'''
        <div style="margin: 4px 0; margin-left: 20px;">
            <div style="display: inline-block; background-color: #e3f2fd; color: #1565c0;
                        padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                🔧 调用工具: <b>{self._escape_html(tool_name)}</b>({self._escape_html(args_str)})
            </div>
        </div>
        '''
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_tool_result(self, tool_name: str, result_preview: str, success: bool = True):
        """Append a tool result indicator."""
        preview = result_preview[:100] + "..." if len(result_preview) > 100 else result_preview

        if success:
            bg_color = "#e8f5e9"
            text_color = "#2e7d32"
            icon = "✅"
        else:
            bg_color = "#ffebee"
            text_color = "#c62828"
            icon = "❌"

        html = f'''
        <div style="margin: 4px 0; margin-left: 20px;">
            <div style="display: inline-block; background-color: {bg_color}; color: {text_color};
                        padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                {icon} 完成: {self._escape_html(preview)}
            </div>
        </div>
        '''
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_thinking(self, message: str):
        """Append a thinking/progress indicator."""
        html = f'''
        <div style="margin: 4px 0; margin-left: 20px;">
            <div style="display: inline-block; background-color: #fff3e0; color: #e65100;
                        padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                💭 {self._escape_html(message)}
            </div>
        </div>
        '''
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()
