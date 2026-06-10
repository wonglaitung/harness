"""
Chat panel for displaying conversation - Simplified ChatGPT-style design.

Design principles:
- No flexbox/grid CSS (QTextBrowser doesn't support it)
- Avatar on separate line
- Color-based role distinction
- Markdown-first content rendering
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
        layout.setContentsMargins(12, 12, 12, 12)

        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setFont(self._get_font())
        self.chat_display.setPlaceholderText("Start a conversation...")

        # Input bar container
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

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message... (Enter to send)")
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

        # Stop button
        self.stop_btn = GlowButton(glow_color=QColor(theme.DANGER), parent=self)
        self.stop_btn.setIcon(create_stop_icon(20, QColor("white")))
        self.stop_btn.setIconSize(QSize(20, 20))
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setMinimumWidth(36)
        self.stop_btn.setMaximumWidth(36)
        self.stop_btn.setVisible(False)
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

        # Send button
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
            "Hello! I'm an AI assistant powered by Harness SDK.\n\n"
            "I can help you:\n"
            "- Read and analyze files\n"
            "- Execute commands\n"
            "- Search the web\n"
            "- Manage projects\n\n"
            "Configure MCP servers and skills in the left panel to unlock more features.",
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
        Append a message to the chat display - ChatGPT-style simple layout.

        Layout:
        - User: Blue background block, no avatar
        - Assistant: Avatar image + gray background block
        - Both: Full-width blocks, simple margins
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
            # User message: simple blue block, right-aligned text
            html = f"""
<div style="margin: 12px 0; text-align: right;">
    <div style="display: inline-block; text-align: left; max-width: 85%;
                background-color: {theme.USER_BUBBLE}; color: #ffffff;
                padding: 12px 16px; border-radius: 16px;
                -webkit-user-select: text; user-select: text;">
        {rendered_content}
    </div>
</div>
"""
        else:
            # Assistant message: avatar on separate line + content block
            avatar_base64 = get_assistant_avatar_base64()
            avatar_size = 32

            if avatar_base64:
                avatar_html = f'<img src="{avatar_base64}" width="{avatar_size}" height="{avatar_size}" style="border-radius: 16px; vertical-align: middle;">'
            else:
                avatar_html = f'<span style="display: inline-block; width: {avatar_size}px; height: {avatar_size}px; border-radius: 16px; background-color: {theme.AVATAR_ASSISTANT_BG}; color: white; font-size: 14px; text-align: center; line-height: {avatar_size}px; font-weight: bold;">A</span>'

            # Simple block layout: avatar line, then content
            html = f"""
<div style="margin: 16px 0;">
    <div style="margin-bottom: 8px;">{avatar_html}</div>
    <div style="background-color: {theme.ASSISTANT_BUBBLE}; border-radius: 16px;
                padding: 12px 16px; color: {theme.TEXT}; line-height: 1.6;">
        {rendered_content}
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
        """
        Append a tool call indicator - simplified card style.

        Simple block with purple left border, no complex layout.
        """
        theme = get_theme()

        # Format arguments preview
        args_items = list(arguments.items())[:3]
        args_preview = ", ".join(f"{k}={repr(v)[:20]}" for k, v in args_items)
        if len(arguments) > 3:
            args_preview += "..."

        html = f"""
<div style="margin: 12px 0; padding: 10px 14px;
            background-color: {theme.TOOL_THINKING_BG};
            border-left: 3px solid {theme.TOOL_THINKING_BORDER};
            border-radius: 8px;">
    <div style="color: {theme.TEXT_SUBTLE}; font-size: 12px; margin-bottom: 4px;">
        <span style="color: {theme.TOOL_THINKING_BORDER};">⚡</span>
        Tool <b style="color: {theme.TOOL_THINKING_TEXT};">{self._escape_html(tool_name)}</b> called
    </div>
    <div style="color: {theme.TOOL_THINKING_LIGHT}; font-size: 11px;
                font-style: italic; padding: 6px 8px;
                background: rgba(0,0,0,0.2); border-radius: 4px;">
        {self._escape_html(args_preview) if args_preview else 'no arguments'}
    </div>
</div>
"""
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, result: str, success: bool = True):
        """
        Append a tool result indicator - simplified card style.

        Simple block with green/red left border.
        """
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
<div style="margin: 8px 0; padding: 10px 14px;
            background-color: {bg};
            border-left: 3px solid {border};
            border-radius: 8px;">
    <div style="color: {theme.TEXT_SUBTLE}; font-size: 12px; margin-bottom: 4px;">
        <span style="color: {text_color}; font-weight: bold;">{icon}</span>
        Tool <b style="color: {text_color};">{self._escape_html(tool_name)}</b> {status_text}
    </div>
    <div style="color: {theme.TEXT_SUBTLE}; font-size: 11px;
                padding: 6px 8px; background: rgba(0,0,0,0.2);
                border-radius: 4px; font-family: monospace;
                max-height: 80px; overflow: hidden;">
        {self._escape_html(preview)}
    </div>
</div>
"""
        self.chat_display.append(html)
        self._scroll_to_bottom()

    def append_thinking(self, message: str):
        """
        Append a thinking/progress indicator - simplified style.

        Simple gray block with subtle indicator.
        """
        theme = get_theme()

        html = f"""
<div style="margin: 8px 0; padding: 8px 14px;
            background-color: {theme.CHROME};
            border-left: 2px solid {theme.TOOL_THINKING_BORDER};
            border-radius: 8px;
            color: {theme.TEXT_SUBTLE}; font-size: 12px;">
    💭 {self._escape_html(message)}
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
        remaining = limit - total

        def fmt(n: int) -> str:
            if n >= 1000:
                return f"{n / 1000:.1f}k"
            return str(n)

        self.token_label.setText(f"{fmt(total)} / {fmt(limit)} · {fmt(remaining)} left")
