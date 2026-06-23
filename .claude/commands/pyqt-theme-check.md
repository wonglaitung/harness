---
name: pyqt-theme-check
description: PyQt6 主题切换开发检查清单。每次修改 UI 代码后必须检查主题切换响应链，避免重启才能生效。
---

# PyQt6 主题切换检查清单

**每次修改 PyQt6 UI 代码后，必须检查主题切换是否正常工作。**

---

## 检查清单

| 场景 | 必须做的事 |
|-----|-----------|
| 新增 QWidget 子类 | 实现 `_on_theme_changed()` 方法 |
| 新增自定义绘制组件 | `paintEvent` 中调用 `get_theme()` 动态获取颜色 |
| 新增嵌套组件 | 父组件的 `_on_theme_changed()` 调用子组件的 `_on_theme_changed()` |
| 使用样式表的组件 | 在 `_on_theme_changed()` 中重新设置 `setStyleSheet()` |

---

## 实现方式

### 方式 1：继承 ThemeAwareWidget（推荐）

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

### 方式 2：手动实现 _on_theme_changed()

```python
class MyWidget(QWidget):
    def _on_theme_changed(self):
        theme = get_theme()
        self.setStyleSheet(f"...")

# 父组件必须传播主题变化
class ParentWidget(QWidget):
    def _on_theme_changed(self):
        for child in self._children:
            if hasattr(child, '_on_theme_changed'):
                child._on_theme_changed()
```

### 方式 3：自定义绘制组件

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
| 新组件主题不变 | 没有实现 `_on_theme_changed()` | 添加方法并更新样式 |
| 子组件主题不变 | 父组件没有传播主题变化 | 父组件调用子组件的 `_on_theme_changed()` |
| 自定义绘制颜色不变 | `paintEvent` 缓存了颜色 | 改为 `get_theme()` 动态获取 |
| QLabel 样式不变 | 样式表写在 `__init__` 中 | 移到 `_on_theme_changed()` 中 |

---

## 验证步骤

1. 启动客户端，切换主题（亮/暗）
2. 检查所有新修改的 UI 组件是否正确变色
3. 如有问题，在组件中添加 `print(f"theme changed: {self}")` 调试

---

## 历史问题

- `memory_panel.py`: CategorySection、MemorySection 缺少 `_on_theme_changed()`
- `chat_panel.py`: session_title_label 缺少主题更新逻辑
