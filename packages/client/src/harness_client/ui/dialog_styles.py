"""
Dialog styling utilities for consistent configuration UI.

All configuration dialogs should use these helpers to ensure
consistent visual appearance across the application.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QGroupBox

from harness_client.themes import get_theme


# Standard dialog dimensions
DIALOG_MIN_WIDTH = 480
DIALOG_MIN_HEIGHT = 300
DIALOG_MARGINS = (20, 20, 20, 20)  # left, top, right, bottom
DIALOG_SPACING = 12

# Form layout settings
FORM_SPACING = 8
FORM_LABEL_ALIGNMENT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

# Input widget settings
INPUT_PADDING = "6px 8px"
INPUT_MIN_HEIGHT = 18
INPUT_MIN_WIDTH = 200


def get_dialog_stylesheet() -> str:
    """
    Get the standard stylesheet for configuration dialogs.

    Returns:
        CSS stylesheet string for QDialog and common widgets.
    """
    theme = get_theme()
    return f"""
        QDialog {{
            background-color: {theme.CHROME};
            color: {theme.TEXT};
        }}
        QLabel {{
            color: {theme.TEXT};
        }}
        QLineEdit {{
            background-color: {theme.COMPOSER};
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            padding: {INPUT_PADDING};
            color: {theme.TEXT};
            min-height: {INPUT_MIN_HEIGHT}px;
        }}
        QLineEdit:focus {{
            border-color: {theme.ACCENT};
        }}
        QLineEdit:placeholder-shown {{
            color: {theme.TEXT_MUTED};
        }}
        QSpinBox {{
            background-color: {theme.COMPOSER};
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            padding: {INPUT_PADDING};
            color: {theme.TEXT};
            min-height: {INPUT_MIN_HEIGHT}px;
        }}
        QSpinBox:focus {{
            border-color: {theme.ACCENT};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;
            background-color: transparent;
            border: none;
        }}
        QSpinBox::up-arrow {{
            width: 10px;
            height: 10px;
        }}
        QSpinBox::down-arrow {{
            width: 10px;
            height: 10px;
        }}
        QComboBox {{
            background-color: {theme.COMPOSER};
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            padding: {INPUT_PADDING};
            color: {theme.TEXT};
            min-height: {INPUT_MIN_HEIGHT}px;
        }}
        QComboBox:focus {{
            border-color: {theme.ACCENT};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.COMPOSER};
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            selection-background-color: {theme.ACCENT};
            selection-color: white;
        }}
        QTextEdit {{
            background-color: {theme.COMPOSER};
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            padding: {INPUT_PADDING};
            color: {theme.TEXT};
        }}
        QTextEdit:focus {{
            border-color: {theme.ACCENT};
        }}
        QCheckBox {{
            color: {theme.TEXT};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
            background-color: {theme.COMPOSER};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.ACCENT};
            border-color: {theme.ACCENT};
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            margin-top: 8px;
            padding-top: 8px;
            color: {theme.TEXT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 4px;
            color: {theme.TEXT_SUBTLE};
        }}
        QPushButton {{
            background-color: {theme.ACCENT};
            color: white;
            border: none;
            border-radius: {theme.RADIUS_SM};
            padding: 8px 16px;
            min-height: 24px;
        }}
        QPushButton:hover {{
            background-color: {theme.ACCENT_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {theme.ACCENT_DARK};
        }}
        QPushButton:disabled {{
            background-color: {theme.BORDER};
            color: {theme.TEXT_MUTED};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
    """


def get_muted_label_stylesheet() -> str:
    """Get stylesheet for muted/helper text labels."""
    theme = get_theme()
    return f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS};"


def get_error_label_stylesheet() -> str:
    """Get stylesheet for error/validation text labels."""
    theme = get_theme()
    return f"color: {theme.DANGER}; font-size: {theme.FONT_SIZE_XS};"


def get_groupbox_stylesheet() -> str:
    """Get stylesheet for QGroupBox containers."""
    theme = get_theme()
    return f"""
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {theme.BORDER};
            border-radius: {theme.RADIUS_SM};
            margin-top: 8px;
            padding-top: 8px;
            color: {theme.TEXT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 4px;
            color: {theme.TEXT_SUBTLE};
        }}
    """


def create_standard_form_layout() -> QFormLayout:
    """
    Create a QFormLayout with standard settings.

    Returns:
        Configured QFormLayout with consistent spacing and alignment.
    """
    form = QFormLayout()
    form.setSpacing(FORM_SPACING)
    form.setLabelAlignment(FORM_LABEL_ALIGNMENT)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    return form


def create_grouped_section(title: str, parent=None) -> QGroupBox:
    """
    Create a QGroupBox with standard styling.

    Args:
        title: The group box title.
        parent: Optional parent widget.

    Returns:
        Styled QGroupBox ready for layout.
    """
    group = QGroupBox(title, parent)
    group.setStyleSheet(get_groupbox_stylesheet())
    return group
