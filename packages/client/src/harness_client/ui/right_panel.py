"""
Right panel with collapsible sections for skills, MCP servers, and file tree.
"""

import logging
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
            self._content_layout.setContentsMargins(0, 0, 0, 0)  # 无边距，由子组件控制
            self._content_layout.setSpacing(8)
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
        """Setup UI with clean banking-app style."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header row - cleaner style without separate add button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 6)
        header_layout.setSpacing(8)

        # Section title with subtle styling
        title_label = QLabel("技能")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}
        """)
        header_layout.addWidget(title_label)

        # Count badge instead of add button (cleaner)
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                background-color: {theme.CHROME};
                border-radius: 8px;
                padding: 2px 8px;
            }}
        """)
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()

        # Add button - subtle, aligned right
        add_btn = QPushButton("+")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM};
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                color: {theme.ACCENT};
            }}
        """)
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)

        layout.addWidget(header_widget)

        # Skills list container with subtle background
        self.skills_list_widget = QWidget()
        self.skills_list_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_MD};
            }}
        """)
        self.skills_list_layout = QVBoxLayout(self.skills_list_widget)
        self.skills_list_layout.setContentsMargins(0, 4, 0, 4)
        self.skills_list_layout.setSpacing(0)
        layout.addWidget(self.skills_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无技能")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 16px 8px;
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

        # Update count badge
        self.count_label.setText(str(len(skills)))

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
        """Create a skill item widget with clean list style.

        Returns:
            dict with 'widget', 'name_label', 'enabled'
        """
        theme = get_theme()
        widget = QWidget()
        widget.setMinimumHeight(36)
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setStyleSheet(f"""
            QWidget#skillItem {{
                background-color: transparent;
                border-bottom: 1px solid {theme.BORDER};
            }}
            QWidget#skillItem:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        widget.setObjectName("skillItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Skill name with status via opacity
        name_label = QLabel(name)
        name_color = theme.TEXT if enabled else theme.TEXT_SUBTLE
        name_label.setStyleSheet(f"""
            color: {name_color};
            font-size: {theme.FONT_SIZE_SM};
        """)
        layout.addWidget(name_label)

        layout.addStretch()

        # Status indicator as small badge
        status_text = "启用" if enabled else "禁用"
        status_color = theme.SUCCESS if enabled else theme.TEXT_SUBTLE
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"""
            color: {status_color};
            font-size: {theme.FONT_SIZE_XS};
            background-color: transparent;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        layout.addWidget(status_label)

        # Double-click to edit
        widget.mouseDoubleClickEvent = lambda event, n=name: self._on_double_click(n)

        return {
            'widget': widget,
            'name_label': name_label,
            'status_label': status_label,
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
                padding: 16px 8px;
            }}
        """)
        self.skills_list_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_MD};
            }}
        """)

        # Update skill items
        for _name, item_data in self._skill_items.items():
            widget = item_data['widget']
            name_label = item_data['name_label']
            status_label = item_data['status_label']
            enabled = item_data['enabled']

            # Update widget style
            widget.setStyleSheet(f"""
                QWidget#skillItem {{
                    background-color: transparent;
                    border-bottom: 1px solid {theme.BORDER};
                }}
                QWidget#skillItem:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                }}
            """)

            # Update name label
            name_color = theme.TEXT if enabled else theme.TEXT_SUBTLE
            name_label.setStyleSheet(f"color: {name_color}; font-size: {theme.FONT_SIZE_SM};")

            # Update status label
            status_color = theme.SUCCESS if enabled else theme.TEXT_SUBTLE
            status_label.setStyleSheet(f"color: {status_color}; font-size: {theme.FONT_SIZE_XS};")


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
        """Setup UI with clean banking-app style."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(2)

        # Header row - cleaner style
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 6)
        header_layout.setSpacing(8)

        # Section title
        title_label = QLabel("MCP")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
        """)
        header_layout.addWidget(title_label)

        # Count badge
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                background-color: {theme.CHROME};
                border-radius: 8px;
                padding: 2px 8px;
            }}
        """)
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()

        # Add button - subtle
        add_btn = QPushButton("+")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM};
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
                color: {theme.ACCENT};
            }}
        """)
        add_btn.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(add_btn)

        layout.addWidget(header_widget)

        # Server list container with subtle background
        self.server_list_widget = QWidget()
        self.server_list_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_MD};
            }}
        """)
        self.server_list_layout = QVBoxLayout(self.server_list_widget)
        self.server_list_layout.setContentsMargins(0, 4, 0, 4)
        self.server_list_layout.setSpacing(0)
        layout.addWidget(self.server_list_widget)

        # Placeholder label
        self.placeholder_label = QLabel("暂无服务器")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_SM};
                padding: 16px 8px;
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

        # Update count badge
        connected_count = sum(1 for s in servers if s.get("status") == "已连接")
        self.count_label.setText(f"{connected_count}/{len(servers)}")

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
        """Create a server item widget with clean list style.

        Returns:
            dict with 'widget', 'name_label', 'status_label', 'action_btn', 'is_connected'
        """
        theme = get_theme()
        widget = QWidget()
        widget.setMinimumHeight(44)
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setStyleSheet(f"""
            QWidget#mcpItem {{
                background-color: transparent;
                border-bottom: 1px solid {theme.BORDER};
            }}
            QWidget#mcpItem:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        widget.setObjectName("mcpItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        is_connected = status == "已连接"
        is_connecting = status == "连接中..."
        is_error = status == "错误"

        # Server name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            color: {theme.TEXT};
            font-size: {theme.FONT_SIZE_SM};
            font-weight: 500;
        """)
        layout.addWidget(name_label)

        # Status as compact badge
        if is_connected:
            status_badge = f"● {tools_count} 工具"
            status_color = theme.SUCCESS
        elif is_connecting:
            status_badge = "● 连接中"
            status_color = theme.STATUS_CONNECTING
        elif is_error:
            status_badge = "● 错误"
            status_color = theme.STATUS_ERROR
        else:
            status_badge = "○ 未连接"
            status_color = theme.TEXT_SUBTLE

        status_label = QLabel(status_badge)
        status_label.setStyleSheet(f"""
            color: {status_color};
            font-size: {theme.FONT_SIZE_XS};
        """)
        layout.addWidget(status_label)

        layout.addStretch()

        # Action button - subtle text button
        action_btn = QPushButton("断开" if is_connected else "连接")
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_connected:
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: {theme.RADIUS_SM};
                    padding: 4px 10px;
                    color: {theme.DANGER};
                    font-size: {theme.FONT_SIZE_XS};
                }}
                QPushButton:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                }}
            """)
        else:
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: {theme.RADIUS_SM};
                    padding: 4px 10px;
                    color: {theme.ACCENT};
                    font-size: {theme.FONT_SIZE_XS};
                }}
                QPushButton:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                }}
            """)

        action_btn.clicked.connect(lambda checked, n=name: self._on_toggle_server(n))
        layout.addWidget(action_btn)

        # Double-click to edit
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
                padding: 16px 8px;
            }}
        """)
        self.server_list_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_MD};
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

            # Update widget style
            widget.setStyleSheet(f"""
                QWidget#mcpItem {{
                    background-color: transparent;
                    border-bottom: 1px solid {theme.BORDER};
                }}
                QWidget#mcpItem:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
                }}
            """)

            # Update name label
            name_label.setStyleSheet(f"""
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: 500;
            """)

            # Update status label with theme colors
            if is_connected:
                status_color = theme.SUCCESS
            elif status == "连接中...":
                status_color = theme.STATUS_CONNECTING
            elif status == "错误":
                status_color = theme.STATUS_ERROR
            else:
                status_color = theme.TEXT_SUBTLE
            status_label.setStyleSheet(f"color: {status_color}; font-size: {theme.FONT_SIZE_XS};")

            # Update action button
            if is_connected:
                action_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: {theme.RADIUS_SM};
                        padding: 4px 10px;
                        color: {theme.DANGER};
                        font-size: {theme.FONT_SIZE_XS};
                    }}
                    QPushButton:hover {{
                        background-color: {theme.HOVER_NEUTRAL};
                    }}
                """)
            else:
                action_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: {theme.RADIUS_SM};
                        padding: 4px 10px;
                        color: {theme.ACCENT};
                        font-size: {theme.FONT_SIZE_XS};
                    }}
                    QPushButton:hover {{
                        background-color: {theme.HOVER_NEUTRAL};
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
    """Section containing secondary tools: Skills, MCP, Monitoring, Schedule, Browser.

    Caps its expanded height so it doesn't overflow the right panel.
    """

    # Forward signals from child sections
    skill_double_clicked = pyqtSignal(str)
    add_skill_requested = pyqtSignal()
    server_double_clicked = pyqtSignal(str)
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)
    schedule_requested = pyqtSignal()
    browser_toggle_requested = pyqtSignal()

    # Max content height — when expanded, internal scroll handles overflow
    # 25% larger than before (350 * 1.25 ≈ 438)
    _MAX_CONTENT_HEIGHT = 438

    def __init__(self, monitoring_controller=None, parent=None):
        super().__init__("更多工具", parent=parent)
        self._monitoring_controller = monitoring_controller
        self._logger = logging.getLogger(__name__)
        self._capped_content_height = 0
        self._collapsed_header_height = 0
        self._animation_connected = False  # Track if we connected the signal
        self._setup_content()
        # Connect animation finished signal AFTER setup to avoid early triggers
        self.toggle_animation.finished.connect(self._on_animation_finished)
        self._animation_connected = True
        self._logger.debug(
            f"MoreToolsSection.__init__: initial max_height={self.maximumHeight()}, "
            f"content_max_height={self.content_area.maximumHeight()}"
        )

    def _on_toggle(self, checked: bool):
        """Override to cap animation values before starting animation.

        The base class _on_toggle starts the animation directly, but we need
        to cap the end values to _MAX_CONTENT_HEIGHT first.
        """
        self._is_collapsed = not checked

        # Update button arrow
        if checked:  # Expanded
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Forward)
        else:  # Collapsed
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_animation.setDirection(QAbstractAnimation.Direction.Backward)

        # Get current content height
        content_widget = self.content_area.widget()
        content_height = content_widget.sizeHint().height() if content_widget else 0
        collapsed_height = self.toggle_button.sizeHint().height()

        # Cap the height
        capped_height = min(content_height, self._MAX_CONTENT_HEIGHT)

        self._logger.debug(
            f"MoreToolsSection._on_toggle: checked={checked}, "
            f"content_height={content_height}, capped_height={capped_height}, "
            f"collapsed_height={collapsed_height}"
        )

        # Set animation values with cap
        for i in range(self.toggle_animation.animationCount() - 1):
            anim = self.toggle_animation.animationAt(i)
            anim.setDuration(self._animation_duration)
            anim.setStartValue(collapsed_height)
            anim.setEndValue(collapsed_height + capped_height)

        content_anim = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_anim.setDuration(self._animation_duration)
        content_anim.setStartValue(0)
        content_anim.setEndValue(capped_height)

        # Store capped height for use after animation
        self._capped_content_height = capped_height if checked else 0
        self._collapsed_header_height = collapsed_height

        self._logger.debug(
            f"Animation end values: widget={collapsed_height + capped_height}, "
            f"content_area={capped_height}"
        )

        self.toggle_animation.start()

    def _on_animation_finished(self):
        """Lock the height after animation completes to prevent resizing.

        This is critical: QScrollArea can resize itself after animation ends,
        so we need to enforce the maximum height constraint.
        """
        # Skip if header height not set yet (initialization phase)
        if self._collapsed_header_height <= 0:
            self._logger.debug(
                f"Animation finished skipped: header_height={self._collapsed_header_height} (initialization)"
            )
            return

        if self._is_collapsed:
            # Collapsed state - lock to header height only
            self.setMaximumHeight(self._collapsed_header_height)
            self.content_area.setMaximumHeight(0)
            self._logger.debug(
                f"Animation finished (collapsed): max_height={self._collapsed_header_height}"
            )
        else:
            # Expanded state - lock to capped height
            total_height = self._collapsed_header_height + self._capped_content_height
            self.setMaximumHeight(total_height)
            self.content_area.setMaximumHeight(self._capped_content_height)
            self._logger.debug(
                f"Animation finished (expanded): max_height={total_height}, "
                f"content_max_height={self._capped_content_height}"
            )

    def set_collapsed(self, collapsed: bool, animate: bool = True):
        """Override to cap expanded content height.

        Caps the animation end value so content_area maximumHeight
        never exceeds _MAX_CONTENT_HEIGHT. This prevents the section
        from filling the entire right panel when expanded.
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
            # Cap the animation end value for the widget height (indices 0,1)
            collapsed_height = self.toggle_button.sizeHint().height()
            for i in range(self.toggle_animation.animationCount() - 1):
                anim = self.toggle_animation.animationAt(i)
                anim.setEndValue(collapsed_height + self._MAX_CONTENT_HEIGHT)
            # Cap the animation end value for content_area
            content_anim = self.toggle_animation.animationAt(
                self.toggle_animation.animationCount() - 1
            )
            content_anim.setEndValue(self._MAX_CONTENT_HEIGHT)
            self.toggle_animation.start()
        else:
            collapsed_height = self.toggle_button.sizeHint().height()
            content_widget = self.content_area.widget()
            content_height = (
                min(content_widget.sizeHint().height(), self._MAX_CONTENT_HEIGHT)
                if content_widget
                else 0
            )

            if collapsed:
                self.setMinimumHeight(collapsed_height)
                self.setMaximumHeight(collapsed_height)
                self.content_area.setMaximumHeight(0)
            else:
                self.setMinimumHeight(collapsed_height + content_height)
                self.setMaximumHeight(collapsed_height + content_height)
                self.content_area.setMaximumHeight(content_height)

    def _setup_content(self):
        """Setup the tools content with clean banking-app style."""
        theme = get_theme()

        # Container for all tools
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(12)

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

        # Quick actions row - clean icon buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 8, 0, 0)
        actions_layout.setSpacing(8)

        # Schedule button - clean, minimal
        self.schedule_btn = QPushButton("排程")
        self.schedule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.schedule_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: none;
                border-radius: {theme.RADIUS_MD};
                padding: 10px 14px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        self.schedule_btn.clicked.connect(self.schedule_requested)
        actions_layout.addWidget(self.schedule_btn)

        # Browser button - clean, minimal
        self.browser_btn = QPushButton("浏览器")
        self.browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browser_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.APP_BACKGROUND};
                border: none;
                border-radius: {theme.RADIUS_MD};
                padding: 10px 14px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
            }}
        """)
        self.browser_btn.clicked.connect(self.browser_toggle_requested)
        actions_layout.addWidget(self.browser_btn)

        tools_layout.addWidget(actions_widget)

        self.add_widget(tools_widget)

        # NOTE: Do NOT set content_area maximumHeight here!
        # Base class already sets it to 0 for collapsed state.
        # Height is controlled by _on_toggle() animation with capping.

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
            self.browser_btn.setText(f"● {browser_type}")
            self.browser_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.ACCENT};
                    border: none;
                    border-radius: {theme.RADIUS_MD};
                    padding: 10px 14px;
                    color: white;
                    font-size: {theme.FONT_SIZE_SM};
                }}
                QPushButton:hover {{
                    background-color: {theme.ACCENT_HOVER};
                }}
            """)
        else:
            self.browser_btn.setText("浏览器")
            self.browser_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.APP_BACKGROUND};
                    border: none;
                    border-radius: {theme.RADIUS_MD};
                    padding: 10px 14px;
                    color: {theme.TEXT};
                    font-size: {theme.FONT_SIZE_SM};
                }}
                QPushButton:hover {{
                    background-color: {theme.HOVER_NEUTRAL};
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
                border: none;
                border-radius: {theme.RADIUS_MD};
                padding: 10px 14px;
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_NEUTRAL};
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
