"""
Chat panel for displaying conversation - Athlon-inspired dark theme style.
"""

import base64
import logging
from pathlib import Path

import markdown
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPointF, QPropertyAnimation, QEasingCurve, QByteArray
from PyQt6.QtGui import QFont, QFontDatabase, QTextCursor, QIcon, QPainter, QColor, QPen, QBrush, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from harness_client.ui.interactive import GlowButton

from harness_client.themes import get_theme
from harness_client.ui.skill_completer import SkillCompleter


# Cache for avatar base64 data
_ASSISTANT_AVATAR_BASE64: str | None = None


def get_assistant_avatar_base64() -> str:
    """Get base64-encoded SVG avatar for assistant.

    Returns base64 data URI string, or empty string if SVG not found.
    """
    global _ASSISTANT_AVATAR_BASE64

    if _ASSISTANT_AVATAR_BASE64 is not None:
        return _ASSISTANT_AVATAR_BASE64

    # Find SVG icon path
    icon_path = Path(__file__).parent.parent.parent.parent / "resources" / "icons" / "icon.svg"

    if icon_path.exists():
        svg_content = icon_path.read_bytes()
        b64 = base64.b64encode(svg_content).decode("utf-8")
        _ASSISTANT_AVATAR_BASE64 = f"data:image/svg+xml;base64,{b64}"
    else:
        _ASSISTANT_AVATAR_BASE64 = ""

    return _ASSISTANT_AVATAR_BASE64


def create_play_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a play/arrow icon (filled triangle pointing right)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw filled triangle
    pen = QPen(Qt.PenStyle.NoPen)
    painter.setPen(pen)
    painter.setBrush(QBrush(color))

    # Triangle points: left center, top-right, bottom-right
    margin = 4
    triangle = [
        QPointF(margin + 2, size // 2),           # Left center (arrow tip)
        QPointF(size - margin, margin + 2),        # Top right
        QPointF(size - margin, size - margin - 2), # Bottom right
    ]
    polygon = QPolygonF(triangle)
    painter.drawPolygon(polygon)

    painter.end()
    return QIcon(pixmap)


def create_stop_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a stop icon (filled square)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw filled square
    pen = QPen(Qt.PenStyle.NoPen)
    painter.setPen(pen)
    painter.setBrush(QBrush(color))

    margin = 5
    painter.drawRect(margin, margin, size - 2 * margin, size - 2 * margin)

    painter.end()
    return QIcon(pixmap)


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    # Signals
    message_sent = pyqtSignal(str)
    stop_requested = pyqtSignal()  # New signal for stop button

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
                border-radius: {theme.RADIUS_LG};
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
                border-radius: {theme.RADIUS_MD};
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

        # Stop button - icon only, hidden by default, with danger glow
        self.stop_btn = GlowButton(glow_color=QColor(theme.DANGER), parent=self)
        self.stop_btn.setIcon(create_stop_icon(20, QColor("white")))
        self.stop_btn.setIconSize(QSize(20, 20))
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setMinimumWidth(36)
        self.stop_btn.setMaximumWidth(36)
        self.stop_btn.setVisible(False)  # Hidden by default
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.DANGER};
                border: none;
                border-radius: {theme.RADIUS_MD};
            }}
            QPushButton:hover {{
                background-color: {theme.DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #a02015;
            }}
        """)

        # Send button - icon only (play arrow) with accent glow
        self.send_btn = GlowButton(glow_color=QColor(theme.ACCENT), parent=self)
        self.send_btn.setIcon(create_play_icon(20, QColor("white")))
        self.send_btn.setIconSize(QSize(20, 20))
        self.send_btn.setMinimumHeight(36)
        self.send_btn.setMinimumWidth(36)
        self.send_btn.setMaximumWidth(36)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT};
                border: none;
                border-radius: {theme.RADIUS_MD};
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #1a47b8;
            }}
            QPushButton:disabled {{
                background-color: {theme.CHROME};
            }}
        """)

        input_layout.addWidget(self.input_field, stretch=1)
        input_layout.addWidget(self.token_label)
        input_layout.addWidget(self.stop_btn)
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

    def _on_stop(self):
        """Handle stop button click."""
        self.stop_requested.emit()

    def set_streaming_state(self, is_streaming: bool):
        """Update UI state based on streaming status.

        Args:
            is_streaming: True if agent is generating response
        """
        self._is_streaming = is_streaming
        self.stop_btn.setVisible(is_streaming)
        self.send_btn.setEnabled(not is_streaming)
        self.input_field.setEnabled(not is_streaming)

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
        """Scroll chat display to bottom with smooth animation."""
        scrollbar = self.chat_display.verticalScrollBar()

        # Use smooth scroll animation
        self._scroll_animation = QPropertyAnimation(scrollbar, QByteArray(b"value"))
        self._scroll_animation.setDuration(300)  # 300ms smooth scroll
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(scrollbar.maximum())
        self._scroll_animation.start()

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display - Athlon-inspired bubble style."""
        # 确保角色值有效（防御性编程）
        if role not in ["user", "assistant"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid role '{role}', defaulting to 'assistant'")
            role = "assistant"

        theme = get_theme()

        # Render markdown for assistant messages
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message - right aligned, blue bubble
            # Use simple div layout for better text selection and responsive width
            html = f"""
            <div style="margin: 8px 0; text-align: right;">
                <div style="display: inline-block;
                            text-align: left;
                            max-width: 85%;
                            background-color: {theme.USER_BUBBLE};
                            color: #ffffff;
                            font-size: 14px;
                            padding: 10px 16px;
                            border-radius: 16px;
                            -webkit-user-select: text;
                            user-select: text;
                            cursor: text;">
                    {rendered_content}
                </div>
            </div>
            """
        else:
            # Assistant message with avatar and gray bubble, left-aligned
            avatar_base64 = get_assistant_avatar_base64()
            avatar_width = 40
            avatar_indent = avatar_width + 12  # 52px indent for content

            if avatar_base64:
                avatar_html = f'<img src="{avatar_base64}" width="{avatar_width}" height="{avatar_width}" style="border-radius: 20px;">'
            else:
                # Fallback to letter avatar
                avatar_html = f'''<div style="width: {avatar_width}px; height: {avatar_width}px; border-radius: 20px;
                            background-color: {theme.AVATAR_ASSISTANT_BG}; color: white; font-size: 18px;
                            text-align: center; line-height: {avatar_width}px; font-weight: bold;">A</div>'''

            html = f"""
            <div style="margin: 12px 0;">
                <div style="display: inline-block; vertical-align: top;">
                    {avatar_html}
                </div>
                <div style="display: inline-block; vertical-align: top;
                            margin-left: 12px; max-width: calc(100% - {avatar_indent}px);">
                    <div style="background-color: {theme.ASSISTANT_BUBBLE};
                                border-radius: 16px;
                                padding: 12px 16px;
                                color: {theme.TEXT}; font-size: 14px; line-height: 1.5;">
                        {rendered_content}
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

        # Indent aligns with avatar + 12px spacing (52px total)
        html = f"""
        <div style="margin: 8px 0 4px 52px;">
            <div style="background-color: {theme.TOOL_THINKING_BG};
                        border: 2px solid {theme.TOOL_THINKING_BORDER};
                        border-radius: 16px;
                        padding: 12px 16px;
                        max-width: calc(100% - 52px);
                        box-shadow: 0 0 8px rgba(109, 40, 217, 0.2);">
                <!-- Header row with spinner indicator -->
                <div style="margin-bottom: 8px;">
                    <span style="color: {theme.TOOL_THINKING_BORDER}; font-size: 12px;">⚡</span>
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
            glow = f"box-shadow: 0 0 8px rgba(5, 150, 105, 0.3);"
        else:
            bg = theme.TOOL_FAILURE_BG
            border = theme.TOOL_FAILURE_BORDER
            text_color = theme.TOOL_FAILURE_TEXT
            icon = "✗"
            status_text = "failed"
            glow = f"box-shadow: 0 0 8px rgba(225, 29, 72, 0.3);"

        # Indent aligns with avatar + 12px spacing (52px total)
        html = f"""
        <div style="margin: 4px 0 8px 52px;">
            <div style="background-color: {bg};
                        border: 2px solid {border};
                        border-radius: 16px;
                        padding: 12px 16px;
                        max-width: calc(100% - 52px);
                        {glow}">
                <!-- Status header -->
                <div style="margin-bottom: 6px;">
                    <span style="color: {text_color}; font-size: 14px; font-weight: bold;">{icon}</span>
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
        # Indent aligns with avatar + 12px spacing (52px total)
        html = f"""
        <div style="margin: 4px 0 4px 52px;">
            <div style="background-color: {theme.CHROME};
                        color: {theme.TEXT_SUBTLE};
                        padding: 8px 12px; border-radius: 8px; font-size: 12px;
                        border-left: 2px solid {theme.TOOL_THINKING_BORDER};
                        max-width: calc(100% - 52px);">
                💭 {self._escape_html(message)}
            </div>
        </div>
        """
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()

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
