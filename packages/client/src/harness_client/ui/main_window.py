"""
Main window for Harness Client.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMenu, QToolBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from harness_client.ui.chat_panel import ChatPanel
from harness_client.ui.sidebar import SidebarPanel


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harness Client")
        self.setMinimumSize(1200, 800)

        # Initialize UI
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()

        # State
        self.work_dir = Path.cwd()

    def _setup_menubar(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")

        new_session_action = QAction("新建会话(&N)", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self._on_new_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("设置(&S)")

        preferences_action = QAction("首选项(&P)...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self._on_preferences)
        settings_menu.addAction(preferences_action)

        # Help menu
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)

        new_session_action = QAction("新建会话", self)
        new_session_action.triggered.connect(self._on_new_session)
        toolbar.addAction(new_session_action)

        toolbar.addSeparator()

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._on_preferences)
        toolbar.addAction(settings_action)

    def _setup_central_widget(self):
        """Setup central widget with splitter layout."""
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left sidebar
        self.sidebar = SidebarPanel()
        self.sidebar.setMaximumWidth(280)

        # Right chat panel
        self.chat_panel = ChatPanel()

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.chat_panel)
        splitter.setSizes([250, 950])

        layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    def _on_new_session(self):
        """Create new session."""
        self.chat_panel.clear_chat()
        self.statusbar.showMessage("新会话已创建", 3000)

    def _on_preferences(self):
        """Open preferences dialog."""
        from harness_client.ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.statusbar.showMessage("设置已保存", 3000)

    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "关于 Harness Client",
            "Harness Client v0.1.0\n\n"
            "Windows 桌面客户端\n"
            "基于 Harness AI Agent SDK\n\n"
            "© 2024 Harness Team"
        )
