"""
Sidebar panel with collapsible icon/text navigation - Hermes Dark Theme Style.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class SidebarPanel(QWidget):
    """Left sidebar with collapsible navigation mode."""

    # Signals
    work_dir_changed = pyqtSignal(Path)
    mcp_connect_requested = pyqtSignal(str)
    skill_load_requested = pyqtSignal(Path)
    session_delete_requested = pyqtSignal(str)
    session_switch_requested = pyqtSignal(str)
    session_new_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    toggle_requested = pyqtSignal()  # emitted when user wants to toggle collapsed state

    # Constants for sizes
    COLLAPSED_WIDTH = 56
    EXPANDED_WIDTH = 220

    def __init__(self):
        super().__init__()
        self._is_collapsed = False
        self._max_width = self.EXPANDED_WIDTH
        self.work_dir = Path.cwd()
        self._setup_ui()
        self._apply_collapsed_state()

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
        """Setup UI components."""
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(4)

        # Top: Logo/App name area (compact)
        self._header_widget = QWidget()
        header_layout = QHBoxLayout(self._header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)

        # Logo button (clickable to toggle)
        self.logo_btn = QToolButton()
        self.logo_btn.setText("A")
        self.logo_btn.setStyleSheet("""
            QToolButton {
                background-color: #007acc;
                color: white;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QToolButton:hover {
                background-color: #106ebe;
            }
        """)
        self.logo_btn.clicked.connect(self._on_toggle)
        header_layout.addWidget(self.logo_btn)

        # App name label (hidden when collapsed)
        self.app_name_label = QLabel("Harness")
        self.app_name_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-size: 12px;
                font-weight: bold;
                margin-left: 4px;
            }
        """)
        header_layout.addWidget(self.app_name_label)
        header_layout.addStretch()

        self._main_layout.addWidget(self._header_widget)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3e3e42; max-height: 1px;")
        self._main_layout.addWidget(separator)

        # Navigation buttons
        self._nav_widget = QWidget()
        nav_layout = QVBoxLayout(self._nav_widget)
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(2)

        # Chat button
        self.chat_btn = self._create_nav_button("💬", "对话")
        self.chat_btn.setToolTip("对话")
        self.chat_btn.clicked.connect(self._on_chat_click)
        nav_layout.addWidget(self.chat_btn)

        # Settings button
        self.settings_btn = self._create_nav_button("⚙", "设置")
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self._on_settings_click)
        nav_layout.addWidget(self.settings_btn)

        # Separator
        nav_separator = QFrame()
        nav_separator.setFrameShape(QFrame.Shape.HLine)
        nav_separator.setStyleSheet("background-color: #3e3e42; max-height: 1px;")
        nav_layout.addWidget(nav_separator)

        # New session button
        self.new_session_btn = self._create_nav_button("+", "新建会话")
        self.new_session_btn.setToolTip("新建会话")
        self.new_session_btn.clicked.connect(self._on_new_session)
        nav_layout.addWidget(self.new_session_btn)

        self._main_layout.addWidget(self._nav_widget)

        # Session list section (collapsible, hidden when sidebar collapsed)
        self._sessions_widget = QWidget()
        sessions_layout = QVBoxLayout(self._sessions_widget)
        sessions_layout.setContentsMargins(4, 4, 4, 4)
        sessions_layout.setSpacing(4)

        sessions_label = QLabel("会话历史")
        sessions_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        sessions_layout.addWidget(sessions_label)

        self.session_list = QListWidget()
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._on_session_context_menu)
        self.session_list.itemClicked.connect(self._on_session_clicked)
        self.session_list.setStyleSheet("""
            QListWidget {
                background-color: #171717;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                color: #d4d4d4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
        """)
        sessions_layout.addWidget(self.session_list)

        self._main_layout.addWidget(self._sessions_widget)

        # Stretch at bottom
        self._main_layout.addStretch()

        # Set initial size
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _create_nav_button(self, icon: str, text: str) -> QPushButton:
        """Create a navigation button with icon and optional text."""
        btn = QPushButton()
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                text-align: left;
                color: #d4d4d4;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
            QPushButton:checked {
                background-color: #094771;
            }
        """)
        # Set font that supports emoji
        font = QFont()
        font.setPointSize(12)
        font.setFamily("Segoe UI Emoji")
        btn.setFont(font)
        btn.setProperty("icon", icon)
        btn.setProperty("text", text)
        btn.setText(icon)  # Initial state: show only icon
        return btn

    def _apply_collapsed_state(self):
        """Apply the collapsed or expanded state to the UI."""
        if self._is_collapsed:
            # Collapsed state: show only icons
            self.setMaximumWidth(self.COLLAPSED_WIDTH)
            self.app_name_label.hide()
            self._sessions_widget.hide()

            # Update buttons to show only icons
            for btn in [self.chat_btn, self.settings_btn, self.new_session_btn]:
                icon = btn.property("icon")
                btn.setText(icon)
                btn.setToolTip(btn.property("text"))
        else:
            # Expanded state: show icons + text
            self.setMaximumWidth(self.EXPANDED_WIDTH)
            self.app_name_label.show()
            self._sessions_widget.show()

            # Update buttons to show icon + text
            for btn in [self.chat_btn, self.settings_btn, self.new_session_btn]:
                icon = btn.property("icon")
                text = btn.property("text")
                btn.setText(f"{icon}  {text}")
                btn.setToolTip("")  # Clear tooltip in expanded mode

    def _on_toggle(self):
        """Handle toggle between collapsed and expanded states."""
        self._is_collapsed = not self._is_collapsed
        self._apply_collapsed_state()
        self.toggle_requested.emit()

    def toggle(self):
        """Public method to toggle the sidebar state."""
        self._on_toggle()

    def set_collapsed(self, collapsed: bool):
        """Set the sidebar collapsed state."""
        if self._is_collapsed != collapsed:
            self._is_collapsed = collapsed
            self._apply_collapsed_state()

    def is_collapsed(self) -> bool:
        """Check if sidebar is collapsed."""
        return self._is_collapsed

    def _on_chat_click(self):
        """Handle chat button click."""
        # If collapsed, expand to show sessions
        if self._is_collapsed:
            self._on_toggle()

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
        self.session_list.clear()

        # Current session (always first)
        if current_session:
            item = QListWidgetItem(f"🔵 {current_session.name}")
            item.setData(Qt.ItemDataRole.UserRole, current_session.id)
            self.session_list.addItem(item)

        # Historical sessions
        for session in history_sessions:
            item = QListWidgetItem(f"📄 {session.name}")
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
        menu.setStyleSheet("""
            QMenu {
                background-color: #252526;
                border: 1px solid #3e3e42;
                color: #d4d4d4;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
        """)

        delete_action = QAction("🗑️ 删除会话", self)
        delete_action.triggered.connect(lambda: self._on_delete_session(session_id, text))
        menu.addAction(delete_action)

        menu.exec(self.session_list.mapToGlobal(position))

    def _on_delete_session(self, session_id: str, session_name: str):
        """Handle delete session request with confirmation."""
        display_name = session_name.replace("🔵 ", "").replace("📄 ", "")
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