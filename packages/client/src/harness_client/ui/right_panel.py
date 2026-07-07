"""
Right panel with collapsible sections for skills, MCP servers, and file tree.
"""

from pathlib import Path

from PyQt6.QtCore import (
    QAbstractAnimation,
    QDir,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QApplication,
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener


class CustomFileIconProvider(QFileIconProvider):
    """Custom icon provider that uses Qt built-in icons for files and folders."""

    def __init__(self):
        super().__init__()
        style = QApplication.style()
        self._folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._folder_open_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self._file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def icon(self, info):
        """Return appropriate icon based on file type.

        Args:
            info: QFileInfo object

        Returns:
            QIcon for the file/folder
        """
        if info.isDir():
            return self._folder_icon
        return self._file_icon


class CollapsibleSection(QWidget):
    """A collapsible section widget with header and content using QPropertyAnimation.

    Based on: https://github.com/MichaelVoelkel/qt-collapsible-section
    Key: Animate both widget and contentArea height simultaneously.
    """

    def __init__(self, title: str, animation_duration: int = 100, parent=None):
        super().__init__(parent)
        self._title = title
        self._animation_duration = animation_duration
        self._is_collapsed = True  # Start collapsed
        self._header_buttons: list[QPushButton] = []

        # Content area (QScrollArea) - must create before _setup_ui
        self.content_area = QScrollArea(self)
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setStyleSheet("background-color: transparent;")

        self._setup_ui()
        # Register theme listener
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        """Setup the collapsible section UI with animation support."""
        theme = get_theme()

        # Content area (QScrollArea for proper sizing) - must create first
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setMaximumHeight(0)  # Start collapsed
        self.content_area.setMinimumHeight(0)  # Start collapsed

        # Toggle button (arrow + title)
        self.toggle_button = QToolButton(self)
        self.toggle_button.setStyleSheet("QToolButton {border: none;}")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)  # Start collapsed (right arrow)
        self.toggle_button.setText(f" {self._title}")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)  # Start collapsed (unchecked)
        self.toggle_button.clicked.connect(self._on_toggle)

        # Apply theme style to toggle button
        self._apply_toggle_style()

        # Header line
        self.header_line = QFrame(self)
        self.header_line.setFrameShape(QFrame.Shape.HLine)
        self.header_line.setFrameShadow(QFrame.Shadow.Sunken)
        self.header_line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        # Animation group for simultaneous animations
        self.toggle_animation = QParallelAnimationGroup(self)

        # Animate: self.minimumHeight, self.maximumHeight, content_area.maximumHeight
        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"minimumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"maximumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self.content_area, b"maximumHeight"))

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header row
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self.toggle_button)
        # Container for extra header buttons (e.g., "+")
        self.header_buttons_widget = QWidget()
        self.header_buttons_layout = QHBoxLayout(self.header_buttons_widget)
        self.header_buttons_layout.setContentsMargins(0, 0, 8, 0)
        self.header_buttons_layout.setSpacing(4)
        header_layout.addWidget(self.header_buttons_widget)
        header_layout.addWidget(self.header_line)

        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.content_area)

        # Set initial collapsed state height
        header_height = self.toggle_button.sizeHint().height()
        self.setMinimumHeight(header_height)
        self.setMaximumHeight(header_height)

    def _apply_toggle_style(self):
        """Apply theme style to toggle button."""
        theme = get_theme()
        self.toggle_button.setStyleSheet(f"""
            QToolButton {{
                border: none;
                background-color: {theme.CHROME};
                border-radius: {theme.RADIUS_MD};
                padding: 8px 12px;
                color: {theme.TEXT};
                font-weight: bold;
                font-size: {theme.FONT_SIZE_MD};
            }}
            QToolButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)

    def add_header_button(self, text: str, callback, tooltip: str = "") -> QPushButton:
        """Add a button to the header row."""
        theme = get_theme()
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.ACCENT};
            }}
        """)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        self.header_buttons_layout.addWidget(btn)
        self._header_buttons.append(btn)
        return btn

    def _on_toggle(self, checked: bool):
        """Handle toggle button click."""
        self._is_collapsed = not checked

        if checked:  # Expanded
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Forward)
        else:  # Collapsed
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Backward)

        self.toggle_animation.start()

    def set_content_layout(self, content_layout: QVBoxLayout):
        """Set the content layout for this section.

        This is the key method that sets up animations properly.
        Must be called after adding all content widgets.

        Args:
            content_layout: The layout containing content widgets
        """
        # Clear old layout from content_area
        old_layout = self.content_area.layout()
        if old_layout:
            # Reparent widgets to avoid deletion
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        # Set new layout
        self.content_area.setLayout(content_layout)

        # Calculate heights for animation
        collapsed_height = self.sizeHint().height() - self.content_area.maximumHeight()
        content_height = content_layout.sizeHint().height()

        # Setup animations for widget height
        for i in range(self.toggle_animation.animationCount() - 1):
            anim = self.toggle_animation.animationAt(i)
            anim.setDuration(self._animation_duration)
            anim.setStartValue(collapsed_height)
            anim.setEndValue(collapsed_height + content_height)

        # Setup animation for content area height
        content_anim = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_anim.setDuration(self._animation_duration)
        content_anim.setStartValue(0)
        content_anim.setEndValue(content_height)
        # Re-bind to content_area
        content_anim.setTargetObject(self.content_area)

    def add_widget(self, widget: QWidget, stretch: int = 0):
        """Add a widget to the content area.

        Args:
            widget: Widget to add
            stretch: Stretch factor (0 = no stretch, >0 = proportional stretch)
        """
        # Get or create content widget and layout
        content_widget = self.content_area.widget()
        if content_widget is None:
            content_widget = QWidget()
            content_widget.setStyleSheet("background-color: transparent;")
            self._content_layout = QVBoxLayout(content_widget)
            self._content_layout.setContentsMargins(8, 4, 8, 8)
            self._content_layout.setSpacing(4)
            self.content_area.setWidget(content_widget)
            self.content_area.setWidgetResizable(True)

        self._content_layout.addWidget(widget, stretch)
        # Update animation values after adding widget
        self._update_animation_values()

    def _update_animation_values(self):
        """Update animation values based on current content."""
        content_widget = self.content_area.widget()
        if content_widget is None:
            return

        collapsed_height = self.toggle_button.sizeHint().height()
        content_height = content_widget.sizeHint().height()

        for i in range(self.toggle_animation.animationCount() - 1):
            anim = self.toggle_animation.animationAt(i)
            anim.setDuration(self._animation_duration)
            anim.setStartValue(collapsed_height)
            anim.setEndValue(collapsed_height + content_height)

        content_anim = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_anim.setDuration(self._animation_duration)
        content_anim.setStartValue(0)
        content_anim.setEndValue(content_height)

    def set_collapsed(self, collapsed: bool, animate: bool = True):
        """Set collapsed state.

        Args:
            collapsed: True to collapse, False to expand
            animate: Whether to animate the transition
        """
        if self._is_collapsed == collapsed:
            return

        self._is_collapsed = collapsed

        # Update button state
        self.toggle_button.setChecked(not collapsed)

        if collapsed:
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Backward)
        else:
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Forward)

        if animate:
            self.toggle_animation.start()
        else:
            # Jump to end state immediately - set values directly
            collapsed_height = self.toggle_button.sizeHint().height()
            content_widget = self.content_area.widget()
            content_height = content_widget.sizeHint().height() if content_widget else 0

            if collapsed:
                self.setMinimumHeight(collapsed_height)
                self.setMaximumHeight(collapsed_height)
                self.content_area.setMaximumHeight(0)
            else:
                self.setMinimumHeight(collapsed_height + content_height)
                self.setMaximumHeight(collapsed_height + content_height)
                self.content_area.setMaximumHeight(content_height)

    def _on_theme_changed(self):
        """Handle theme change - update header styles."""
        self._apply_toggle_style()

        # Update header buttons
        theme = get_theme()
        for btn in self._header_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.APP_BACKGROUND};
                    border: 1px solid {theme.BORDER};
                    border-radius: {theme.RADIUS_SM};
                    min-width: 26px;
                    max-width: 26px;
                    min-height: 26px;
                    max-height: 26px;
                    color: {theme.TEXT};
                    font-size: {theme.FONT_SIZE_SM};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                    border-color: {theme.ACCENT};
                }}
            """)


class SkillsSection(QWidget):
    """Section displaying loaded skills (non-collapsible inside MoreToolsSection)."""

    skill_double_clicked = pyqtSignal(str)  # skill name
    add_skill_requested = pyqtSignal()  # request to add new skill

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skill_items: dict[str, dict] = {}
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        """Setup UI."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row with title and add button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 4)
        header_layout.setSpacing(8)

        title_label = QLabel("技能")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(title_label)

        add_btn = QPushButton("+")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)
        header_layout.addStretch()

        layout.addWidget(header_widget)

        # Skills list container
        self.skills_list_widget = QWidget()
        self.skills_list_layout = QVBoxLayout(self.skills_list_widget)
        self.skills_list_layout.setContentsMargins(0, 4, 0, 0)
        self.skills_list_layout.setSpacing(4)
        layout.addWidget(self.skills_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无已加载的技能")
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 4px;
            }}
        """)
        self.skills_list_layout.addWidget(self.placeholder_label)

    def _on_add_clicked(self):
        """Handle add skill button click."""
        self.add_skill_requested.emit()

    def update_skills(self, skills: list):
        """Update the skills list display.

        Args:
            skills: List of dicts with 'name' and 'enabled' keys
        """
        # Clear existing items
        for item_data in self._skill_items.values():
            item_data['widget'].deleteLater()
        self._skill_items.clear()

        if not skills:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        for skill in skills:
            name = skill.get("name", "Unknown")
            enabled = skill.get("enabled", True)

            # Create skill item widget
            item_data = self._create_skill_item(name, enabled)
            self.skills_list_layout.addWidget(item_data['widget'])
            self._skill_items[name] = item_data

    def _create_skill_item(self, name: str, enabled: bool) -> dict:
        """Create a skill item widget.

        Returns:
            dict with 'widget', 'name_label', 'indicator', 'enabled'
        """
        theme = get_theme()
        widget = QWidget()
        widget.setMinimumHeight(32)
        widget.setStyleSheet(f"""
            QWidget#skillItem {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)
        widget.setObjectName("skillItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Status indicator
        indicator_color = theme.SUCCESS if enabled else theme.TEXT_SUBTLE
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {indicator_color}; font-size: {theme.FONT_SIZE_SM};")
        layout.addWidget(indicator)

        # Skill name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: {theme.FONT_SIZE_SM};")
        layout.addWidget(name_label)

        layout.addStretch()

        # Double-click to edit
        widget.mouseDoubleClickEvent = lambda event, n=name: self._on_double_click(n)

        return {
            'widget': widget,
            'name_label': name_label,
            'indicator': indicator,
            'enabled': enabled,
        }

    def _on_double_click(self, name: str):
        """Handle double-click on skill item."""
        self.skill_double_clicked.emit(name)

    def _on_theme_changed(self):
        """Handle theme change - update content styles."""
        theme = get_theme()

        # Update placeholder
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 4px;
            }}
        """)

        # Update skill items
        for _name, item_data in self._skill_items.items():
            widget = item_data['widget']
            name_label = item_data['name_label']
            indicator = item_data['indicator']
            enabled = item_data['enabled']

            # Update widget background
            widget.setStyleSheet(f"""
                QWidget#skillItem {{
                    background-color: {theme.APP_BACKGROUND};
                    border-radius: {theme.RADIUS_SM};
                }}
            """)

            # Update name label
            name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: {theme.FONT_SIZE_SM};")

            # Update indicator color
            indicator_color = theme.SUCCESS if enabled else theme.TEXT_SUBTLE
            indicator.setStyleSheet(f"color: {indicator_color}; font-size: {theme.FONT_SIZE_SM};")


class MCPServersSection(QWidget):
    """Section displaying MCP server status (non-collapsible inside MoreToolsSection)."""

    server_double_clicked = pyqtSignal(str)  # server name
    add_server_requested = pyqtSignal()  # request to add server
    toggle_server_requested = pyqtSignal(str)  # server name to connect/disconnect

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_items: dict[str, dict] = {}
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        """Setup UI."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row with title and add button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 4)
        header_layout.setSpacing(8)

        title_label = QLabel("MCP")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(title_label)

        add_btn = QPushButton("+")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)
        header_layout.addStretch()

        layout.addWidget(header_widget)

        # Server list container
        self.server_list_widget = QWidget()
        self.server_list_layout = QVBoxLayout(self.server_list_widget)
        self.server_list_layout.setContentsMargins(0, 4, 0, 0)
        self.server_list_layout.setSpacing(4)
        layout.addWidget(self.server_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无 MCP 配置")
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 4px;
            }}
        """)
        self.server_list_layout.addWidget(self.placeholder_label)

    def _on_add_clicked(self):
        """Handle add server button click."""
        self.add_server_requested.emit()

    def update_servers(self, servers: list):
        """Update the MCP servers list display.

        Args:
            servers: List of dicts with 'name', 'status', and 'tools_count' keys
        """
        # Clear existing items
        for item_data in self._server_items.values():
            item_data['widget'].deleteLater()
        self._server_items.clear()

        if not servers:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        for server in servers:
            name = server.get("name", "Unknown")
            status = server.get("status", "未连接")
            tools_count = server.get("tools_count", 0)

            # Create server item widget
            item_data = self._create_server_item(name, status, tools_count)
            self.server_list_layout.addWidget(item_data['widget'])
            self._server_items[name] = item_data

    def _create_server_item(self, name: str, status: str, tools_count: int) -> dict:
        """Create a server item widget.

        Returns:
            dict with 'widget', 'name_label', 'status_label', 'action_btn', 'is_connected'
        """
        theme = get_theme()
        widget = QWidget()
        widget.setMinimumHeight(32)
        widget.setStyleSheet(f"""
            QWidget#mcpItem {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)
        widget.setObjectName("mcpItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Status indicator with animation
        from harness_client.ui.interactive import StatusDot

        is_connected = status == "已连接"
        is_connecting = status == "连接中..."
        is_error = status == "错误"

        indicator = StatusDot(size=10, parent=self)
        if is_connected:
            indicator.setStatus("connected")
        elif is_connecting:
            indicator.setStatus("connecting")
        elif is_error:
            indicator.setStatus("error")
        else:
            indicator.setStatus("disconnected")
        layout.addWidget(indicator)

        # Server name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: {theme.FONT_SIZE_SM};")
        layout.addWidget(name_label)

        # Status text
        if is_connected:
            status_text = f"已连接 ({tools_count} 工具)"
            status_color = theme.STATUS_CONNECTED
        elif is_connecting:
            status_text = status
            status_color = theme.STATUS_CONNECTING
        elif is_error:
            status_text = status
            status_color = theme.STATUS_ERROR
        else:
            status_text = status
            status_color = theme.STATUS_DISCONNECTED

        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-size: {theme.FONT_SIZE_XS};")
        layout.addWidget(status_label)

        layout.addStretch()

        # Connect/Disconnect button with glow effect
        from PyQt6.QtGui import QColor

        from harness_client.ui.interactive import GlowButton

        if is_connected:
            action_btn = GlowButton(glow_color=QColor(theme.DANGER), parent=self)
            action_btn.setText("断开")
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.MCP_DISCONNECT_BG};
                    border: none;
                    border-radius: {theme.RADIUS_SM};
                    padding: 4px 8px;
                    color: {theme.MCP_DISCONNECT_TEXT};
                    font-size: {theme.FONT_SIZE_XS};
                }}
                QPushButton:hover {{
                    background-color: {theme.MCP_DISCONNECT_BG_HOVER};
                }}
            """)
        else:
            action_btn = GlowButton(glow_color=QColor(theme.ACCENT), parent=self)
            action_btn.setText("连接")
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.MCP_CONNECT_BG};
                    border: none;
                    border-radius: {theme.RADIUS_SM};
                    padding: 4px 8px;
                    color: {theme.MCP_CONNECT_TEXT};
                    font-size: {theme.FONT_SIZE_XS};
                }}
                QPushButton:hover {{
                    background-color: {theme.MCP_CONNECT_BG_HOVER};
                }}
            """)

        action_btn.clicked.connect(lambda checked, n=name: self._on_toggle_server(n))
        layout.addWidget(action_btn)

        # Double-click to toggle
        widget.mouseDoubleClickEvent = lambda event, n=name: self._on_double_click(n)

        return {
            'widget': widget,
            'name_label': name_label,
            'status_label': status_label,
            'action_btn': action_btn,
            'is_connected': is_connected,
            'status': status,  # Store original status for theme updates
        }

    def _on_toggle_server(self, name: str):
        """Handle connect/disconnect button click."""
        self.toggle_server_requested.emit(name)

    def _on_double_click(self, name: str):
        """Handle double-click on server item."""
        self.server_double_clicked.emit(name)

    def _on_theme_changed(self):
        """Handle theme change - update content styles."""
        theme = get_theme()

        # Update placeholder
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 4px;
            }}
        """)

        # Update server items
        for _name, item_data in self._server_items.items():
            widget = item_data['widget']
            name_label = item_data['name_label']
            status_label = item_data['status_label']
            action_btn = item_data['action_btn']
            is_connected = item_data['is_connected']
            status = item_data['status']

            # Update widget background
            widget.setStyleSheet(f"""
                QWidget#mcpItem {{
                    background-color: {theme.APP_BACKGROUND};
                    border-radius: {theme.RADIUS_SM};
                }}
            """)

            # Update name label
            name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: {theme.FONT_SIZE_SM};")

            # Update status label with theme colors
            if is_connected:
                status_color = theme.STATUS_CONNECTED
            elif status == "连接中...":
                status_color = theme.STATUS_CONNECTING
            elif status == "错误":
                status_color = theme.STATUS_ERROR
            else:
                status_color = theme.STATUS_DISCONNECTED
            status_label.setStyleSheet(f"color: {status_color}; font-size: {theme.FONT_SIZE_XS};")

            # Update action button
            if is_connected:
                action_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme.MCP_DISCONNECT_BG};
                        border: none;
                        border-radius: {theme.RADIUS_SM};
                        padding: 4px 8px;
                        color: {theme.MCP_DISCONNECT_TEXT};
                        font-size: {theme.FONT_SIZE_XS};
                    }}
                    QPushButton:hover {{
                        background-color: {theme.MCP_DISCONNECT_BG_HOVER};
                    }}
                """)
            else:
                action_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme.MCP_CONNECT_BG};
                        border: none;
                        border-radius: {theme.RADIUS_SM};
                        padding: 4px 8px;
                        color: {theme.MCP_CONNECT_TEXT};
                        font-size: {theme.FONT_SIZE_XS};
                    }}
                    QPushButton:hover {{
                        background-color: {theme.MCP_CONNECT_BG_HOVER};
                    }}
                """)


class FileTreeSection(CollapsibleSection):
    """Section displaying workspace file tree using QFileSystemModel."""

    file_clicked = pyqtSignal(Path)
    work_dir_changed = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__("工作区", parent=parent)
        self._work_dir = Path.cwd()
        # Add folder button in header for changing directory
        self.add_header_button("📁", self._on_change_dir, "更改工作目录")
        self._setup_content()

    def _setup_content(self):
        """Setup file tree content."""
        theme = get_theme()

        # Work directory name
        self.work_dir_label = QLabel(str(self._work_dir.name))
        self.work_dir_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
                padding: 6px;
            }}
        """)
        self.add_widget(self.work_dir_label)

        # File tree view
        self.tree_view = QTreeView()
        self.fs_model = QFileSystemModel()
        self.fs_model.setIconProvider(CustomFileIconProvider())
        self.fs_model.setRootPath(str(self._work_dir))
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(str(self._work_dir)))

        for col in [1, 2, 3]:
            self.tree_view.setColumnHidden(col, True)

        self.tree_view.setHeaderHidden(True)
        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                color: {theme.TEXT};
            }}
            QTreeView::item {{
                padding: 6px;
            }}
            QTreeView::item:selected {{
                background-color: {theme.SELECTION_ACTIVE};
            }}
            QTreeView::item:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
            QTreeView::branch {{
                background-color: {theme.APP_BACKGROUND};
            }}
        """)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self.add_widget(self.tree_view, 1)

    def set_work_dir(self, path: Path):
        """Set the work directory."""
        self._work_dir = path
        self.work_dir_label.setText(path.name if path.name else str(path))
        self.fs_model.setRootPath(str(path))
        self.tree_view.setRootIndex(self.fs_model.index(str(path)))

    def _on_item_double_clicked(self, index):
        """Handle item double-click - open file."""
        path_str = self.fs_model.filePath(index)
        path = Path(path_str)
        if path.is_file():
            self.file_clicked.emit(path)

    def _on_change_dir(self):
        """Handle change directory button click."""
        from PyQt6.QtWidgets import QFileDialog

        dir_path = QFileDialog.getExistingDirectory(
            self, "选择工作目录", str(self._work_dir)
        )
        if dir_path:
            self.set_work_dir(Path(dir_path))
            self.work_dir_changed.emit(Path(dir_path))

    def refresh(self):
        """Refresh the file tree."""
        self.fs_model.setRootPath("")  # Force refresh
        self.fs_model.setRootPath(str(self._work_dir))
        self.tree_view.setRootIndex(self.fs_model.index(str(self._work_dir)))

    def _on_theme_changed(self):
        """Handle theme change - update content styles."""
        super()._on_theme_changed()
        theme = get_theme()

        # Update work directory label
        self.work_dir_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
                padding: 6px;
            }}
        """)

        # Update tree view
        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                color: {theme.TEXT};
            }}
            QTreeView::item {{
                padding: 6px;
            }}
            QTreeView::item:selected {{
                background-color: {theme.SELECTION_ACTIVE};
            }}
            QTreeView::item:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
            QTreeView::branch {{
                background-color: {theme.APP_BACKGROUND};
            }}
        """)


class MoreToolsSection(CollapsibleSection):
    """Section containing secondary tools: Skills, MCP, Monitoring, Schedule, Browser."""

    # Forward signals from child sections
    skill_double_clicked = pyqtSignal(str)
    add_skill_requested = pyqtSignal()
    server_double_clicked = pyqtSignal(str)
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)
    schedule_requested = pyqtSignal()
    browser_toggle_requested = pyqtSignal()

    def __init__(self, monitoring_controller=None, parent=None):
        super().__init__("更多工具", parent=parent)
        self._monitoring_controller = monitoring_controller
        self._setup_content()

    def _setup_content(self):
        """Setup the tools content."""
        theme = get_theme()

        # Container for all tools
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(8)

        # Skills section (nested, no separate collapse)
        self.skills_section = SkillsSection()
        self.skills_section.skill_double_clicked.connect(self.skill_double_clicked)
        self.skills_section.add_skill_requested.connect(self.add_skill_requested)
        tools_layout.addWidget(self.skills_section)

        # MCP section (nested)
        self.mcp_section = MCPServersSection()
        self.mcp_section.server_double_clicked.connect(self.server_double_clicked)
        self.mcp_section.add_server_requested.connect(self.add_mcp_server_requested)
        self.mcp_section.toggle_server_requested.connect(self.toggle_mcp_server_requested)
        tools_layout.addWidget(self.mcp_section)

        # Monitoring sections (if controller provided)
        if self._monitoring_controller:
            from harness_client.ui.monitoring_panel import ExecutionLogSection, MonitoringSection
            self.monitoring_section = MonitoringSection(self._monitoring_controller)
            tools_layout.addWidget(self.monitoring_section)

            self.log_section = ExecutionLogSection(self._monitoring_controller)
            tools_layout.addWidget(self.log_section)
        else:
            self.monitoring_section = None
            self.log_section = None

        # Schedule button (simple button, not collapsible)
        self.schedule_btn = QPushButton("📅 排程")
        self.schedule_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.ACCENT};
            }}
        """)
        self.schedule_btn.clicked.connect(self.schedule_requested)
        tools_layout.addWidget(self.schedule_btn)

        # Browser button (simple button)
        self.browser_btn = QPushButton("🌐 浏览器")
        self.browser_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.ACCENT};
            }}
        """)
        self.browser_btn.clicked.connect(self.browser_toggle_requested)
        tools_layout.addWidget(self.browser_btn)

        self.add_widget(tools_widget)

        # Nested sections should not collapse independently - they show content directly
        # when "More Tools" is expanded

    def update_skills(self, skills: list):
        """Update skills list."""
        self.skills_section.update_skills(skills)

    def update_servers(self, servers: list):
        """Update MCP servers list."""
        self.mcp_section.update_servers(servers)

    def update_browser_status(self, is_active: bool, browser_type: str = ""):
        """Update browser button status."""
        theme = get_theme()
        if is_active:
            self.browser_btn.setText(f"● 浏览器 ({browser_type})")
            self.browser_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.ACCENT};
                    border: none;
                    border-radius: {theme.RADIUS_MD};
                    padding: 12px 16px;
                    color: white;
                    font-size: {theme.FONT_SIZE_SM};
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {theme.ACCENT_HOVER};
                }}
            """)
        else:
            self.browser_btn.setText("🌐 浏览器")
            self.browser_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.APP_BACKGROUND};
                    border: 1px solid {theme.BORDER};
                    border-radius: {theme.RADIUS_MD};
                    padding: 12px 16px;
                    color: {theme.TEXT};
                    font-size: {theme.FONT_SIZE_SM};
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                    border-color: {theme.ACCENT};
                }}
            """)

    def _on_theme_changed(self):
        """Handle theme change."""
        super()._on_theme_changed()
        theme = get_theme()

        # Update schedule button
        self.schedule_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                border-color: {theme.ACCENT};
            }}
        """)

        # Update browser button
        self.update_browser_status(
            "●" in self.browser_btn.text(),
            self.browser_btn.text().split("(")[-1].rstrip(")") if "(" in self.browser_btn.text() else ""
        )


class RightPanel(QWidget):
    """Right panel with collapsible sections for memory, files, and tools.

    Layout priorities:
    1. Memory (context-driven, expanded by default)
    2. Files (context-driven, collapsed by default)
    3. More Tools (collapsed by default) - Skills, MCP, Monitoring, Schedule, Browser
    """

    # Signals
    memory_add_requested = pyqtSignal(str)
    memory_edit_requested = pyqtSignal(str, int)
    memory_remove_requested = pyqtSignal(str, int)
    memory_importance_changed = pyqtSignal(str, int, float)  # category, index, importance
    skill_double_clicked = pyqtSignal(str)
    add_skill_requested = pyqtSignal()
    server_double_clicked = pyqtSignal(str)
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)
    file_clicked = pyqtSignal(Path)
    work_dir_changed = pyqtSignal(Path)
    schedule_requested = pyqtSignal()
    browser_toggle_requested = pyqtSignal()

    def __init__(self, monitoring_controller=None, parent=None):
        super().__init__(parent)
        self._monitoring_controller = monitoring_controller
        self.setMinimumWidth(220)
        self.setMaximumWidth(380)
        self._setup_ui()
        # Register theme listener
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        """Setup the right panel UI - context-driven layout."""
        theme = get_theme()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.CHROME};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Memory section (primary - context-driven, expanded by default)
        from harness_client.ui.memory_panel import MemorySection
        self.memory_section = MemorySection()
        self.memory_section.add_entry_requested.connect(self.memory_add_requested)
        self.memory_section.edit_entry_requested.connect(self.memory_edit_requested)
        self.memory_section.remove_entry_requested.connect(self.memory_remove_requested)
        self.memory_section.importance_changed.connect(self.memory_importance_changed)
        # Memory is expanded by default (not collapsed)
        layout.addWidget(self.memory_section)

        # 2. File tree section (context-driven, collapsed by default)
        self.file_section = FileTreeSection()
        self.file_section.file_clicked.connect(self.file_clicked)
        self.file_section.work_dir_changed.connect(self.work_dir_changed)
        self.file_section.set_collapsed(True, animate=False)
        layout.addWidget(self.file_section)

        # 3. More Tools section (collapsed by default)
        self.more_tools_section = MoreToolsSection(self._monitoring_controller)
        self.more_tools_section.skill_double_clicked.connect(self.skill_double_clicked)
        self.more_tools_section.add_skill_requested.connect(self.add_skill_requested)
        self.more_tools_section.server_double_clicked.connect(self.server_double_clicked)
        self.more_tools_section.add_mcp_server_requested.connect(self.add_mcp_server_requested)
        self.more_tools_section.toggle_mcp_server_requested.connect(self.toggle_mcp_server_requested)
        self.more_tools_section.schedule_requested.connect(self.schedule_requested)
        self.more_tools_section.browser_toggle_requested.connect(self.browser_toggle_requested)
        self.more_tools_section.set_collapsed(True, animate=False)
        layout.addWidget(self.more_tools_section)

        # Push all sections to the top when collapsed
        layout.addStretch()

    def update_memory(self, sections):
        """Update memory display."""
        self.memory_section.update_memory(sections)

    def update_memory_entries(self, category, entries):
        """Update memory display with full MemoryEntry objects.

        Args:
            category: MemoryCategory enum
            entries: List of MemoryEntry with importance metadata
        """
        self.memory_section.update_memory_with_entries(category, entries)

    def update_skills(self, skills: list):
        """Update skills list."""
        self.more_tools_section.update_skills(skills)

    def update_servers(self, servers: list):
        """Update MCP servers list."""
        self.more_tools_section.update_servers(servers)

    def update_browser_status(self, is_active: bool, browser_type: str = ""):
        """Update browser button status."""
        self.more_tools_section.update_browser_status(is_active, browser_type)

    def set_work_dir(self, path: Path):
        """Set work directory for file tree."""
        self.file_section.set_work_dir(path)

    def refresh_files(self):
        """Refresh file tree."""
        self.file_section.refresh()

    def _on_theme_changed(self):
        """Handle theme change - update all styles."""
        theme = get_theme()

        # Update panel background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.CHROME};
            }}
        """)

        # Notify sections to update their styles
        if hasattr(self.memory_section, '_on_theme_changed'):
            self.memory_section._on_theme_changed()
        if hasattr(self.more_tools_section, '_on_theme_changed'):
            self.more_tools_section._on_theme_changed()
        if hasattr(self.file_section, '_on_theme_changed'):
            self.file_section._on_theme_changed()

        self.update()
