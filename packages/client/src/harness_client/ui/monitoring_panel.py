"""
Monitoring Panel for Harness Client.

Displays real-time metrics:
- Token usage (input, output, cache)
- Session statistics (iterations, tools, duration)
- Cost estimation
- Token usage trend chart
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from harness_client.controllers.monitoring_controller import (
    LogEntry,
    MonitoringController,
)
from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener
from harness_client.ui.right_panel import CollapsibleSection

logger = logging.getLogger(__name__)


class TrendChart(QWidget):
    """
    Token 使用趋势柱状图 - 主题感知绘制。

    使用 QPainter 自定义绘制，支持主题切换。
    """

    def __init__(self, max_items: int = 10, parent=None):
        super().__init__(parent)
        self._data: list[int] = []
        self._max_items = max_items
        self.setFixedHeight(60)
        self.setMinimumWidth(180)
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def set_data(self, data: list[int]):
        """设置趋势数据"""
        self._data = data[-self._max_items:] if data else []
        self.update()

    def _on_theme_changed(self):
        """主题切换时重绘"""
        self.update()

    def paintEvent(self, event):
        """绘制柱状图 - 动态获取主题"""
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.APP_BACKGROUND)))
        painter.drawRect(self.rect())

        if not self._data:
            # 无数据时显示占位文本
            painter.setPen(QColor(theme.TEXT_SUBTLE))
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "暂无数据"
            )
            painter.end()
            return

        # 计算柱状图参数
        padding = 8
        bar_spacing = 4
        available_width = self.width() - 2 * padding
        available_height = self.height() - 2 * padding

        bar_width = (available_width - (len(self._data) - 1) * bar_spacing) / len(self._data)
        max_value = max(self._data) if self._data else 1

        # 绘制柱子
        bar_color = QColor(theme.ACCENT)
        bar_color.setAlpha(180)  # 略微透明

        for i, value in enumerate(self._data):
            # 计算高度和位置
            bar_height = (value / max_value) * available_height if max_value > 0 else 0
            x = padding + i * (bar_width + bar_spacing)
            y = self.height() - padding - bar_height

            # 绘制圆角矩形
            bar_rect = QRectF(x, y, bar_width, bar_height)
            painter.setBrush(QBrush(bar_color))
            painter.drawRoundedRect(bar_rect, 2, 2)

        painter.end()


class MetricsRow(QWidget):
    """指标行组件 - 显示标签和数值"""

    def __init__(self, label: str, value: str = "0", parent=None):
        super().__init__(parent)
        self._setup_ui(label, value)
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self, label: str, value: str):
        theme = get_theme()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._label = QLabel(label)
        self._label.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
        layout.addWidget(self._label)

        layout.addStretch()

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self._value)

    def set_value(self, value: str):
        """设置数值"""
        self._value.setText(value)

    def set_value_color(self, color: str):
        """设置数值颜色"""
        self._value.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
            }}
        """)

    def _on_theme_changed(self):
        """主题切换"""
        theme = get_theme()
        self._label.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
        self._value.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT};
                font-weight: bold;
            }}
        """)


class MonitoringSection(CollapsibleSection):
    """监控区块 - 可折叠"""

    def __init__(self, controller: MonitoringController, parent=None):
        self._controller = controller
        super().__init__("监控", parent)
        self._setup_content()

        # 连接信号
        self._controller.metrics_updated.connect(self._on_metrics_updated)

    def _setup_content(self):
        """设置内容"""
        theme = get_theme()

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
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
        self.add_widget(scroll, 1)

        # 容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        scroll.setWidget(container)

        # === Token 使用区块 ===
        token_group = QGroupBox("Token 使用")
        token_group.setStyleSheet(f"""
            QGroupBox {{
                color: {theme.TEXT};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        token_layout = QVBoxLayout(token_group)
        token_layout.setContentsMargins(8, 12, 8, 8)
        token_layout.setSpacing(4)

        # Token 指标网格
        token_grid = QGridLayout()
        token_grid.setSpacing(8)

        self._input_label = MetricsRow("输入:")
        self._output_label = MetricsRow("输出:")
        self._cache_label = MetricsRow("缓存:")

        token_grid.addWidget(self._input_label, 0, 0)
        token_grid.addWidget(self._output_label, 0, 1)
        token_grid.addWidget(self._cache_label, 1, 0)

        token_layout.addLayout(token_grid)
        layout.addWidget(token_group)

        # === 会话统计区块 ===
        session_group = QGroupBox("本次会话")
        session_group.setStyleSheet(f"""
            QGroupBox {{
                color: {theme.TEXT};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        session_layout = QVBoxLayout(session_group)
        session_layout.setContentsMargins(8, 12, 8, 8)
        session_layout.setSpacing(4)

        self._iterations_label = MetricsRow("迭代:")
        self._tools_label = MetricsRow("工具调用:")
        self._duration_label = MetricsRow("耗时:")

        session_layout.addWidget(self._iterations_label)
        session_layout.addWidget(self._tools_label)
        session_layout.addWidget(self._duration_label)

        layout.addWidget(session_group)

        # === 成本估算 ===
        cost_widget = QWidget()
        cost_layout = QHBoxLayout(cost_widget)
        cost_layout.setContentsMargins(0, 4, 0, 4)

        cost_icon = QLabel("💰")
        cost_icon.setStyleSheet("font-size: 14px;")
        cost_layout.addWidget(cost_icon)

        cost_title = QLabel("成本:")
        cost_title.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
        cost_layout.addWidget(cost_title)

        cost_layout.addStretch()

        self._cost_label = QLabel("$0.00")
        self._cost_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.ACCENT};
                font-weight: bold;
                font-size: {theme.FONT_SIZE_MD};
            }}
        """)
        cost_layout.addWidget(self._cost_label)

        layout.addWidget(cost_widget)

        # === 趋势图 ===
        trend_label = QLabel("📈 趋势 (最近请求)")
        trend_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: {theme.FONT_SIZE_XS};")
        layout.addWidget(trend_label)

        self._trend_chart = TrendChart()
        layout.addWidget(self._trend_chart)

        # 间距
        layout.addStretch()

    def _on_metrics_updated(self):
        """指标更新时刷新显示"""
        metrics = self._controller.metrics

        # Token 使用
        self._input_label.set_value(f"{metrics.input_tokens:,}")
        self._output_label.set_value(f"{metrics.output_tokens:,}")

        cache_text = f"{metrics.cache_read_tokens:,}"
        if metrics.cache_read_tokens > 0:
            cache_text += f" ({metrics.cache_hit_rate():.0%})"
        self._cache_label.set_value(cache_text)

        # 会话统计
        self._iterations_label.set_value(str(metrics.iterations))
        self._tools_label.set_value(
            f"{metrics.tool_calls} (成功: {metrics.tool_success}, 失败: {metrics.tool_errors})"
        )
        self._duration_label.set_value(f"{metrics.duration_seconds():.1f}s")

        # 成本
        self._cost_label.setText(f"${metrics.cost_usd:.2f}")

        # 趋势图
        self._trend_chart.set_data(metrics.token_history)

    def _on_theme_changed(self):
        """主题切换"""
        super()._on_theme_changed()
        theme = get_theme()

        # 更新分组框样式
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(f"""
                QGroupBox {{
                    color: {theme.TEXT};
                    border: 1px solid {theme.BORDER};
                    border-radius: {theme.RADIUS_SM};
                    margin-top: 8px;
                    padding-top: 8px;
                    font-weight: bold;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px;
                }}
            """)

        # 更新成本标签
        self._cost_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.ACCENT};
                font-weight: bold;
                font-size: {theme.FONT_SIZE_MD};
            }}
        """)

        # 趋势图会自动重绘


class ExecutionLogSection(CollapsibleSection):
    """执行日志区块 - 可折叠"""

    def __init__(self, controller: MonitoringController, parent=None):
        self._controller = controller
        super().__init__("执行日志", parent)
        self._setup_content()

        # 连接信号
        self._controller.log_entry_added.connect(self._add_log_entry)

    def _setup_content(self):
        """设置内容"""
        theme = get_theme()

        # 日志容器
        self._log_container = QWidget()
        self._log_layout = QVBoxLayout(self._log_container)
        self._log_layout.setContentsMargins(4, 4, 4, 4)
        self._log_layout.setSpacing(2)
        self._log_layout.addStretch()

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.APP_BACKGROUND};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
            }}
            QScrollBar:vertical {{
                background-color: {theme.CHROME};
                width: 5px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.TEXT_SUBTLE};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme.TEXT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        scroll.setWidget(self._log_container)
        self.add_widget(scroll, 1)

        # 占位符
        self._placeholder = QLabel("执行过程中将显示日志...")
        self._placeholder.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 16px;
            }}
        """)
        self._log_layout.insertWidget(0, self._placeholder)

        # 存储日志条目组件
        self._log_widgets: list[LogEntryWidget] = []
        self._max_log_widgets = 50

    def _add_log_entry(self, entry: LogEntry):
        """添加日志条目"""
        # 移除占位符
        if self._placeholder:
            self._placeholder.deleteLater()
            self._placeholder = None

        # 创建日志条目组件
        widget = LogEntryWidget(entry, self._controller)
        self._log_layout.insertWidget(self._log_layout.count() - 1, widget)  # 插入到 stretch 之前
        self._log_widgets.append(widget)

        # 限制数量
        if len(self._log_widgets) > self._max_log_widgets:
            old_widget = self._log_widgets.pop(0)
            old_widget.deleteLater()

    def clear(self):
        """清空日志"""
        for widget in self._log_widgets:
            widget.deleteLater()
        self._log_widgets.clear()

        # 恢复占位符
        theme = get_theme()
        self._placeholder = QLabel("执行过程中将显示日志...")
        self._placeholder.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SUBTLE};
                font-size: {theme.FONT_SIZE_XS};
                padding: 16px;
            }}
        """)
        self._log_layout.insertWidget(0, self._placeholder)

    def _on_theme_changed(self):
        """主题切换"""
        super()._on_theme_changed()

        # 更新所有日志条目
        for widget in self._log_widgets:
            widget.apply_theme()


class LogEntryWidget(QWidget):
    """单条日志条目"""

    def __init__(self, entry: LogEntry, controller: MonitoringController, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._controller = controller
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _setup_ui(self):
        theme = get_theme()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # 时间戳
        time_str = self._entry.timestamp.strftime("%H:%M:%S")
        self._time_label = QLabel(f"[{time_str}]")
        self._time_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 10px;")
        layout.addWidget(self._time_label)

        # 图标
        icon = self._controller.get_log_icon(self._entry.event_type)
        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._icon_label)

        # 消息
        self._message_label = QLabel(self._entry.message)
        self._message_label.setStyleSheet(f"color: {theme.TEXT}; font-size: 11px;")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label, 1)

        # 耗时（如果有）
        if self._entry.duration_ms is not None:
            duration_str = f"({self._entry.duration_ms:.0f}ms)"
            self._duration_label = QLabel(duration_str)
            self._duration_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 10px;")
            layout.addWidget(self._duration_label)

    def apply_theme(self):
        """应用当前主题"""
        theme = get_theme()

        self._time_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 10px;")
        self._message_label.setStyleSheet(f"color: {theme.TEXT}; font-size: 11px;")

        if hasattr(self, "_duration_label"):
            self._duration_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 10px;")

    def _on_theme_changed(self):
        """主题切换"""
        self.apply_theme()
