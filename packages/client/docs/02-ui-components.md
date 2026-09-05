# 02 - UI 组件详解

## 概述

客户端采用 PyQt6 构建用户界面，遵循三栏布局设计。本文档详细介绍各个 UI 组件的设计和实现。

## 自动补全组件

输入框支持两种自动补全：

### 文件名补全（`@` 前缀）

输入 `@` 后弹出文件名补全菜单，支持快速引用工作区文件。

```python
class FileCompleter(QCompleter):
    """文件名自动补全，@ 前缀触发"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setFilterMode(Qt.MatchFlag.MatchContains)

    def update_files(self, files: list[str]):
        """更新文件列表"""
        model = QStringListModel(files, self)
        self.setModel(model)
```

### 技能补全（`/` 前缀）

输入 `/` 后弹出技能列表，支持快速调用预定义技能。

```python
class SkillCompleter(QCompleter):
    """技能自动补全，/ 前缀触发，支持主题和描述显示"""

    def __init__(self, skills: list[SkillInfo], parent=None):
        super().__init__(parent)
        self._skills = skills
        self._popup: QListView | None = None
        self._setup_model()

    def _setup_model(self):
        """设置模型，显示技能名称和描述"""
        model = QStringListModel()
        model.setStringList([s.name for s in self._skills])
        self.setModel(model)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
```

**功能特性**：
- **主题支持**：Popup 样式随深色/浅色主题切换
- **描述显示**：Tooltip 显示技能详细描述
- **显式激活**：支持 `/skill-name` 格式直接调用指定技能

**实现要点**：
- Popup 使用 `Qt.WindowType.Popup` 确保正确的窗口层级
- 通过 `eventFilter` 处理键盘导航（上/下/Enter/Esc）
- `textChanged` 信号触发补全列表更新
- 选中后通过 `activated` 信号插入技能名称

**显式技能激活**：

```python
# 用户输入 /skill-name 直接激活技能
def _on_text_changed(self, text: str):
    if text.startswith("/"):
        skill_name = text[1:].strip()
        if skill_name:
            # 查找匹配技能
            for skill in self._skills:
                if skill.name == skill_name:
                    self._activate_skill(skill)
                    return
```

**相关提交**：
- `0d05deb`: 改进 UI，添加主题支持和描述显示
- `7f7f46f`: 添加 `/skill-name` 显式激活支持

## 消息气泡组件

### 水平滚动支持

助手消息气泡支持水平滚动，用于显示长代码行：

```python
class MessageBubble(QWidget):
    """消息气泡，助手消息支持水平滚动"""

    def _setup_assistant_content(self, html: str):
        # 使用 QScrollArea + QLabel 组合
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # QLabel 显示 Markdown 渲染后的 HTML
        self._content_label = QLabel()
        self._content_label.setTextFormat(Qt.TextFormat.RichText)
        self._content_label.setText(html)
        self._content_label.adjustSize()

        # 设置固定高度
        self._scroll_area.setFixedHeight(self._content_label.height())
        self.setFixedHeight(self._scroll_area.height() + padding * 2)

        # 父控件使用 Fixed 策略
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed
        )
```

**关键点**：
- `setWidgetResizable(False)` 允许内部 widget 保持自己的尺寸
- `adjustSize()` 让 QLabel 根据内容计算尺寸
- 父控件使用 `Fixed` size policy 防止过度扩展

### 消息气泡尺寸策略

AI 消息和用户消息采用不同的尺寸策略，优化视觉布局：

```python
class MessageBubble(QWidget):
    def __init__(self, role: str, content: str, max_width: int = 600):
        # ...

        if self._role == "assistant":
            # AI 消息：水平扩展，填充可用空间
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self._content_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            # 设置最小宽度（60% max_width），避免消息过窄
            self.setMinimumWidth(int(self._max_width * 0.6))
        else:
            # 用户消息：收缩到内容宽度
            self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.MinimumExpanding)
            self.setMinimumWidth(60)
```

**设计原理**：

| 消息类型 | Size Policy | 行为 |
|----------|-------------|------|
| AI 消息 | `Preferred` × `Preferred` | 水平扩展，填充可用空间（有最小宽度） |
| 用户消息 | `Maximum` × `MinimumExpanding` | 收缩到内容宽度，高度自适应 |

**布局效果**：
- AI 消息左对齐，占据较宽的空间，便于阅读代码和长文本
- 用户消息右对齐，紧凑显示用户输入

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

左侧栏提供会话列表和新建会话功能。它是固定宽度的面板（不可折叠）。

### 功能

- 显示会话列表（当前会话在前，支持右键删除）
- 新建会话按钮
- 切换会话
- 删除会话
- 打开设置

### 尺寸

```python
FIXED_WIDTH = 180   # 固定宽度（不可折叠）
```

### 信号

```python
class SidebarPanel(ThemeAwareWidget):
    # 信号定义
    work_dir_changed = pyqtSignal(Path)               # 工作目录已变更
    mcp_connect_requested = pyqtSignal(str)           # 请求连接 MCP 服务器（名称）
    skill_load_requested = pyqtSignal(Path)           # 请求加载技能（路径）
    session_delete_requested = pyqtSignal(str)        # 删除会话（id）
    session_switch_requested = pyqtSignal(str)        # 切换会话（id）
    session_new_requested = pyqtSignal()              # 新建会话
    settings_requested = pyqtSignal()                 # 打开设置
```

### 数据更新

```python
def update_sessions(self, current_session, history_sessions: list):
    """
    更新会话列表显示。
    
    Args:
        current_session: 当前 ClientSession 对象（或 None）
        history_sessions: 历史 ClientSession 对象列表
    """
    # 清空现有列表
    # 当前会话排在第一项（带 ● 高亮）
    # 历史会话项支持右键菜单删除
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
├── InputBar (输入栏，垂直布局)
│   ├── BrowserStatusBar (浏览器状态条，条件显示)
│   │   ├── StatusDot (绿色圆点)
│   │   ├── StatusText ("浏览器工具已激活 (7 个工具)")
│   │   └── CloseButton (× 按钮)
│   ├── AttachmentPreview (附件预览区)
│   ├── InputRow (输入行)
│   │   ├── AttachmentButton (附件按钮)
│   │   ├── QLineEdit (文本输入)
│   │   └── SendButton (发送按钮)
│   └── SkillCompleter (技能自动补全)
```

### 浏览器状态条

当浏览器工具激活时，输入框上方显示状态条：

```python
class ChatPanel(QWidget):
    browser_close_requested = pyqtSignal()  # 关闭浏览器信号

    def set_browser_active(self, is_active: bool, tool_count: int = 7):
        """设置浏览器状态显示"""
        if is_active:
            self._browser_status_text.setText(f"浏览器工具已激活 ({tool_count} 个工具)")
            self._browser_status_bar.setVisible(True)
        else:
            self._browser_status_bar.setVisible(False)
```

**状态条布局**：

```
┌────────────────────────────────────────────────────────────┐
│ ● 浏览器工具已激活 (7 个工具)                          [×] │
└────────────────────────────────────────────────────────────┘
```

- **绿色圆点**：表示运行中
- **工具数量**：动态显示可用工具数
- **关闭按钮**：点击快速关闭浏览器

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

### 附件上传组件

支持上传图片和文档，发送多模态消息。

#### 支持的文件类型

| 类型 | 扩展名 | 大小限制 |
|------|--------|----------|
| 图片 | PNG, JPEG, GIF, WebP | ≤ 10MB |
| 文档 | PDF, TXT | ≤ 10MB |

#### 文档大小警告

当文档超过建议大小（5MB）时，会弹出警告对话框：

```python
class AttachmentPreview(QWidget):
    # 建议大小阈值
    RECOMMENDED_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB

    def _show_large_document_warning(self, filename: str, size_mb: float) -> bool:
        """显示大文档警告对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("文档大小警告")
        msg_box.setText(f"文档 '{filename}' 大小为 {size_mb:.1f}MB，可能影响处理速度。")
        msg_box.setInformativeText("是否继续添加此附件？")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        # 自定义按钮
        continue_btn = msg_box.addButton("继续发送", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        msg_box.setDefaultButton(cancel_btn)
        msg_box.exec()

        return msg_box.clickedButton() == continue_btn
```

**警告对话框按钮**：
- **继续发送**：添加附件（用户确认）
- **取消**：取消添加（默认选中）

**设计理念**：不提供"查看文档"按钮，避免用户在警告弹窗中分心，保持决策焦点。

#### 组件结构

```
ChatPanel
└── InputBar (输入栏，垂直布局)
    ├── AttachmentPreview (附件预览区，内嵌于输入栏)
    │   ├── ImageThumbnail (图片缩略图，水平排列)
    │   │   ├── QPixmap (缩略图，32x32)
    │   │   └── RemoveButton (删除按钮)
    │   └── DocumentCard (文档卡片，水平排列)
    │       ├── QPainter 绘制的图标
    │       ├── 文件名标签
    │       └── RemoveButton (删除按钮)
    └── InputRow (输入行，水平布局)
        ├── AttachmentButton (附件按钮)
        ├── QLineEdit (文本输入)
        └── SendButton (发送按钮)
```

**注意**：附件预览区已集成到输入栏内部，采用水平紧凑布局（高度 32px），提供更流畅的用户体验。

#### 附件预览

附件预览区显示已选择的文件，支持移除操作：

```python
class AttachmentPreview(QWidget):
    """附件预览区，显示已选择的图片和文档"""

    remove_requested = pyqtSignal(str)  # file_path

    def add_image(self, file_path: str, thumbnail: QPixmap):
        """添加图片预览"""
        # 创建缩略图控件
        thumb = ImageThumbnail(file_path, thumbnail)
        thumb.remove_clicked.connect(lambda: self.remove_requested.emit(file_path))
        self._layout.addWidget(thumb)

    def add_document(self, file_path: str, doc_type: str):
        """添加文档预览"""
        # 创建文档图标控件
        icon = DocumentIcon(file_path, doc_type)
        icon.remove_clicked.connect(lambda: self.remove_requested.emit(file_path))
        self._layout.addWidget(icon)

    def clear(self):
        """清空所有预览"""
        for i in reversed(range(self._layout.count())):
            widget = self._layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
```

#### 图片缩略图

使用 QPainter 绘制矢量图标，避免模糊问题：

```python
class ImageThumbnail(QWidget):
    """图片缩略图，带删除按钮"""

    remove_clicked = pyqtSignal()

    def __init__(self, file_path: str, thumbnail: QPixmap, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self._thumbnail = thumbnail
        self.setFixedSize(80, 80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角背景
        theme = get_theme()
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.PANEL)))
        painter.drawRoundedRect(self.rect(), 8, 8)

        # 绘制缩略图
        scaled = self._thumbnail.scaled(
            70, 70,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # 绘制删除按钮（右上角）
        self._draw_remove_button(painter)

    def _draw_remove_button(self, painter):
        """绘制删除按钮"""
        # 红色圆形背景
        painter.setBrush(QBrush(QColor("#E74C3C")))
        painter.drawEllipse(60, 4, 16, 16)

        # 白色 X 图标
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(64, 8, 72, 16)
        painter.drawLine(72, 8, 64, 16)
```

#### 文档图标

使用 QPainter 绘制矢量文档图标：

```python
class DocumentIcon(QWidget):
    """文档图标，使用 QPainter 绘制"""

    remove_clicked = pyqtSignal()

    def __init__(self, file_path: str, doc_type: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self._doc_type = doc_type  # "pdf" or "txt"
        self.setFixedSize(80, 80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = get_theme()

        # 绘制文档背景
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(theme.PANEL)))
        painter.drawRoundedRect(10, 5, 60, 70, 4, 4)

        # 绘制折角效果
        painter.setBrush(QBrush(QColor(theme.BORDER)))
        fold = [QPointF(55, 5), QPointF(70, 20), QPointF(55, 20)]
        painter.drawPolygon(QPolygonF(fold))

        # 根据类型绘制图标
        if self._doc_type == "pdf":
            painter.setPen(QPen(QColor("#E74C3C"), 2))
            painter.drawText(25, 45, "PDF")
        else:
            painter.setPen(QPen(QColor(theme.TEXT), 2))
            painter.drawText(30, 45, "TXT")

        # 绘制删除按钮
        self._draw_remove_button(painter)
```

#### 文件选择

通过文件对话框选择文件：

```python
def _show_file_dialog(self):
    """显示文件选择对话框"""
    dialog = QFileDialog(self)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    dialog.setNameFilter(
        "支持的文件 (*.png *.jpg *.jpeg *.gif *.webp *.pdf *.txt)"
    )

    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        for file_path in files:
            self._add_attachment(file_path)

def _add_attachment(self, file_path: str):
    """添加附件到预览区"""
    # 检查文件大小
    size = os.path.getsize(file_path)
    if size > 10 * 1024 * 1024:  # 10MB
        self._show_error(f"文件过大: {file_path}")
        return

    # 根据类型添加预览
    ext = Path(file_path).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        thumbnail = self._create_thumbnail(file_path)
        self._preview.add_image(file_path, thumbnail)
    elif ext in (".pdf", ".txt"):
        self._preview.add_document(file_path, ext[1:])
```

#### 发送多模态消息

附件与文本一起发送：

```python
def _send_message(self):
    """发送消息（可能包含附件）"""
    text = self._input.text().strip()
    attachments = self._preview.get_attachments()

    if not text and not attachments:
        return

    # 构建多模态消息
    if attachments:
        content = self._build_multimodal_content(text, attachments)
    else:
        content = text

    # 发送到控制器
    self.message_submitted.emit(content)

    # 清空输入
    self._input.clear()
    self._preview.clear()

def _build_multimodal_content(self, text: str, attachments: list) -> list[dict]:
    """构建多模态消息内容"""
    content = []

    # 添加文本
    if text:
        content.append({"type": "text", "text": text})

    # 添加附件
    for attachment in attachments:
        if attachment["type"] == "image":
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": attachment["media_type"],
                    "data": attachment["base64_data"],
                }
            })
        elif attachment["type"] == "document":
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": attachment["media_type"],
                    "data": attachment["base64_data"],
                }
            })

    return content
```

## 右侧面板 (RightPanel)

右侧面板是可折叠的多功能面板，包含记忆、文件树和"更多工具"三个区块。

### 区块结构

```
RightPanel
├── MemorySection (记忆，默认展开)
│   ├── CategoryList
│   └── EntryList
├── FileTreeSection (文件树，默认折叠)
│   └── QTreeView
└── MoreToolsSection (更多工具，默认折叠)
    ├── SkillsSection (技能)
    │   ├── SkillList
    │   └── AddButton
    ├── MCPServersSection (MCP 服务器)
    │   ├── ServerList
    │   └── AddButton
    ├── MonitoringSection (监控)
    ├── ExecutionLogSection (执行日志)
    ├── ScheduleButton (排程)
    └── BrowserButton (浏览器)
```

### 折叠状态

记忆区块默认展开，文件树与"更多工具"区块默认折叠：

```python
# MemorySection 默认展开
# FileTreeSection: set_collapsed(True)  # 折叠
# MoreToolsSection: set_collapsed(True)  # 折叠（含技能/MCP/监控/排程/浏览器）
```

### 信号

```python
class RightPanel(ThemeAwareWidget):
    # 记忆相关
    memory_add_requested = pyqtSignal(str)          # category
    memory_edit_requested = pyqtSignal(str, int)   # category, index
    memory_remove_requested = pyqtSignal(str, int)  # category, index
    memory_importance_changed = pyqtSignal(str, int, float)  # category, index, importance

    # 技能相关
    add_skill_requested = pyqtSignal()
    skill_double_clicked = pyqtSignal(str)          # skill_name

    # MCP 相关
    add_mcp_server_requested = pyqtSignal()
    toggle_mcp_server_requested = pyqtSignal(str)   # server_name
    server_double_clicked = pyqtSignal(str)         # server_name

    # 文件树相关
    file_clicked = pyqtSignal(Path)                 # 双击文件
    work_dir_changed = pyqtSignal(Path)             # 工作目录已变更

    # 更多工具
    schedule_requested = pyqtSignal()               # 打开排程
    browser_toggle_requested = pyqtSignal()         # 切换浏览器状态
```

## 记忆面板 (MemoryPanel)

记忆面板提供对全局 MEMORY.md 的可视化管理。

### 功能

- 查看四种记忆类别
- 添加新记忆条目
- 编辑现有条目
- 删除条目
- 清空所有记忆
- 调整记忆条目重要性（ImportanceSlider，0.0–1.0）

### 记忆重要性

每条记忆条目都带有一个重要性分数（importance，0.0–1.0），用于智能归档与显示：

- **高 (≥ 0.8)**：核心偏好（绿色标记）
- **中 (0.5–0.8)**：有用模式（橙色标记）
- **低 (< 0.5)**：临时信息（灰色标记）

重要性可通过 `MemoryPanel` 中的 `ImportanceSlider` 拖动调整，对应 `MemoryController.update_importance(category, index, importance)`，并通过 `RightPanel.memory_importance_changed(str, int, float)` 信号通知上层。

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

设置对话框提供应用配置界面，包含多个标签页。

### 标签页结构

| 标签页 | 配置项 |
|--------|--------|
| API | Provider, API Key, Base URL, Model, Context Window |
| 常规 | Theme, Stream, Auto Save, Temperature, Max Iterations |
| 目录 | Work Directory, Remember Dir |
| 路由 | Enable Routing, High/Low Model, Router Path/URL |
| 浏览器 | Browser Type, Headless, Screenshot, Timeout |

### 浏览器配置标签页

从 v1.5.0 开始，设置对话框包含浏览器配置标签页：

```python
# 浏览器类型选择（带推荐标签）
self.browser_type_combo = QComboBox()
self.browser_type_combo.addItems(["msedge", "chrome", "chromium", "firefox"])

# msedge 显示"推荐"标签
self.browser_recommended_label = QLabel("推荐")
self.browser_recommended_label.setStyleSheet(f"""
    QLabel {{
        background-color: {theme.ACCENT};
        color: white;
        border-radius: 4px;
    }}
""")
self.browser_recommended_label.setVisible(browser_type == "msedge")
```

**配置项说明**：

| 配置项 | 类型 | 说明 |
|--------|------|------|
| Browser Type | ComboBox | 浏览器类型（msedge 推荐） |
| Headless Mode | CheckBox | 无头模式，后台运行 |
| Auto Screenshot | CheckBox | 每次操作后自动截图 |
| Timeout | SpinBox | 页面加载超时时间（毫秒） |

### API 配置项

| 配置项 | 类型 | 说明 |
|--------|------|------|
| Provider | ComboBox | LLM 提供商 |
| API Key | LineEdit | API 密钥 |
| Base URL | LineEdit | 自定义 API 端点 |
| Model | ComboBox | 模型选择 |
| Context Window | ComboBox | 上下文窗口大小 |
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

客户端支持 **亮色/暗色双主题**，使用 Banking-grade 调色板设计，专为信任、专业和清晰设计。

### 主题架构

主题系统由核心模块组成：

```
themes/
├── __init__.py       # 主题管理器 - 切换、监听、通知
├── dark.py           # DarkTheme 类 - 暗色调色板
├── light.py          # LightTheme 类 - 亮色调色板
├── stylesheet.py     # generate_stylesheet() - QSS 生成器
└── theme_aware.py    # ThemeAwareWidget - 主题感知基类
```

### 主题模式

支持三种主题模式：

| 模式 | 说明 |
|------|------|
| `auto` | 自动跟随系统主题（Windows/macOS/Linux） |
| `light` | 强制使用亮色主题 |
| `dark` | 强制使用暗色主题 |

```python
from harness_client.themes import set_theme_mode, ThemeMode

# 自动跟随系统
set_theme_mode("auto", app)

# 强制亮色主题
set_theme_mode("light", app)

# 强制暗色主题
set_theme_mode("dark", app)
```

### 主题感知组件

所有 UI 组件应继承 `ThemeAwareWidget` 或使用 `get_theme()` 获取当前主题：

```python
from harness_client.ui.theme_aware import ThemeAwareWidget
from harness_client.themes import get_theme

class MyCustomWidget(ThemeAwareWidget):
    def _apply_theme_style(self):
        """主题切换时自动调用"""
        theme = self.theme()  # 或 get_theme()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                color: {theme.TEXT};
            }}
        """)
```

#### paintEvent 主题适配

在 `paintEvent` 中动态获取主题颜色：

```python
def paintEvent(self, event):
    theme = get_theme()
    painter = QPainter(self)
    painter.setBrush(QBrush(QColor(theme.ASSISTANT_BUBBLE)))
    # ...
```

### 主题监听器

可注册自定义监听器响应主题切换：

```python
from harness_client.themes import register_theme_listener, unregister_theme_listener

def on_theme_changed():
    """主题切换时调用"""
    theme = get_theme()
    print(f"主题已切换为: {type(theme).__name__}")

register_theme_listener(on_theme_changed)
```

### DarkTheme 调色板
    # === Background Hierarchy ===
    APP_BACKGROUND = "#0D1117"  # 主窗口 - 最深层
    CHROME = "#161B22"          # 标题栏、侧边栏
    PANEL = "#21262D"           # 面板背景
    PANEL_ALT = "#292E36"       # 替代面板
    COMPOSER = "#1C2128"        # 输入区域

    # === Trust Blue (Not AI Blue) ===
    ACCENT = "#1F6FEB"          # 信任蓝 - 主强调色
    ACCENT_HOVER = "#388BFD"    # 悬停状态
    ACCENT_LIGHT = "#58A6FF"    # 高亮色

    # === Typography System ===
    FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", system-ui, sans-serif'
    FONT_FAMILY_MONO = '"Consolas", "Courier New", monospace'
    FONT_SIZE_BASE = "13px"

    # === Border Radius Scale ===
    RADIUS_SM = "3px"   # 小型：标签、迷你按钮
    RADIUS_MD = "6px"   # 标准：按钮、输入框、面板
    RADIUS_LG = "8px"   # 大型：消息气泡、卡片
```

### Trust Blue 设计理念

从 "AI Blue" (#2563EB) 迁移到更深沉的 "Trust Blue" (#1F6FEB)，为金融/专业场景建立信任感：

| 设计维度 | AI Blue | Trust Blue |
|---------|---------|------------|
| 主色调 | #2563EB (亮蓝) | #1F6FEB (深蓝) |
| 视感 | 科技感、年轻化 | 专业、权威、可信赖 |
| 适用场景 | AI 产品、消费级应用 | 金融、企业级应用 |

### 颜色系统

#### 背景层次

| 层级 | 颜色 | 用途 |
|------|------|------|
| `APP_BACKGROUND` | `#0D1117` | 主窗口背景（最深） |
| `CHROME` | `#161B22` | 标题栏、侧边栏、边框区域 |
| `PANEL` | `#21262D` | 面板背景 |
| `PANEL_ALT` | `#292E36` | 替代面板、悬停状态 |
| `COMPOSER` | `#1C2128` | 输入区域 |

#### 文本颜色

| 层级 | 颜色 | 用途 |
|------|------|------|
| `TEXT` | `#E6EDF3` | 主文本（高对比） |
| `TEXT_SUBTLE` | `#8B949E` | 次级文本 |
| `TEXT_MUTED` | `#6E7681` | 提示文本、占位符 |
| `TEXT_DISABLED` | `#484F58` | 禁用状态 |

#### 语义颜色

| 状态 | 主色 | 背景色 | 文本色 |
|------|------|--------|--------|
| Success | `#2EA043` | `#1A2F23` | `#6EE7B7` |
| Warning | `#D29922` | `#2E2518` | `#F0C674` |
| Danger | `#DA3633` | `#3D1F20` | `#FDA4AF` |
| Info | `#58A6FF` | `#1C2B3E` | `#93C5FD` |

### 字体系统

#### 字体族

```python
# 主字体堆栈（优化清晰度和专业性）
FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", system-ui, sans-serif'

# 等宽字体（代码显示）
FONT_FAMILY_MONO = '"Consolas", "Courier New", monospace'
```

#### 字号层级

| 常量 | 尺寸 | 用途 |
|------|------|------|
| `FONT_SIZE_XS` | 11px | 时间戳、提示文本 |
| `FONT_SIZE_SM` | 12px | 次级文本、标签 |
| `FONT_SIZE_BASE` | 13px | 正文（默认） |
| `FONT_SIZE_MD` | 14px | 强调文本 |
| `FONT_SIZE_LG` | 16px | 区块标题 |
| `FONT_SIZE_XL` | 18px | 页面标题 |
| `FONT_SIZE_2XL` | 24px | 大标题 |

#### 行高与字重

```python
# 行高倍数
LINE_HEIGHT_TIGHT = 1.25     # 紧凑（标题）
LINE_HEIGHT_NORMAL = 1.5     # 标准（正文）
LINE_HEIGHT_RELAXED = 1.75   # 舒适（长文本）

# 字重
FONT_WEIGHT_NORMAL = "normal"
FONT_WEIGHT_MEDIUM = "500"
FONT_WEIGHT_BOLD = "bold"
FONT_WEIGHT_SEMIBOLD = "600"
```

### 圆角系统

金融场景偏好更锐利的边缘，建立专业感：

| 常量 | 尺寸 | 用途 |
|------|------|------|
| `RADIUS_SM` | 3px | 标签、迷你按钮、复选框 |
| `RADIUS_MD` | 6px | 按钮、输入框、面板 |
| `RADIUS_LG` | 8px | 消息气泡、卡片、对话框 |

### 样式生成器

使用 `generate_stylesheet()` 生成完整 QSS：

```python
from harness_client.themes.dark import DarkTheme
from harness_client.themes.stylesheet import generate_stylesheet

theme = DarkTheme()
stylesheet = generate_stylesheet(theme)
app.setStyleSheet(stylesheet)
```

样式生成器使用主题常量，避免硬编码颜色值：

```python
# stylesheet.py 示例
def generate_stylesheet(theme: DarkTheme) -> str:
    return """
    QWidget {
        background-color: """ + theme.APP_BACKGROUND + """;
        color: """ + theme.TEXT + """;
        font-family: """ + theme.FONT_FAMILY + """;
        font-size: """ + theme.FONT_SIZE_BASE + """;
    }

    QPushButton {
        border-radius: """ + theme.RADIUS_MD + """;
    }
    """
```

### 主题色总览

| 用途 | 颜色 | 常量 | 说明 |
|------|------|------|------|
| 主背景 | `#0D1117` | `APP_BACKGROUND` | 最深层背景 |
| 面板背景 | `#21262D` | `PANEL` | 面板区域 |
| 主文本 | `#E6EDF3` | `TEXT` | 高对比文本 |
| 强调色 | `#1F6FEB` | `ACCENT` | Trust Blue |
| 成功色 | `#2EA043` | `SUCCESS` | 绿色 |
| 警告色 | `#D29922` | `WARNING` | 琥珀色 |
| 错误色 | `#DA3633` | `DANGER` | 红色 |

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

## 排程面板 (SchedulePanel)

排程面板提供可视化的定时任务管理界面。

### 功能

- 创建 Cron 表达式或固定间隔的定时任务
- 编辑和删除排程
- 启动/暂停排程
- Cron 表达式验证和下次运行时间预览

### 组件结构

```
SchedulePanel
├── ScheduleSection (可折叠区块，用于右侧面板)
│   ├── AddButton (新建排程)
│   └── ScheduleItemWidget[] (排程列表)
│       ├── StatusIndicator (状态指示器)
│       ├── ScheduleInfo (名称、触发条件)
│       └── Controls (启动/暂停、编辑、删除)
├── ScheduleListWidget (非折叠组件，用于对话框)
│   ├── AddButton (新建排程，统一样式)
│   └── ScheduleItemWidget[] (排程列表)
└── ScheduleDialog (新建/编辑对话框)
    ├── NameInput (名称)
    ├── GoalInput (目标)
    ├── TriggerTypeSelector (Cron/Interval)
    ├── CronEditor (Cron 表达式编辑器)
    │   ├── CronInput
    │   └── NextRunPreview (下次运行时间)
    └── IntervalEditor (固定间隔编辑器)
```

### ScheduleSection vs ScheduleListWidget

两个组件用于不同的场景：

| 组件 | 继承 | 使用场景 | 特点 |
|------|------|----------|------|
| `ScheduleSection` | `CollapsibleSection` | 右侧面板 | 可折叠，标题栏可展开/收起 |
| `ScheduleListWidget` | `QWidget` | 对话框 | 非折叠，统一样式，直接显示内容 |

**ScheduleListWidget 设计要点**：

```python
class ScheduleListWidget(QWidget):
    """用于对话框的排程列表组件（非折叠）

    与 ScheduleSection 不同，此组件：
    - 不继承 CollapsibleSection，无折叠功能
    - 使用统一对话框样式（DIALOG_MARGINS, DIALOG_SPACING）
    - 新建按钮使用 ACCENT 颜色，与其他对话框按钮一致
    - 滚动区域带边框，与对话框整体风格协调
    """

    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str)
```

### 对话框样式统一

排程管理对话框使用 `dialog_styles.py` 中的统一样式：

```python
from harness_client.ui.dialog_styles import (
    DIALOG_MARGINS,
    DIALOG_SPACING,
    get_dialog_stylesheet,
)

def _on_schedule_panel(self):
    dialog = QDialog(self)
    dialog.setWindowTitle("排程管理")
    dialog.setStyleSheet(get_dialog_stylesheet())

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(*DIALOG_MARGINS)
    layout.setSpacing(DIALOG_SPACING)

    # 使用 ScheduleListWidget（非折叠）
    schedule_list = ScheduleListWidget()
    layout.addWidget(schedule_list)

    # 使用 QDialogButtonBox（统一样式）
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    layout.addWidget(button_box)
```

### 状态指示器

排程状态通过彩色圆点指示：

| 状态 | 颜色 | 说明 |
|------|------|------|
| 运行中 | 绿色 `#22c55e` | 排程正在执行 |
| 空闲 | 橙色 `#f59e0b` | 排程已启用，等待触发 |
| 已暂停 | 灰色 `#6b7280` | 排程已禁用 |
| 错误 | 红色 `#ef4444` | 排程执行出错 |

### Cron 表达式编辑器

支持标准 5 字段 Cron 表达式，并提供实时预览：

```
┌──────── 分钟 (0-59)
│ ┌────── 小时 (0-23)
│ │ ┌──── 日 (1-31)
│ │ │ ┌── 月 (1-12)
│ │ │ │ ┌ 星期 (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

常用示例：
- `0 9 * * *` - 每天 9:00
- `*/5 * * * *` - 每 5 分钟
- `0 9 * * 1-5` - 工作日 9:00

### 信号

```python
class ScheduleSection(CollapsibleSection):
    add_requested = pyqtSignal()              # 新建排程
    edit_requested = pyqtSignal(str)          # 编辑排程 (schedule_id)
    delete_requested = pyqtSignal(str)        # 删除排程 (schedule_id)
    toggle_requested = pyqtSignal(str)        # 切换启停 (schedule_id)
```

### 主题适配

排程面板继承 `ThemeAwareWidget`，自动响应主题切换：

```python
class ScheduleItemWidget(QWidget):
    def __init__(self, schedule_data: dict, parent=None):
        super().__init__(parent)
        register_theme_listener(self._on_theme_changed)

    def _on_theme_changed(self):
        theme = get_theme()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.APP_BACKGROUND};
                border-radius: {theme.RADIUS_SM};
            }}
        """)
```

## 监控面板 (MonitoringPanel)

监控面板提供实时会话指标和执行日志的可视化。

### 功能

- Token 使用统计（输入、输出、缓存命中）
- 会话统计（迭代次数、工具调用、耗时）
- 成本估算（美元）
- Token 使用趋势柱状图
- 执行日志实时显示

### 组件结构

```
MonitoringPanel
├── TokenSection (Token 使用)
│   ├── InputTokensLabel
│   ├── OutputTokensLabel
│   └── CacheHitRateLabel
├── StatsSection (会话统计)
│   ├── IterationsLabel
│   ├── ToolCallsLabel
│   └── DurationLabel
├── CostSection (成本估算)
│   └── CostLabel
├── TrendChart (趋势图)
│   └── Custom QPainter 绘制
└── ExecutionLogSection (执行日志)
    ├── Header (可折叠)
    └── LogList
        └── LogEntryWidget[]
```

### 趋势图 (TrendChart)

使用 QPainter 自定义绘制柱状图，支持主题切换：

```python
class TrendChart(QWidget):
    """Token 使用趋势柱状图 - 主题感知绘制"""

    def __init__(self, max_items: int = 10, parent=None):
        super().__init__(parent)
        self._data: list[int] = []
        self._max_items = max_items
        self.setFixedHeight(60)
        self.setMinimumWidth(180)
        register_theme_listener(self._on_theme_changed)

    def set_data(self, data: list[int]):
        """设置趋势数据"""
        self._data = data[-self._max_items:] if data else []
        self.update()

    def paintEvent(self, event):
        """绘制柱状图 - 动态获取主题"""
        theme = get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._data:
            # 无数据时显示占位文本
            painter.setPen(QColor(theme.TEXT_SUBTLE))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无数据")
            painter.end()
            return

        # 计算柱状图参数
        bar_width = (self.width() - 20) / len(self._data)
        max_value = max(self._data) if self._data else 1

        for i, value in enumerate(self._data):
            bar_height = (value / max_value) * (self.height() - 20)
            x = 10 + i * bar_width
            y = self.height() - 10 - bar_height

            # 绘制柱子
            bar_rect = QRectF(x, y, bar_width - 2, bar_height)
            painter.setBrush(QBrush(QColor(theme.ACCENT)))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawRoundedRect(bar_rect, 2, 2)

        painter.end()
```

**关键点**：
- 在 `paintEvent` 中动态获取主题颜色，不缓存
- 注册主题监听器，主题切换时调用 `update()` 重绘
- 支持无数据占位显示

### 执行日志区块 (ExecutionLogSection)

显示实时的执行日志：

```python
class ExecutionLogSection(CollapsibleSection):
    """执行日志区块 - 可折叠"""

    def __init__(self, controller: MonitoringController, parent=None):
        self._controller = controller
        self._log_widgets: list[LogEntryWidget] = []

        # 连接信号
        self._controller.log_entry_added.connect(self._add_log_entry)

    def _add_log_entry(self, entry: LogEntry):
        """添加日志条目"""
        widget = LogEntryWidget(entry)
        self._log_layout.addWidget(widget)
        self._log_widgets.append(widget)

        # 限制最大条目数
        if len(self._log_widgets) > 100:
            old_widget = self._log_widgets.pop(0)
            self._log_layout.removeWidget(old_widget)
            old_widget.deleteLater()
```

### 日志条目组件 (LogEntryWidget)

单条日志的显示：

```python
class LogEntryWidget(QWidget):
    """单条日志条目"""

    # 图标映射
    ICON_MAP = {
        "llm_call": "🤖",
        "llm_response": "💬",
        "tool_call": "🔧",
        "tool_result": "⚙️",
        "iteration": "🔄",
        "error": "❌",
    }

    def __init__(self, entry: LogEntry, parent=None):
        super().__init__(parent)
        self._entry = entry

        # 时间戳
        time_str = entry.timestamp.strftime("%H:%M:%S")
        self._time_label = QLabel(time_str)

        # 图标
        icon = self.ICON_MAP.get(entry.type, "📌")
        self._icon_label = QLabel(icon)

        # 消息
        self._message_label = QLabel(entry.message)

        # 根据类型设置样式
        self._apply_style()
```

### 与 MonitoringController 集成

```python
# MainWindow 中创建和连接
self.monitoring_controller = MonitoringController()
self.monitoring_panel = MonitoringPanel(self.monitoring_controller)

# 连接 ChatController 进度回调
self.chat_controller.set_progress_callback(
    self.monitoring_controller.handle_progress_event
)
```

### 主题适配

监控面板继承 `ThemeAwareWidget`，所有子组件自动响应主题切换：

```python
class MonitoringPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()

        # 更新数值标签
        self._input_label.setStyleSheet(f"color: {theme.TEXT};")
        self._output_label.setStyleSheet(f"color: {theme.TEXT_SUBTLE};")
        self._cost_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.ACCENT};
                font-size: {theme.FONT_SIZE_MD};
                font-weight: bold;
            }}
        """)

        # 触发趋势图重绘
        self._trend_chart.update()
```

## 可折叠区块组件 (CollapsibleSection)

可折叠区块是右侧面板的核心组件，支持动画展开/折叠。

### 实现模式

使用 QScrollArea + QPropertyAnimation 模式：

```python
class CollapsibleSection(QWidget):
    """可折叠区块 - 使用 QScrollArea + QPropertyAnimation"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._is_collapsed = True

        # QScrollArea 作为内容容器
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setMaximumHeight(0)  # 初始折叠
        self.content_area.setMinimumHeight(0)

        # 动画组
        self.toggle_animation = QParallelAnimationGroup()
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self, b"minimumHeight")
        )
        self.toggle_animation.addAnimation(
            QPropertyAnimation(self.content_area, b"maximumHeight")
        )
```

### 关键设计点

1. **QScrollArea 作为内容容器**：允许内容超出可视区域时滚动
2. **QParallelAnimationGroup**：同时动画整体高度和内容区域高度
3. **header_widget 使用 Fixed 垂直 policy**：防止标题区域被意外拉伸

```python
# 标题区域固定高度
header_widget = QWidget()
header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

# 布局设置 stretch factor
main_layout.addWidget(header_widget, 0)  # stretch=0
main_layout.addWidget(self.content_area, 1)  # stretch=1
```

### MoreToolsSection 自动伸展

`MoreToolsSection` 在展开状态下可以自动填充面板底部剩余空间：

```python
class MoreToolsSection(CollapsibleSection):
    """更多工具区块 - 展开时自动伸展到底部"""

    stretch_mode_changed = pyqtSignal(bool)  # True=stretch to fill space

    def _on_animation_finished(self):
        if self._is_collapsed:
            # 折叠状态 - 固定高度
            self.setMaximumHeight(self._collapsed_header_height)
            self.content_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self.stretch_mode_changed.emit(False)
        else:
            # 展开状态 - 允许伸展
            self.setMinimumHeight(min_height)
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.content_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.stretch_mode_changed.emit(True)
```

**RightPanel 响应伸展模式**：

```python
def _on_more_tools_stretch_changed(self, stretch: bool):
    layout = self.layout()
    if stretch:
        # 移除尾部 stretch，给 more_tools_section stretch factor
        layout.setStretch(2, 1)
    else:
        # 恢复尾部 stretch
        layout.setStretch(2, 0)
        layout.addStretch()
```

### 子类继承要点

所有子类必须使用 `parent=parent` 关键字参数：

```python
class FileTreeSection(CollapsibleSection):
    def __init__(self, root_dir: Path, parent=None):
        super().__init__("文件树", parent=parent)  # 使用 parent=parent
```

## 下一步

- [01-overview.md](./01-overview.md) - 了解客户端整体架构
- [03-controllers.md](./03-controllers.md) - 了解控制器层设计（BrowserController、ScheduleController）
- [04-configuration.md](./04-configuration.md) - 了解配置管理（浏览器配置、schedules.json）
- [development_guide.md](./development_guide.md) - 了解客户端开发经验教训（QSizePolicy、布局陷阱等）
