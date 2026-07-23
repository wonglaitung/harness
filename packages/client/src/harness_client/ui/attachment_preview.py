"""
Attachment preview widget for file uploads.

Displays image thumbnails and document icons for files attached to messages.
Inline design for integration inside input bar.
"""

import base64
import logging
import mimetypes
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QBrush, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)

from harness_client.themes import get_theme
from harness_client.ui.icons import create_image_icon, create_document_icon
from harness_client.ui.theme_aware import ThemeAwareWidget

logger = logging.getLogger(__name__)

# File size limits
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DOCUMENT_SIZE = 32 * 1024 * 1024  # 32MB
RECOMMENDED_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB - warning threshold

# Supported formats
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".json", ".csv"}


def create_close_icon(size: int = 16, color: QColor = QColor("#FFFFFF")) -> QIcon:
    """Create a close/X icon for removing attachments."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    margin = 3
    # X mark
    painter.drawLine(margin, margin, size - margin, size - margin)
    painter.drawLine(size - margin, margin, margin, size - margin)

    painter.end()
    return QIcon(pixmap)


class AttachmentCard(ThemeAwareWidget):
    """Single attachment preview card with remove button - compact inline version."""

    removed = pyqtSignal(str)  # attachment_id

    def __init__(self, attachment: dict, parent: QWidget | None = None):
        self._attachment = attachment
        self._id = attachment.get("id", "")
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the card UI - compact size for inline display."""
        theme = self.theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.setFixedHeight(32)  # Single line height
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Icon preview
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)

        # Set icon based on type
        att_type = self._attachment.get("type", "document")
        if att_type == "image":
            self._set_image_icon()
        else:
            self._set_document_icon()

        layout.addWidget(self._icon_label)

        # Filename label
        self._filename_label = QLabel()
        font = QFont()
        font.setPointSize(9)
        self._filename_label.setFont(font)

        filename = self._attachment.get("filename", "")
        if len(filename) > 20:
            filename = filename[:17] + "..."
        self._filename_label.setText(filename)

        layout.addWidget(self._filename_label)

        # Remove button
        self._remove_btn = QPushButton()
        self._remove_btn.setIcon(create_close_icon(10, QColor(theme.TEXT_SUBTLE)))
        self._remove_btn.setIconSize(QSize(10, 10))
        self._remove_btn.setFixedSize(18, 18)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setToolTip("移除附件")
        self._remove_btn.clicked.connect(self._on_remove)

        layout.addWidget(self._remove_btn)

    def _set_image_icon(self):
        """Set image icon."""
        theme = self.theme()
        self._icon_label.setPixmap(create_image_icon(16, QColor(theme.TEXT_SUBTLE)).pixmap(16, 16))

    def _set_document_icon(self):
        """Set document icon."""
        theme = self.theme()
        self._icon_label.setPixmap(create_document_icon(16, QColor(theme.TEXT_SUBTLE)).pixmap(16, 16))

    def _apply_theme_style(self) -> None:
        """Apply theme styling."""
        theme = self.theme()
        self.setStyleSheet(f"""
            AttachmentCard {{
                background-color: {theme.COMPOSER};
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
            }}
            AttachmentCard:hover {{
                border-color: {theme.ACCENT};
            }}
            QLabel {{
                background: transparent;
                color: {theme.TEXT};
            }}
        """)

        # Style remove button
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 9px;
            }}
            QPushButton:hover {{
                background-color: {theme.DANGER};
            }}
        """)

        # Re-render icon
        att_type = self._attachment.get("type", "document")
        if att_type == "image":
            self._set_image_icon()
        else:
            self._set_document_icon()

    def _on_remove(self):
        """Handle remove button click."""
        self.removed.emit(self._id)

    def get_attachment(self) -> dict:
        """Get the attachment data."""
        return self._attachment


class AttachmentPreview(ThemeAwareWidget):
    """
    Attachment preview area for displaying attached files before sending.
    Compact inline design for integration inside input bar.

    Features:
    - Horizontal inline list of attachment cards
    - Support for images and documents
    - Remove individual attachments
    - Clear all attachments
    """

    attachments_changed = pyqtSignal()  # Emitted when attachments are added/removed

    def __init__(self, parent: QWidget | None = None):
        self._attachments: list[dict] = []
        self._cards: dict[str, AttachmentCard] = {}
        super().__init__(parent)
        self._setup_ui()
        self.setVisible(False)  # Hidden when empty

    def _setup_ui(self):
        """Setup the UI - compact inline version for input bar."""
        theme = self.theme()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 6, 24, 6)  # Match input bar margins
        main_layout.setSpacing(8)

        # Title label (compact)
        self._title_label = QLabel("附件")
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
                background: transparent;
            }}
        """)
        main_layout.addWidget(self._title_label)

        # Cards container (horizontal)
        self._cards_container = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(6)
        main_layout.addWidget(self._cards_container)

        main_layout.addStretch()

        # Clear button
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                color: {theme.ACCENT};
            }}
        """)
        self._clear_btn.clicked.connect(self.clear)
        main_layout.addWidget(self._clear_btn)

        # No border since it's inside input bar
        self.setStyleSheet(f"""
            AttachmentPreview {{
                background-color: transparent;
            }}
        """)

    def add_attachment(self, file_path: str) -> bool:
        """
        Add an attachment from file path.

        Args:
            file_path: Path to the file

        Returns:
            True if added successfully, False if file is invalid or too large
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        # Check file extension
        ext = path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            att_type = "image"
            max_size = MAX_IMAGE_SIZE
        elif ext in DOCUMENT_EXTENSIONS:
            att_type = "document"
            max_size = MAX_DOCUMENT_SIZE
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return False

        # Check file size
        file_size = path.stat().st_size
        if file_size > max_size:
            logger.warning(f"File too large: {file_size} > {max_size}")
            return False

        # Show warning for large documents (exceeds recommended but under max)
        if att_type == "document" and file_size > RECOMMENDED_DOCUMENT_SIZE:
            size_mb = file_size / 1024 / 1024
            if not self._show_large_document_warning(path.name, size_mb):
                return False

        # Read and encode file
        try:
            file_data = path.read_bytes()
            base64_data = base64.b64encode(file_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return False

        # Determine media type
        media_type = mimetypes.guess_type(file_path)[0]
        if not media_type:
            if ext in IMAGE_EXTENSIONS:
                media_type = f"image/{ext[1:]}"  # .png -> image/png
            else:
                media_type = "application/octet-stream"

        # Create attachment record
        import uuid
        attachment_id = str(uuid.uuid4())[:8]
        attachment = {
            "id": attachment_id,
            "type": att_type,
            "path": file_path,
            "filename": path.name,
            "media_type": media_type,
            "data": base64_data,
            "size": file_size,
        }

        self._attachments.append(attachment)

        # Create card
        card = AttachmentCard(attachment)
        card.removed.connect(self._on_card_removed)
        self._cards[attachment_id] = card

        # Add to layout
        self._cards_layout.addWidget(card)

        # Show preview area
        self.setVisible(True)
        self._update_title()

        self.attachments_changed.emit()
        return True

    def _show_large_document_warning(self, filename: str, size_mb: float) -> bool:
        """
        Show warning dialog for large documents.

        Args:
            filename: Name of the file
            size_mb: File size in MB

        Returns:
            True if user wants to proceed, False to cancel
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("文档大小警告")
        msg_box.setText(f"文档 '{filename}' 大小为 {size_mb:.1f}MB，可能影响处理速度。")
        msg_box.setInformativeText("是否继续添加此附件？")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        # Add custom buttons
        continue_btn = msg_box.addButton("继续发送", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        msg_box.setDefaultButton(cancel_btn)
        msg_box.exec()

        return msg_box.clickedButton() == continue_btn

    def remove_attachment(self, attachment_id: str):
        """Remove an attachment by ID."""
        if attachment_id in self._cards:
            card = self._cards.pop(attachment_id)
            card.deleteLater()

        self._attachments = [a for a in self._attachments if a.get("id") != attachment_id]

        if not self._attachments:
            self.setVisible(False)

        self._update_title()
        self.attachments_changed.emit()

    def clear(self):
        """Clear all attachments."""
        for card in self._cards.values():
            card.deleteLater()

        self._cards.clear()
        self._attachments.clear()
        self.setVisible(False)

        self.attachments_changed.emit()

    def get_attachments(self) -> list[dict]:
        """Get all attachments."""
        return self._attachments.copy()

    def get_supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS

    def has_attachments(self) -> bool:
        """Check if there are any attachments."""
        return len(self._attachments) > 0

    def _on_card_removed(self, attachment_id: str):
        """Handle card removed signal."""
        self.remove_attachment(attachment_id)

    def _update_title(self):
        """Update the title with attachment count."""
        count = len(self._attachments)
        if count == 0:
            self._title_label.setText("附件")
        else:
            self._title_label.setText(f"附件 ({count})")

    def _apply_theme_style(self) -> None:
        """Handle theme change."""
        theme = self.theme()

        self.setStyleSheet(f"""
            AttachmentPreview {{
                background-color: transparent;
            }}
        """)

        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
                background: transparent;
            }}
        """)

        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {theme.TEXT_SUBTLE};
                font-size: 11px;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                color: {theme.ACCENT};
            }}
        """)

        # Update all cards
        for card in self._cards.values():
            card._apply_theme_style()
