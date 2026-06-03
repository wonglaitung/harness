"""
Chat panel for displaying conversation - Hermes Dark Theme Style.
"""

import markdown
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    # Signals
    message_sent = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._streaming_text = ""  # Buffer for streaming text
        self._is_streaming = False
        self._stream_message_start = 0  # Cursor position where streaming message starts
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
        """Setup UI components with dark theme."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Chat display area - dark theme
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setFont(self._get_font())
        # Dark theme handled by global QSS, no inline styles needed
        self.chat_display.setPlaceholderText("开始对话...")

        # Input bar container with dark background
        input_bar = QWidget()
        input_bar.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-top: 1px solid #3e3e42;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(8)

        # Input field - dark theme
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息... (Enter 发送)")
        self.input_field.setFont(self._get_font())
        self.input_field.setMinimumHeight(36)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 8px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        self.input_field.returnPressed.connect(self._on_send)

        # Token usage label
        self.token_label = QLabel("0 / 200k")
        self.token_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
                padding: 0 4px;
            }
        """)

        # Send button - primary blue
        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumHeight(36)
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

        input_layout.addWidget(self.input_field, stretch=1)
        input_layout.addWidget(self.token_label)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(self.chat_display, stretch=1)
        layout.addWidget(input_bar)

        # Welcome message
        self._append_message(
            "assistant",
            "你好！我是基于 Harness SDK 的 AI 助手。\n\n"
            "我可以帮助你：\n"
            "- 读取和分析文件\n"
            "- 执行命令\n"
            "- 搜索网络\n"
            "- 管理项目\n\n"
            "请配置左侧的 MCP 服务器和技能以解锁更多功能。",
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
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "nl2br",
        ]
        return markdown.markdown(text, extensions=extensions)

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display with dark theme styling."""
        # Render markdown for assistant messages
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message with dark blue bubble, right-aligned
            html = f"""
            <div style="margin: 8px 0; text-align: right;">
                <div style="display: inline-block; background-color: #0e4063;
                            border-radius: 12px; padding: 10px 14px; max-width: 70%;
                            color: #ffffff; font-size: 13px;">
                    {rendered_content}
                </div>
            </div>
            """
        else:
            # Assistant message with avatar and gray bubble, left-aligned
            html = f"""
            <div style="margin: 8px 0;">
                <div style="display: inline-flex; align-items: flex-start; gap: 8px;">
                    <div style="width: 28px; height: 28px; border-radius: 50%;
                                background-color: #007acc; color: white; font-size: 14px;
                                display: inline-flex; align-items: center; justify-content: center;">A</div>
                    <div style="background-color: #2d2d30; border-radius: 12px;
                                padding: 10px 14px; max-width: 85%;
                                color: #d4d4d4; font-size: 13px;">
                        <div style="margin-top: 0; color: #d4d4d4;">{rendered_content}</div>
                    </div>
                </div>
            </div>
            """
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
        """Append a tool call indicator with dark theme card style."""
        args_str = ", ".join(f"{k}={v}" for k, v in list(arguments.items())[:3])
        if len(arguments) > 3:
            args_str += "..."
        html = f"""
        <div style="margin: 4px 0 4px 36px;">
            <div style="background-color: #264f78; color: #58a6ff;
                        padding: 6px 10px; border-radius: 6px; font-size: 12px;
                        border-left: 3px solid #58a6ff;">
                🔧 <b>{self._escape_html(tool_name)}</b>({self._escape_html(args_str)})
            </div>
        </div>
        """
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_tool_result(self, tool_name: str, result_preview: str, success: bool = True):
        """Append a tool result indicator with dark theme styling."""
        preview = result_preview[:100] + "..." if len(result_preview) > 100 else result_preview

        if success:
            bg_color = "#1a3a2a"
            text_color = "#50c878"
            border_color = "#50c878"
            icon = "✅"
        else:
            bg_color = "#3a1a1a"
            text_color = "#ff6b6b"
            border_color = "#ff6b6b"
            icon = "❌"

        html = f"""
        <div style="margin: 4px 0 4px 36px;">
            <div style="background-color: {bg_color}; color: {text_color};
                        padding: 6px 10px; border-radius: 6px; font-size: 12px;
                        border-left: 3px solid {border_color};">
                {icon} {self._escape_html(preview)}
            </div>
        </div>
        """
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_thinking(self, message: str):
        """Append a thinking/progress indicator with blockquote style."""
        html = f"""
        <div style="margin: 4px 0 4px 36px;">
            <div style="background-color: #252526; color: #808080;
                        padding: 6px 10px; border-radius: 4px; font-size: 12px;
                        border-left: 3px solid #6e6e80; font-style: italic;">
                💭 {self._escape_html(message)}
            </div>
        </div>
        """
        self.chat_display.append(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()

    def start_streaming(self):
        """Start streaming mode for assistant response."""
        self._streaming_text = ""
        self._is_streaming = True
        # Store the initial cursor position to update in place
        self._stream_start_position = self.chat_display.textCursor().position()
        # Add an empty assistant message with avatar that will be updated
        html = """
        <div style="margin: 8px 0;">
            <div style="display: inline-flex; align-items: flex-start; gap: 8px;">
                <div style="width: 28px; height: 28px; border-radius: 50%;
                            background-color: #007acc; color: white; font-size: 14px;
                            display: inline-flex; align-items: center; justify-content: center;">A</div>
                <div style="background-color: #2d2d30; border-radius: 12px;
                            padding: 10px 14px; max-width: 85%;
                            color: #d4d4d4; font-size: 13px;">
                    <div id="streaming-content" style="color: #d4d4d4;">▌</div>
                </div>
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._stream_message_start = self.chat_display.textCursor().position()
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_streaming_chunk(self, chunk: str):
        """Append a text chunk during streaming with dark theme."""
        if not self._is_streaming:
            return

        self._streaming_text += chunk
        # Render the full accumulated text so far
        rendered = self._render_markdown(self._streaming_text + "▌")
        html = f"""
        <div style="margin: 8px 0;">
            <div style="display: inline-flex; align-items: flex-start; gap: 8px;">
                <div style="width: 28px; height: 28px; border-radius: 50%;
                            background-color: #007acc; color: white; font-size: 14px;
                            display: inline-flex; align-items: center; justify-content: center;">A</div>
                <div style="background-color: #2d2d30; border-radius: 12px;
                            padding: 10px 14px; max-width: 85%;
                            color: #d4d4d4; font-size: 13px;">
                    <div style="color: #d4d4d4;">{rendered}</div>
                </div>
            </div>
        </div>
        """
        # Replace content from the streaming start position
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._stream_message_start)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(html)

        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def finish_streaming(self):
        """Finish streaming and finalize the message with dark theme."""
        if not self._is_streaming:
            return

        self._is_streaming = False
        # Render final text without cursor
        rendered = self._render_markdown(self._streaming_text)
        html = f"""
        <div style="margin: 8px 0;">
            <div style="display: inline-flex; align-items: flex-start; gap: 8px;">
                <div style="width: 28px; height: 28px; border-radius: 50%;
                            background-color: #007acc; color: white; font-size: 14px;
                            display: inline-flex; align-items: center; justify-content: center;">A</div>
                <div style="background-color: #2d2d30; border-radius: 12px;
                            padding: 10px 14px; max-width: 85%;
                            color: #d4d4d4; font-size: 13px;">
                    <div style="color: #d4d4d4;">{rendered}</div>
                </div>
            </div>
        </div>
        """
        # Replace content from the streaming start position
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._stream_message_start)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(html)

        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._streaming_text = ""

    def set_token_usage(self, usage: dict, limit: int = 200000):
        """Update the token usage indicator in the input bar.

        Args:
            usage: dict with 'input' and 'output' token counts
            limit: maximum context window size (default 200k)
        """
        input_t = usage.get("input", 0)
        output_t = usage.get("output", 0)
        total = input_t + output_t
        remaining = limit - total

        def fmt(n: int) -> str:
            """Format token count as human readable."""
            if n >= 1000:
                return f"{n / 1000:.1f}k"
            return str(n)

        self.token_label.setText(f"{fmt(total)} / {fmt(limit)} · 剩余 {fmt(remaining)}")
