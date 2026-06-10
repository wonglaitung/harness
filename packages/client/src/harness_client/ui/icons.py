"""
Vector icon factory for Harness Client.

Provides QPainter-drawn vector icons for consistent rendering across all systems.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QBrush, QPixmap, QPolygonF, QPainterPath


def _create_pixmap(size: int) -> QPixmap:
    """Create a transparent pixmap for drawing."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def create_chat_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a chat/speech bubble icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    # Draw speech bubble outline
    margin = size * 0.15
    bubble_width = size - 2 * margin
    bubble_height = size * 0.55
    tail_width = size * 0.15
    tail_height = size * 0.2
    corner_radius = size * 0.12

    # Main bubble (rounded rect)
    bubble_rect = QRectF(margin, margin, bubble_width, bubble_height)
    painter.drawRoundedRect(bubble_rect, corner_radius, corner_radius)

    # Tail (small triangle at bottom left)
    tail_base_y = margin + bubble_height - corner_radius * 0.5
    tail_points = [
        QPointF(margin + tail_width, tail_base_y),
        QPointF(margin + tail_width * 2, tail_base_y + tail_height),
        QPointF(margin + tail_width * 0.5, tail_base_y),
    ]
    painter.drawPolyline(QPolygonF(tail_points))

    painter.end()
    return QIcon(pixmap)


def create_settings_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a settings/gear icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    center = size / 2
    outer_radius = size * 0.35
    inner_radius = size * 0.15
    tooth_width = size * 0.08
    num_teeth = 8

    # Draw gear teeth
    import math
    for i in range(num_teeth):
        angle = i * (2 * math.pi / num_teeth)
        # Inner point
        x1 = center + inner_radius * math.cos(angle)
        y1 = center + inner_radius * math.sin(angle)
        # Outer point
        x2 = center + outer_radius * math.cos(angle)
        y2 = center + outer_radius * math.sin(angle)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Tooth side
        next_angle = angle + math.pi / num_teeth
        x3 = center + outer_radius * math.cos(next_angle * 0.7 + angle * 0.3)
        y3 = center + outer_radius * math.sin(next_angle * 0.7 + angle * 0.3)

    # Draw center circle
    painter.drawEllipse(QPointF(center, center), inner_radius, inner_radius)

    painter.end()
    return QIcon(pixmap)


def create_add_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create an add/plus icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    center = size / 2
    margin = size * 0.25
    length = size - 2 * margin

    # Horizontal line
    painter.drawLine(QPointF(margin, center), QPointF(size - margin, center))
    # Vertical line
    painter.drawLine(QPointF(center, margin), QPointF(center, size - margin))

    painter.end()
    return QIcon(pixmap)


def create_session_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a session/document icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    margin = size * 0.2
    width = size - 2 * margin
    height = size - 2 * margin
    corner_radius = size * 0.08

    # Draw document outline (rounded rect)
    doc_rect = QRectF(margin, margin, width, height)
    painter.drawRoundedRect(doc_rect, corner_radius, corner_radius)

    # Draw lines inside (text lines)
    line_margin = size * 0.32
    line_width = width - 2 * (line_margin - margin)
    line_y1 = size * 0.4
    line_y2 = size * 0.52
    line_y3 = size * 0.64

    painter.drawLine(QPointF(line_margin, line_y1), QPointF(line_margin + line_width * 0.8, line_y1))
    painter.drawLine(QPointF(line_margin, line_y2), QPointF(line_margin + line_width, line_y2))
    painter.drawLine(QPointF(line_margin, line_y3), QPointF(line_margin + line_width * 0.6, line_y3))

    painter.end()
    return QIcon(pixmap)


def create_folder_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a folder icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    margin = size * 0.15
    tab_width = size * 0.25
    tab_height = size * 0.12
    width = size - 2 * margin
    height = size * 0.55
    body_y = margin + tab_height + size * 0.05
    corner_radius = size * 0.06

    # Draw folder tab (top left)
    tab_points = [
        QPointF(margin, margin),
        QPointF(margin + tab_width, margin),
        QPointF(margin + tab_width + size * 0.08, margin + tab_height),
        QPointF(margin + size * 0.5, margin + tab_height),
    ]
    painter.drawPolyline(QPolygonF(tab_points))

    # Draw folder body (rounded rect)
    body_rect = QRectF(margin, body_y, width, height)
    painter.drawRoundedRect(body_rect, corner_radius, corner_radius)

    painter.end()
    return QIcon(pixmap)


def create_delete_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a delete/trash icon (outline style)."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    margin = size * 0.2
    lid_height = size * 0.1
    body_height = size * 0.5
    width = size - 2 * margin
    corner_radius = size * 0.06

    # Draw lid
    lid_margin = size * 0.1
    painter.drawLine(QPointF(margin - lid_margin, margin), QPointF(size - margin + lid_margin, margin))

    # Draw body (rounded rect)
    body_rect = QRectF(margin, margin + lid_height + size * 0.05, width, body_height)
    painter.drawRoundedRect(body_rect, corner_radius, corner_radius)

    # Draw inner lines
    inner_margin = size * 0.32
    inner_top = margin + lid_height + size * 0.15
    inner_bottom = margin + lid_height + body_height - size * 0.08
    painter.drawLine(QPointF(inner_margin, inner_top), QPointF(inner_margin, inner_bottom))

    inner2 = size * 0.5
    painter.drawLine(QPointF(inner2, inner_top), QPointF(inner2, inner_bottom))

    inner3 = size - inner_margin
    painter.drawLine(QPointF(inner3, inner_top), QPointF(inner3, inner_bottom))

    painter.end()
    return QIcon(pixmap)


def create_status_dot(size: int = 12, color: QColor = QColor("#50c878")) -> QIcon:
    """Create a solid status dot indicator."""
    pixmap = _create_pixmap(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(color))

    # Draw filled circle
    margin = 1
    painter.drawEllipse(QPointF(size / 2, size / 2), (size - margin) / 2, (size - margin) / 2)

    painter.end()
    return QIcon(pixmap)
