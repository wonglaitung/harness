"""
Interactive button components with animation feedback.

Provides buttons with tactile press feedback (scale animation) for better UX.
"""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QSize, pyqtProperty
from PyQt6.QtGui import QColor, QIcon, QCursor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect, QWidget

from harness_client.ui.theme_aware import ThemeAwareWidget


class TactileButton(QPushButton):
    """
    Button with tactile press feedback using scale animation.

    When pressed, the button briefly scales down (0.96) to simulate physical push.
    This creates a more responsive feel compared to static color changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale = 1.0
        self._animation = QPropertyAnimation(self, "scale", self)
        self._animation.setDuration(100)  # 100ms - quick response
        self._animation.setEasingCurve(QPropertyAnimation.EasingCurve.OutCubic)

        # Track press state
        self._pressed = False

    @pyqtProperty(float)
    def scale(self) -> float:
        return self._scale

    def setScale(self, value: float):
        """Set scale factor and apply visual transformation."""
        if self._scale == value:
            return
        self._scale = value

        # Apply scale via stylesheet transform
        # PyQt6 doesn't support CSS transform, so we use size adjustment
        base_size = self.sizeHint()
        scaled_width = int(base_size.width() * value)
        scaled_height = int(base_size.height() * value)

        # Center the scaled button
        offset_x = (base_size.width() - scaled_width) // 2
        offset_y = (base_size.height() - scaled_height) // 2

        # Move and resize (creates visual scale effect)
        if value < 1.0:
            # Scale down: move right/down, resize smaller
            self.move(self.pos().x() + offset_x, self.pos().y() + offset_y)
            self.setFixedSize(scaled_width, scaled_height)
        else:
            # Reset to original
            self.setFixedSize(base_size)

    def mousePressEvent(self, event):
        """On press, animate scale down."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._animation.setStartValue(1.0)
            self._animation.setEndValue(0.96)
            self._animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """On release, animate scale back to normal."""
        if event.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            self._animation.setStartValue(0.96)
            self._animation.setEndValue(1.0)
            self._animation.start()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """Reset scale if mouse leaves while pressed."""
        if self._pressed:
            self._pressed = False
            self._animation.setStartValue(0.96)
            self._animation.setEndValue(1.0)
            self._animation.start()
        super().leaveEvent(event)


class GlowButton(QPushButton):
    """
    Button with subtle glow effect on hover using drop shadow.

    Creates a soft colored glow around the button when hovered,
    enhancing visual feedback without being distracting.
    """

    def __init__(self, glow_color: QColor = None, glow_radius: int = 8, parent=None):
        super().__init__(parent)
        from harness_client.themes import get_theme
        theme = get_theme()
        self._glow_color = glow_color or QColor(theme.ACCENT)  # Default Trust Blue
        self._glow_radius = glow_radius
        self._shadow_effect = None
        self._hover = False

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def setGlowColor(self, color: QColor):
        """Set the glow color."""
        self._glow_color = color
        if self._shadow_effect and self._hover:
            self._update_shadow()

    def _update_shadow(self):
        """Update shadow effect based on hover state."""
        if self._shadow_effect:
            if self._hover:
                self._shadow_effect.setColor(self._glow_color)
                self._shadow_effect.setBlurRadius(self._glow_radius)
                self._shadow_effect.setOffset(0, 0)
            else:
                self._shadow_effect.setBlurRadius(0)

    def enterEvent(self, event):
        """On hover, show glow effect."""
        self._hover = True

        if not self._shadow_effect:
            self._shadow_effect = QGraphicsDropShadowEffect(self)
            self._shadow_effect.setColor(self._glow_color)
            self._shadow_effect.setBlurRadius(self._glow_radius)
            self._shadow_effect.setOffset(0, 0)
            self.setGraphicsEffect(self._shadow_effect)

        self._update_shadow()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """On leave, hide glow effect."""
        self._hover = False
        self._update_shadow()
        super().leaveEvent(event)


class IconButton(GlowButton):
    """
    Circular icon button with glow effect, optimized for toolbars.

    Fixed size square/circle button with centered icon.
    """

    def __init__(self, icon: QIcon = None, size: int = 36, glow_color: QColor = None, parent=None):
        super().__init__(glow_color, parent=parent)
        self._icon_size = size

        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(size - 8, size - 8))  # Icon slightly smaller than button

        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class StatusDot(ThemeAwareWidget):
    """
    Animated status indicator dot with pulse effect.

    Used for connection status:
    - Connected: static green
    - Connecting: pulsing yellow (breathing animation)
    - Error: static red
    - Disconnected: static gray

    Note: Colors are fetched dynamically in paintEvent() to support theme switching.
    """

    def __init__(self, size: int = 12, parent=None):
        self._size = size
        self._status = "disconnected"  # connected, connecting, error, disconnected
        self._pulse_opacity = 1.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_direction = -1  # -1 = fade out, 1 = fade in

        super().__init__(parent)
        self.setFixedSize(size + 4, size + 4)  # Small padding

    def _apply_theme_style(self) -> None:
        """Repaint when theme changes."""
        self.update()

    def _get_status_color(self) -> QColor:
        """Get color for current status from theme (dynamic)."""
        theme = self.theme()
        color_map = {
            "connected": theme.STATUS_CONNECTED,
            "connecting": theme.STATUS_CONNECTING,
            "error": theme.STATUS_ERROR,
            "disconnected": theme.STATUS_DISCONNECTED,
        }
        return QColor(color_map.get(self._status, theme.STATUS_DISCONNECTED))

    def setStatus(self, status: str):
        """
        Set status and start/stop animation.

        Args:
            status: "connected", "connecting", "error", "disconnected"
        """
        self._status = status.lower()

        if self._status == "connecting":
            # Start pulse animation
            self._pulse_opacity = 1.0
            self._pulse_direction = -1
            self._pulse_timer.start(50)  # 50ms = 20fps, smooth pulse
        else:
            # Stop animation, solid color
            self._pulse_timer.stop()
            self._pulse_opacity = 1.0

        self.update()  # Trigger repaint

    def _pulse_tick(self):
        """Update opacity for breathing effect."""
        # Change opacity by 0.05 each tick
        self._pulse_opacity += self._pulse_direction * 0.05

        # Reverse direction at bounds
        if self._pulse_opacity <= 0.4:
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_direction = -1

        self.update()

    def paintEvent(self, event):
        """Draw the status dot - dynamically fetches theme colors."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get color dynamically from theme (supports theme switching)
        color = self._get_status_color()
        color.setAlphaF(self._pulse_opacity)

        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(color))

        # Draw centered circle
        center_x = (self.width() - self._size) // 2
        center_y = (self.height() - self._size) // 2
        painter.drawEllipse(center_x, center_y, self._size, self._size)

        painter.end()