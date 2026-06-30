"""
Toggle switch widget for mode selection.

iOS-style sliding switch for toggling between Chat mode and Task mode.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QWidget

from harness_client.ui.theme_aware import ThemeAwareWidget


class ModeToggleSwitch(ThemeAwareWidget):
    """
    双态滑动开关 - 聊天/任务模式切换.

    左侧: 💬 聊天模式 (run) - 单轮对话
    右侧: 🎯 任务模式 (run_goal) - 多轮自主执行

    Inherits from ThemeAwareWidget to automatically respond to theme changes.

    Signals:
        mode_changed: (is_goal_mode: bool) 模式切换信号
    """

    mode_changed = pyqtSignal(bool)  # True = 任务模式

    def __init__(self, parent: QWidget | None = None):
        # Initialize state BEFORE calling super().__init__
        # because ThemeAwareWidget.__init__ calls _apply_theme_style
        # which calls update() that reads _is_goal_mode
        self._is_goal_mode = False
        super().__init__(parent)
        self.setFixedSize(64, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_goal_mode(self) -> bool:
        """Return True if in task/goal mode."""
        return self._is_goal_mode

    def set_goal_mode(self, enabled: bool) -> None:
        """Set the mode programmatically."""
        if self._is_goal_mode != enabled:
            self._is_goal_mode = enabled
            self.mode_changed.emit(self._is_goal_mode)
            self.update()

    def _apply_theme_style(self) -> None:
        """主题切换时重绘 - 由 ThemeAwareWidget 自动调用."""
        self.update()

    def paintEvent(self, event):
        """Paint the toggle switch with track, slider, and icons."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self.theme()

        # === 轨道背景 ===
        track_rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.CHROME)))
        painter.drawRoundedRect(track_rect, 12, 12)

        # === 滑块 (宽度 = 一半 - 2px padding) ===
        slider_w = self.width() // 2 - 2
        slider_h = self.height() - 2

        if self._is_goal_mode:
            # 任务模式: 滑块在右边
            slider_x = self.width() // 2 + 1
            slider_color = QColor("#10B981")  # emerald-500
        else:
            # 聊天模式: 滑块在左边
            slider_x = 1
            slider_color = QColor(theme.ACCENT)

        painter.setBrush(QBrush(slider_color))
        painter.drawRoundedRect(QRectF(slider_x, 1, slider_w, slider_h), 11, 11)

        # === 图标 ===
        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)

        half_width = self.width() // 2

        # 💬 (左边) - 当前模式高亮
        if not self._is_goal_mode:
            # 聊天模式激活 - 白色文字
            left_color = QColor("#FFFFFF")
        else:
            # 聊天模式未激活 - 次要文字色
            left_color = QColor(theme.TEXT_SUBTLE)
        painter.setPen(left_color)
        painter.drawText(QRectF(0, 0, half_width, self.height()),
                        Qt.AlignmentFlag.AlignCenter, "💬")

        # 🎯 (右边)
        if self._is_goal_mode:
            # 任务模式激活 - 白色文字
            right_color = QColor("#FFFFFF")
        else:
            # 任务模式未激活 - 次要文字色
            right_color = QColor(theme.TEXT_SUBTLE)
        painter.setPen(right_color)
        painter.drawText(QRectF(half_width, 0, half_width, self.height()),
                        Qt.AlignmentFlag.AlignCenter, "🎯")

        painter.end()

    def mousePressEvent(self, event):
        """Toggle mode on click."""
        self._is_goal_mode = not self._is_goal_mode
        self.mode_changed.emit(self._is_goal_mode)
        self.update()

    def enterEvent(self, event):
        """Show hand cursor on hover."""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Restore default cursor on leave."""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().leaveEvent(event)
