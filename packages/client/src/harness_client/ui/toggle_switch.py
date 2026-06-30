"""
Toggle switch widget for mode selection.

Clean sliding switch for toggling between Chat mode and Task mode.
Uses QPainter-drawn icons for crisp rendering on all displays.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtWidgets import QWidget

from harness_client.ui.theme_aware import ThemeAwareWidget


class ModeToggleSwitch(ThemeAwareWidget):
    """
    双态滑动开关 - 聊天/任务模式切换.

    左侧: 聊天模式 (run) - 单轮对话
    右侧: 任务模式 (run_goal) - 多轮自主执行

    Inherits from ThemeAwareWidget to automatically respond to theme changes.

    Signals:
        mode_changed: (is_goal_mode: bool) 模式切换信号
    """

    mode_changed = pyqtSignal(bool)  # True = 任务模式

    def __init__(self, parent: QWidget | None = None):
        # Initialize state BEFORE calling super().__init__
        self._is_goal_mode = False
        self._hover = False
        super().__init__(parent)
        self.setFixedSize(80, 28)
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
        painter.drawRoundedRect(track_rect, 14, 14)

        # === 滑块 ===
        # 宽度略小于一半，留出视觉间隙
        slider_w = self.width() // 2 - 4
        slider_h = self.height() - 4

        if self._is_goal_mode:
            # 任务模式: 滑块在右边
            slider_x = self.width() // 2 + 2
            slider_color = QColor("#10B981")  # emerald-500
        else:
            # 聊天模式: 滑块在左边
            slider_x = 2
            slider_color = QColor(theme.ACCENT)

        # Hover 时略微提亮
        if self._hover:
            slider_color = slider_color.lighter(110)

        painter.setBrush(QBrush(slider_color))
        painter.drawRoundedRect(QRectF(slider_x, 2, slider_w, slider_h), 12, 12)

        # === 图标 ===
        half_width = self.width() // 2

        # 绘制聊天图标 (对话气泡) 或文字
        if not self._is_goal_mode:
            # 激活状态 - 白色
            icon_color = QColor("#FFFFFF")
        else:
            # 未激活状态 - 次要色
            icon_color = QColor(theme.TEXT_SUBTLE)

        # 左侧图标区域
        left_center_x = half_width // 2
        self._draw_chat_icon(painter, left_center_x, self.height() // 2, icon_color)

        # 右侧图标区域
        if self._is_goal_mode:
            icon_color = QColor("#FFFFFF")
        else:
            icon_color = QColor(theme.TEXT_SUBTLE)

        right_center_x = half_width + half_width // 2
        self._draw_target_icon(painter, right_center_x, self.height() // 2, icon_color)

        painter.end()

    def _draw_chat_icon(self, painter: QPainter, cx: float, cy: float, color: QColor):
        """绘制聊天图标 (简化的对话气泡)."""
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(color))

        # 主气泡 (圆角矩形)
        bubble_w = 12
        bubble_h = 10
        bubble_rect = QRectF(cx - bubble_w // 2, cy - bubble_h // 2 - 1, bubble_w, bubble_h)
        painter.drawRoundedRect(bubble_rect, 3, 3)

        # 小尾巴 (三角形)
        tail = QPolygonF([
            QPointF(cx - 2, cy + bubble_h // 2 - 1),
            QPointF(cx + 2, cy + bubble_h // 2 - 1),
            QPointF(cx - 1, cy + bubble_h // 2 + 3),
        ])
        painter.drawPolygon(tail)

    def _draw_target_icon(self, painter: QPainter, cx: float, cy: float, color: QColor):
        """绘制目标图标 (靶心/靶标)."""
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 外圈
        painter.drawEllipse(QPointF(cx, cy), 6, 6)

        # 内圈
        painter.drawEllipse(QPointF(cx, cy), 3, 3)

        # 中心点
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(cx, cy), 1, 1)

    def mousePressEvent(self, event):
        """Toggle mode on click."""
        self._is_goal_mode = not self._is_goal_mode
        self.mode_changed.emit(self._is_goal_mode)
        self.update()

    def enterEvent(self, event):
        """Show hover state."""
        self._hover = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Remove hover state."""
        self._hover = False
        self.update()
        super().leaveEvent(event)
