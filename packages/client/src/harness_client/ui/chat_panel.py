"""
Chat panel for displaying conversation - Clean, minimal design.

Design principles:
- No flexbox/grid CSS (QTextBrowser doesn't support it)
- Visual hierarchy: messages prominent, tool activity secondary
- Icon glyphs instead of emoji for consistent rendering
- Chinese UI text matching the app locale
"""

import base64
import logging
from pathlib import Path

import markdown
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPointF, QPropertyAnimation, QEasingCurve, QByteArray
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
    """Get base64-encoded SVG avatar for assistant."""
    global _ASSISTANT_AVATAR_BASE64

    if _ASSISTANT_AVATAR_BASE64 is not None:
        return _ASSISTANT_AVATAR_BASE64

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

    pen = QPen(Qt.PenStyle.NoPen)
    painter.setPen(pen)
    painter.setBrush(QBrush(color))

    margin = 4
    triangle = [
        QPointF(margin + 2, size // 2),
        QPointF(size - margin, margin + 2),
        QPointF(size - margin, size - margin - 2),
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

    pen = QPen(Qt.PenStyle.NoPen)
    painter.setPen(pen)
    painter.setBrush(QBrush(color))

    margin = 5
    painter.drawRect(margin, margin, size - 2 * margin, size - 2 * margin)

    painter.end()
    return QIcon(pixmap)


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    message_sent = pyqtSignal(str)
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._streaming_text = ""
        self._is_streaming = False
        self._setup_ui()

    def _get_font(self) -> QFont:
        """Get a suitable font for the system."""
        font = QFont()
        font.setPointSize(10)
        for family in ["Microsoft YaHei", "Segoe UI", "SimHei", "Arial"]:
            font.setFamily(family)
            if QFontDatabase.families().count(family) > 0 or family in QFontDatabase.families():
                break
        return font

    def _setup_ui(self):
        """Setup UI components with dark theme."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setFont(self._get_font())
        self.chat_display.setPlaceholderText("输入消息开始对话...")
        self.chat_display.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme.PANEL};
                border: none;
                color: {theme.TEXT};
                padding: 16px 20px;
            }}
        """)

        # --- Input bar ---
        input_bar = QWidget()
        input_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.PANEL};
                border-top: 1px solid {theme.BORDER};
            }}
        """)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(10)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息…  (Enter 发送)")
        self.input_field.setFont(self._get_font())
        self.input_field.setMinimumHeight(40)
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.COMPOSER};
                border: 1px solid {theme.BORDER};
                border-radius: 20px;
                padding: 0 16px;
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
                padding: 0px;
            }}
        """)

        # Stop button
        self.stop_btn = GlowButton(glow_color=QColor(theme.DANGER), parent=self)
        self.stop_btn.setIcon(create_stop_icon(18, QColor("white")))
        self.stop_btn.setIconSize(QSize(18, 18))
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setMinimumWidth(38)
        self.stop_btn.setMaximumWidth(38)
        self.stop_btn.setVisible(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.DANGER};
                border: none;
                border-radius: 19px;
            }}
            QPushButton:hover {{
                background-color: {theme.DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #a02015;
            }}
            QPushButton:disabled {{
                background-color: {theme.CHROME};
            }}
        """)

        # Send button
        self.send_btn = GlowButton(glow_color=QColor(theme.ACCENT), parent=self)
        self.send_btn.setIcon(create_play_icon(18, QColor("white")))
        self.send_btn.setIconSize(QSize(18, 18))
        self.send_btn.setMinimumHeight(38)
        self.send_btn.setMinimumWidth(38)
        self.send_btn.setMaximumWidth(38)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT};
                border: none;
                border-radius: 19px;
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

        # Welcome message (Chinese)
        self._append_message(
            "assistant",
            "你好！我是你的 AI 助手，很高兴为你服务。有什么我可以帮助你的吗？",
        )

    def _on_send(self):
        """Handle send button click."""
        text = self.input_field.text().strip()
        if not text:
            return

        self._append_message("user", text)
        self.input_field.clear()
        self.message_sent.emit(text)

    def _on_stop(self):
        """Handle stop button click."""
        self.stop_requested.emit()

    def set_streaming_state(self, is_streaming: bool):
        """Update UI state based on streaming status."""
        self._is_streaming = is_streaming
        self.stop_btn.setVisible(is_streaming)
        self.send_btn.setEnabled(not is_streaming)
        self.input_field.setEnabled(not is_streaming)

    def _on_text_edited(self, text: str):
        """Handle text editing to trigger skill completer."""
        if self.skill_completer.should_complete(text):
            self.skill_completer.setCompletionPrefix(text)
            if self.skill_completer.completionCount() > 0:
                self.skill_completer.complete()

    def set_skills(self, skills: list[dict]) -> None:
        """Update the skill completer with available skills."""
        self.skill_completer.update_skills(skills)

    def _render_markdown(self, text: str) -> str:
        """Render markdown to HTML."""
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

        self._scroll_animation = QPropertyAnimation(scrollbar, QByteArray(b"value"))
        self._scroll_animation.setDuration(300)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(scrollbar.maximum())
        self._scroll_animation.start()

    def _append_message(self, role: str, content: str):
        """
        Append a message to the chat display - clean, minimal layout.

        Layout:
        - User: blue background block, right-aligned text, no avatar
        - Assistant: avatar + content block, left-aligned
        """
        if role not in ["user", "assistant"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid role '{role}', defaulting to 'assistant'")
            role = "assistant"

        theme = get_theme()

        # Render markdown for assistant, escape for user
        if role == "assistant":
            rendered_content = self._render_markdown(content)
        else:
            rendered_content = self._escape_html(content)

        if role == "user":
            # User message: blue block, right-aligned, no avatar
            # Use table with align="right" since QTextBrowser doesn't support text-align on divs
            html = f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin: 12px 20px;">
    <tr>
        <td align="right">
            <div style="display: inline-block; text-align: left; max-width: 80%;
                        background-color: {theme.USER_BUBBLE}; color: #ffffff;
                        padding: 10px 16px; border-radius: 16px;
                        -webkit-user-select: text; user-select: text;
                        font-size: 14px; line-height: 1.6;">
                {rendered_content}
            </div>
        </td>
    </tr>
</table>
"""
        else:
            # Assistant message: avatar + content block
            avatar_base64 = get_assistant_avatar_base64()
            avatar_size = 22  # Smaller, proportional to text size

            if avatar_base64:
                avatar_html = f'<img src="{avatar_base64}" width="{avatar_size}" height="{avatar_size}" style="border-radius: 6px; vertical-align: top;">'
            else:
                avatar_html = f'<span style="display: inline-block; width: {avatar_size}px; height: {avatar_size}px; border-radius: 6px; background-color: {theme.AVATAR_ASSISTANT_BG}; color: white; font-size: 11px; text-align: center; line-height: {avatar_size}px; font-weight: bold;">A</span>'

            html = f"""
<div style="margin: 14px 20px;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td width="{avatar_size + 6}" valign="top">{avatar_html}</td>
            <td valign="top">
                <div style="background-color: {theme.ASSISTANT_BUBBLE}; border-radius: 16px;
                            padding: 10px 14px; color: {theme.TEXT}; line-height: 1.6;
                            font-size: 14px;">
                    {rendered_content}
                </div>
            </td>
        </tr>
    </table>
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
        """
        Append a tool call indicator - subtle thin style.

        Small, no background, thin left border to avoid competing with messages.
        Uses colored dot instead of emoji.
        """
        theme = get_theme()

        # Format arguments preview
        args_items = list(arguments.items())[:3]
        args_preview = ", ".join(f"{k}={repr(v)[:20]}" for k, v in args_items)
        if len(arguments) > 3:
            args_preview += "..."

        html = f"""
<div style="margin: 6px 20px; padding: 6px 12px;
            background-color: {theme.TOOL_THINKING_BG};
            border-left: 2px solid {theme.TOOL_THINKING_BORDER};
            border-radius: 4px;
            color: {theme.TEXT_SUBTLE}; font-size: 11px;">
    <span style="color: {theme.TOOL_THINKING_BORDER};">&#9670; </span>
    <b style="color: {theme.TOOL_THINKING_TEXT}; font-size: 11px;">{self._escape_html(tool_name)}</b>
    <span style="color: {theme.TEXT_SUBTLE};"> called</span>
    <div style="color: {theme.TOOL_THINKING_LIGHT}; font-size: 10px;
                font-style: italic; padding-top: 2px;">
        {self._escape_html(args_preview) if args_preview else 'no arguments'}
    </div>
</div>
"""
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, result: str, success: bool = True):
        """
        Append a tool result indicator - subtle thin style.

        Uses a colored dot glyph instead of emoji. Thin block to avoid
        competing with actual messages.
        """
        theme = get_theme()
        preview = result[:80] + "..." if len(result) > 80 else result

        if success:
            border = theme.TOOL_SUCCESS_BORDER
            icon = "&#10004;"  # ✓
            status_text = "succeeded"
        else:
            border = theme.TOOL_FAILURE_BORDER
            icon = "&#10008;"  # ✗
            status_text = "failed"

        html = f"""
<div style="margin: 6px 20px; padding: 6px 12px;
            background-color: {'transparent' if success else theme.TOOL_FAILURE_BG};
            border-left: 2px solid {border};
            border-radius: 4px;
            color: {theme.TEXT_SUBTLE}; font-size: 11px;">
    <span style="color: {border};">{icon}</span>
    <b style="color: {border}; font-size: 11px;">{self._escape_html(tool_name)}</b>
    <span style="color: {theme.TEXT_SUBTLE};"> {status_text}</span>
    <div style="color: {theme.TEXT_SUBTLE}; font-size: 10px;
                padding-top: 2px;
                font-family: monospace;
                max-height: 60px; overflow: hidden;">
        {self._escape_html(preview)}
    </div>
</div>
"""
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_thinking(self, message: str):
        """
        Append a thinking/progress indicator - minimal thin style.

        Thin, no background, uses a dot glyph instead of emoji.
        """
        theme = get_theme()

        html = f"""
<div style="margin: 6px 20px; padding: 6px 12px;
            color: {theme.TEXT_SUBTLE}; font-size: 11px;">
    <span style="color: {theme.TOOL_THINKING_BORDER};">&#8226;</span>
    {self._escape_html(message)}
</div>
"""
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()

    def set_token_usage(self, usage: dict, limit: int = 200000):
        """Update the token usage indicator in the input bar."""
        input_t = usage.get("input", 0)
        output_t = usage.get("output", 0)
        total = input_t + output_t

        def fmt(n: int) -> str:
            if n >= 1000:
                return f"{n / 1000:.1f}k"
            return str(n)

        # Clean format: "4.3k / 200k"
        self.token_label.setText(f"{fmt(total)} / {fmt(limit)}")
