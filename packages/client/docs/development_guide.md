# Harness Client 开发规范

本文档总结了 Harness Client 桌面应用的开发经验，包括架构设计决策、踩坑教训和最佳实践。

> **相关文档**：UI 设计规范请参考 [ui_spec.md](./ui_spec.md)

---

## 目录

1. [架构设计决策](#架构设计决策)
2. [问题与解决方案](#问题与解决方案)
3. [最佳实践](#最佳实践)
4. [代码结构](#代码结构)
5. [调试方法](#调试方法)
6. [检查清单](#检查清单)
7. [问题统计](#问题统计)

---

## 架构设计决策

### 1. 为什么不直接使用 SDK 的 Session？

SDK 提供了 `Session` 类用于存储对话历史，但客户端引入了额外的 `SessionManager` 和 `ClientSession`。原因如下：

#### SDK Session 的局限性

SDK 的 `Session` 是为 **Agent 执行周期** 设计的：
- 存储 Agent 执行过程中的消息
- 与 `ContextBuilder` 紧密耦合
- 不持久化（每次 `run()` 结束后可能丢失）
- 没有多会话管理能力

#### ClientSession 的需求

客户端需要 **用户视角的会话管理**：
- 多会话支持（用户可同时打开多个对话）
- 会话持久化（切换会话后历史不丢失）
- 会话元数据（名称、时间戳、token 使用量）
- 会话列表显示（历史会话、当前会话）

#### 设计分离原则

```python
# SDK Session - Agent 执行周期
session = Session(messages=[...])
result = agent.run(prompt, session=session)

# ClientSession - 用户会话管理
client_session = ClientSession(
    id="abc123",
    name="帮我分析项目结构",
    messages=[...],  # 从 SDK Session 复制
    created_at=datetime.now(),
    token_usage={"input": 500, "output": 200},
)
```

**关键洞察**：
- SDK 的 Session 是 **执行上下文**
- Client 的 Session 是 **用户数据模型**
- 两者职责不同，不应混用

---

### 2. SessionManager 作为单一数据源

#### 问题背景

早期设计中，会话状态分散在多处：
- `ChatController._session_cache`
- `SidebarPanel._current_session_id`
- `MainWindow._current_session_id`

导致数据不一致、同步复杂、Bug 频发。

#### 解决方案

引入 `SessionManager` 作为唯一数据源：

```python
class SessionManager:
    """会话状态单一数据源"""
    
    _sessions: OrderedDict[str, ClientSession]
    _current_id: str | None
    
    def create() -> ClientSession          # 创建新会话
    def get_current() -> ClientSession     # 获取当前会话
    def switch_to(session_id) -> bool      # 切换会话
    def get_history_list() -> list         # 获取历史列表
```

#### UI 组件只渲染不存储

```python
class SidebarPanel(QWidget):
    # ❌ 早期设计：存储状态
    _current_session_id: str  # 不要这样做！
    
    # ✅ 正确设计：只渲染
    def update_sessions(self, current, history):
        """被动接收数据，只负责渲染"""
        self.session_list.clear()
        # 添加当前会话
        # 添加历史会话
```

#### 数据流

```
用户操作（切换会话）
    ↓
SessionManager.switch_to(session_id)
    ↓
MainWindow._refresh_session_list()
    ↓
SidebarPanel.update_sessions()  ← 纯渲染
```

---

### 3. qasync 异步集成设计

#### 为什么选择 qasync？

客户端需要：
- PyQt6 GUI（事件驱动）
- asyncio 异步（SDK 异步 API）
- 流式响应实时显示

qasync 允许在 Qt 事件循环中运行 asyncio：

```python
# app.py
app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)  # Qt + asyncio 融合
asyncio.set_event_loop(loop)
```

#### 关键约束：禁止 QThread + asyncio

**踩坑教训**：程序静默崩溃，无异常输出。

原因：`AsyncWorker(QThread)` 在子线程创建新的 event loop，与 qasync 的 `QEventLoop` 不兼容。

**正确做法**：使用 `@asyncSlot()` 装饰器

```python
from qasync import asyncSlot

class MainWindow(QMainWindow):
    # ❌ 错误：QThread + new_event_loop
    class AsyncWorker(QThread):
        def run(self):
            loop = asyncio.new_event_loop()  # 与 qasync 冲突！
    
    # ✅ 正确：@asyncSlot() 在主线程执行
    @asyncSlot(str)  # 必须声明参数类型
    async def _on_message_sent(self, message: str):
        async for chunk in self.controller.send_message(message):
            self.chat_panel.append_streaming_chunk(chunk)
```

#### @asyncSlot 使用要点

| 场景 | 装饰器 | 说明 |
|------|--------|------|
| 信号有参数 | `@asyncSlot(str)` | 声明参数类型 |
| 信号无参数 | `@asyncSlot()` | 无参数声明 |
| 多个参数 | `@asyncSlot(str, int)` | 按顺序声明类型 |

---

### 4. ChatController 配置分离

#### 为什么不直接用 HarnessConfig？

SDK 的 `HarnessConfig` 包含大量 Agent 运行参数，客户端需要：

1. **用户可配置项**：provider, api_key, model, temperature
2. **固定配置项**：system_prompt, sandbox_workspace, memory_md_path
3. **额外配置**：stream_enabled, work_dir, auto_save

#### ChatConfig 设计

```python
@dataclass
class ChatConfig:
    """客户端聊天配置 - 用户可配置项"""
    
    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: str = "auto"
    max_iterations: int = 10
    temperature: float = 0.3
    tool_result_role: str = "tool"
    
    # 客户端特有配置
    system_prompt: str = "..."  # 固定，优化过的
```

#### 配置转换

```python
async def initialize(self):
    # ChatConfig → HarnessConfig
    sdk_config = HarnessConfig(
        model=self.config.model,
        api_key=self.config.api_key,
        provider=self.config.provider,
        base_url=self.config.base_url,
        # 固定配置
        system_prompt=self.config.system_prompt,
        sandbox_workspace=str(self.work_dir),
        memory_md_path=get_config_dir() / "MEMORY.md",
    )
```

---

### 5. 控制器模式

每个控制器专注一个领域：

| 控制器 | 职责 |
|--------|------|
| `ChatController` | 对话交互、Agent 管理 |
| `SessionManager` | 会话状态管理 |
| `MCPController` | MCP 服务器管理 |
| `SkillController` | 技能管理 |
| `MemoryController` | 记忆管理 |

---

## 问题与解决方案

### 核心原则

#### 1. 查文档优先

**PyQt6 行为差异大，禁止凭经验猜测！**

| 场景 | 必须查阅 |
|------|----------|
| 使用新组件 | Qt 官方文档或 Context7 |
| 布局问题 | 检查 sizePolicy 和 sizeHint 行为 |
| CSS/QSS | Qt Supported HTML Subset（非常有限） |
| 异步操作 | qasync 文档和最佳实践 |

**参考文档**：https://doc.qt.io/qt-6/ 或使用 Context7 查阅

#### 2. 硬约束优先

当软约束（sizePolicy、setAlignment）失效时，升级到硬约束：

```python
# 软约束可能被覆盖
widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

# 硬约束是最终解决方案
widget.setFixedHeight(100)
widget.setMinimumHeight(50)
widget.setMaximumHeight(150)
```

---

### 后台组件初始化

#### 问题：Agent 未就绪时 UI 无数据

**现象**：用户打开应用后，MCP 面板和技能面板为空，因为 `_agent` 还是 `None`。

**关键提交**：`4352b82`, `69f2bce`, `52171e7`, `e623806`

#### 解决方案：Fallback 数据源

**模式**：UI 数据不能依赖后台组件就绪，需要有 fallback 数据源。

```python
# MCP 控制器示例
class MCPController:
    def __init__(self):
        self._agent: AgentHarness | None = None
        self._cached_configs: dict = {}  # Fallback 数据源

    def _load_from_config(self) -> None:
        """启动时从配置文件加载，不依赖 agent"""
        config_path = Path.home() / ".harness" / "mcp.json"
        if config_path.exists():
            self._cached_configs = json.loads(config_path.read_text())

    def get_server_config(self, name: str) -> dict | None:
        """获取服务器配置（兼容 agent 未就绪）"""
        if self._agent:
            return self._agent.get_mcp_server_config(name)
        return self._cached_configs.get(name)

    def set_agent(self, agent: AgentHarness) -> None:
        """Agent 就绪后同步数据"""
        self._agent = agent
        for name, config in self._cached_configs.items():
            agent.add_mcp_server(name, config)
```

#### 初始化状态管理

```python
class ChatController:
    def __init__(self):
        self._initializing = False  # 防止重入

    async def initialize(self) -> None:
        if self._initializing:
            return
        self._initializing = True
        try:
            await self._do_initialize()
        finally:
            self._initializing = False
```

---

### UI 组件触发问题

#### 问题：Skill Completer Popup 行为异常

**现象**：
- Popup 被主窗口遮挡
- 窗口移动时位置错误
- `complete()` 返回 `None` rect 导致崩溃

**关键提交**：`38d52ea`, `591455c`, `1627ded`, `deae518`

#### 解决方案

**1. 确保 Popup 层级正确**

```python
popup.setWindowFlags(
    Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
)
popup.setWindowModality(Qt.WindowModality.NonModal)
```

**2. 不要自动重定位**

Qt 会自动处理 Popup 位置，手动监听窗口移动反而导致问题。

**3. 处理 None rect**

```python
def complete(self, rect: QRect | None = None) -> None:
    if rect is None:
        cursor = self.widget().textCursor()
        if cursor.position() >= 0:
            rect = self.widget().cursorRect()
        else:
            rect = QRect(0, 0, 200, 100)
    super().complete(rect)
```

---

### 消息气泡渲染

#### 问题概述

这是 CLIENT 开发中**最耗时**的问题，经历了 30+ 次修复。

**现象**：
- 气泡高度过高（480px 而非预期 40px）
- AI 回复和输入框之间有大片空白
- 首行文字被裁剪

**关键提交**：`c5f326d`, `d08a9a1`, `c4677c6`, `d486989`, `ec2d797`

#### 根因链条

```
QScrollArea.setWidgetResizable(True)
    ↓
覆盖 sizePolicy 和 setAlignment
    ↓
消息气泡被拉伸填满视口
    ↓
最终用 minimumHeight + maximumHeight 硬约束
```

#### PyQt6 布局优先级

| 设置 | 行为 | 优先级 |
|------|------|--------|
| `setWidgetResizable(True)` | widget 填满视口 | 最高（覆盖其他） |
| `setAlignment()` | widget 对齐方式 | 被 setWidgetResizable 覆盖 |
| `sizePolicy` | 尺寸策略 | 被 setWidgetResizable 覆盖 |
| **`minimumHeight/maximumHeight`** | 尺寸硬约束 | **最高优先级** |

#### 解决方案

```python
class MessageBubble(QWidget):
    def _setup_ui(self, content: str, role: str) -> None:
        # QLabel 显示内容（sizeHint 可靠）
        self._content_label = QLabel()
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.TextFormat.RichText)
        self._content_label.setText(content)
        self._content_label.adjustSize()

        # 关键：设置硬约束
        self.setMinimumHeight(self._content_label.height() + 16)
        self.setMaximumHeight(self._content_label.height() + 16)

        # 垂直方向 Fixed，防止被拉伸
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed
        )
```

#### QTextBrowser vs QLabel

| 特性 | QLabel | QTextBrowser |
|------|--------|--------------|
| sizeHint 可靠性 | ✅ 即使未显示也准确 | ❌ 未显示时不可靠 |
| 富文本支持 | ✅ setWordWrap + RichText | ✅ setHtml |
| CSS 支持 | - | ❌ 非常有限（无 flexbox/grid） |
| 适用场景 | 静态文本显示 | 需要滚动/编辑 |

---

### 主题切换响应

#### 问题：paintEvent 颜色不更新

**现象**：切换主题后，paintEvent 中绘制的颜色没有变化。

**关键提交**：`9fa2836`, `eec08ef`, `1a89ded`, `92e7941`

#### 解决方案

**1. 继承 ThemeAwareWidget**

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        theme = self.theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

**2. paintEvent 动态获取主题**

```python
def paintEvent(self, event):
    theme = get_theme()  # 每次绘制都获取
    painter = QPainter(self)
    painter.setBrush(QColor(theme.ASSISTANT_BUBBLE))
```

**禁止**：在 `__init__` 中缓存颜色值。

**3. 监听器生命周期管理**

```python
def closeEvent(self, event):
    unregister_theme_listener(self._theme_callback)
    super().closeEvent(event)
```

#### 问题：StatusDot 颜色缓存导致主题切换失效

**现象**：`StatusDot` 组件在 `__init__` 中缓存主题颜色，切换主题后颜色不更新。

**关键提交**：`186b8b7`

**错误示例**：

```python
# ❌ 错误：在 __init__ 中缓存颜色
def __init__(self, size: int = 12, parent=None):
    super().__init__(parent)
    self._theme = get_theme()  # 缓存主题
    self._colors = {
        "connected": QColor(self._theme.STATUS_CONNECTED),
        # ...
    }
    self._current_color = self._colors["disconnected"]
```

**正确做法**：

```python
# ✅ 正确：动态获取颜色 + 注册监听器
def __init__(self, size: int = 12, parent=None):
    super().__init__(parent)
    register_theme_listener(self._on_theme_changed)

def _get_status_color(self) -> QColor:
    """动态获取当前状态的颜色"""
    theme = get_theme()
    return QColor(getattr(theme, f"STATUS_{self._status.upper()}"))

def paintEvent(self, event):
    color = self._get_status_color()  # 每次绘制动态获取
    # ...
```

---

### 布局系统陷阱

#### 问题 1：QSizePolicy.Fixed 阻止扩展

**现象**：`CollapsibleSection` 标题区域被意外拉伸（37px → 265px）。

**原因**：未显式设置 size policy，使用默认 `Preferred`，可以被扩展。

**解决**：

```python
header.setSizePolicy(
    QSizePolicy.Policy.Expanding,  # 水平方向填满
    QSizePolicy.Policy.Fixed       # 垂直方向固定
)
```

#### 问题 2：QTextBrowser CSS 支持有限

**现象**：`display: inline-flex` 布局在 QTextBrowser 中不工作。

**解决**：使用 `<table>` + `valign` 替代 flexbox。

```html
<!-- ✅ 正确：使用 table 布局 -->
<table style="border: none; border-spacing: 0;">
    <tr>
        <td width="40" valign="top">头像</td>
        <td valign="top" style="padding-left: 12px;">内容</td>
    </tr>
</table>
```

#### 调试技巧

```python
print(f"widget geometry: {widget.geometry()}")
print(f"sizePolicy: {widget.sizePolicy().verticalPolicy()}")
print(f"minHeight={widget.minimumHeight()}, maxHeight={widget.maximumHeight()}")
```

---

### 异步与并发问题

#### 问题 1：qasync + asyncio.Queue 不兼容

**现象**：`RuntimeError: <Queue> is bound to a different event loop`

**关键提交**：见 `lessons.md` 2026-07-02

**原因**：
- `asyncio.Queue` 创建时绑定到当时的 event loop
- qasync 在窗口操作时可能切换 event loop

**解决方案**：自定义 `EventQueue`，存储层不绑定 event loop。

```python
class EventQueue:
    def __init__(self):
        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._notifier: asyncio.Event | None = None

    async def get(self):
        # 关键：在当前 event loop 中创建 notifier
        if self._notifier is None:
            self._notifier = asyncio.Event()
        # ...
```

#### 问题 2：QThread + asyncio.new_event_loop() 导致静默崩溃

**现象**：MCP 测试连接使用 `QThread` + `asyncio.new_event_loop()`，可能导致程序静默崩溃。

**关键提交**：`186b8b7`

**原因**：
- `QThread.run()` 在子线程创建新的 event loop
- 与 qasync 的 `QEventLoop` 不兼容
- 可能导致信号槽机制异常

**解决方案**：使用 `@asyncSlot()` 装饰器替代 `QThread`。

```python
# ❌ 错误：QThread + new_event_loop
class TestConnectionThread(QThread):
    def run(self):
        loop = asyncio.new_event_loop()  # 与 qasync 冲突！
        result = loop.run_until_complete(self._test_connection())

# ✅ 正确：@asyncSlot() 在主线程执行
class MCPServerDialog(QDialog):
    @asyncSlot()
    async def _test_connection(self):
        tools = await _test_mcp_connection(config)
        self._on_test_success(tools)
```

**注意**：`@asyncSlot()` 在主线程的 qasync event loop 中运行，但不会阻塞 UI（asyncio 是协作式多任务）。

---

### MCP 配置管理

#### 问题：Agent 未就绪无法操作

**关键提交**：`4352b82`, `52171e7`, `fc37cef`, `26f8782`, `b2539d3`

#### 数据流设计

```
启动时: mcp.json → _cached_configs
    ↓
Agent 就绪后: _cached_configs → agent.sync_mcp_servers()
    ↓
编辑/删除时: 更新 _cached_configs + 同步 agent
```

#### 常见问题

| 问题 | 提交 | 说明 |
|------|------|------|
| 编辑时丢失 env/headers | `26f8782` | 未加载现有配置 |
| 配置更新未同步 | `53c0aab` | UI 和 SDK 数据不一致 |
| 解析空格问题 | `675b8d1` | 用户输入 env 时带空格 |

---

### 技能系统

#### 问题：Agent 未就绪无法显示技能

**关键提交**：`69f2bce`, `ea603f9`, `f3c7bf5`

**解决方案**：从文件系统缓存技能信息，不依赖 agent。

---

### 会话管理

#### 问题：状态分散

**解决方案**：`SessionManager` 作为唯一数据源，UI 只渲染不存储。

#### 常见问题

| 问题 | 提交 | 说明 |
|------|------|------|
| 会话排序 | `4d2c87f` | 按 updated_at 排序 |
| 会话标题裁剪 | `fb29e17` | QFontMetrics 计算宽度 |
| 清除上下文未同步 | `f356e20` | SDK session 也需要清除 |

---

### 附件与输入系统

#### 问题：附件按钮启动时不显示

**关键提交**：`a007131`, `1b37276`

**解决方案**：在 `__init__` 中创建并显示附件按钮。

---

### 图标绘制

#### 问题：Unicode 字符图标模糊

**关键提交**：`44ca92c`, `5cb135e`, `b8be658`

**解决方案**：使用 QPainter 绘制矢量图标。

```python
def create_play_icon(size: int = 24, color: QColor) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # 绘制三角形...
    return QIcon(pixmap)
```

---

### 调度系统

#### 问题：启用调度未启动

**关键提交**：`0f004fa`

**解决方案**：应用启动时启动 ScheduleController。

---

### 记忆面板

#### 问题：编辑时丢失元数据

**关键提交**：`c784d94`, `46ffc36`

**解决方案**：编辑时保留 importance 等元数据。

---

## 最佳实践

### 1. 回调机制解耦

```python
# 控制器定义回调接口
def set_tool_call_callback(self, callback: Callable[[str, dict], None]):
    self._on_tool_call = callback

# UI 设置回调
self.chat_controller.set_tool_call_callback(self._show_tool_call)
```

### 2. PyQt 信号驱动

```python
class MemoryController(QObject):
    memory_changed = pyqtSignal()

self.memory_controller.memory_changed.connect(self._on_memory_changed)
```

### 3. 配置目录统一

```
~/.harness/
├── settings.json     # 应用设置
├── mcp.json          # MCP 配置
├── MEMORY.md         # 全局记忆
└── skills/           # 技能目录
```

**优势**：
- 跨工作目录使用（配置不随目录变化）
- 便于迁移和备份

### 4. 配置迁移兼容性

当配置目录变更时，提供自动迁移：

```python
def migrate_old_config() -> None:
    old_dir = get_old_config_dir()
    new_dir = get_config_dir()
    if old_settings.exists() and not new_settings.exists():
        shutil.copy2(old_settings, new_settings)
```

### 5. 优先使用 Qt 内置组件

| 组件 | 自定义实现 | Qt 内置 | 代码减少 |
|------|-----------|---------|----------|
| 文件树 | 手动构建模型 | `QFileSystemModel` | ~70% |
| 导航按钮 | 自定义 QWidget | `QToolButton` | ~90 行 |
| 文件图标 | 手动映射扩展名 | `QFileIconProvider` | ~50% |

### 6. 默认折叠高频使用区块

```python
# 文件树默认展开（最常用），其他折叠
self.memory_section.set_collapsed(True)
self.skills_section.set_collapsed(True)
self.mcp_section.set_collapsed(True)
```

---

## 代码结构

```
packages/client/src/harness_client/
├── ui/                           # PyQt6 组件（纯渲染）
│   ├── main_window.py            # 主窗口（协调器）
│   ├── sidebar.py                # 左侧导航
│   ├── chat_panel.py             # 对话面板
│   ├── right_panel.py            # 右侧面板
│   ├── settings_dialog.py        # 设置对话框
│   ├── mcp_panel.py              # MCP 管理面板
│   └── memory_panel.py           # 记忆管理面板
│
├── controllers/                  # 控制器（业务逻辑）
│   ├── chat_controller.py        # 对话控制
│   ├── session_manager.py        # 会话管理（单一数据源）
│   ├── mcp_controller.py         # MCP 控制
│   ├── skill_controller.py       # 技能控制
│   └── memory_controller.py      # 记忆控制
│
├── utils/                        # 工具
│   └── settings.py               # 设置管理
│
├── app.py                        # 应用启动（qasync 配置）
└── main.py                       # 入口
```

---

## 调试方法

### 添加日志定位问题

```python
# 布局问题
print(f"widget geometry: {widget.geometry()}")
print(f"sizePolicy: {widget.sizePolicy().verticalPolicy()}")

# 状态问题
print(f"_agent is None: {self._agent is None}")
print(f"_initializing: {self._initializing}")
```

### 渐进排查

1. **添加日志** → 定位问题范围
2. **查阅文档** → 理解组件行为
3. **写最小测试** → 验证假设
4. **应用修复** → 验证效果

---

## 检查清单

### 新增 UI 组件

- [ ] 继承 `ThemeAwareWidget` 响应主题切换
- [ ] `paintEvent` 中动态调用 `get_theme()`
- [ ] 检查数据是否依赖 agent 就绪，提供 fallback
- [ ] 显式设置 `QSizePolicy`，不依赖默认值
- [ ] 使用主题变量而非硬编码颜色

### 新增后台组件

- [ ] 启动时从配置文件加载，不依赖其他组件
- [ ] 提供无依赖的数据访问方法
- [ ] 其他组件就绪后同步数据
- [ ] 初始化过程添加防重入保护

### 异步操作

- [ ] 使用 `@asyncSlot()` 而非 QThread
- [ ] asyncio 同步原语动态创建，不在 `__init__` 中创建
- [ ] 关闭时先取消所有后台任务

### 会话相关修改

- [ ] 消息是否持久化到 SessionManager？
- [ ] 多轮迭代后消息是否完整？
- [ ] 切换会话时历史是否正确加载？

### Qt 布局调试

- [ ] 是否理解 stretch vs sizePolicy 的区别？
- [ ] 是否检查 minimumSizeHint()？
- [ ] 是否需要用 maximumHeight/minimumHeight 硬约束？

### 使用 Qt 组件

- [ ] 是否优先使用 Qt 内置组件？
- [ ] 是否检查布局类型（QVBoxLayout vs QGridLayout）？
- [ ] 是否查阅官方 API 文档确认签名？

---

## 问题统计

### 按类别统计

| 类别 | 修复提交数 | 严重程度 |
|------|-----------|---------|
| 消息气泡渲染 | 30+ | 🔴 高（反复修复） |
| 主题切换响应 | 15+ | 🟡 中 |
| MCP 配置管理 | 12+ | 🔴 高 |
| 布局和滚动 | 10+ | 🟡 中 |
| Skill Completer | 8+ | 🟡 中 |
| 异步和并发 | 5+ | 🔴 高（崩溃） |

### 关键教训

1. **PyQt6 布局优先级**：`setWidgetResizable > sizePolicy > setAlignment`
2. **硬约束才是最终解决方案**：`setFixedHeight()` 比 sizePolicy 更可靠
3. **主题切换三要素**：继承 ThemeAwareWidget + paintEvent 动态获取 + 不缓存颜色
4. **后台组件未就绪**：UI 数据必须有 fallback 来源
5. **qasync 环境特殊**：不能用 QThread，asyncio 同步原语要动态创建

---

## 下一步

- [ui_spec.md](./ui_spec.md) - UI 设计规范（主题、组件、样式）
- [02-ui-components.md](./02-ui-components.md) - UI 组件详解
- [03-controllers.md](./03-controllers.md) - 控制器设计
- [lessons.md](../../../lessons.md) - 全项目经验教训

---

## 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-16 | 2.0 | 合并 `05-client-lessons.md` 架构设计与 `development_guide.md` 问题总结 |
| 2026-07-16 | 1.0 | 初始版本，基于 362 个提交分析 |
