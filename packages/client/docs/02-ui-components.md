# 02 - UI 组件详解

## 概述

客户端采用 PyQt6 构建用户界面，遵循三栏布局设计。本文档详细介绍各个 UI 组件的设计和实现。

## 主窗口 (MainWindow)

主窗口是整个应用的容器，负责协调所有子组件。

### 布局结构

```
MainWindow
├── MenuBar (菜单栏)
├── HeaderBar (顶部栏)
│   ├── Model Selector
│   ├── Provider Info
│   └── Settings Button
├── CentralWidget
│   └── QSplitter (三栏)
│       ├── SidebarPanel (左)
│       ├── ChatPanel (中)
│       └── RightPanel (右)
└── StatusBar (状态栏)
```

### 关键代码

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化控制器
        self.chat_controller = ChatController()
        self.mcp_controller = MCPController()
        self.skill_controller = SkillController()
        self.memory_controller = MemoryController()
        
        # 连接控制器回调
        self.mcp_controller.set_change_callback(self._on_mcp_changed)
        self.memory_controller.memory_changed.connect(self._on_memory_changed)
        
        # 初始化 UI
        self._setup_menubar()
        self._setup_header_bar()
        self._setup_central_widget()
        self._setup_statusbar()
        
        # 连接信号
        self.chat_panel.message_sent.connect(self._on_message_sent)
```

## 左侧栏 (SidebarPanel)

左侧栏提供会话列表和新建会话功能。

### 功能

- 显示会话列表（最近使用在前）
- 新建会话按钮
- 切换会话
- 删除会话
- 打开设置

### 尺寸

```python
COLLAPSED_WIDTH = 56   # 折叠宽度（仅图标）
EXPANDED_WIDTH = 220   # 展开宽度（图标 + 文字）
```

### 信号

```python
class SidebarPanel(QWidget):
    # 信号定义
    session_new_requested = pyqtSignal()           # 新建会话
    session_switch_requested = pyqtSignal(str)     # 切换会话
    session_delete_requested = pyqtSignal(str)     # 删除会话
    settings_requested = pyqtSignal()               # 打开设置
```

### 数据更新

```python
def update_sessions(self, sessions: list, current_id: str | None):
    """
    更新会话列表显示。
    
    Args:
        sessions: 会话信息列表 [{"id": str, "name": str}, ...]
        current_id: 当前会话 ID
    """
    # 清空现有列表
    # 重新创建会话按钮
    # 高亮当前会话
```

## 中央对话面板 (ChatPanel)

中央面板是主要的交互区域，显示对话历史和输入框。

### 组件结构

```
ChatPanel
├── QScrollArea (消息显示区)
│   └── MessagesWidget
│       ├── UserMessage
│       ├── AssistantMessage
│       ├── ToolCallMessage
│       └── ...
├── InputArea (输入框)
│   ├── QLineEdit (文本输入)
│   └── SendButton
└── SkillCompleter (技能自动补全)
```

### 消息渲染

使用 Markdown 渲染助手响应：

```python
from markdown import Markdown

class ChatPanel(QWidget):
    def __init__(self):
        self.md = Markdown(extensions=[
            'fenced_code',
            'codehilite',
            'tables',
            'toc',
            'nl2br',
        ])
    
    def append_assistant_message(self, content: str):
        """渲染助手消息（Markdown）"""
        html = self.md.convert(content)
        # 显示 HTML
```

### 流式输出

支持逐字符流式显示，并在追加内容后通过 `QPropertyAnimation` 平滑滚动到底部：

```python
def append_text_chunk(self, chunk: str):
    """追加文本块（流式）"""
    # 更新当前消息的文本
    # 启动滚动动画
```

### 工具调用状态样式

工具调用与结果卡片使用更明显的视觉反馈来区分状态：

- `thinking` 状态：更粗的边框、轻微光晕和 ⚡ 标识
- `succeeded` 状态：更粗的边框、绿色光晕和加粗图标
- `failed` 状态：更粗的边框、红色光晕和加粗图标

这类样式调整用于在 QTextBrowser 的能力范围内模拟“活跃/完成/失败”的状态变化。

### 技能自动补全

输入 `/` 时触发技能补全：

```python
class SkillCompleter(QCompleter):
    def __init__(self, skills: list[str], parent=None):
        super().__init__(skills, parent)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
```

## 右侧面板 (RightPanel)

右侧面板是可折叠的多功能面板，包含四个区块。

### 区块结构

```
RightPanel
├── MemorySection (记忆)
│   ├── CategoryList
│   └── EntryList
├── SkillsSection (技能)
│   ├── SkillList
│   └── AddButton
├── MCPSection (MCP 服务器)
│   ├── ServerList
│   └── AddButton
└── FileTreeSection (文件树)
    └── QTreeView
```

### 折叠状态

默认折叠所有区块：

```python
# 初始状态
self._sections_expanded = {
    "memory": False,
    "skills": False,
    "mcp": False,
    "files": True,
}
```

### 信号

```python
class RightPanel(QWidget):
    # 记忆相关
    memory_add_requested = pyqtSignal()
    memory_edit_requested = pyqtSignal(str, int)  # category, index
    memory_remove_requested = pyqtSignal(str, int)  # category, index
    
    # 技能相关
    add_skill_requested = pyqtSignal()
    skill_double_clicked = pyqtSignal(str)  # skill_name
    
    # MCP 相关
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)  # server_name
    server_double_clicked = pyqtSignal(str)  # server_name
    
    # 文件树相关
    work_dir_changed = pyqtSignal(str)  # path
```

## 记忆面板 (MemoryPanel)

记忆面板提供对全局 MEMORY.md 的可视化管理。

### 功能

- 查看四种记忆类别
- 添加新记忆条目
- 编辑现有条目
- 删除条目
- 清空所有记忆

### 类别映射

| 枚举值 | 显示名称 | 说明 |
|--------|----------|------|
| `USER_PROFILE` | 用户偏好 | 用户角色、偏好、技能 |
| `KEY_DECISIONS` | 关键决策 | 重要技术决策 |
| `LEARNED_PATTERNS` | 学习模式 | Agent 学习到的模式 |
| `PROJECT_CONTEXT` | 项目上下文 | 项目特定约定 |

### 添加条目对话框

```python
class AddEntryDialog(QDialog):
    def __init__(self, category: MemoryCategory, parent=None):
        self.category_combo = QComboBox()
        self.content_edit = QTextEdit()
        
    def get_entry(self) -> tuple[MemoryCategory, str]:
        """返回 (类别, 内容)"""
        return self.category, self.content
```

## 设置对话框 (SettingsDialog)

设置对话框提供应用配置界面。

### 配置项

| 配置项 | 类型 | 说明 |
|--------|------|------|
| Provider | ComboBox | LLM 提供商 |
| API Key | LineEdit | API 密钥 |
| Base URL | LineEdit | 自定义 API 端点 |
| Model | ComboBox | 模型选择 |
| Temperature | SpinBox | 温度参数 |
| Max Iterations | SpinBox | 最大迭代次数 |

### 保存配置

```python
def accept(self):
    """保存配置"""
    self.settings.update({
        "provider": self.provider_combo.currentText(),
        "api_key": self.api_key_edit.text(),
        "base_url": self.base_url_edit.text(),
        "model": self.model_combo.currentText(),
        "temperature": self.temp_spin.value(),
        "max_iterations": self.iter_spin.value(),
    })
    super().accept()
```

## 样式系统

### 样式定义

使用 QSS (Qt Style Sheet) 定义应用样式：

```python
STYLES = """
QMainWindow {
    background-color: #1a1a2e;
}

QPushButton {
    background-color: #4a4a6a;
    color: white;
    border-radius: 4px;
    padding: 8px 16px;
}

QPushButton:hover {
    background-color: #5a5a7a;
}

/* ... 更多样式 */
"""
```

### 主题色

| 用途 | 颜色 | 说明 |
|------|------|------|
| 背景色 | `#1a1a2e` | 深色背景 |
| 前景色 | `#ffffff` | 白色文字 |
| 强调色 | `#6c5ce7` | 紫色 |
| 成功色 | `#00b894` | 绿色 |
| 警告色 | `#fdcb6e` | 黄色 |
| 错误色 | `#e74c3c` | 红色 |

## 最佳实践

### 1. UI 线程安全

所有 UI 更新必须在主线程执行：

```python
# ✓ 正确：使用信号
self.some_signal.emit(data)

# ✗ 错误：直接从其他线程更新 UI
self.some_label.setText(data)  # 如果在其他线程调用会崩溃
```

### 2. 异步操作

使用 `@asyncSlot` 处理异步操作：

```python
@asyncSlot(str)
async def _on_message_sent(self, message: str):
    """信号连接的异步方法"""
    async for chunk in self.controller.send_message(message):
        self.chat_panel.append_text_chunk(chunk)
```

### 3. 内存管理

及时断开信号连接，避免内存泄漏：

```python
def closeEvent(self, event):
    """窗口关闭时清理"""
    self.chat_panel.message_sent.disconnect(self._on_message_sent)
    super().closeEvent(event)
```
