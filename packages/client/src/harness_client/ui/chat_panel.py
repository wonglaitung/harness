"""
Chat panel for displaying conversation - Clean, minimal design.

Design principles:
- Custom painted message bubbles with proper rounded corners (QPainter.drawRoundedRect)
- Visual hierarchy: messages prominent, tool activity secondary
- Icon glyphs instead of emoji for consistent rendering
- Chinese UI text matching the app locale
"""

import base64
import logging
from pathlib import Path

import markdown
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPointF, QPropertyAnimation, QEasingCurve, QByteArray, QRectF, QEvent
from PyQt6.QtGui import QFont, QFontDatabase, QIcon, QPainter, QColor, QPen, QBrush, QPixmap, QPolygonF, QFontMetrics, QTextDocument, QAbstractTextDocumentLayout
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
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


def create_clear_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a clear/cancel X icon - simple and clean."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color, 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    margin = 5
    # Simple X mark
    painter.drawLine(margin, margin, size - margin, size - margin)
    painter.drawLine(size - margin, margin, margin, size - margin)

    painter.end()
    return QIcon(pixmap)


class MessageBubble(QWidget):
    """
    Custom painted message bubble with rounded corners.

    Uses QPainter.drawRoundedRect() since QTextBrowser HTML
    engine doesn't support border-radius CSS property.
    For assistant messages, uses QTextDocument for Markdown rendering.
    """

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
        self._role = role
        self._border_radius = 12.0
        self._padding_h = 14
        self._padding_v = 10
        self._max_width = 450

        # For assistant: render markdown to HTML, use QTextDocument
        self._text_document = None
        if role == "assistant":
            html = self._render_markdown(content)
            self._text_document = QTextDocument()
            self._text_document.setHtml(html)
            self._text_document.setTextWidth(self._max_width - 2 * self._padding_h)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._calculate_size()

    def _get_font(self) -> QFont:
        """Get a suitable font for the system."""
        font = QFont()
        font.setPointSize(10)
        for family in ["Microsoft YaHei", "Segoe UI", "SimHei", "Arial"]:
            font.setFamily(family)
            if QFontDatabase.families().count(family) > 0 or family in QFontDatabase.families():
                break
        return font

    def _render_markdown(self, text: str) -> str:
        """Render markdown to HTML with basic styling."""
        extensions = ["fenced_code", "codehilite", "tables", "nl2br"]
        html = markdown.markdown(text, extensions=extensions)

        # Add inline styles for code blocks and other elements
        # Note: QTextDocument has limited CSS support, use inline styles
        theme = get_theme()
        styled_html = f"""
        <style>
            body {{
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 10pt;
            }}
            p {{
                color: {theme.TEXT};
            }}
            span {{
                color: {theme.TEXT};
            }}
            code {{
                background-color: {theme.CODE_BACKGROUND};
                color: {theme.CODE_FOREGROUND};
                padding: 2px 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }}
            pre {{
                background-color: {theme.CODE_BACKGROUND};
                color: {theme.CODE_FOREGROUND};
                padding: 10px;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            a {{
                color: {theme.ACCENT_LIGHT};
            }}
            table {{
                border-collapse: collapse;
                margin: 8px 0;
            }}
            th, td {{
                border: 1px solid {theme.BORDER};
                padding: 6px 12px;
            }}
            th {{
                background-color: {theme.CHROME};
                font-weight: bold;
            }}
            td {{
                background-color: transparent;
            }}
            ul, ol {{
                margin-left: 20px;
                padding-left: 0;
            }}
            li {{
                margin: 4px 0;
            }}
        </style>
        <div style="color: {theme.TEXT};">
        {html}
        </div>
        """
        return styled_html

    def _calculate_size(self):
        """Calculate widget size based on content."""
        if self._text_document:
            # Use QTextDocument for accurate size
            self._text_document.setTextWidth(self._max_width - 2 * self._padding_h)
            doc_height = self._text_document.size().height()
            ideal_width = self._text_document.idealWidth()
            self._preferred_width = int(min(ideal_width + 2 * self._padding_h, self._max_width))
            self._preferred_height = int(doc_height + 2 * self._padding_v + 4)
        else:
            # User message: simple text calculation
            font = self._get_font()
            fm = QFontMetrics(font)

            lines = self._content.split('\n')
            total_height = 0
            max_line_width = 0

            for line in lines:
                if line.strip():
                    text_rect = fm.boundingRect(
                        0, 0, self._max_width - 2 * self._padding_h, 1000,
                        Qt.TextFlag.TextWordWrap,
                        line
                    )
                    total_height += text_rect.height()
                    max_line_width = max(max_line_width, text_rect.width())
                else:
                    total_height += fm.height() // 2

            min_width = 60
            self._text_width = max(max_line_width, min_width - 2 * self._padding_h)
            self._text_height = max(total_height, fm.height())

            self._preferred_width = int(min(self._text_width + 2 * self._padding_h, self._max_width))
            self._preferred_height = int(self._text_height + 2 * self._padding_v + 4)

    def sizeHint(self) -> QSize:
        return QSize(self._preferred_width, self._preferred_height)

    def minimumSizeHint(self) -> QSize:
        return QSize(50, 30)

    def paintEvent(self, event):
        """Paint the rounded bubble."""
        theme = get_theme()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Bubble colors
        if self._role == "user":
            bg_color = QColor(theme.USER_BUBBLE)
            text_color = QColor("#ffffff")
        else:
            bg_color = QColor(theme.ASSISTANT_BUBBLE)
            text_color = QColor(theme.TEXT)

        # Draw rounded rectangle
        rect = QRectF(0, 0, self.width() - 1, self.height() - 1)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, self._border_radius, self._border_radius)

        # Draw content
        if self._text_document:
            # Render QTextDocument
            painter.translate(self._padding_h, self._padding_v)
            self._text_document.drawContents(painter, QRectF(0, 0, self.width() - 2 * self._padding_h, self.height() - 2 * self._padding_v))
        else:
            # Draw plain text for user
            painter.setPen(text_color)
            painter.setFont(self._get_font())

            text_rect = QRectF(
                self._padding_h,
                self._padding_v,
                self.width() - 2 * self._padding_h,
                self.height() - 2 * self._padding_v
            )
            painter.drawText(
                text_rect,
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                self._content
            )

        painter.end()


class AvatarWidget(QWidget):
    """Simple avatar widget with rounded corners."""

    def __init__(self, size: int = 24, parent: QWidget | None = None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded background
        rect = QRectF(0, 0, self._size - 1, self._size - 1)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.AVATAR_ASSISTANT_BG)))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        # Draw "A" letter
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "A")

        painter.end()


class MessageRow(QWidget):
    """A row containing a message bubble with proper alignment."""

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
        self._role = role
        self._setup_ui()

    def _setup_ui(self):
        theme = get_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(0)

        # Create bubble
        bubble = MessageBubble(self._content, self._role)

        if self._role == "user":
            # Right-aligned: stretch on left, bubble on right
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addSpacing(4)
        else:
            # Left-aligned: avatar, bubble, stretch
            avatar = AvatarWidget(24)
            layout.addWidget(avatar)
            layout.addSpacing(6)
            layout.addWidget(bubble)
            layout.addStretch()

        self.setStyleSheet(f"background-color: {theme.PANEL};")


class ToolIndicator(QWidget):
    """Visual indicator for tool calls/results with rounded corners."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._border_radius = 6.0

    def _get_font(self) -> QFont:
        font = QFont()
        font.setPointSize(9)
        for family in ["Microsoft YaHei", "Segoe UI", "SimHei", "Arial"]:
            font.setFamily(family)
            break
        return font


class ToolCallIndicator(ToolIndicator):
    """Visual indicator for tool calls."""

    def __init__(
        self,
        tool_name: str,
        arguments: dict,
        parent: QWidget | None = None,
    ):
        self._tool_name = tool_name
        self._arguments = arguments
        super().__init__(parent)
        self._calculate_size()

    def _calculate_size(self):
        args_items = list(self._arguments.items())[:3]
        self._args_preview = ", ".join(f"{k}={repr(v)[:20]}" for k, v in args_items)
        if len(self._arguments) > 3:
            self._args_preview += "..."

        fm = QFontMetrics(self._get_font())
        text = f"▶ {self._tool_name} {self._args_preview}"
        text_width = fm.horizontalAdvance(text)
        self._preferred_width = min(text_width + 48, 400)
        self._preferred_height = 28
        self.setFixedHeight(28)

    def sizeHint(self) -> QSize:
        return QSize(self._preferred_width, 28)

    def paintEvent(self, event):
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        rect = QRectF(32, 0, self.width() - 33, 27)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.TOOL_THINKING_BG)))
        painter.drawRoundedRect(rect, self._border_radius, self._border_radius)

        # Left border
        painter.setPen(QPen(QColor(theme.TOOL_THINKING_BORDER), 3))
        painter.drawLine(32, 2, 32, 26)

        # Text
        text = f"▶ {self._tool_name} {self._args_preview}"
        painter.setPen(QColor(theme.TEXT_SUBTLE))
        painter.setFont(self._get_font())
        painter.drawText(44, 18, text)

        painter.end()


class ToolResultIndicator(ToolIndicator):
    """Visual indicator for tool results."""

    def __init__(
        self,
        tool_name: str,
        success: bool = True,
        parent: QWidget | None = None,
    ):
        self._tool_name = tool_name
        self._success = success
        super().__init__(parent)
        self.setFixedHeight(28)

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._get_font())
        text = f"{'✓' if self._success else '✗'} {self._tool_name}"
        width = fm.horizontalAdvance(text) + 48
        return QSize(min(width, 200), 28)

    def paintEvent(self, event):
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = "transparent" if self._success else theme.TOOL_FAILURE_BG
        border_color = theme.TOOL_SUCCESS_BORDER if self._success else theme.TOOL_FAILURE_BORDER

        rect = QRectF(32, 0, self.width() - 33, 27)
        if bg_color != "transparent":
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QBrush(QColor(bg_color)))
            painter.drawRoundedRect(rect, self._border_radius, self._border_radius)

        # Left border
        painter.setPen(QPen(QColor(border_color), 3))
        painter.drawLine(32, 2, 32, 26)

        # Icon and text
        icon = "✓" if self._success else "✗"
        painter.setPen(QColor(border_color))
        painter.setFont(self._get_font())
        painter.drawText(44, 18, f"{icon} {self._tool_name}")

        painter.end()


class ThinkingIndicator(QWidget):
    """Visual indicator for thinking/progress."""

    def __init__(self, message: str, parent: QWidget | None = None):
        self._message = message
        super().__init__(parent)
        self.setFixedHeight(24)

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._get_font())
        width = fm.horizontalAdvance(self._message) + 48
        return QSize(width, 24)

    def _get_font(self) -> QFont:
        font = QFont()
        font.setPointSize(9)
        font.setItalic(True)
        return font

    def paintEvent(self, event):
        theme = get_theme()
        painter = QPainter(self)

        painter.setFont(self._get_font())
        painter.setPen(QColor(theme.TEXT_SUBTLE))
        painter.drawText(32, 16, self._message)

        painter.end()


class MessagesContainer(QWidget):
    """Container widget for all messages with scroll support."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 16, 0, 16)
        self._layout.setSpacing(0)
        self._layout.addStretch()

        theme = get_theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")

    def add_message(self, content: str, role: str):
        """Add a message bubble."""
        row = MessageRow(content, role)
        self._layout.insertWidget(self._layout.count() - 1, row)

    def add_tool_call(self, tool_name: str, arguments: dict):
        """Add a tool call indicator."""
        indicator = ToolCallIndicator(tool_name, arguments)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(indicator)
        layout.addStretch()
        self._layout.insertWidget(self._layout.count() - 1, container)

    def add_tool_result(self, tool_name: str, success: bool = True):
        """Add a tool result indicator."""
        indicator = ToolResultIndicator(tool_name, success)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(indicator)
        layout.addStretch()
        self._layout.insertWidget(self._layout.count() - 1, container)

    def add_thinking(self, message: str):
        """Add a thinking indicator."""
        indicator = ThinkingIndicator(message)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(indicator)
        layout.addStretch()
        self._layout.insertWidget(self._layout.count() - 1, container)

    def clear(self):
        """Clear all messages."""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ChatPanel(QWidget):
    """Panel for displaying chat messages and input."""

    message_sent = pyqtSignal(str)
    stop_requested = pyqtSignal()
    clear_chat_requested = pyqtSignal()

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

        # Chat header bar with clear button
        header_bar = QWidget()
        header_bar_layout = QHBoxLayout(header_bar)
        header_bar_layout.setContentsMargins(16, 12, 16, 8)
        header_bar_layout.setSpacing(0)
        header_bar_layout.addStretch()

        # Clear context button
        clear_btn = QPushButton("清空上下文")
        clear_btn.setIcon(create_clear_icon(16, QColor(theme.TEXT_SUBTLE)))
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.TEXT_SUBTLE};
            }}
        """)
        clear_btn.clicked.connect(lambda: self.clear_chat_requested.emit())
        header_bar_layout.addWidget(clear_btn)

        layout.addWidget(header_bar)

        # Chat display area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.PANEL};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme.TEXT_SUBTLE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        # Messages container
        self.messages_container = MessagesContainer()
        scroll_area.setWidget(self.messages_container)

        # --- Input bar ---
        input_bar = QWidget()
        input_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.PANEL};
                border-top: 1px solid {theme.BORDER};
            }}
        """)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 8, 16, 8)
        input_layout.setSpacing(10)

        # Multi-line input field (QTextEdit)
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息…  (Enter 发送, Shift+Enter 换行)")
        self.input_field.setFont(self._get_font())
        self.input_field.setMinimumHeight(40)
        self.input_field.setMaximumHeight(72)  # ~3 lines
        self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_field.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.COMPOSER};
                border: 1px solid {theme.BORDER};
                border-radius: 12px;
                padding: 8px 12px;
                color: {theme.TEXT};
            }}
            QTextEdit:focus {{
                border-color: {theme.ACCENT};
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.BORDER};
                border-radius: 3px;
                min-height: 20px;
            }}
        """)
        # Install event filter for Enter/Shift+Enter handling
        self.input_field.installEventFilter(self)

        # Skill completer (for QLineEdit compatibility, we'll handle manually)
        self.skill_completer = SkillCompleter(self)

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

        layout.addWidget(scroll_area, stretch=1)
        layout.addWidget(input_bar)

        # Store scroll area for scrolling
        self._scroll_area = scroll_area

        # Welcome message (Chinese)
        self.messages_container.add_message(
            "你好！我是你的 AI 助手，很高兴为你服务。有什么我可以帮助你的吗？",
            "assistant",
        )

    def _on_send(self):
        """Handle send button click."""
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        self.messages_container.add_message(text, "user")
        self.input_field.clear()
        self._scroll_to_bottom()
        self.message_sent.emit(text)

    def _on_stop(self):
        """Handle stop button click."""
        self.stop_requested.emit()

    def eventFilter(self, obj, event):
        """Handle Enter/Shift+Enter for multi-line input."""
        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            key_event = event
            # Enter without Shift: send message
            if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                if not key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self._on_send()
                    return True  # Consume the event
                # Shift+Enter: allow default behavior (insert newline)
        return super().eventFilter(obj, event)

    def set_streaming_state(self, is_streaming: bool):
        """Update UI state based on streaming status."""
        self._is_streaming = is_streaming
        self.stop_btn.setVisible(is_streaming)
        self.send_btn.setEnabled(not is_streaming)
        self.input_field.setEnabled(not is_streaming)

    def set_skills(self, skills: list[dict]) -> None:
        """Update the skill completer with available skills."""
        self.skill_completer.update_skills(skills)

    def _scroll_to_bottom(self):
        """Scroll chat display to bottom with smooth animation."""
        # Force layout update first
        self.messages_container.updateGeometry()
        self._scroll_area.ensureVisible(0, self.messages_container.height())

        scrollbar = self._scroll_area.verticalScrollBar()

        # Use QTimer to ensure scroll happens after layout update
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._do_scroll(scrollbar))

    def _do_scroll(self, scrollbar):
        """Perform the actual scroll animation."""
        self._scroll_animation = QPropertyAnimation(scrollbar, QByteArray(b"value"))
        self._scroll_animation.setDuration(200)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(scrollbar.maximum())
        self._scroll_animation.start()

    def _append_message(self, role: str, content: str):
        """Append a message to the chat display."""
        if role not in ["user", "assistant"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid role '{role}', defaulting to 'assistant'")
            role = "assistant"

        self.messages_container.add_message(content, role)
        self._scroll_to_bottom()

    def append_assistant_message(self, content: str):
        """Append an assistant message."""
        self._append_message("assistant", content)

    def append_user_message(self, content: str):
        """Append a user message."""
        self._append_message("user", content)

    def append_tool_call(self, tool_name: str, arguments: dict):
        """Append a tool call indicator."""
        self.messages_container.add_tool_call(tool_name, arguments)
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, result: str, success: bool = True):
        """Append a tool result indicator."""
        self.messages_container.add_tool_result(tool_name, success)
        self._scroll_to_bottom()

    def append_thinking(self, message: str):
        """Append a thinking/progress indicator."""
        self.messages_container.add_thinking(message)
        self._scroll_to_bottom()

    def clear_chat(self):
        """Clear the chat display."""
        self.messages_container.clear()

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
