"""
Sidebar panel with navigation buttons and session list - Modern theme-aware style.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QCursor, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from harness_client.themes import get_theme
from harness_client.ui.icons import (
    create_chat_icon,
    create_settings_icon,
    create_add_icon,
    create_session_icon,
    create_delete_icon,
)


class SidebarPanel(QWidget):
    """Left sidebar with navigation and session list."""

    # Signals
    work_dir_changed = pyqtSignal(Path)
    mcp_connect_requested = pyqtSignal(str)
    skill_load_requested = pyqtSignal(Path)
    session_delete_requested = pyqtSignal(str)
    session_switch_requested = pyqtSignal(str)
    session_new_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    # Fixed width
    FIXED_WIDTH = 180

    def __init__(self):
        super().__init__()
        self.work_dir = Path.cwd()
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

    def _create_nav_button(self, icon: QIcon | None, text: str) -> QPushButton:
        """Create a navigation button with icon and text."""
        theme = get_theme()
        btn = QPushButton(f"  {text}") if icon else QPushButton(text)
        if icon:
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_MD};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        btn.setFixedHeight(44)
        return btn

    def _setup_ui(self):
        """Setup UI components."""
        theme = get_theme()

        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(12, 12, 12, 12)
        self._main_layout.setSpacing(4)

        # Set panel background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.CHROME};
            }}
        """)

        # Navigation buttons
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        # Chat button
        self.chat_btn = self._create_nav_button(create_chat_icon(18, QColor(theme.TEXT)), "对话")
        nav_layout.addWidget(self.chat_btn)

        # Settings button
        self.settings_btn = self._create_nav_button(create_settings_icon(18, QColor(theme.TEXT)), "设置")
        self.settings_btn.clicked.connect(self._on_settings_click)
        nav_layout.addWidget(self.settings_btn)

        # Separator
        nav_separator = QFrame()
        nav_separator.setFrameShape(QFrame.Shape.HLine)
        nav_separator.setStyleSheet(f"background-color: {theme.BORDER}; max-height: 1px;")
        nav_layout.addWidget(nav_separator)

        # New session button
        self.new_session_btn = self._create_nav_button(create_add_icon(18, QColor(theme.TEXT)), "新建会话")
        self.new_session_btn.clicked.connect(self._on_new_session)
        nav_layout.addWidget(self.new_session_btn)

        self._main_layout.addWidget(nav_widget)

        # Session list section
        sessions_label = QLabel("会话历史")
        sessions_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                font-weight: bold;
                padding: 12px 0 6px 0;
            }}
        """)
        self._main_layout.addWidget(sessions_label)

        self.session_list = QListWidget()
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._on_session_context_menu)
        self.session_list.itemClicked.connect(self._on_session_clicked)
        self.session_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: {theme.RADIUS_SM};
                margin: 2px 4px;
            }}
            QListList::item:selected {{
                background-color: {theme.SELECTION_ACTIVE};
                border: 1px solid {theme.SELECTION_BORDER};
                color: {theme.TEXT};
            }}
            QListWidget::item:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        self._main_layout.addWidget(self.session_list, 1)

        # Set fixed size
        self.setFixedWidth(self.FIXED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _on_settings_click(self):
        """Handle settings button click."""
        self.settings_requested.emit()

    def _on_new_session(self):
        """Handle new session button click."""
        self.session_new_requested.emit()

    # === Session List Management ===

    def update_sessions(self, current_session, history_sessions: list):
        """
        Update the session list display.

        Args:
            current_session: Current ClientSession object (or None)
            history_sessions: List of historical ClientSession objects
        """
        theme = get_theme()
        self.session_list.clear()

        # Current session (always first) - with active indicator
        if current_session:
            item = QListWidgetItem(f"● {current_session.name}")
            item.setData(Qt.ItemDataRole.UserRole, current_session.id)
            item.setForeground(Qt.GlobalColor.white)  # Make current session stand out
            self.session_list.addItem(item)

        # Historical sessions
        for session in history_sessions:
            item = QListWidgetItem(f"  {session.name}")
            item.setData(Qt.ItemDataRole.UserRole, session.id)
            self.session_list.addItem(item)

    def _on_session_clicked(self, item: QListWidgetItem):
        """Handle session list item click."""
        row = self.session_list.row(item)
        session_id = item.data(Qt.ItemDataRole.UserRole)

        # First item is current session - no action needed
        if row == 0:
            return

        # Switch to this session
        if session_id:
            self.session_switch_requested.emit(session_id)

    def _on_session_context_menu(self, position):
        """Show context menu for session list."""
        theme = get_theme()
        item = self.session_list.itemAt(position)
        if not item:
            return

        row = self.session_list.row(item)
        text = item.text()

        # Don't show menu for current session (first item)
        if row == 0:
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        if not session_id:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.MENU_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                color: {theme.TEXT};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)

        delete_action = QAction(create_delete_icon(16, QColor(theme.TEXT_SUBTLE)), "删除会话", self)
        delete_action.triggered.connect(lambda: self._on_delete_session(session_id, text))
        menu.addAction(delete_action)

        menu.exec(self.session_list.mapToGlobal(position))

    def _on_delete_session(self, session_id: str, session_name: str):
        """Handle delete session request with confirmation."""
        # Clean display name (remove prefix indicators)
        display_name = session_name.lstrip("● ")
        display_name = display_name.lstrip()
        if "(" in display_name:
            display_name = display_name.split("(")[0].strip()

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话「{display_name}」吗？\n\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.session_delete_requested.emit(session_id)
