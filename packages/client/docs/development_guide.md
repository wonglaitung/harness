# Harness Client 技术规范

> **版本**: 3.0 | **更新**: 2026-07-17
> 
> 本文档定义 Harness Client 桌面应用的**强制技术规范**。开发时必须遵循这些规范，避免重复踩坑。

---

## 目录

1. [核心原则](#核心原则)
2. [PyQt6 开发规范](#pyqt6-开发规范)
3. [异步编程规范](#异步编程规范)
4. [数据管理规范](#数据管理规范)
5. [主题系统规范](#主题系统规范)
6. [SDK 集成规范](#sdk-集成规范)
7. [代码结构](#代码结构)
8. [检查清单](#检查清单)
9. [附录：问题参考](#附录问题参考)

---

## 核心原则

### 原则 1：查文档优先

**PyQt6 行为差异大，禁止凭经验猜测！**

| 场景 | 必须查阅 |
|------|----------|
| 使用新组件 | [Qt 官方文档](https://doc.qt.io/qt-6/) 或 Context7 |
| 布局问题 | 检查 sizePolicy 和 sizeHint 行为 |
| CSS/QSS | [Qt Supported HTML Subset](https://doc.qt.io/qt-6/richtext-html-subset.html)（非常有限） |
| 异步操作 | qasync 文档和本规范 |

### 原则 2：硬约束优先

当软约束（sizePolicy、setAlignment）失效时，**立即升级到硬约束**：

```python
# ❌ 软约束可能被覆盖
widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

# ✅ 硬约束是最终解决方案
widget.setMinimumHeight(50)
widget.setMaximumHeight(150)
# 或
widget.setFixedHeight(100)
```

### 原则 3：UI 组件不存储状态

UI 组件只负责**渲染**，状态由数据层管理。

```python
# ❌ 错误：UI 组件存储状态
class SidebarPanel(QWidget):
    _current_session_id: str  # 禁止！

# ✅ 正确：UI 组件被动接收数据
class SidebarPanel(QWidget):
    def update_sessions(self, current, history):
        """只渲染，不存储"""
```

---

## PyQt6 开发规范

### 1. 组件选择规范

#### QLabel vs QTextBrowser

| 特性 | QLabel | QTextBrowser |
|------|--------|--------------|
| sizeHint 可靠性 | ✅ 即使未显示也准确 | ❌ 未显示时不可靠 |
| 富文本支持 | ✅ setWordWrap + RichText | ✅ setHtml |
| CSS 支持 | - | ❌ 非常有限（无 flexbox/grid） |
| **适用场景** | **静态文本显示** | 需要滚动/编辑 |

**规范**：静态文本优先使用 `QLabel`。

```python
# ✅ 正确：消息气泡使用 QLabel
self._content_label = QLabel()
self._content_label.setWordWrap(True)
self._content_label.setTextFormat(Qt.TextFormat.RichText)
self._content_label.setText(content)
self._content_label.adjustSize()  # sizeHint 可靠
```

#### QScrollArea 布局规范

**警告**：`setWidgetResizable(True)` 会覆盖 sizePolicy 和 setAlignment。

| 设置 | 行为 | 优先级 |
|------|------|--------|
| `setWidgetResizable(True)` | widget 填满视口 | 最高（覆盖其他） |
| `setAlignment()` | widget 对齐方式 | 被 setWidgetResizable 覆盖 |
| `sizePolicy` | 尺寸策略 | 被 setWidgetResizable 覆盖 |
| **`minimumHeight/maximumHeight`** | 尺寸硬约束 | **最高优先级** |

**规范**：在 `QScrollArea` 内的 widget 必须设置高度硬约束。

```python
# ✅ 正确：消息气泡设置硬约束
class MessageBubble(QWidget):
    def _setup_ui(self, content: str) -> None:
        self._label = QLabel(content)
        self._label.setWordWrap(True)
        self._label.adjustSize()
        
        # 关键：设置硬约束
        height = self._label.height() + padding
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        
        # 垂直方向 Fixed，防止被拉伸
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
```

### 2. 布局规范

#### QSizePolicy 必须显式设置

**禁止依赖默认值**，默认 `Preferred` 可能被意外拉伸。

```python
# ✅ 正确：显式设置 size policy
header.setSizePolicy(
    QSizePolicy.Policy.Expanding,  # 水平方向填满
    QSizePolicy.Policy.Fixed       # 垂直方向固定
)
```

#### QTextBrowser CSS 限制

**禁止使用**：
- `display: flex`, `display: grid`, `display: inline-flex`
- `align-items`, `justify-content`, `gap`
- `position: absolute/relative`

**替代方案**：使用 `<table>` + `valign`。

```html
<!-- ✅ 正确：使用 table 布局 -->
<table style="border: none; border-spacing: 0;">
    <tr>
        <td width="40" valign="top">头像</td>
        <td valign="top" style="padding-left: 12px;">内容</td>
    </tr>
</table>
```

### 3. Popup 组件规范

#### 层级设置

```python
# ✅ 正确：确保 Popup 在最上层
popup.setWindowFlags(
    Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
)
popup.setWindowModality(Qt.WindowModality.NonModal)
```

#### 禁止自动重定位

Qt 会自动处理 Popup 位置，**禁止手动监听窗口移动**。

#### 处理 None rect

```python
def complete(self, rect: QRect | None = None) -> None:
    if rect is None:
        cursor = self.widget().textCursor()
        if cursor.position() >= 0:
            rect = self.widget().cursorRect()
        else:
            rect = QRect(0, 0, 200, 100)  # 默认位置
    super().complete(rect)
```

### 4. 图标绘制规范

**禁止使用 Unicode 字符作为图标**（渲染模糊）。

**规范**：使用 QPainter 绘制矢量图标。

```python
def create_play_icon(size: int = 24, color: QColor) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(color))
    
    # 绘制三角形
    triangle = [
        QPointF(6, size // 2),
        QPointF(size - 4, 6),
        QPointF(size - 4, size - 6),
    ]
    painter.drawPolygon(QPolygonF(triangle))
    painter.end()
    return QIcon(pixmap)
```

---

## 异步编程规范

### 1. qasync 集成

#### 初始化

```python
# app.py
app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)  # Qt + asyncio 融合
asyncio.set_event_loop(loop)
```

#### 禁止 QThread + asyncio.new_event_loop()

**这是最高危操作，会导致静默崩溃！**

```python
# ❌ 禁止：QThread + new_event_loop
class AsyncWorker(QThread):
    def run(self):
        loop = asyncio.new_event_loop()  # 与 qasync 冲突！
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.coro)
```

#### 必须使用 @asyncSlot()

```python
from qasync import asyncSlot

class MainWindow(QMainWindow):
    # ✅ 正确：@asyncSlot() 在主线程执行
    @asyncSlot(str)  # 必须声明参数类型
    async def _on_message_sent(self, message: str):
        async for chunk in self.controller.send_message(message):
            self.chat_panel.append_streaming_chunk(chunk)
    
    @asyncSlot()  # 无参数时
    async def _on_test_connection(self):
        result = await self._test_connection()
```

### 2. asyncio 同步原语规范

**禁止在 `__init__` 中创建 asyncio 同步原语**（Event、Queue、Lock）。

**原因**：qasync 可能切换 event loop，导致 `RuntimeError: bound to a different event loop`。

```python
# ❌ 禁止：在 __init__ 中创建
class MyController:
    def __init__(self):
        self._queue = asyncio.Queue()  # 绑定到当时的 event loop
        self._event = asyncio.Event()   # 同样问题

# ✅ 正确：在方法中动态创建
class MyController:
    def __init__(self):
        self._queue: deque = deque()  # 存储层用 deque
        self._lock = threading.Lock()  # 线程安全
        self._event: asyncio.Event | None = None
    
    async def get_event(self) -> asyncio.Event:
        if self._event is None:
            self._event = asyncio.Event()  # 在当前 event loop 创建
        return self._event
```

### 3. 自定义 EventQueue 模式

```python
class EventQueue:
    """跨 event loop 安全的事件队列"""
    
    def __init__(self):
        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._notifier: asyncio.Event | None = None
    
    def put_nowait(self, event) -> None:
        with self._lock:
            self._queue.append(event)
        if self._notifier:
            try:
                self._notifier.set()
            except Exception:
                pass  # 可能绑定到旧 loop
    
    async def get(self):
        if self._notifier is None:
            self._notifier = asyncio.Event()  # 在当前 loop 创建
        
        while True:
            with self._lock:
                if self._queue:
                    return self._queue.popleft()
            
            self._notifier.clear()
            try:
                await self._notifier.wait()
            except Exception:
                self._notifier = asyncio.Event()  # 重建
```

---

## 数据管理规范

### 1. SessionManager 作为单一数据源

**所有会话数据必须通过 SessionManager 访问**。

```python
class SessionManager:
    """会话状态单一数据源"""
    
    _sessions: OrderedDict[str, ClientSession]
    _current_id: str | None
    
    def create(self) -> ClientSession
    def get_current(self) -> ClientSession | None
    def switch_to(self, session_id: str) -> bool
    def get_history_list(self) -> list[ClientSession]
```

**数据流**：

```
用户操作（切换会话）
    ↓
SessionManager.switch_to(session_id)
    ↓
MainWindow._refresh_session_list()
    ↓
SidebarPanel.update_sessions()  ← 纯渲染
```

### 2. 后台组件初始化规范

**UI 数据不能依赖后台组件就绪，必须有 fallback 数据源。**

```python
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
        return self._cached_configs.get(name)  # Fallback
    
    def set_agent(self, agent: AgentHarness) -> None:
        """Agent 就绪后同步数据"""
        self._agent = agent
        for name, config in self._cached_configs.items():
            agent.add_mcp_server(name, config)
```

### 3. 防重入保护

```python
class ChatController:
    def __init__(self):
        self._initializing = False
    
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

## 主题系统规范

### 1. 继承 ThemeAwareWidget

**所有自定义 widget 必须继承 ThemeAwareWidget**。

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """重写此方法应用主题样式"""
        theme = self.theme()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.PANEL};
                color: {theme.TEXT_PRIMARY};
            }}
        """)
```

### 2. paintEvent 动态获取主题

**禁止在 `__init__` 中缓存颜色值。**

```python
# ❌ 禁止：在 __init__ 中缓存
def __init__(self):
    self._theme = get_theme()
    self._colors = {"bg": QColor(self._theme.PANEL)}

# ✅ 正确：在 paintEvent 中动态获取
def paintEvent(self, event):
    theme = get_theme()  # 每次绘制都获取
    painter = QPainter(self)
    painter.setBrush(QColor(theme.ASSISTANT_BUBBLE))
```

### 3. 监听器生命周期管理

```python
def __init__(self):
    register_theme_listener(self._on_theme_changed)

def closeEvent(self, event):
    unregister_theme_listener(self._on_theme_changed)
    super().closeEvent(event)

def __del__(self):
    # 备用清理
    try:
        unregister_theme_listener(self._on_theme_changed)
    except Exception:
        pass
```

---

## SDK 集成规范

### 1. Python 类方法 logger 规范

**禁止使用未定义的 logger 变量。**

```python
# ❌ 错误：直接使用未定义的 logger
def connect_server(self, name: str):
    logger.info(f"Connecting to {name}")  # NameError!

# ✅ 正确方式 1：在方法内获取
def connect_server(self, name: str):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Connecting to {name}")

# ✅ 正确方式 2：在类级别定义
class MCPManager:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    def connect_server(self, name: str):
        self._logger.info(f"Connecting to {name}")
```

### 2. Tool 包装器必须实现完整接口

**新增 Tool 包装器时，必须实现所有接口方法。**

```python
class MCPToolWrapper:
    # 必须实现的属性
    @property
    def name(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def input_schema(self) -> dict: ...
    
    # 必须实现的方法
    async def execute(self, args: dict, ctx) -> ToolResult: ...
    
    def validate_arguments(self, args: dict) -> tuple[bool, str | None]: ...
    
    def to_definition(self) -> dict:  # ← 容易遗漏！
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

### 3. 技能执行环境规范

**如果技能涉及运行脚本或命令，客户端必须注册 BashTool。**

```python
# packages/client/src/harness_client/controllers/chat_controller.py
from harness.tools.builtins import (
    ReadTool,
    WriteTool,
    EditTool,
    GlobTool,
    GrepTool,
    BashTool,  # 必须
)

def _init_tools(self) -> list[Tool]:
    return [
        ReadTool(),
        WriteTool(),
        EditTool(),
        GlobTool(),
        GrepTool(),
        BashTool(),  # 技能执行必需
    ]
```

### 4. 技能文档规范

**技能文档（SKILL.md）必须包含 LLM 执行指令。**

```markdown
## ⚡ 执行指令（LLM 必读）

**当用户请求 [功能] 时，你必须：**

1. **直接运行脚本**：
   ```bash
   python ~/.harness/skills/[skill-name]/scripts/script.py [args]
   ```

**⚠️ 重要提示**：
- 不要尝试创建新脚本，脚本已经存在
- 直接使用 bash 工具运行上述命令
```

### 5. SDK ProgressEvent 格式兼容

**客户端必须兼容 SDK 的两种事件格式。**

**问题**：SDK 发送的 ProgressEvent 可能是两种格式：
1. 新格式：`event.data.input_tokens`（顶层字段）
2. 旧格式：`event.data.token_usage.input_tokens`（嵌套字段）

**解决方案**：检查两种格式，优先使用顶层字段：

```python
def _on_llm_response(self, event: ProgressEvent):
    event_data = event.data or {}

    # 优先检查顶层字段（当前 SDK 格式）
    input_tokens = event_data.get("input_tokens", 0)
    output_tokens = event_data.get("output_tokens", 0)

    # 如果顶层没有，检查 token_usage 字段（兼容旧格式）
    if not input_tokens and not output_tokens:
        token_usage = event_data.get("token_usage", {})
        if isinstance(token_usage, dict):
            input_tokens = token_usage.get("input_tokens", 0)
            output_tokens = token_usage.get("output_tokens", 0)
```

**关键提交**：`17fee0f`

### 6. 设置对话框配置加载

**打开设置对话框时必须加载所有配置。**

**问题**：如果 `_on_preferences()` 未加载某些配置，保存时会重置这些配置为默认值。

**解决方案**：

```python
def _on_preferences(self):
    settings = get_settings()
    # 必须加载所有配置项，包括：
    # - API/模型配置
    # - 成本配置（input_cost_per_1m, output_cost_per_1m）
    # - 路由配置
    self._settings_dialog.load_settings(settings)
```

**关键提交**：`39c17e6`

### 7. 技能 enabled 字段持久化

**技能的 `enabled` 状态必须保存到文件 frontmatter。**

**问题**：`Skill` 类缺少 `enabled` 字段，导致编辑技能时无法保存启用状态。

**解决方案**：

```python
# SDK: Skill 基类添加 enabled 字段
@dataclass
class Skill:
    name: str
    description: str
    content: str
    enabled: bool = True  # 添加此字段
    ...

# to_file() 保存 enabled
frontmatter["enabled"] = self.enabled

# from_file() 读取 enabled
enabled=frontmatter.get("enabled", True)
```

**关键提交**：`d63790e`

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
│   ├── memory_panel.py           # 记忆管理面板
│   └── theme_aware.py            # 主题感知基类
│
├── controllers/                  # 控制器（业务逻辑）
│   ├── chat_controller.py        # 对话控制
│   ├── session_manager.py        # 会话管理（单一数据源）
│   ├── mcp_controller.py         # MCP 控制
│   ├── skill_controller.py       # 技能控制
│   └── memory_controller.py      # 记忆控制
│
├── themes/                       # 主题系统
│   ├── __init__.py               # 监听器机制
│   ├── dark.py                   # 暗色主题
│   └── light.py                  # 亮色主题
│
├── utils/                        # 工具
│   └── settings.py               # 设置管理
│
├── app.py                        # 应用启动（qasync 配置）
└── main.py                       # 入口
```

---

## 检查清单

### 新增 UI 组件

- [ ] 继承 `ThemeAwareWidget` 响应主题切换
- [ ] `paintEvent` 中动态调用 `get_theme()`
- [ ] 检查数据是否依赖 agent 就绪，提供 fallback
- [ ] 显式设置 `QSizePolicy`，不依赖默认值
- [ ] 使用主题变量而非硬编码颜色
- [ ] 静态文本使用 `QLabel`，不用 `QTextBrowser`

### 新增后台组件

- [ ] 启动时从配置文件加载，不依赖其他组件
- [ ] 提供无依赖的数据访问方法
- [ ] 其他组件就绪后同步数据
- [ ] 初始化过程添加防重入保护

### 异步操作

- [ ] 使用 `@asyncSlot()` 而非 QThread
- [ ] asyncio 同步原语动态创建，不在 `__init__` 中创建
- [ ] 关闭时先取消所有后台任务

### SDK 集成

- [ ] 类方法使用 logger 前必须定义
- [ ] Tool 包装器实现完整接口（包括 `to_definition()`）
- [ ] 测试端到端流程，不只是连接测试

### 会话相关修改

- [ ] 消息是否持久化到 SessionManager？
- [ ] 多轮迭代后消息是否完整？
- [ ] 切换会话时历史是否正确加载？

---

## 附录：问题参考

> 以下问题记录供参考，遇到问题时查阅。

### 问题统计

| 类别 | 修复提交数 | 严重程度 |
|------|-----------|---------|
| 消息气泡渲染 | 30+ | 🔴 高 |
| 主题切换响应 | 15+ | 🟡 中 |
| MCP 配置管理 | 12+ | 🔴 高 |
| 布局和滚动 | 10+ | 🟡 中 |
| Skill Completer | 8+ | 🟡 中 |
| 异步和并发 | 5+ | 🔴 高 |

### 关键问题参考

| 问题 | 关键提交 | 规范章节 |
|------|----------|----------|
| QScrollArea 覆盖 sizePolicy | `c5f326d`, `d486989` | [PyQt6 布局规范](#qscrollarea-布局规范) |
| QThread + asyncio 崩溃 | `186b8b7` | [异步编程规范](#禁止-qthread--asyncionew_event_loop) |
| 主题切换不更新 | `9fa2836`, `186b8b7` | [主题系统规范](#主题系统规范) |
| MCP logger 未定义 | `ab96e5f` | [SDK 集成规范](#python-类方法-logger-规范) |
| MCP 工具不工作 | `10073df` | [SDK 集成规范](#tool-包装器必须实现完整接口) |
| 技能无法执行 | `cd94565` | [SDK 集成规范](#技能执行环境规范) |
| asyncio.Queue 切换 loop | 见 lessons.md 2026-07-02 | [异步编程规范](#asyncio-同步原语规范) |
| Token 统计始终为零 | `17fee0f` | [SDK 集成规范](#sdk-progressevent-格式兼容) |
| 设置对话框配置丢失 | `39c17e6` | [数据管理规范](#设置对话框配置加载) |
| 技能启用状态无法保存 | `d63790e` | [SDK 集成规范](#技能-enabled-字段持久化) |

### 详细问题记录

详细问题分析请参考：
- [lessons.md](../../../lessons.md) - 全项目经验教训
- [02-ui-components.md](./02-ui-components.md) - UI 组件详解
- [03-controllers.md](./03-controllers.md) - 控制器设计

---

## 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-20 | 3.1 | 添加 Token 统计、设置配置、技能 enabled 字段问题 |
| 2026-07-17 | 3.0 | 重构为技术规范，添加强制性规范章节 |
| 2026-07-17 | 2.1 | 添加 MCP logger 未定义问题、MCP 工具不工作问题 |
| 2026-07-16 | 2.0 | 合并架构设计与问题总结 |
| 2026-07-16 | 1.0 | 初始版本 |