"""
Schedule panel for managing automated tasks with cron/interval triggers.

Features:
- Display schedule list with status indicators
- Add/edit/delete schedules
- Toggle schedule enabled state
- Cron expression validation and preview
"""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener
from harness_client.ui.icons import create_schedule_icon, create_play_icon, create_pause_icon
from harness_client.ui.dialog_styles import (
    DIALOG_MARGINS,
    DIALOG_MIN_WIDTH,
    DIALOG_SPACING,
    create_standard_form_layout,
    get_dialog_stylesheet,
    get_muted_label_stylesheet,
    get_groupbox_stylesheet,
)
from harness_client.ui.right_panel import CollapsibleSection


class ScheduleItemWidget(QWidget):
    """Widget for a single schedule item with status and controls."""

    toggle_requested = pyqtSignal(str)  # schedule_id
    edit_requested = pyqtSignal(str)  # schedule_id
    delete_requested = pyqtSignal(str)  # schedule_id

    def __init__(self, schedule_data: dict, parent=None):
        """Initialize schedule item widget.

        Args:
            schedule_data: Dict with keys: id, name, status, trigger_type, trigger_value, enabled
        """
        super().__init__(parent)
        self._schedule_id = schedule_data.get("id", "")
        self._setup_ui(schedule_data)
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self, data: dict):
        """Setup UI components."""
        theme = get_theme()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Status indicator (colored dot)
        self._status_label = QLabel()
        self._update_status_indicator(data.get("status", "idle"), data.get("enabled", True))
        layout.addWidget(self._status_label)

        # Schedule info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        # Name
        self._name_label = QLabel(data.get("name", ""))
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        info_layout.addWidget(self._name_label)

        # Trigger info
        trigger_type = data.get("trigger_type", "cron")
        trigger_value = data.get("trigger_value", "")
        trigger_text = f"Cron: {trigger_value}" if trigger_type == "cron" else f"间隔: {trigger_value}秒"
        self._trigger_label = QLabel(trigger_text)
        self._trigger_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
            }}
        """)
        info_layout.addWidget(self._trigger_label)

        layout.addWidget(info_widget, 1)

        # Toggle button (play/pause)
        self._toggle_btn = QLabel()
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_toggle_button(data.get("enabled", True))
        self._toggle_btn.mousePressEvent = lambda e: self.toggle_requested.emit(self._schedule_id)
        layout.addWidget(self._toggle_btn)

        # Edit button
        self._edit_btn = QLabel("✏")
        self._edit_btn.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 14px;
            }}
        """)
        self._edit_btn.setFixedSize(24, 24)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.mousePressEvent = lambda e: self.edit_requested.emit(self._schedule_id)
        layout.addWidget(self._edit_btn)

        # Delete button
        self._delete_btn = QLabel("×")
        self._delete_btn.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
            }}
        """)
        self._delete_btn.setFixedSize(24, 24)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.mousePressEvent = lambda e: self.delete_requested.emit(self._schedule_id)
        layout.addWidget(self._delete_btn)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)

    def _update_status_indicator(self, status: str, enabled: bool):
        """Update the status indicator dot."""
        theme = get_theme()

        if not enabled:
            color = "#6b7280"  # gray - paused
            tooltip = "已暂停"
        elif status == "running":
            color = "#22c55e"  # green - running
            tooltip = "运行中"
        elif status == "error":
            color = "#ef4444"  # red - error
            tooltip = "错误"
        else:
            color = "#f59e0b"  # orange - idle
            tooltip = "空闲"

        self._status_label.setText("●")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
            }}
        """)
        self._status_label.setToolTip(tooltip)

    def _update_toggle_button(self, enabled: bool):
        """Update the toggle button icon."""
        theme = get_theme()
        if enabled:
            icon = create_pause_icon(16, QColor(theme.TEXT_SUBTLE))
            self._toggle_btn.setToolTip("暂停")
        else:
            icon = create_play_icon(16, QColor(theme.ACCENT))
            self._toggle_btn.setToolTip("启动")
        self._toggle_btn.setPixmap(icon.pixmap(16, 16))

    def _on_theme_changed(self):
        """Handle theme change."""
        theme = get_theme()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_SM};
                font-weight: bold;
            }}
        """)
        self._trigger_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
            }}
        """)
        self._delete_btn.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: 18px;
            }}
        """)


class ScheduleDialog(QDialog):
    """Dialog for adding or editing a schedule."""

    def __init__(self, parent=None, schedule_data: dict = None):
        """Initialize dialog.

        Args:
            parent: Parent widget
            schedule_data: Existing schedule data for editing (None for new)
        """
        super().__init__(parent)
        self._schedule_data = schedule_data or {}
        self.setMinimumWidth(DIALOG_MIN_WIDTH)
        self.setStyleSheet(get_dialog_stylesheet())
        self._setup_ui()

        if schedule_data:
            self._populate_fields(schedule_data)
            self.setWindowTitle("编辑排程")
        else:
            self.setWindowTitle("新建排程")

    def _setup_ui(self):
        """Setup dialog UI with professional form layout."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(DIALOG_SPACING)

        # Form with proper alignment
        form = create_standard_form_layout()

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("排程名称")
        form.addRow("名称:", self._name_edit)

        # Goal
        self._goal_edit = QLineEdit()
        self._goal_edit.setPlaceholderText("任务目标，如：生成每日报告")
        form.addRow("目标:", self._goal_edit)

        # Trigger type
        self._trigger_type_combo = QComboBox()
        self._trigger_type_combo.addItems(["Cron 表达式", "固定间隔"])
        self._trigger_type_combo.currentIndexChanged.connect(self._on_trigger_type_changed)
        form.addRow("触发类型:", self._trigger_type_combo)

        layout.addLayout(form)

        # Trigger value section (with border)
        trigger_group = QGroupBox("触发设置")
        trigger_group.setStyleSheet(get_groupbox_stylesheet())
        trigger_layout = QVBoxLayout(trigger_group)
        trigger_layout.setSpacing(6)

        # Trigger value (stacked widget for cron/interval)
        self._trigger_stack = QStackedWidget()

        # Cron input
        cron_widget = QWidget()
        cron_layout = QVBoxLayout(cron_widget)
        cron_layout.setContentsMargins(8, 4, 8, 4)
        cron_layout.setSpacing(4)

        self._cron_edit = QLineEdit()
        self._cron_edit.setPlaceholderText("0 9 * * *")
        self._cron_edit.textChanged.connect(self._validate_cron)
        cron_layout.addWidget(self._cron_edit)

        # Cron preview and help in one row
        cron_info = QLabel("格式: 分 时 日 月 周 · 例如 0 9 * * * = 每天 9:00")
        cron_info.setStyleSheet(get_muted_label_stylesheet())
        cron_info.setWordWrap(True)
        cron_layout.addWidget(cron_info)

        # Cron validation feedback
        self._cron_preview = QLabel()
        self._cron_preview.setStyleSheet(get_muted_label_stylesheet())
        cron_layout.addWidget(self._cron_preview)

        self._trigger_stack.addWidget(cron_widget)

        # Interval input
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(8, 4, 8, 4)
        interval_layout.setSpacing(8)

        self._interval_spin = QSpinBox()
        self._interval_spin.setMinimum(1)
        self._interval_spin.setMaximum(86400)
        self._interval_spin.setValue(300)
        self._interval_spin.setSuffix(" 秒")
        self._interval_spin.setMinimumWidth(120)
        interval_layout.addWidget(self._interval_spin)

        interval_layout.addWidget(QLabel("(1-86400 秒)"))
        interval_layout.addStretch()

        self._trigger_stack.addWidget(interval_widget)

        trigger_layout.addWidget(self._trigger_stack)
        layout.addWidget(trigger_group)

        # Settings row (max iterations + timeout)
        settings_group = QGroupBox("执行设置")
        settings_group.setStyleSheet(get_groupbox_stylesheet())
        settings_layout = create_standard_form_layout()
        settings_group.setLayout(settings_layout)

        self._max_iter_spin = QSpinBox()
        self._max_iter_spin.setMinimum(1)
        self._max_iter_spin.setMaximum(1000)
        self._max_iter_spin.setValue(50)
        settings_layout.addRow("最大迭代:", self._max_iter_spin)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setMinimum(60)
        self._timeout_spin.setMaximum(86400)
        self._timeout_spin.setValue(3600)
        self._timeout_spin.setSuffix(" 秒")
        settings_layout.addRow("超时:", self._timeout_spin)

        layout.addWidget(settings_group)

        layout.addStretch()

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set up focus chain for keyboard navigation
        self._setup_focus_chain()

    def _setup_focus_chain(self):
        """Set up tab order for keyboard navigation."""
        self.setTabOrder(self._name_edit, self._goal_edit)
        self.setTabOrder(self._goal_edit, self._trigger_type_combo)
        self.setTabOrder(self._trigger_type_combo, self._cron_edit)
        self.setTabOrder(self._cron_edit, self._interval_spin)
        self.setTabOrder(self._interval_spin, self._max_iter_spin)
        self.setTabOrder(self._max_iter_spin, self._timeout_spin)

    def _on_trigger_type_changed(self, index: int):
        """Handle trigger type change."""
        self._trigger_stack.setCurrentIndex(index)

    def _validate_cron(self, text: str):
        """Validate cron expression and show preview."""
        theme = get_theme()
        if not text.strip():
            self._cron_preview.setText("下次运行: -")
            return

        # Basic validation
        parts = text.strip().split()
        if len(parts) != 5:
            self._cron_preview.setText("❌ Cron 表达式需要 5 个字段")
            self._cron_preview.setStyleSheet(f"color: {theme.DANGER}; font-size: {theme.FONT_SIZE_XS};")
            return

        # Try to get next run time
        try:
            from croniter import croniter
            cron = croniter(text.strip(), datetime.now())
            next_run = cron.get_next(datetime)
            next_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
            self._cron_preview.setText(f"✓ 下次运行: {next_str}")
            self._cron_preview.setStyleSheet(f"color: {theme.SUCCESS}; font-size: {theme.FONT_SIZE_XS};")
        except ImportError:
            self._cron_preview.setText("⚠ 安装 croniter 以获取预览")
            self._cron_preview.setStyleSheet(f"color: {theme.WARNING}; font-size: {theme.FONT_SIZE_XS};")
        except Exception as e:
            self._cron_preview.setText(f"❌ 无效: {str(e)[:30]}")
            self._cron_preview.setStyleSheet(f"color: {theme.DANGER}; font-size: {theme.FONT_SIZE_XS};")

    def _populate_fields(self, data: dict):
        """Populate fields from existing schedule data."""
        self._name_edit.setText(data.get("name", ""))
        self._goal_edit.setText(data.get("goal", ""))

        trigger_type = data.get("trigger_type", "cron")
        self._trigger_type_combo.setCurrentIndex(0 if trigger_type == "cron" else 1)

        if trigger_type == "cron":
            self._cron_edit.setText(data.get("trigger_value", ""))
        else:
            try:
                self._interval_spin.setValue(int(data.get("trigger_value", "300")))
            except ValueError:
                pass

        self._max_iter_spin.setValue(data.get("max_iterations", 50))
        self._timeout_spin.setValue(data.get("timeout_seconds", 3600))

    def get_schedule_data(self) -> dict:
        """Get schedule data from form fields."""
        trigger_type = "cron" if self._trigger_type_combo.currentIndex() == 0 else "interval"
        trigger_value = self._cron_edit.text().strip() if trigger_type == "cron" else str(self._interval_spin.value())

        data = {
            "name": self._name_edit.text().strip(),
            "goal": self._goal_edit.text().strip(),
            "trigger_type": trigger_type,
            "trigger_value": trigger_value,
            "max_iterations": self._max_iter_spin.value(),
            "timeout_seconds": self._timeout_spin.value(),
            "enabled": True,
        }

        # Preserve id if editing
        if self._schedule_data.get("id"):
            data["id"] = self._schedule_data["id"]

        return data


class ScheduleSection(CollapsibleSection):
    """Section for managing schedules in the right panel."""

    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)  # schedule_id
    delete_requested = pyqtSignal(str)  # schedule_id
    toggle_requested = pyqtSignal(str)  # schedule_id

    def __init__(self, parent=None):
        """Initialize schedule section."""
        super().__init__("排程", parent=parent)
        self._setup_content()
        # Theme listener registered in CollapsibleSection

    def _setup_content(self):
        """Setup section content."""
        theme = get_theme()

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.BORDER};
                border-radius: 3px;
            }}
        """)
        self.add_widget(self._scroll, 1)

        # Container
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(8)
        self._scroll.setWidget(container)

        # Add button
        self._add_btn = QLabel("+ 新建排程")
        self._add_btn.setStyleSheet(f"""
            QLabel {{
                color: {theme.ACCENT};
                font-size: {theme.FONT_SIZE_SM};
                padding: 8px;
            }}
        """)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.mousePressEvent = lambda e: self.add_requested.emit()
        self._container_layout.addWidget(self._add_btn)

        # Schedule list container
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._container_layout.addWidget(self._list_widget)

        # Placeholder
        self._placeholder = QLabel("暂无排程任务")
        self._placeholder.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 16px;
            }}
        """)
        self._list_layout.addWidget(self._placeholder)

        self._container_layout.addStretch()

        # Store item widgets
        self._item_widgets: list[ScheduleItemWidget] = []

    def update_schedules(self, schedules: list):
        """Update the schedule list display.

        Args:
            schedules: List of ScheduleConfig objects or dicts
        """
        # Clear existing items
        for widget in self._item_widgets:
            widget.deleteLater()
        self._item_widgets.clear()

        if not schedules:
            self._placeholder.setVisible(True)
            return

        self._placeholder.setVisible(False)

        for schedule in schedules:
            # Convert to dict if needed
            if hasattr(schedule, 'to_dict'):
                data = schedule.to_dict()
            else:
                data = schedule

            item_widget = ScheduleItemWidget(data)
            item_widget.toggle_requested.connect(self.toggle_requested.emit)
            item_widget.edit_requested.connect(self.edit_requested.emit)
            item_widget.delete_requested.connect(self.delete_requested.emit)
            self._list_layout.addWidget(item_widget)
            self._item_widgets.append(item_widget)

    def _on_theme_changed(self):
        """Handle theme change."""
        super()._on_theme_changed()
        theme = get_theme()

        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.BORDER};
                border-radius: 3px;
            }}
        """)

        self._add_btn.setStyleSheet(f"""
            QLabel {{
                color: {theme.ACCENT};
                font-size: {theme.FONT_SIZE_SM};
                padding: 8px;
            }}
        """)

        self._placeholder.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 16px;
            }}
        """)


class SchedulePanel(QWidget):
    """Full panel for schedule management (alternative to collapsed section)."""

    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        """Initialize schedule panel."""
        super().__init__(parent)
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        """Setup UI components."""
        theme = get_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(f"background-color: {theme.CHROME};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("排程管理")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SIZE_LG};
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)

        # Schedule section
        self._section = ScheduleSection()
        self._section.add_requested.connect(self.add_requested.emit)
        self._section.edit_requested.connect(self.edit_requested.emit)
        self._section.delete_requested.connect(self.delete_requested.emit)
        self._section.toggle_requested.connect(self.toggle_requested.emit)
        layout.addWidget(self._section)

        self.setStyleSheet(f"background-color: {theme.APP_BACKGROUND};")

    def update_schedules(self, schedules: list):
        """Update the schedule list."""
        self._section.update_schedules(schedules)

    def _on_theme_changed(self):
        """Handle theme change."""
        theme = get_theme()
        self.setStyleSheet(f"background-color: {theme.APP_BACKGROUND};")
