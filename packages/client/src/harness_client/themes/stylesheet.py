"""
QSS stylesheet generator for Harness Client.

Generates PyQt6 stylesheet strings from theme color palettes.
"""

from harness_client.themes.dark import DarkTheme


def generate_stylesheet(theme: DarkTheme) -> str:
    """
    Generate a complete QSS stylesheet from the theme.

    Args:
        theme: DarkTheme instance with color definitions

    Returns:
        QSS stylesheet string
    """
    # Use string concatenation to avoid f-string issues with CSS braces
    return """
    /* === Global Styles === */

    QWidget {
        background-color: """ + theme.APP_BACKGROUND + """;
        color: """ + theme.TEXT + """;
        font-family: "Segoe UI", "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
    }

    QMainWindow {
        background-color: """ + theme.APP_BACKGROUND + """;
    }

    QMainWindow::separator {
        background-color: """ + theme.BORDER + """;
    }

    /* === Menu Bar === */

    QMenuBar {
        background-color: """ + theme.CHROME + """;
        border-bottom: 1px solid """ + theme.BORDER + """;
        color: """ + theme.TEXT + """;
        padding: 4px 8px;
    }

    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }

    QMenuBar::item:selected {
        background-color: """ + theme.HOVER_NEUTRAL + """;
    }

    QMenu {
        background-color: """ + theme.MENU_BACKGROUND + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        background-color: transparent;
        padding: 8px 24px;
        border-radius: 4px;
        color: """ + theme.TEXT + """;
    }

    QMenu::item:selected {
        background-color: """ + theme.MENU_HOVER + """;
    }

    QMenu::separator {
        height: 1px;
        background-color: """ + theme.BORDER + """;
        margin: 4px 8px;
    }

    /* === Status Bar === */

    QStatusBar {
        background-color: """ + theme.ACCENT + """;
        color: white;
        font-size: 12px;
        padding: 4px 8px;
    }

    QStatusBar::item {
        border: none;
    }

    /* === Buttons === */

    QPushButton {
        background-color: transparent;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px;
        padding: 8px 16px;
        color: """ + theme.TEXT + """;
        font-size: 13px;
    }

    QPushButton:hover {
        background-color: """ + theme.HOVER_NEUTRAL + """;
        border-color: """ + theme.BORDER_LIGHT + """;
    }

    QPushButton:pressed {
        background-color: """ + theme.BORDER + """;
    }

    QPushButton:disabled {
        background-color: """ + theme.DISABLED_BACKGROUND + """;
        color: """ + theme.TEXT_DISABLED + """;
        border-color: """ + theme.DISABLED_BACKGROUND + """;
    }

    /* Primary button (accent color) */
    QPushButton[primary="true"] {
        background-color: """ + theme.ACCENT + """;
        border: none;
        color: white;
        font-weight: bold;
    }

    QPushButton[primary="true"]:hover {
        background-color: """ + theme.ACCENT_HOVER + """;
    }

    QPushButton[primary="true"]:pressed {
        background-color: #1a47b8;
    }

    /* Danger button */
    QPushButton[danger="true"] {
        background-color: """ + theme.DANGER + """;
        border: none;
        color: white;
    }

    QPushButton[danger="true"]:hover {
        background-color: """ + theme.DANGER_HOVER + """;
    }

    /* Ghost button (minimal style) */
    QPushButton[ghost="true"] {
        background-color: transparent;
        border: 1px solid """ + theme.BORDER + """;
        color: """ + theme.TEXT_SUBTLE + """;
    }

    QPushButton[ghost="true"]:hover {
        background-color: """ + theme.HOVER_NEUTRAL + """;
        color: """ + theme.TEXT + """;
    }

    /* === Input Fields === */

    QLineEdit {
        background-color: """ + theme.CHROME + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 6px;
        padding: 8px 12px;
        color: """ + theme.TEXT + """;
        selection-background-color: """ + theme.SELECTION_ACTIVE + """;
    }

    QLineEdit:focus {
        border-color: """ + theme.ACCENT + """;
    }

    QLineEdit:disabled {
        background-color: """ + theme.DISABLED_BACKGROUND + """;
        color: """ + theme.TEXT_DISABLED + """;
    }

    QLineEdit::placeholder {
        color: """ + theme.TEXT_SUBTLE + """;
    }

    QTextEdit {
        background-color: """ + theme.CHROME + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 6px;
        padding: 8px 12px;
        color: """ + theme.TEXT + """;
        selection-background-color: """ + theme.SELECTION_ACTIVE + """;
    }

    QTextEdit:focus {
        border-color: """ + theme.ACCENT + """;
    }

    /* === Labels === */

    QLabel {
        background-color: transparent;
        color: """ + theme.TEXT + """;
    }

    QLabel[subtle="true"] {
        color: """ + theme.TEXT_SUBTLE + """;
    }

    /* === Scroll Areas === */

    QScrollArea {
        background-color: transparent;
        border: none;
    }

    QScrollArea > QWidget > QWidget {
        background-color: transparent;
    }

    /* === Scroll Bars === */

    QScrollBar:vertical {
        background: transparent;
        width: 12px;
        margin: 4px 4px 4px 4px;
        border-radius: 4px;
    }

    QScrollBar::handle:vertical {
        background: """ + theme.SCROLL_THUMB + """;
        border-radius: 4px;
        min-height: 32px;
    }

    QScrollBar::handle:vertical:hover {
        background: """ + theme.TEXT_SUBTLE + """;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
        background: transparent;
    }

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: transparent;
    }

    QScrollBar:horizontal {
        background: transparent;
        height: 12px;
        margin: 4px 4px 4px 4px;
        border-radius: 4px;
    }

    QScrollBar::handle:horizontal {
        background: """ + theme.SCROLL_THUMB + """;
        border-radius: 4px;
        min-width: 32px;
    }

    QScrollBar::handle:horizontal:hover {
        background: """ + theme.TEXT_SUBTLE + """;
    }

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        width: 0px;
        background: transparent;
    }

    /* === Splitters === */

    QSplitter {
        background-color: """ + theme.APP_BACKGROUND + """;
    }

    QSplitter::handle {
        background-color: """ + theme.BORDER + """;
    }

    QSplitter::handle:horizontal {
        width: 1px;
    }

    QSplitter::handle:vertical {
        height: 1px;
    }

    QSplitter::handle:hover {
        background-color: """ + theme.ACCENT + """;
    }

    /* === List/Tree Views === */

    QListView {
        background-color: transparent;
        border: none;
        color: """ + theme.TEXT + """;
    }

    QListView::item {
        background-color: transparent;
        padding: 8px 12px;
        border-radius: 8px;
    }

    QListView::item:hover {
        background-color: """ + theme.HOVER_NEUTRAL + """;
    }

    QListView::item:selected {
        background-color: """ + theme.SELECTION_ACTIVE + """;
        border: 1px solid """ + theme.SELECTION_BORDER + """;
    }

    QTreeView {
        background-color: """ + theme.PANEL + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px;
        color: """ + theme.TEXT + """;
    }

    QTreeView::item {
        background-color: transparent;
        padding: 4px 8px;
        border-radius: 6px;
    }

    QTreeView::item:hover {
        background-color: """ + theme.HOVER_SURFACE + """;
    }

    QTreeView::item:selected {
        background-color: """ + theme.SELECTION_ACTIVE + """;
        border: 1px solid """ + theme.SELECTION_BORDER + """;
    }

    QTreeView::branch {
        background-color: """ + theme.PANEL + """;
    }

    /* === ComboBox === */

    QComboBox {
        background-color: """ + theme.CHROME + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 6px;
        padding: 6px 12px;
        color: """ + theme.TEXT + """;
    }

    QComboBox:hover {
        border-color: """ + theme.BORDER_LIGHT + """;
    }

    QComboBox:focus {
        border-color: """ + theme.ACCENT + """;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox::down-arrow {
        color: """ + theme.TEXT_SUBTLE + """;
    }

    QComboBox QAbstractItemView {
        background-color: """ + theme.MENU_BACKGROUND + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 6px;
        selection-background-color: """ + theme.HOVER_NEUTRAL + """;
    }

    /* === SpinBox === */

    QSpinBox {
        background-color: """ + theme.CHROME + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 6px;
        padding: 6px 12px;
        color: """ + theme.TEXT + """;
    }

    QSpinBox:focus {
        border-color: """ + theme.ACCENT + """;
    }

    QSpinBox::up-button,
    QSpinBox::down-button {
        background-color: transparent;
        border: none;
        width: 20px;
    }

    QSpinBox::up-arrow,
    QSpinBox::down-arrow {
        color: """ + theme.TEXT_SUBTLE + """;
    }

    /* === CheckBox === */

    QCheckBox {
        background-color: transparent;
        color: """ + theme.TEXT + """;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid """ + theme.BORDER + """;
        background-color: transparent;
    }

    QCheckBox::indicator:checked {
        background-color: """ + theme.ACCENT + """;
        border-color: """ + theme.ACCENT + """;
    }

    QCheckBox::indicator:hover {
        border-color: """ + theme.ACCENT + """;
    }

    /* === GroupBox === */

    QGroupBox {
        background-color: transparent;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px;
        padding-top: 16px;
        color: """ + theme.TEXT + """;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: """ + theme.TEXT + """;
        font-weight: bold;
    }

    /* === Tab Widget === */

    QTabWidget::pane {
        background-color: """ + theme.PANEL + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px;
    }

    QTabBar::tab {
        background-color: transparent;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        color: """ + theme.TEXT_SUBTLE + """;
    }

    QTabBar::tab:selected {
        background-color: """ + theme.PANEL_ALT + """;
        color: """ + theme.TEXT + """;
        border-bottom-color: """ + theme.PANEL_ALT + """;
    }

    QTabBar::tab:hover:!selected {
        background-color: """ + theme.HOVER_NEUTRAL + """;
    }

    /* === Progress Bar === */

    QProgressBar {
        background-color: """ + theme.CHROME + """;
        border: 1px solid """ + theme.BORDER + """;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: """ + theme.ACCENT + """;
        border-radius: 3px;
    }

    /* === Tool Tip === */

    QToolTip {
        background-color: """ + theme.TOAST_BACKGROUND + """;
        border: 1px solid """ + theme.TOAST_BORDER + """;
        border-radius: 6px;
        padding: 6px 10px;
        color: """ + theme.TEXT + """;
    }

    /* === Message Box === */

    QMessageBox {
        background-color: """ + theme.PANEL + """;
    }

    QMessageBox QLabel {
        color: """ + theme.TEXT + """;
    }

    /* === Dialog === */

    QDialog {
        background-color: """ + theme.PANEL + """;
    }

    /* === Text Browser (Chat Display) === */

    QTextBrowser {
        background-color: transparent;
        border: none;
        color: """ + theme.TEXT + """;
    }
    """
