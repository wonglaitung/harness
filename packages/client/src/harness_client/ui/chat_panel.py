"""
Chat panel for displaying conversation - Hermes Dark Theme Style.
"""

import markdown
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QFontDatabase, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from harness_client.ui.skill_completer import SkillCompleter


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    # Signals
    message_sent = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._streaming_text = ""  # Buffer for streaming text
        self._is_streaming = False
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
        self.input_field.textEdited.connect(self._on_text_edited)

        # Skill completer
        self.skill_completer = SkillCompleter(self)
        self.input_field.setCompleter(self.skill_completer)

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

    def _on_text_edited(self, text: str):
        """Handle text editing to trigger skill completer."""
        if self.skill_completer.should_complete(text):
            # Set prefix for filtering (without the '/')
            self.skill_completer.setCompletionPrefix(text)
            # Show popup manually if needed
            if self.skill_completer.completionCount() > 0:
                self.skill_completer.complete()

    def set_skills(self, skills: list[dict]) -> None:
        """
        Update the skill completer with available skills.

        Args:
            skills: List of dicts with 'name', 'description', 'enabled' keys
        """
        self.skill_completer.update_skills(skills)

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

    def _escape_html(self, text: str) -> str:
        """Escape HTML characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _scroll_to_bottom(self):
        """Scroll chat display to bottom."""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display with dark theme styling."""
        # Render markdown for assistant messages
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message - right aligned with table for QTextBrowser compatibility
            # QTextBrowser doesn't support inline-block, so we use table layout
            html = f"""
            <table width="100%" style="margin: 8px 0;">
                <tr>
                    <td width="25%"></td>
                    <td width="75%" align="right">
                        <span style="background-color: #1e4a6d; color: #ffffff;
                                     font-size: 13px; padding: 8px 12px;
                                     border-radius: 12px;">
                            {rendered_content}
                        </span>
                    </td>
                </tr>
            </table>
            """
        else:
            # Assistant message with avatar and gray bubble, left-aligned
            html = f"""
            <div style="margin: 12px 0;">
                <div style="display: inline-flex; align-items: flex-start; gap: 10px;">
                    <div style="width: 32px; height: 32px; border-radius: 50%;
                                background-color: #007acc; color: white; font-size: 16px;
                                display: inline-flex; align-items: center; justify-content: center;
                                flex-shrink: 0;">A</div>
                    <div style="background-color: #2d2d30; border-radius: 16px;
                                padding: 10px 16px; max-width: 85%;
                                color: #d4d4d4; font-size: 13px; line-height: 1.5;">
                        <div style="color: #d4d4d4;">{rendered_content}</div>
                    </div>
                </div>
            </div>
            """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_assistant_message(self, content: str):
        """Append an assistant message."""
        self._append_message("assistant", content)

    def append_user_message(self, content: str):
        """Append a user message."""
        self._append_message("user", content)

    def append_tool_call(self, tool_name: str, arguments: dict):
        """Append a tool call indicator with dark theme card style - matching Athlon Agent style."""
        # Format arguments preview (first 3 args)
        args_preview = ", ".join(f"{k}={repr(v)[:20]}" for k, v in list(arguments.items())[:3])
        if len(arguments) > 3:
            args_preview += "..."

        html = f"""
        <div style="margin: 8px 0 4px 36px;">
            <div style="background-color: #1a1a2e; color: #58a6ff;
                        padding: 8px 12px; border-radius: 8px; font-size: 12px;
                        border: 1px solid #264f78;">
                <div style="margin-bottom: 4px;">
                    <span style="color: #808080;">Tool</span>
                    <b style="color: #58a6ff;">'{self._escape_html(tool_name)}'</b>
                    <span style="color: #808080;">called</span>
                </div>
                <div style="color: #808080; font-size: 11px; font-style: italic;">
                    {self._escape_html(args_preview) if args_preview else 'no arguments'}
                </div>
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, result: str, success: bool = True):
        """Append a tool result indicator with expandable details - matching Athlon Agent style."""
        preview = result[:80] + "..." if len(result) > 80 else result

        if success:
            bg_color = "#1a3a2a"
            border_color = "#2ea043"
            text_color = "#3fb950"
            icon = "✓"
            status_text = "succeeded"
        else:
            bg_color = "#3a1a1a"
            border_color = "#da3633"
            text_color = "#f85149"
            icon = "✗"
            status_text = "failed"

        html = f"""
        <div style="margin: 4px 0 8px 36px;">
            <div style="background-color: {bg_color}; color: {text_color};
                        padding: 8px 12px; border-radius: 8px; font-size: 12px;
                        border: 1px solid {border_color};">
                <div style="margin-bottom: 4px;">
                    <span style="color: {text_color};">{icon}</span>
                    Tool <b>'{self._escape_html(tool_name)}'</b> {status_text}.
                </div>
                <div style="color: #808080; font-size: 11px; margin-top: 4px;
                            padding: 6px 8px; background-color: rgba(0,0,0,0.2);
                            border-radius: 4px; font-family: monospace;
                            max-height: 60px; overflow: hidden;">
                    {self._escape_html(preview)}
                </div>
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_thinking(self, message: str):
        """Append a thinking/progress indicator with subtle blockquote style."""
        html = f"""
        <div style="margin: 4px 0 4px 36px;">
            <div style="background-color: #1e1e1e; color: #6e7681;
                        padding: 6px 12px; border-radius: 4px; font-size: 12px;
                        border-left: 2px solid #3e3e42;">
                💭 {self._escape_html(message)}
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()

    def start_streaming(self):
        """Start streaming mode for assistant response."""
        self._streaming_text = ""
        self._is_streaming = True
        # Add placeholder with cursor
        self._append_message("assistant", "▌")
        # Store position for updates
        self._stream_cursor = self.chat_display.textCursor()
        self._stream_cursor.movePosition(QTextCursor.MoveOperation.End)

    def append_streaming_chunk(self, chunk: str):
        """Append a text chunk during streaming."""
        if not self._is_streaming:
            return

        self._streaming_text += chunk
        # Update the last message in place
        rendered = self._render_markdown(self._streaming_text + "▌")

        # Move cursor to end and select last line, then replace
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(rendered)
        self._scroll_to_bottom()

    def finish_streaming(self):
        """Finish streaming and finalize the message."""
        if not self._is_streaming:
            return

        self._is_streaming = False
        # Render final text without cursor
        rendered = self._render_markdown(self._streaming_text)

        # Replace last block with final content
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(rendered)
        self._scroll_to_bottom()
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
