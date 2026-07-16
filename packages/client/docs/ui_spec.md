# Harness Client UI 设计规范

本文档定义了 Harness Client 桌面应用的完整视觉标准，确保所有界面元素的一致性和专业性。

> **相关文档**：开发问题与解决方案请参考 [development_guide.md](./development_guide.md)

---

## 目录

1. [核心原则](#核心原则)
2. [主题系统](#主题系统)
3. [布局架构](#布局架构)
4. [组件规范](#组件规范)
5. [对话框规范](#对话框规范)
6. [间距与尺寸](#间距与尺寸)
7. [字体排版](#字体排版)
8. [颜色系统](#颜色系统)
9. [图标系统](#图标系统)
10. [交互状态](#交互状态)
11. [动画规范](#动画规范)
12. [主题感知组件](#主题感知组件)
13. [文件引用](#文件引用)
14. [检查清单](#检查清单)
15. [窗口尺寸策略](#窗口尺寸策略)
16. [焦点链规范](#焦点链规范)
17. [状态管理规范](#状态管理规范)
18. [空状态规范](#空状态规范)
19. [加载状态规范](#加载状态规范)
20. [错误处理 UI 规范](#错误处理-ui-规范)
21. [可访问性规范](#可访问性规范)
22. [性能警示](#性能警示)
23. [PyQt6 版本兼容](#pyqt6-版本兼容)

---

## 核心原则

1. **功能性优先**：这是开发工具，不是营销页面。清晰、简洁、高效。
2. **一致性**：所有界面使用相同的间距、颜色、字体和组件样式。
3. **主题感知**：所有组件必须响应深色/浅色主题切换。
4. **银行级专业感**：深色主题采用"Trust Blue"美学，避免 AI 紫色渐变。

---

## 主题系统

### 主题切换机制

```python
from harness_client.themes import get_theme, set_theme_mode, ThemeMode

# 获取当前主题
theme = get_theme()

# 设置主题模式
set_theme_mode(ThemeMode.DARK)    # 强制深色
set_theme_mode(ThemeMode.LIGHT)   # 强制亮色
set_theme_mode(ThemeMode.AUTO)    # 跟随系统
```

### 主题监听

所有需要响应主题切换的组件必须：

```python
from harness_client.themes import register_theme_listener, unregister_theme_listener

class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self):
        """主题切换时更新样式"""
        theme = get_theme()
        self.setStyleSheet(f"background-color: {theme.APP_BACKGROUND};")
```

### 主题感知基类

对于需要动态重绘的组件，继承 `ThemeAwareWidget`：

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

**重要**：在 `paintEvent` 中必须动态调用 `get_theme()`，不能缓存主题对象。

---

## 布局架构

### 主窗口结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MainWindow (QMainWindow)                     │
├────────────┬──────────────────────────────────┬────────────────────┤
│            │                                  │                    │
│  Sidebar   │           ChatPanel              │     RightPanel     │
│  (180px)   │        (flexible width)          │     (300px)        │
│            │                                  │                    │
│  - 导航    │  - 消息列表                      │  - 记忆管理        │
│  - 会话    │  - 输入区域                      │  - 技能列表        │
│            │  - 浏览器状态                    │  - MCP 服务器      │
│            │                                  │  - 文件树          │
└────────────┴──────────────────────────────────┴────────────────────┘
```

### 三栏布局规范

| 区域 | 宽度 | 说明 |
|------|------|------|
| Sidebar | 固定 180px | 左侧导航栏 |
| ChatPanel | 自适应 | 中央对话区，占用剩余空间 |
| RightPanel | 固定 300px | 右侧功能面板 |

### 使用 QSplitter 实现可调整布局

```python
splitter = QSplitter(Qt.Orientation.Horizontal)

# 左侧栏
sidebar = SidebarPanel()
sidebar.setMinimumWidth(180)
sidebar.setMaximumWidth(300)

# 中央区
chat_panel = ChatPanel()

# 右侧栏
right_panel = RightPanel()
right_panel.setMinimumWidth(250)
right_panel.setMaximumWidth(400)

splitter.addWidget(sidebar)
splitter.addWidget(chat_panel)
splitter.addWidget(right_panel)

# 设置初始比例
splitter.setSizes([180, 800, 300])
```

---

## 组件规范

### 1. 可折叠区块 (CollapsibleSection)

右侧面板中的可折叠区块使用 `CollapsibleSection` 基类：

```python
from harness_client.ui.right_panel import CollapsibleSection

class MemorySection(CollapsibleSection):
    def __init__(self, parent=None):
        super().__init__("记忆", parent=parent)
        self._setup_content()
        # 主题监听已在 CollapsibleSection 中注册

    def _setup_content(self):
        # 添加内容到 content_area
        self.add_widget(my_widget, stretch=1)

    def _on_theme_changed(self):
        super()._on_theme_changed()  # 必须调用父类方法
        theme = get_theme()
        # 更新子组件样式
```

### 2. 按钮样式

**主按钮 (Primary Button)**：
```python
theme = get_theme()
btn.setStyleSheet(f"""
    QPushButton {{
        background-color: {theme.ACCENT};
        color: white;
        border: none;
        border-radius: {theme.RADIUS_SM};
        padding: 8px 16px;
        min-height: 24px;
    }}
    QPushButton:hover {{
        background-color: {theme.ACCENT_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {theme.ACCENT_LIGHT};
    }}
    QPushButton:disabled {{
        background-color: {theme.BORDER};
        color: {theme.TEXT_MUTED};
    }}
""")
```

**次要按钮 (Secondary Button)**：
```python
btn.setStyleSheet(f"""
    QPushButton {{
        background-color: transparent;
        color: {theme.TEXT};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_SM};
        padding: 8px 16px;
    }}
    QPushButton:hover {{
        background-color: {theme.HOVER_NEUTRAL};
        border-color: {theme.BORDER_LIGHT};
    }}
""")
```

**危险按钮 (Danger Button)**：
```python
btn.setStyleSheet(f"""
    QPushButton {{
        background-color: {theme.DANGER};
        color: white;
        border: none;
        border-radius: {theme.RADIUS_SM};
        padding: 8px 16px;
    }}
    QPushButton:hover {{
        background-color: {theme.DANGER_HOVER};
    }}
""")
```

### 3. 输入框样式

**文本输入框 (QLineEdit)**：
```python
edit.setStyleSheet(f"""
    QLineEdit {{
        background-color: {theme.COMPOSER};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_SM};
        padding: 6px 8px;
        color: {theme.TEXT};
        min-height: 18px;
    }}
    QLineEdit:focus {{
        border-color: {theme.ACCENT};
    }}
    QLineEdit:placeholder-shown {{
        color: {theme.TEXT_MUTED};
    }}
""")
```

**多行文本 (QTextEdit)**：
```python
edit.setStyleSheet(f"""
    QTextEdit {{
        background-color: {theme.COMPOSER};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_SM};
        padding: 8px;
        color: {theme.TEXT};
    }}
    QTextEdit:focus {{
        border-color: {theme.ACCENT};
    }}
""")
```

### 4. 下拉框 (QComboBox)

```python
combo.setStyleSheet(f"""
    QComboBox {{
        background-color: {theme.COMPOSER};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_SM};
        padding: 6px 8px;
        color: {theme.TEXT};
        min-height: 18px;
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
        selection-background-color: {theme.ACCENT};
        selection-color: white;
    }}
""")
```

### 5. 复选框 (QCheckBox)

```python
check.setStyleSheet(f"""
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
""")
```

### 6. 分组框 (QGroupBox)

```python
group.setStyleSheet(f"""
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
""")
```

### 7. 标签样式

**普通标签**：
```python
label.setStyleSheet(f"color: {theme.TEXT};")
```

**次要标签**：
```python
label.setStyleSheet(f"""
    QLabel {{
        color: {theme.TEXT_SUBTLE};
        font-size: {theme.FONT_SIZE_SM};
    }}
""")
```

**辅助/提示标签**：
```python
from harness_client.ui.dialog_styles import get_muted_label_stylesheet

label.setStyleSheet(get_muted_label_stylesheet())
```

**错误标签**：
```python
from harness_client.ui.dialog_styles import get_error_label_stylesheet

label.setStyleSheet(get_error_label_stylesheet())
```

---

## 对话框规范

### 标准尺寸

```python
from harness_client.ui.dialog_styles import (
    DIALOG_MIN_WIDTH,
    DIALOG_MARGINS,
    DIALOG_SPACING,
)
```

| 参数 | 值 | 说明 |
|------|-----|------|
| `DIALOG_MIN_WIDTH` | 480 | 对话框最小宽度 |
| `DIALOG_MARGINS` | (20, 20, 20, 20) | 左、上、右、下边距 |
| `DIALOG_SPACING` | 12 | 主要元素间距 |
| `FORM_SPACING` | 8 | 表单行间距 |

### 对话框模板

**简单表单对话框**：

```python
from harness_client.ui.dialog_styles import (
    get_dialog_stylesheet,
    create_standard_form_layout,
    DIALOG_MIN_WIDTH,
    DIALOG_MARGINS,
    DIALOG_SPACING,
)

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("标题")
        self.setMinimumWidth(DIALOG_MIN_WIDTH)
        self.setStyleSheet(get_dialog_stylesheet())
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(DIALOG_SPACING)

        form = create_standard_form_layout()
        form.addRow("名称:", QLineEdit())
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
```

**分组表单对话框**：

```python
from harness_client.ui.dialog_styles import get_groupbox_stylesheet

def _setup_ui(self):
    # ... 基本设置同上

    # 分组 1
    group1 = QGroupBox("基本设置")
    group1.setStyleSheet(get_groupbox_stylesheet())
    group1_layout = create_standard_form_layout()
    group1_layout.addRow("字段1:", QLineEdit())
    group1.setLayout(group1_layout)
    layout.addWidget(group1)

    # 分组 2
    group2 = QGroupBox("高级设置")
    group2.setStyleSheet(get_groupbox_stylesheet())
    # ...
```

---

## 间距与尺寸

### 标准间距

| 级别 | 值 | 用途 |
|------|-----|------|
| 紧凑 | 4px | 列表项内部、标签组 |
| 标准 | 8px | 表单行、组件间 |
| 宽松 | 12px | 区块间、对话框元素 |
| 区块 | 16px | 主要区块、面板间 |

### 固定尺寸

| 组件 | 尺寸 |
|------|------|
| 导航按钮高度 | 44px |
| 输入框最小高度 | 18px + padding |
| 按钮最小高度 | 24px |
| 图标标准尺寸 | 16px / 24px |
| 头像尺寸 | 32px |

### 圆角系统

| 级别 | 值 | 用途 |
|------|-----|------|
| `RADIUS_SM` | 3px | 小标签、微型按钮 |
| `RADIUS_MD` | 6px | 按钮、输入框、面板 |
| `RADIUS_LG` | 8px | 消息气泡、卡片 |

---

## 字体排版

### 字体栈

```python
# 无衬线字体
FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", system-ui, sans-serif'

# 等宽字体
FONT_FAMILY_MONO = '"Consolas", "Courier New", monospace'
```

### 字号系统

| 级别 | 值 | 用途 |
|------|-----|------|
| `FONT_SIZE_XS` | 11px | 标题、提示、时间戳 |
| `FONT_SIZE_SM` | 12px | 次要文本、标签 |
| `FONT_SIZE_BASE` | 13px | 正文（默认） |
| `FONT_SIZE_MD` | 14px | 强调正文 |
| `FONT_SIZE_LG` | 16px | 区块标题 |
| `FONT_SIZE_XL` | 18px | 页面标题 |
| `FONT_SIZE_2XL` | 24px | 主要标题 |

### 使用方式

```python
theme = get_theme()
label.setStyleSheet(f"""
    QLabel {{
        font-family: {theme.FONT_FAMILY};
        font-size: {theme.FONT_SIZE_BASE};
        color: {theme.TEXT};
    }}
""")
```

---

## 颜色系统

### 背景层次

| 变量 | 用途 |
|------|------|
| `APP_BACKGROUND` | 主窗口背景（最深） |
| `CHROME` | 标题栏、侧边栏 |
| `PANEL` | 面板背景 |
| `COMPOSER` | 输入区域 |

### 文本颜色

| 变量 | 用途 |
|------|------|
| `TEXT` | 主要文本 |
| `TEXT_SUBTLE` | 次要文本 |
| `TEXT_MUTED` | 提示、占位符 |
| `TEXT_DISABLED` | 禁用状态 |

### 语义颜色

| 语义 | 颜色变量 | 用途 |
|------|----------|------|
| 主色调 | `ACCENT` | 主按钮、链接、高亮 |
| 成功 | `SUCCESS` | 成功状态、连接成功 |
| 警告 | `WARNING` | 警告状态 |
| 危险 | `DANGER` | 错误、删除、断开 |

### 状态指示器

| 状态 | 颜色 |
|------|------|
| 已连接 | `STATUS_CONNECTED` (#2EA043) |
| 连接中 | `STATUS_CONNECTING` (#D29922) |
| 错误 | `STATUS_ERROR` (#DA3633) |
| 已断开 | `STATUS_DISCONNECTED` (#6E7681) |

---

## 图标系统

### 图标创建

使用 `icons.py` 中的工厂函数创建图标：

```python
from harness_client.ui.icons import (
    create_chat_icon,
    create_settings_icon,
    create_add_icon,
    create_delete_icon,
    create_play_icon,
    create_pause_icon,
)
from PyQt6.QtGui import QColor

# 创建带颜色的图标
icon = create_chat_icon(24, QColor("#FFFFFF"))
btn.setIcon(icon)
```

### 标准图标尺寸

| 场景 | 尺寸 |
|------|------|
| 导航按钮 | 18px |
| 工具栏 | 24px |
| 状态指示 | 12px |

### 禁止使用 Emoji

界面中禁止使用 Emoji，必须使用图标库或自定义绘制图标。

---

## 交互状态

### 悬停状态

```python
# 中性悬停
background-color: {theme.HOVER_NEUTRAL};

# 激活悬停
background-color: {theme.HOVER_ACTIVE};
```

### 焦点状态

```python
# 输入框焦点
border-color: {theme.ACCENT};

# 导航激活
background-color: {theme.NAV_ACTIVE_BG};
color: {theme.NAV_ACTIVE_TEXT};
border-left: 2px solid {theme.NAV_ACTIVE_BORDER};
```

### 禁用状态

```python
background-color: {theme.DISABLED_BACKGROUND};
color: {theme.TEXT_MUTED};
```

### 按下状态

```python
# 使用更深的背景色
background-color: {theme.HOVER_SURFACE_PRESSED};
```

---

## 动画规范

### 可折叠区块动画

`CollapsibleSection` 默认使用 100ms 的展开/收起动画：

```python
section = CollapsibleSection("标题", animation_duration=100)
```

### 消息气泡动画

使用 `QPropertyAnimation` 实现平滑过渡：

```python
animation = QPropertyAnimation(widget, b"maximumHeight")
animation.setDuration(100)
animation.setStartValue(0)
animation.setEndValue(target_height)
animation.start()
```

### 禁止使用的动画模式

- 无限循环的微动画（除非明确需要，如加载指示器）
- 过度花哨的过渡效果
- 影响性能的复杂动画

---

## 主题感知组件

### ThemeAwareWidget 基类

用于需要动态重绘的组件：

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class CustomWidget(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()
        self.setStyleSheet(f"...")

    def paintEvent(self, event):
        """绘制时动态获取主题"""
        theme = self.theme()  # 或 get_theme()
        painter = QPainter(self)
        painter.setPen(QColor(theme.TEXT))
        # ...
```

### paintEvent 规则

在 `paintEvent` 中**必须**动态调用 `get_theme()` 或 `self.theme()`，不能在初始化时缓存颜色值，否则主题切换后不会更新。

---

## 文件引用

### 核心文件

| 文件 | 说明 |
|------|------|
| `themes/__init__.py` | 主题系统入口 |
| `themes/dark.py` | 深色主题定义 |
| `themes/light.py` | 浅色主题定义 |
| `themes/stylesheet.py` | 全局样式表生成 |
| `ui/dialog_styles.py` | 对话框样式工具 |
| `ui/theme_aware.py` | 主题感知基类 |
| `ui/icons.py` | 图标工厂函数 |

### 主要组件

| 文件 | 说明 |
|------|------|
| `ui/main_window.py` | 主窗口 |
| `ui/sidebar.py` | 左侧导航栏 |
| `ui/chat_panel.py` | 中央对话面板 |
| `ui/right_panel.py` | 右侧功能面板 |
| `ui/settings_dialog.py` | 设置对话框 |
| `ui/mcp_panel.py` | MCP 配置面板 |
| `ui/memory_panel.py` | 记忆管理面板 |
| `ui/schedule_panel.py` | 排程管理面板 |
| `ui/skill_dialog.py` | 技能编辑对话框 |

---

## 检查清单

### 创建新组件时

- [ ] 使用 `get_theme()` 获取当前主题
- [ ] 注册主题监听器 `register_theme_listener`
- [ ] 在 `__del__` 中注销监听器
- [ ] 在 `paintEvent` 中动态获取主题（如有绘制）
- [ ] 使用主题变量而非硬编码颜色
- [ ] 测试深色和浅色主题

### 创建对话框时

- [ ] 使用 `get_dialog_stylesheet()` 设置整体样式
- [ ] 使用 `DIALOG_MARGINS` 和 `DIALOG_SPACING`
- [ ] 使用 `create_standard_form_layout()` 创建表单
- [ ] 分组使用 `get_groupbox_stylesheet()`
- [ ] 辅助文本使用 `get_muted_label_stylesheet()`
- [ ] 错误文本使用 `get_error_label_stylesheet()`
- [ ] 设置合理的焦点链（Tab Order）
- [ ] 测试主题切换

### 修改现有组件时

- [ ] 确保修改后的样式使用主题变量
- [ ] 检查是否有硬编码的颜色值
- [ ] 验证主题切换后的显示效果
- [ ] 更新相关文档

---

## 窗口尺寸策略

### 最小窗口尺寸

| 场景 | 最小宽度 | 最小高度 | 说明 |
|------|----------|----------|------|
| 紧凑模式 | 1024px | 600px | 最小可用尺寸 |
| 标准模式 | 1280px | 720px | 推荐最小尺寸 |

### QSizePolicy 使用规范

| 组件 | 水平策略 | 垂直策略 | 说明 |
|------|----------|----------|------|
| Sidebar | Fixed | Expanding | 固定宽度，高度跟随窗口 |
| ChatPanel | Expanding | Expanding | 占用剩余空间 |
| RightPanel | Fixed | Expanding | 固定宽度，高度跟随窗口 |
| 输入框 | Expanding | Fixed | 水平扩展，高度固定 |
| 按钮组 | Fixed | Fixed | 不随布局扩展 |
| 列表项 | Expanding | Fixed | 宽度跟随容器 |

### 实现示例

```python
from PyQt6.QtWidgets import QSizePolicy

# 固定宽度组件
sidebar = SidebarPanel()
sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

# 自适应组件
chat_panel = ChatPanel()
chat_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

---

## 焦点链规范

### Tab Order 设置

所有对话框必须设置合理的键盘导航顺序：

```python
def _setup_ui(self):
    # ... 创建控件

    # 设置焦点链：从上到下，从左到右
    self.setTabOrder(self.name_edit, self.version_edit)
    self.setTabOrder(self.version_edit, self.author_edit)
    self.setTabOrder(self.author_edit, self.description_edit)
```

### 焦点顺序规则

1. **表单对话框**：标题 → 表单字段（从上到下）→ 复选框 → 按钮（左到右）
2. **设置页**：左侧导航 → 右侧内容区 → 内容区内表单
3. **模态对话框**：首个输入框获得初始焦点

### 初始焦点

```python
def showEvent(self, event):
    super().showEvent(event)
    # 对话框显示时聚焦到首个输入框
    self.name_edit.setFocus()
```

---

## 状态管理规范

### 单一数据源原则

**核心规则**：UI 组件不存储业务数据，只负责渲染。

```
┌─────────────────────────────────────────────────────────────┐
│                   SessionManager (单一数据源)                │
│                          ↓ 信号发射                          │
│                      MainWindow._refresh()                   │
│                          ↓ 数据传递                          │
│                    UI Components (纯渲染)                    │
└─────────────────────────────────────────────────────────────┘
```

### 数据流规范

```python
# ✓ 正确：控制器管理数据，UI 监听信号
class MainWindow(QMainWindow):
    def __init__(self):
        self.session_manager.session_changed.connect(self._refresh_session_list)

    def _refresh_session_list(self):
        sessions = self.session_manager.get_sessions()  # 从控制器获取
        self.sidebar.update_sessions(sessions)  # 只传递，不存储

# ✗ 错误：UI 组件缓存数据
class SidebarPanel(QWidget):
    def __init__(self):
        self._sessions = []  # 禁止：UI 不应存储数据
```

### 控制器层职责

| 控制器 | 职责 |
|--------|------|
| `ChatController` | 管理 AgentHarness 实例、消息流 |
| `SessionManager` | 会话状态、消息历史持久化 |
| `MCPController` | MCP 服务器连接、工具发现 |
| `SkillController` | 技能加载、匹配、执行 |
| `MemoryController` | 全局记忆的 CRUD |

---

## 空状态规范

### 设计原则

空状态应提供清晰的指引，帮助用户理解如何填充数据。

### 标准空状态

| 组件 | 空状态文案 | 行动指引 |
|------|------------|----------|
| 会话列表 | "暂无会话" | "点击 + 新建对话" |
| 技能列表 | "暂无技能" | "点击添加技能" |
| MCP 服务器 | "暂无服务器配置" | "点击添加 MCP 服务器" |
| 记忆列表 | "暂无记忆条目" | "点击 + 添加记忆" |
| 文件树 | "未打开工作区" | "选择文件夹开始" |

### 实现模板

```python
from harness_client.ui.dialog_styles import get_muted_label_stylesheet

def create_empty_state(message: str, hint: str = None) -> QWidget:
    """创建标准空状态组件"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # 主文案
    label = QLabel(message)
    label.setStyleSheet(get_muted_label_stylesheet())
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    # 可选提示
    if hint:
        hint_label = QLabel(hint)
        hint_label.setStyleSheet(get_muted_label_stylesheet())
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

    return widget
```

---

## 加载状态规范

### 骨架屏优先

**禁止**使用无限旋转的圆形加载器，优先使用骨架屏：

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

class SkeletonLoader(QWidget):
    """骨架屏加载组件"""

    def __init__(self, lines: int = 3, parent=None):
        super().__init__(parent)
        self._setup_ui(lines)

    def _setup_ui(self, lines: int):
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        for i in range(lines):
            # 宽度变化模拟真实内容
            width = "80%" if i == 0 else ("60%" if i == lines - 1 else "100%")
            line = QLabel()
            line.setFixedHeight(16)
            line.setStyleSheet(f"""
                background-color: {theme.BORDER};
                border-radius: {theme.RADIUS_SM};
                min-width: 100px;
            """)
            layout.addWidget(line)

        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

### 加载状态使用场景

| 场景 | 加载组件 | 位置 |
|------|----------|------|
| 列表加载 | 骨架屏 | 列表区域内 |
| 对话消息生成 | 打字动画 | 消息气泡内 |
| 按钮操作 | 按钮内图标旋转 | 按钮内 |
| 全局操作 | 状态栏提示 | 底部状态栏 |

---

## 错误处理 UI 规范

### 错误展示方式

| 场景 | 方式 | 位置 | 持续时间 |
|------|------|------|----------|
| 表单验证失败 | 内联错误文本 | 字段下方 | 持续显示 |
| 操作失败 | Toast 通知 | 右上角 | 5秒后消失 |
| 连接错误 | 状态指示器 + 提示 | 组件旁 | 持续显示 |
| 致命错误 | 模态对话框 | 屏幕中央 | 需用户关闭 |

### 表单验证

```python
from harness_client.ui.dialog_styles import get_error_label_stylesheet

class ValidatedForm(QDialog):
    def _show_field_error(self, field: QLineEdit, message: str):
        """显示字段验证错误"""
        # 清除旧错误
        old_error = field.findChild(QLabel, "error_label")
        if old_error:
            old_error.deleteLater()

        # 设置字段错误样式
        field.setStyleSheet(field.styleSheet() + f"""
            QLineEdit {{ border-color: {get_theme().DANGER}; }}
        """)

        # 显示错误文本
        error_label = QLabel(message)
        error_label.setObjectName("error_label")
        error_label.setStyleSheet(get_error_label_stylesheet())
        # 插入到字段下方（需要布局支持）
```

### Toast 通知

```python
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout

class Toast(QLabel):
    """轻量级通知组件"""

    def __init__(self, parent, message: str, duration: int = 5000):
        super().__init__(message, parent)
        self._setup_style()
        QTimer.singleShot(duration, self.deleteLater)

    def _setup_style(self):
        theme = get_theme()
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {theme.CHROME};
                color: {theme.TEXT};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
            }}
        """)
        self.adjustSize()

    @staticmethod
    def info(parent, message: str, duration: int = 5000):
        toast = Toast(parent, message, duration)
        toast.move(parent.width() - toast.width() - 20, 20)
        toast.show()
        return toast

    @staticmethod
    def error(parent, message: str, duration: int = 5000):
        toast = Toast(parent, message, duration)
        theme = get_theme()
        toast.setStyleSheet(f"""
            QLabel {{
                background-color: {theme.DANGER_BG};
                color: {theme.DANGER_TEXT};
                border: 1px solid {theme.DANGER};
                border-radius: {theme.RADIUS_MD};
                padding: 12px 16px;
            }}
        """)
        toast.move(parent.width() - toast.width() - 20, 20)
        toast.show()
        return toast
```

---

## 可访问性规范

### 基本要求

| 要求 | 说明 |
|------|------|
| 工具提示 | 所有图标按钮必须有 `toolTip` |
| 键盘导航 | 关键操作需支持快捷键 |
| 焦点可见 | 焦点环不可隐藏 |
| 颜色对比度 | 正文 4.5:1，大文本 3:1 |

### 工具提示设置

```python
# 图标按钮必须有 toolTip
btn = QPushButton()
btn.setIcon(create_add_icon(18, QColor(theme.TEXT)))
btn.setToolTip("添加新会话")  # 必须
btn.setFixedWidth(44)
```

### 快捷键注册

```python
from PyQt6.QtGui import QShortcut, QKeySequence

class MainWindow(QMainWindow):
    def _setup_shortcuts(self):
        # Ctrl+N: 新建会话
        QShortcut(QKeySequence("Ctrl+N"), self, self._new_session)
        # Ctrl+,: 打开设置
        QShortcut(QKeySequence("Ctrl+,"), self, self._open_settings)
        # Ctrl+K: 聚焦到输入框
        QShortcut(QKeySequence("Ctrl+K"), self, self._focus_input)
```

### 对比度检查

| 元素 | 前景色 | 背景色 | 对比度 | 状态 |
|------|--------|--------|--------|------|
| 正文 | #E6EDF3 | #0D1117 | 14.7:1 | ✓ AAA |
| 次要文本 | #8B949E | #0D1117 | 5.1:1 | ✓ AA |
| 主按钮 | #FFFFFF | #1F6FEB | 4.6:1 | ✓ AA |
| 禁用文本 | #6E7681 | #0D1117 | 3.2:1 | ⚠ 需检查 |

---

## 性能警示

### 禁止的操作

| 禁止 | 原因 | 替代方案 |
|------|------|----------|
| 在滚动容器上使用 CSS `filter` | GPU 重绘导致卡顿 | 使用静态图片或纯色 |
| 频繁调用 `setStyleSheet()` | 触发完整样式重计算 | 批量更新或使用动态属性 |
| 在 `paintEvent` 中创建对象 | 每帧创建对象导致 GC 压力 | 在 `__init__` 中预创建 |
| 大量使用 `QLabel` 显示富文本 | HTML 解析开销 | 使用 `QTextBrowser` 或纯文本 |

### 性能最佳实践

```python
# ✓ 正确：静态样式在初始化时设置一次
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_static_style()

    def _setup_static_style(self):
        self.setStyleSheet(get_dialog_stylesheet())

# ✓ 正确：动态部分使用 QProperty 动画
self._animation = QPropertyAnimation(self, b"maximumHeight")
self._animation.setDuration(100)

# ✗ 错误：每次更新都重设样式
def update_content(self, text):
    self.setStyleSheet(f"color: {theme.TEXT};")  # 不必要
    self.label.setText(text)
```

---

## PyQt6 版本兼容

### 最低版本要求

```
PyQt6 >= 6.6.0
Qt >= 6.6.0
```

### API 兼容性说明

| API | 最低版本 | 说明 |
|-----|----------|------|
| `QColorScheme` | Qt 6.5+ | 系统主题检测 |
| `:placeholder-shown` | Qt 6.4+ | QSS 伪类 |
| `QPropertyAnimation` | Qt 6.0+ | 属性动画 |
| `qasync` | 0.27+ | 异步事件循环集成 |

### 版本检测

```python
from PyQt6.QtCore import qVersion

def check_qt_version():
    version = qVersion()
    major, minor, _ = map(int, version.split('.'))
    if major < 6 or (major == 6 and minor < 6):
        import sys
        sys.exit("需要 Qt 6.6.0 或更高版本")
```

---

## 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-11 | 2.1 | 新增：窗口尺寸策略、焦点链、状态管理、空状态、加载状态、错误处理、可访问性、性能警示、版本兼容 |
| 2026-07-11 | 2.0 | 升级为完整 Client UI 规范 |
| 2026-07-11 | 1.0 | 初始版本（仅对话框规范） |
