---
name: pyqt-theme-check
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

**第二个常见错误**：在 `_setup_ui()` 中创建的 QLabel、QPushButton 等是局部变量，`_on_theme_changed()` 无法访问。

```python
# ❌ 错误：局部变量，_on_theme_changed 无法访问
def _setup_ui(self):
    name_label = QLabel("标题")  # 局部变量
    add_btn = QPushButton("+")   # 局部变量

def _on_theme_changed(self):
    name_label.setStyleSheet(...)  # NameError: 未定义

# ✅ 正确：保存为实例属性
def _setup_ui(self):
    self._name_label = QLabel("标题")  # 实例属性
    self._add_btn = QPushButton("+")   # 实例属性

def _on_theme_changed(self):
    self._name_label.setStyleSheet(...)
    self._add_btn.setStyleSheet(...)
```

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

---

## 检查清单

| 场景 | 必须做的事 |
|-----|-----------|
| 新增 QWidget 子类 | 1. 实现 `_on_theme_changed()` **2. 注册监听器** 3. 添加 `__del__` 清理 |
| 新增自定义绘制组件 | `paintEvent` 中调用 `get_theme()` 动态获取颜色 |
| 新增嵌套组件 | 父组件的 `_on_theme_changed()` 调用子组件的 `_on_theme_changed()` |
| 使用样式表的组件 | 在 `_on_theme_changed()` 中重新设置 `setStyleSheet()` |
| `_setup_ui()` 中创建 UI 元素 | 保存为实例属性 `self._xxx`，否则 `_on_theme_changed()` 无法访问 |
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

---

## 常见错误

| 错误现象 | 原因 | 修复方法 |
|---------|------|---------|
| 新组件主题不变，重启后正常 | 没有注册监听器 | `__init__` 中调用 `register_theme_listener()` |
| `_on_theme_changed()` 不执行 | 方法定义了但没注册监听器 | 添加监听器注册 |
| NameError: 'xxx' is not defined | UI 元素是局部变量 | 改为 `self._xxx` 实例属性 |
| 子组件主题不变 | 父组件没有传播主题变化 | 父组件调用子组件的 `_on_theme_changed()` |
| 自定义绘制颜色不变 | `paintEvent` 缓存了颜色 | 改为 `get_theme()` 动态获取 |
| 监听器重复触发 | 父类和子类都注册了监听器 | 子类不重复注册，只重写方法 |

---

## 调试技巧

在 `_on_theme_changed()` 中添加调试输出：

```python
def _on_theme_changed(self):
    print(f"[DEBUG] theme changed: {self.__class__.__name__}")
    theme = get_theme()
    ...
```

如果切换主题后没有看到输出，说明监听器没有注册。

---

## 验证步骤

1. 启动客户端，切换主题（亮/暗）
2. 检查所有新修改的 UI 组件是否正确变色
3. 如有问题，添加 `print()` 调试确认方法是否被调用
4. 检查 UI 元素是否保存为实例属性

---

## 历史问题

| 文件 | 问题 | 修复 |
|-----|------|------|
| `memory_panel.py` | CategorySection、MemorySection 定义了 `_on_theme_changed()` 但没注册监听器 | 添加 `register_theme_listener()` |
| `memory_panel.py` | `name_label`、`add_btn`、`info_label` 是局部变量 | 改为 `self._xxx` 实例属性 |
| `chat_panel.py` | session_title_label 缺少主题更新逻辑 | 添加到 `_on_theme_changed()` |
