"""
Chat panel for displaying conversation - Athlon-inspired dark theme style.
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

from harness_client.themes import get_theme
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
        theme = get_theme()
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
        input_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.PANEL_ALT};
                border-top: 1px solid {theme.BORDER};
                border-radius: 12px;
                padding: 8px;
            }}
        """)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(8)

        # Input field - dark theme
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息... (Enter 发送)")
        self.input_field.setFont(self._get_font())
        self.input_field.setMinimumHeight(36)
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.CHROME};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {theme.TEXT};
            }}
            QLineEdit:focus {{
                border-color: {theme.ACCENT};
            }}
        """)
        self.input_field.returnPressed.connect(self._on_send)
        self.input_field.textEdited.connect(self._on_text_edited)

        # Skill completer
        self.skill_completer = SkillCompleter(self)
        self.input_field.setCompleter(self.skill_completer)

        # Token usage label
        self.token_label = QLabel("0 / 200k")
        self.token_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
                padding: 0 4px;
            }}
        """)

        # Send button - primary blue
        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumHeight(36)
        self.send_btn.setMinimumWidth(80)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #1a47b8;
            }}
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
        """Append a message to the chat display - Athlon-inspired bubble style."""
        theme = get_theme()

        # Render markdown for assistant messages
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message - right aligned, blue bubble
            html = f"""
            <table width="100%" style="margin: 8px 0;">
                <tr>
                    <td width="25%"></td>
                    <td width="75%" align="right">
                        <span style="background-color: {theme.USER_BUBBLE};
                                     color: #ffffff;
                                     font-size: 14px; padding: 10px 16px;
                                     border-radius: 16px;
                                     display: inline-block;
                                     max-width: 100%;
                                     text-align: left;">
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
                <div style="display: inline-flex; align-items: flex-start; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 20px;
                                background-color: {theme.ACCENT}; color: white; font-size: 18px;
                                display: inline-flex; align-items: center; justify-content: center;
                                flex-shrink: 0; font-weight: bold;">A</div>
                    <div style="background-color: {theme.ASSISTANT_BUBBLE};
                                border-radius: 16px;
                                padding: 12px 16px; max-width: 85%;
                                color: {theme.TEXT}; font-size: 14px; line-height: 1.5;">
                        <div style="color: {theme.TEXT};">{rendered_content}</div>
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
        """Append a tool call indicator - Athlon-inspired purple thinking style."""
        theme = get_theme()

        # Format arguments preview (first 3 args)
        args_items = list(arguments.items())[:3]
        args_preview = ", ".join(f"{k}={repr(v)[:20]}" for k, v in args_items)
        if len(arguments) > 3:
            args_preview += "..."

        html = f"""
        <div style="margin: 8px 0 4px 40px;">
            <div style="background-color: {theme.TOOL_THINKING_BG};
                        border: 1px solid {theme.TOOL_THINKING_BORDER};
                        border-radius: 16px;
                        padding: 12px 16px;
                        max-width: 640px;">
                <!-- Header row -->
                <div style="margin-bottom: 8px;">
                    <span style="color: {theme.TEXT_SUBTLE}; font-size: 12px;">Tool</span>
                    <span style="color: {theme.TOOL_THINKING_TEXT}; font-weight: bold; font-size: 13px;">
                        '{self._escape_html(tool_name)}'
                    </span>
                    <span style="color: {theme.TEXT_SUBTLE}; font-size: 12px;">called</span>
                </div>
                <!-- Arguments preview -->
                <div style="color: {theme.TOOL_THINKING_LIGHT}; font-size: 11px;
                            font-style: italic;
                            padding: 6px 8px; background: rgba(0,0,0,0.2);
                            border-radius: 6px;">
                    {self._escape_html(args_preview) if args_preview else 'no arguments'}
                </div>
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, result: str, success: bool = True):
        """Append a tool result indicator - Athlon-inspired success/failure cards."""
        theme = get_theme()
        preview = result[:80] + "..." if len(result) > 80 else result

        if success:
            bg = theme.TOOL_SUCCESS_BG
            border = theme.TOOL_SUCCESS_BORDER
            text_color = theme.TOOL_SUCCESS_TEXT
            icon = "✓"
            status_text = "succeeded"
        else:
            bg = theme.TOOL_FAILURE_BG
            border = theme.TOOL_FAILURE_BORDER
            text_color = theme.TOOL_FAILURE_TEXT
            icon = "✗"
            status_text = "failed"

        html = f"""
        <div style="margin: 4px 0 8px 40px;">
            <div style="background-color: {bg};
                        border: 1px solid {border};
                        border-radius: 16px;
                        padding: 12px 16px;
                        max-width: 640px;">
                <!-- Status header -->
                <div style="margin-bottom: 6px;">
                    <span style="color: {text_color}; font-size: 14px;">{icon}</span>
                    <span style="color: {theme.TEXT_SUBTLE}; font-size: 12px;">Tool</span>
                    <span style="color: {text_color}; font-weight: bold; font-size: 13px;">
                        '{self._escape_html(tool_name)}'
                    </span>
                    <span style="color: {text_color}; font-size: 12px; font-weight: bold;">
                        {status_text}
                    </span>
                </div>
                <!-- Result preview -->
                <div style="color: {theme.TEXT_SUBTLE}; font-size: 11px;
                            padding: 6px 8px; background: rgba(0,0,0,0.2);
                            border-radius: 6px; font-family: monospace;
                            max-height: 80px; overflow: hidden;">
                    {self._escape_html(preview)}
                </div>
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_thinking(self, message: str):
        """Append a thinking/progress indicator - Athlon-inspired subtle style."""
        theme = get_theme()
        html = f"""
        <div style="margin: 4px 0 4px 40px;">
            <div style="background-color: {theme.CHROME};
                        color: {theme.TEXT_SUBTLE};
                        padding: 8px 12px; border-radius: 8px; font-size: 12px;
                        border-left: 2px solid {theme.TOOL_THINKING_BORDER};">
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
        # Clear chat display to prepare for streaming
        # We'll build the message incrementally
        # Store the position BEFORE adding the placeholder
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._stream_start_position = cursor.position()
        # Add placeholder with cursor
        self._append_message("assistant", "▌")

    def append_streaming_chunk(self, chunk: str):
        """Append a text chunk during streaming."""
        if not self._is_streaming:
            return

        self._streaming_text += chunk
        # Update the last message in place
        rendered = self._render_markdown(self._streaming_text + "▌")

        # Select from saved start position to end, then replace
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._stream_start_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
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

        # Select from saved start position to end, then replace
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._stream_start_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
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
