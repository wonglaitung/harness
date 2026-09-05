---
description: PyQt6 主题切换开发检查清单。每次修改 UI 代码后必须检查主题切换响应链，避免重启才能生效。
---


# PyQt6 主题切换检查清单

**每次修改 PyQt6 UI 代码后，必须检查主题切换是否正常工作。**

---

## ⚠️ 核心原则

### 原则 1：定义了 `_on_theme_changed()` 不等于会自动响应

**最常见的错误**：写了 `_on_theme_changed()` 方法，但没有注册监听器，导致方法永远不会被调用。

```python
# ❌ 错误：方法定义了但不会自动调用
class MyWidget(QWidget):
    def _on_theme_changed(self):
        theme = get_theme()
        self.setStyleSheet(f"...")

# ✅ 正确：必须注册监听器
class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)  # 关键！

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)  # 清理
        except Exception:
            pass

    def _on_theme_changed(self):
        theme = get_theme()
        self.setStyleSheet(f"...")
```

### 原则 2：`_setup_ui()` 中的 UI 元素必须保存为实例属性

**第二个常见错误**：在 `_setup_ui()` 中创建的 QLabel、QPushButton、QWidget 等是局部变量，`_on_theme_changed()` 无法访问。

```python
# ❌ 错误：局部变量，_on_theme_changed 无法访问
def _setup_ui(self):
    name_label = QLabel("标题")  # 局部变量
    add_btn = QPushButton("+")   # 局部变量
    input_bar = QWidget()        # 局部变量
    scroll = QScrollArea()       # 局部变量

def _on_theme_changed(self):
    name_label.setStyleSheet(...)  # NameError: 未定义

# ✅ 正确：保存为实例属性
def _setup_ui(self):
    self._name_label = QLabel("标题")  # 实例属性
    self._add_btn = QPushButton("+")   # 实例属性
    self._input_bar = QWidget()        # 实例属性
    self._scroll = QScrollArea()       # 实例属性

def _on_theme_changed(self):
    self._name_label.setStyleSheet(...)
    self._add_btn.setStyleSheet(...)
    self._input_bar.setStyleSheet(...)
    self._scroll.setStyleSheet(...)
```

**特别注意容器组件**：`input_bar`、`scroll`、`container` 等布局容器也必须保存！

### 原则 3：继承时避免重复注册监听器

如果父类已经注册了主题监听器，子类只需重写 `_on_theme_changed()` 方法，**不需要再次注册**。

```python
# 父类已注册
class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)

    def _on_theme_changed(self):
        theme = get_theme()
        self.header_btn.setStyleSheet(f"...")

# ✅ 子类：只重写方法，不重复注册
class MemorySection(CollapsibleSection):
    def __init__(self, parent=None):
        super().__init__("记忆", parent)  # 父类已注册监听器
        self._setup_content()
        # 不要再次调用 register_theme_listener！

    def _on_theme_changed(self):
        super()._on_theme_changed()  # 调用父类方法
        theme = get_theme()
        self._info_label.setStyleSheet(f"...")
```

### 原则 4：使用 `setProperty()` 标记动态创建的子组件

**问题**：`findChildren(QLabel)` 会找到所有 QLabel，但无法区分哪些需要更新。用文本匹配（如 `label.text() == "●"`）不可靠。

```python
# ❌ 错误：用文本匹配不可靠
for label in widget.findChildren(QLabel):
    if label.text() == "●":  # 可能匹配到其他内容
        continue
    label.setStyleSheet(...)

# ✅ 正确：用 property 标记
# 创建时
content_label = QLabel(entry.content)
content_label.setProperty("isContentLabel", True)  # 标记

remove_btn = QPushButton("×")
remove_btn.setProperty("isRemoveButton", True)  # 标记

# 主题切换时
for label in widget.findChildren(QLabel):
    if label.property("isContentLabel"):
        label.setStyleSheet(f"color: {theme.TEXT};")
for btn in widget.findChildren(QPushButton):
    if btn.property("isRemoveButton"):
        btn.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
```

### 原则 5：QListWidget/QTableWidget 的 item 颜色需要单独更新

**问题**：`QListWidget.setStyleSheet()` 只影响容器样式，不会更新已有 item 的前景色。

```python
# ❌ 错误：setStyleSheet 不会更新 item 颜色
self.session_list.setStyleSheet(f"QListWidget {{ color: {theme.TEXT}; }}")

# ✅ 正确：遍历更新每个 item
def _on_theme_changed(self):
    theme = get_theme()
    self.session_list.setStyleSheet(f"""...""")
    
    # 更新每个 item 的前景色
    for i in range(self.session_list.count()):
        item = self.session_list.item(i)
        if item:
            item.setForeground(QColor(theme.TEXT))

# 如果 item 有不同状态（如当前会话高亮）
for i in range(self.session_list.count()):
    item = self.session_list.item(i)
    if item:
        if item.text().startswith("●"):
            item.setForeground(QColor(theme.ACCENT))  # 当前会话
        else:
            item.setForeground(QColor(theme.TEXT))    # 历史会话
```

### 原则 6：禁止硬编码颜色

**问题**：硬编码的颜色（如 `Qt.GlobalColor.white`、`"#FFFFFF"`）在主题切换时不会自动更新。

```python
# ❌ 错误：硬编码颜色
item.setForeground(Qt.GlobalColor.white)
label.setStyleSheet("color: #FFFFFF;")

# ✅ 正确：使用主题颜色
item.setForeground(QColor(theme.ACCENT))
label.setStyleSheet(f"color: {theme.TEXT};")
```

---

## 检查清单

| 场景 | 必须做的事 |
|-----|-----------|
| 新增 QWidget 子类 | 1. 实现 `_on_theme_changed()` **2. 注册监听器** 3. 添加 `__del__` 清理 |
| 新增自定义绘制组件 | `paintEvent` 中调用 `get_theme()` 动态获取颜色 |
| 新增嵌套组件 | 父组件的 `_on_theme_changed()` 调用子组件的 `_on_theme_changed()` |
| 使用样式表的组件 | 在 `_on_theme_changed()` 中重新设置 `setStyleSheet()` |
| `_setup_ui()` 中创建 UI 元素 | **所有元素**保存为实例属性 `self._xxx`，包括容器组件 |
| 动态创建子组件（如列表项） | 用 `setProperty()` 标记，在 `_on_theme_changed()` 中用 `property()` 识别 |
| 使用 QListWidget/QTableWidget | 遍历更新每个 item 的 `setForeground()` |
| 继承已注册监听器的父类 | 只重写 `_on_theme_changed()`，调用 `super()._on_theme_changed()`，**不重复注册** |

---

## 实现方式

### 方式 1：继承 ThemeAwareWidget（推荐）

自动处理监听器注册/注销，最省心。

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

### 方式 2：继承 CollapsibleSection

父类已注册监听器，子类只需重写方法。

```python
from harness_client.ui.right_panel import CollapsibleSection

class MySection(CollapsibleSection):
    def __init__(self, parent=None):
        super().__init__("标题", parent)  # 父类已注册监听器
        self._setup_content()

    def _on_theme_changed(self):
        super()._on_theme_changed()  # 调用父类方法更新 header
        theme = get_theme()
        self._my_label.setStyleSheet(f"...")
```

### 方式 3：手动实现（独立 QWidget）

```python
from harness_client.themes import get_theme, register_theme_listener, unregister_theme_listener

class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        register_theme_listener(self._on_theme_changed)  # 注册

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)  # 清理
        except Exception:
            pass

    def _on_theme_changed(self):
        theme = get_theme()
        self.setStyleSheet(f"...")
        # 更新所有子元素
        self._label.setStyleSheet(f"...")
        self._button.setStyleSheet(f"...")
```

### 方式 4：自定义绘制组件

```python
class CustomSlider(QWidget):
    def paintEvent(self, event):
        theme = get_theme()  # 必须动态获取，不能缓存
        painter.setBrush(QBrush(QColor(theme.ACCENT)))
```

### 方式 5：动态列表项

```python
class MyListSection(CollapsibleSection):
    def _setup_content(self):
        self._items: list[QWidget] = []
        # ...

    def _create_item(self, data) -> QWidget:
        widget = QWidget()
        
        label = QLabel(data)
        label.setProperty("isItemLabel", True)  # 标记
        label.setStyleSheet(f"color: {get_theme().TEXT};")
        
        btn = QPushButton("×")
        btn.setProperty("isItemButton", True)  # 标记
        btn.setStyleSheet(f"color: {get_theme().TEXT_SUBTLE};")
        
        return widget

    def _on_theme_changed(self):
        super()._on_theme_changed()
        theme = get_theme()
        for widget in self._items:
            for label in widget.findChildren(QLabel):
                if label.property("isItemLabel"):
                    label.setStyleSheet(f"color: {theme.TEXT};")
            for btn in widget.findChildren(QPushButton):
                if btn.property("isItemButton"):
                    btn.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
```

---

## 常见错误

| 错误现象 | 原因 | 修复方法 |
|---------|------|---------|
| 新组件主题不变，重启后正常 | 没有注册监听器 | `__init__` 中调用 `register_theme_listener()` |
| `_on_theme_changed()` 不执行 | 方法定义了但没注册监听器 | 添加监听器注册 |
| NameError: 'xxx' is not defined | UI 元素是局部变量 | 改为 `self._xxx` 实例属性 |
| 容器背景不变 | `input_bar`、`scroll` 等容器是局部变量 | 保存为实例属性 |
| 子组件主题不变 | 父组件没有传播主题变化 | 父组件调用子组件的 `_on_theme_changed()` |
| 动态创建的子组件颜色不变 | `findChildren()` 找到错误组件 | 用 `setProperty()` 标记组件 |
| QListWidget item 颜色不变 | `setStyleSheet` 不影响已有 item | 遍历调用 `item.setForeground()` |
| 硬编码颜色不变 | 颜色写死在代码中 | 改用 `theme.XXX` |
| 自定义绘制颜色不变 | `paintEvent` 缓存了颜色 | 改为 `get_theme()` 动态获取 |
| 监听器重复触发 | 父类和子类都注册了监听器 | 子类不重复注册，只重写方法 |

---

## 调试技巧

### 1. 确认监听器是否注册

在 `_on_theme_changed()` 中添加调试输出：

```python
def _on_theme_changed(self):
    print(f"[DEBUG] theme changed: {self.__class__.__name__}")
    theme = get_theme()
    ...
```

如果切换主题后没有看到输出，说明监听器没有注册。

### 2. 检查实例属性是否存在

```python
def _on_theme_changed(self):
    if hasattr(self, '_my_label'):
        self._my_label.setStyleSheet(...)
    else:
        print(f"[DEBUG] _my_label not found in {self.__class__.__name__}")
```

### 3. 打印所有子组件

```python
def _on_theme_changed(self):
    for child in self.findChildren(QWidget):
        print(f"[DEBUG] child: {child.__class__.__name__}, property: {child.property('isContentLabel')}")
```

---

## 验证步骤

1. 启动客户端，切换主题（亮/暗）
2. 检查所有新修改的 UI 组件是否正确变色
3. **检查容器背景**：`input_bar`、`scroll`、`container` 等
4. **检查动态列表**：展开记忆条目、会话列表等
5. 如有问题，添加 `print()` 调试确认方法是否被调用
6. 检查 UI 元素是否保存为实例属性

---

## 历史问题

| 文件 | 问题 | 修复 |
|-----|------|------|
| `memory_panel.py` | CategorySection、MemorySection 定义了 `_on_theme_changed()` 但没注册监听器 | 添加 `register_theme_listener()` |
| `memory_panel.py` | `name_label`、`add_btn`、`info_label`、`scroll` 是局部变量 | 改为 `self._xxx` 实例属性 |
| `memory_panel.py` | `findChildren()` 用文本匹配不可靠 | 改用 `setProperty()` 标记组件 |
| `chat_panel.py` | `input_bar` 是局部变量 | 改为 `self._input_bar` |
| `chat_panel.py` | session_title_label 缺少主题更新逻辑 | 添加到 `_on_theme_changed()` |
| `chat_panel.py` | CSS `line-height: 1.4` 不被 Qt 支持，导致文本截断 | 移除不支持的 CSS 属性 |
| `chat_panel.py` | QScrollArea 默认有 frame 边框导致额外空间 | 添加 `setFrameShape(QFrame.Shape.NoFrame)` |
| `chat_panel.py` | QLabel 文本未顶部对齐，第一行被截断 | `setAlignment(AlignTop \| AlignLeft)` + `setMargin(0)` |
| `chat_panel.py` | QScrollBar 背景 `transparent` 不可见 | 改用 `theme.CHROME` 背景 + `theme.TEXT_SUBTLE` 手柄 |
| `sidebar.py` | `update_sessions()` 硬编码 `Qt.GlobalColor.white` | 改为 `QColor(theme.ACCENT)` |
| `sidebar.py` | QListWidget item 颜色只在 `_on_theme_changed` 更新，新建会话时硬编码 | 两处都改用主题颜色 |

---

## Qt CSS 不支持的属性

**重要**：Qt 的 HTML/CSS 子集有限，以下属性不支持：

| 属性 | 状态 |
|-----|------|
| `line-height` | ❌ 不支持 |
| `display: flex/grid` | ❌ 不支持 |
| `position` | ❌ 不支持 |
| `float` | ❌ 不支持 |
| CSS 变量 | ❌ 不支持 |
| `box-shadow` | ❌ 不支持 |

参考文档：https://doc.qt.io/qt-6/richtext-html-subset.html

**如果使用了不支持的 CSS 属性，可能导致文本截断或布局异常。**
