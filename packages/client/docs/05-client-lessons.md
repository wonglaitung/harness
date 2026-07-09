# 05 - 客户端开发经验总结

## 概述

Harness Client 在开发过程中积累了大量宝贵经验，这些经验对未来开发类似客户端具有重要借鉴价值。本文档总结关键设计决策、踩坑教训和最佳实践。

> **重要**：本文档是从 `lessons.md` 和实际代码中提取的客户端特定经验，通用开发规范请参阅 `packages/sdk/docs/programmer_skill.md`。

---

## 一、架构设计决策

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

## 二、关键踩坑教训

### 0. QSizePolicy.Fixed 阻止布局扩展（2026-07-09）⭐ 新增

#### 问题现象

实现 `MoreToolsSection` 自动伸展到底部时，标题区域被错误拉伸（高度从 37px 变成 265px），内容区域反而显示在下方。

#### 根因分析

`CollapsibleSection` 基类中：
1. `content_area` 的 vertical size policy 是 `Fixed`
2. `header_widget` 没有设置 size policy（默认为 `Preferred`）
3. 当外部布局设置 `stretch=1` 时，空间需要被分配

**Qt 布局分配逻辑**：
- stretch factor 决定空间分配比例
- 但 `Fixed` policy 的 widget 不能扩展
- 空间被分配到其他可以扩展的 widget
- `header_widget` 使用默认 `Preferred`，可以扩展，于是被拉伸

#### 解决方案

```python
# 1. header_widget 设置 Fixed policy
header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

# 2. content_area 展开时改为 Expanding
if expanded:
    self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
else:
    self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

# 3. 布局设置 stretch factor
main_layout.addWidget(header_widget, 0)  # stretch=0
main_layout.addWidget(self.content_area, 1)  # stretch=1
```

#### 关键洞察

- **QSizePolicy 是布局扩展的关键**：不设置时使用默认值 `Preferred`，可能导致意外扩展
- **Fixed 阻止扩展**：如果 widget 不应该扩展，必须显式设置 `Fixed` policy
- **stretch factor 配合 size policy**：stretch 决定分配比例，size policy 决定能否接受分配

> **详细分析**：参见根目录 [lessons.md](../../../lessons.md) 的 "2026-07-09: QSizePolicy.Fixed 阻止布局扩展" 章节。

---

### 1. QScrollArea 布局陷阱（2026-06-25）

#### 问题现象

对话框中 AI 回复后，AI 气泡和输入框之间有大块空白区域；或消息气泡高度远高于内容高度。

#### 根因分析

`QScrollArea.setWidgetResizable(True)` 会强制内部 widget 填满视口高度，即使设置了 `setAlignment(Qt.AlignmentFlag.AlignTop)` 也无效。

#### 尝试过的方案

| 方案 | 结果 |
|------|------|
| `setAlignment(AlignTop)` | ❌ 无效，widget 仍被扩展 |
| `sizePolicy = Minimum` | ❌ 无效，被 setWidgetResizable 覆盖 |
| `layout.setSizeConstraint(SetMinimumSize)` | ❌ 无效 |
| `setWidgetResizable(False)` | ❌ widget 宽度变为 0，不可见 |
| **`setMinimumHeight() + setMaximumHeight()`** | ✅ 成功 |

#### 正确实现

```python
class MessagesContainer(QWidget):
    def _update_height(self):
        """更新容器高度以适应内容。"""
        # 计算所有子组件的总高度
        total_height = 32  # 上下 margin (16 + 16)
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                total_height += w.sizeHint().height()
        # 同时设置最小和最大高度，防止被扩展
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)

    def add_message(self, content: str, role: str):
        """Add a message bubble."""
        row = MessageRow(content, role)
        self._layout.addWidget(row)
        self._update_height()  # 每次添加消息后更新高度
```

同时确保子组件的 sizePolicy 正确：

```python
class MessageBubble(QWidget):
    def _setup_ui(self):
        # 垂直方向使用 Minimum，高度适应内容
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

class MessageRow(QWidget):
    def _setup_ui(self):
        # MessageRow 高度应刚好适应内容，不扩展
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
```

#### Qt 布局机制总结

| 设置 | 行为 | 约束级别 |
|------|------|----------|
| `setWidgetResizable(True)` | widget 填满视口 | 覆盖 sizePolicy |
| `setAlignment()` | widget 对齐方式 | 在 setWidgetResizable 下无效 |
| `sizePolicy` | 尺寸策略 | 被 setWidgetResizable 覆盖 |
| **`minimumHeight/maximumHeight`** | 尺寸硬约束 | **最高优先级** |

#### 关键洞察

- `setWidgetResizable(True)` 是"强约束"，会覆盖 sizePolicy
- `setAlignment()` 在 `setWidgetResizable(True)` 时无效
- **硬约束（maximumHeight）优先级最高**，是最终解决方案
- 当软约束失效时，升级到硬约束

---

### 1. Qt 布局机制深层理解（2026-06-07）

#### 问题现象

右侧面板折叠后，后续区块之间出现空白间隙，文件树无法紧贴 MCP 区块下方。

#### 调试过程

这是一个需要 4 次迭代才完全解决的问题：

| 提交 | 尝试方法 | 结果 |
|------|----------|------|
| `581231a` | 移除 content_widget 的 stretch=1 | 失败，仍有间隙 |
| `777ee8f` | 设置 content_widget sizePolicy=Ignored | 失败，仍有间隙 |
| `3c68cfc` | 设置 CollapsibleSection sizePolicy=Fixed | 失败，仍有间隙 |
| `e11cf37` | 设置 maximumHeight=header_height | ✅ 成功 |

#### 根因分析

Qt 的 `QVBoxLayout` 有特殊的 **最小尺寸计算逻辑**：

1. **stretch ≠ sizePolicy**：
   - `stretch` 是布局分配**剩余空间**的比例
   - `sizePolicy` 是组件的**尺寸策略**
   - 即使 `stretch=0`，组件仍会保持其 `sizeHint()` 或 `minimumSizeHint()`

2. **setVisible(False) ≠ 零空间**：
   - 隐藏组件（`setVisible(False)`）后，组件仍有 `minimumSizeHint()`
   - 布局会为隐藏组件保留最小尺寸空间

3. **sizePolicy.Ignored 的局限**：
   - `Ignored` 策略让组件的 sizeHint 被**忽略**
   - 但布局仍会考虑组件的 `minimumSizeHint()`
   - QWidget 默认有非零的 minimumSizeHint

4. **最终方案：maximumHeight 强制约束**：
   - 设置 `maximumHeight` 是**硬约束**
   - 布局必须遵守 maximumHeight，无法绕过
   - 折叠时 `maximumHeight = header_height`，强制布局收紧

#### 正确实现

```python
class CollapsibleSection(QWidget):
    def _toggle_collapsed(self):
        self._is_collapsed = not self._is_collapsed
        self.content_widget.setVisible(not self._is_collapsed)
        
        if self._is_collapsed:
            # 1. 隐藏内容区域
            self.content_widget.setSizePolicy(
                QSizePolicy.Policy.Ignored, 
                QSizePolicy.Policy.Ignored
            )
            # 2. 强制约束整体高度（关键！）
            self.setMaximumHeight(
                self.header_btn.sizeHint().height() + 16  # header + padding
            )
        else:
            # 恢复展开状态
            self.content_widget.setSizePolicy(
                QSizePolicy.Policy.Preferred, 
                QSizePolicy.Policy.Preferred
            )
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
```

#### Qt 布局机制总结

| 概念 | 说明 | 优先级 |
|------|------|--------|
| `minimumSizeHint()` | 组件建议最小尺寸 | 基础约束 |
| `sizePolicy` | 尺寸策略（Fixed/Preferred/Expanding/Ignored） | 软约束 |
| `minimumHeight/maximumHeight` | 尺寸硬约束 | **硬约束（最高）** |
| `stretch` | 剩余空间分配比例 | 布局分配 |

**关键洞察**：
- `sizePolicy.Ignored` 只是"忽略 sizeHint"，不是"忽略所有尺寸"
- **真正控制尺寸必须用 maximumHeight/minimumHeight 硬约束**
- 调试布局问题时，要从"软约束"升级到"硬约束"

#### 验证方法

```python
# 打印布局信息调试
def debug_layout(widget):
    layout = widget.layout()
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget():
            w = item.widget()
            print(f"Widget: {w.__class__.__name__}")
            print(f"  sizeHint: {w.sizeHint()}")
            print(f"  minimumSizeHint: {w.minimumSizeHint()}")
            print(f"  sizePolicy: {w.sizePolicy()}")
            print(f"  maximumHeight: {w.maximumHeight()}")
```

---

### 2. QThread + qasync 静默崩溃（2026-05-31）

#### 症状

程序在创建 OpenAI client 时静默崩溃，无异常输出，日志突然中断。

#### 根因

```python
class AsyncWorker(QThread):
    def run(self):
        loop = asyncio.new_event_loop()  # 新 event loop
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.coro)
```

qasync 要求所有异步操作在主线程的 `QEventLoop` 运行，子线程的新 event loop 导致冲突。

#### 解决

删除 `AsyncWorker`，改用 `@asyncSlot()`：

```python
@asyncSlot(str)
async def _on_message_sent(self, message: str):
    async for chunk in self.controller.send_message(message):
        response = chunk
```

#### 验证方法

```bash
# 检查是否有 QThread + asyncio 组合
grep -r "QThread" packages/client/src/
grep -r "asyncio.new_event_loop" packages/client/src/
```

---

### 3. 会话状态分散问题（2026-05-31）

#### 症状

- 切换会话后历史丢失
- 会话列表显示不一致
- 消息缓存 Bug

#### 根因

状态分散在多处：

```python
# ChatController
self._session_cache: dict

# SidebarPanel
self._current_session_id: str

# MainWindow
self._current_session_id: str
```

#### 解决

引入 `SessionManager` 作为唯一数据源，UI 组件只渲染不存储。

---

### 4. QListWidgetItem 未设置数据（2026-05-31）

#### 症状

点击历史会话时，`item.data(Qt.ItemDataRole.UserRole)` 返回 `None`，切换信号不触发。

#### 根因

```python
# ❌ 错误：只添加文本
self.session_list.addItem("🔵 当前会话")

# ✅ 正确：创建项并设置数据
current_item = QListWidgetItem("🔵 当前会话")
current_item.setData(Qt.ItemDataRole.UserRole, session_id)
self.session_list.addItem(current_item)
```

---

### 5. 用户消息在第二轮迭代丢失（2026-06-06）

#### 症状

日志显示第二轮 LLM 调用时，用户消息丢失。

#### 根因

用户消息临时添加到 `windowed_messages`，未持久化到 `session.messages`。

#### 解决

在 `agent_loop.py` 第一次迭代时持久化：

```python
if iteration == 0 and prompt:
    session.add_message(Message(role="user", content=prompt))
```

#### 教训

**Session 是单一数据源**：所有消息必须持久化到 session，不能临时添加。

---

### 6. 达到迭代上限返回空回复（2026-06-07）

#### 症状

任务成功完成（Word 文档已生成），但 UI 显示空回复。

#### 根因

达到 `max_iterations` 时，`LoopResult` 没有设置 `final_response`。

#### 解决

从 session 中提取最后的助手消息：

```python
final_response = None
for msg in reversed(session.messages):
    if msg.role == "assistant" and msg.content:
        final_response = msg.content
        break

return LoopResult(
    final_response=final_response,
    ...
)
```

---

### 7. QGridLayout 参数签名错误（2026-06-07）

#### 症状

`AddEntryDialog` 继承 `QMessageBox`，添加输入框时报错：
```
TypeError: addWidget(self, w: QWidget, stretch: int = 0, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag())
```

#### 根因

`QMessageBox` 的布局是 `QGridLayout`，不是 `QVBoxLayout`。

```python
# ❌ 错误：QGridLayout.addWidget(w, stretch) 签名不存在
self.layout().addWidget(self._input, 1)

# ✅ 正确：QGridLayout.addWidget(w, row, column, rowSpan, colSpan)
layout = self.layout()
layout.addWidget(self._input, 1, 0, 1, layout.columnCount())
```

#### 教训

1. **不同布局有不同的 addWidget 签名**：
   - `QVBoxLayout.addWidget(w, stretch=0)`
   - `QGridLayout.addWidget(w, row, col, rowSpan=1, colSpan=1)`

2. **继承 Qt 内置控件时检查布局类型**：
   ```python
   layout = self.layout()
   print(type(layout))  # 确认布局类型
   ```

3. **参考官方文档而非凭经验**：不同 Qt 版本 API 可能变化

---

### 8. 使用 Qt 内置组件替代自定义实现（2026-06-05）⭐ 推荐

#### 背景

早期实现中，为了实现特定 UI 效果，编写了大量自定义组件。

#### 重构收益

| 组件 | 自定义实现 | Qt 内置 | 代码减少 |
|------|-----------|---------|----------|
| 文件树 | `QStandardItemModel` + 手动填充 | `QFileSystemModel` | ~70% |
| 导航按钮 | `NavButton(QWidget)` | `QToolButton` | ~90 行 |
| 文件图标 | 手动映射扩展名 | `QFileIconProvider` | ~50% |

#### 示例：文件树重构

```python
# ❌ 旧实现：手动构建模型
class FileTreeSection(QWidget):
    def _load_directory(self, path):
        model = QStandardItemModel()
        root = model.invisibleRootItem()
        for entry in os.scandir(path):
            item = QStandardItem(entry.name)
            if entry.is_dir():
                item.setIcon(self._folder_icon)
            else:
                item.setIcon(self._file_icon)
            root.appendRow(item)
        # ... 约 100 行代码

# ✅ 新实现：使用 QFileSystemModel
class FileTreeSection(QWidget):
    def _setup_ui(self):
        self._model = QFileSystemModel()
        self._model.setRootPath(str(self._root_dir))
        self._tree.setModel(self._model)
        self._tree.setRootIndex(self._model.index(str(self._root_dir)))
        # ~30 行代码
```

#### QFileSystemModel 优势

- **自动文件系统监控**：文件变化自动更新视图
- **系统图标支持**：无需手动映射扩展名
- **线程安全**：后台加载不阻塞 UI
- **性能优化**：延迟加载大目录

#### 教训

1. **优先使用 Qt 内置组件**：Qt 经过多年优化，内置组件通常比自定义实现更稳定
2. **减少维护成本**：自定义代码越多，维护负担越重
3. **功能与复杂度平衡**：如果内置组件能满足 80% 需求，不要为了剩余 20% 重新造轮子

#### 检查清单

在编写自定义组件前，检查：
- [ ] Qt 是否已有类似控件？（`QToolButton`, `QTreeView`, `QListView`...）
- [ ] Qt 是否提供对应模型？（`QFileSystemModel`, `QStringListModel`...）
- [ ] Qt 样式表（QSS）能否实现目标效果？
- [ ] 是否真的需要自定义，还是可以通过配置实现？

---

## 三、最佳实践

### 1. 控制器模式

每个控制器专注一个领域：

| 控制器 | 职责 |
|--------|------|
| `ChatController` | 对话交互、Agent 管理 |
| `SessionManager` | 会话状态管理 |
| `MCPController` | MCP 服务器管理 |
| `SkillController` | 技能管理 |
| `MemoryController` | 记忆管理 |

---

### 2. 回调机制解耦

```python
# 控制器定义回调接口
def set_tool_call_callback(self, callback: Callable[[str, dict], None]):
    self._on_tool_call = callback

# UI 设置回调
self.chat_controller.set_tool_call_callback(self._show_tool_call)

# 控制器触发回调
if self._on_tool_call:
    self._on_tool_call(tool_name, arguments)
```

---

### 3. PyQt 信号驱动

```python
# 定义信号
class MemoryController(QObject):
    memory_changed = pyqtSignal()

# 发射信号
self.memory_changed.emit()

# UI 连接信号
self.memory_controller.memory_changed.connect(self._on_memory_changed)
```

---

### 4. 配置目录统一

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
- 用户期望的行为

---

### 5. 流式输出模拟

由于 SDK 返回完整响应，客户端实现流式输出模拟提升 UX：

```python
def _simulate_streaming(self, text: str):
    self.chat_panel.start_streaming()
    self._stream_buffer = text
    self._stream_pos = 0
    
    chunk_size = max(1, len(text) // 100)
    interval = max(10, 1500 // 100)
    
    self._stream_timer = QTimer()
    self._stream_timer.timeout.connect(self._stream_next_chunk)
    self._stream_timer.start(interval)
```

---

### 6. 配置迁移兼容性

当配置目录变更时，提供自动迁移：

```python
def migrate_old_config() -> None:
    """从旧位置迁移配置到 ~/.harness"""
    old_dir = get_old_config_dir()  # 平台特定旧位置
    new_dir = get_config_dir()      # 统一新位置
    
    if not old_dir.exists():
        return
    
    # 迁移 settings.json
    old_settings = old_dir / "settings.json"
    new_settings = new_dir / "settings.json"
    if old_settings.exists() and not new_settings.exists():
        shutil.copy2(old_settings, new_settings)
```

**优势**：
- 用户无感知升级
- 避免配置丢失
- 保持向后兼容

---

### 7. 默认折叠高频使用区块

右侧面板的折叠状态设计：

```python
# 文件树默认展开（最常用），其他折叠
self.memory_section.set_collapsed(True)
self.skills_section.set_collapsed(True)
self.mcp_section.set_collapsed(True)
# 文件树保持展开
```

**设计考量**：
- 减少视觉干扰
- 突出常用功能
- 用户可随时展开

---

### 8. 用轻量动画提升可读性

在不引入复杂自定义绘制的前提下，用最小的动画增强状态感：

- ChatPanel 使用平滑滚动，减少流式输出时的跳动感
- Tool call / result 卡片使用更强的边框和光晕区分状态
- RightPanel 折叠/展开加入淡入淡出，降低切换时的突兀感

**设计考量**：
- 动画只服务于阅读体验，不改变信息结构
- 保持实现简单，避免把过多行为塞进控制器
- 优先使用 Qt 与 QTextBrowser 能稳定支持的能力

---

## 四、代码结构参考

### 客户端文件组织

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
│   └── skill_dialog.py           # 技能编辑对话框
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

## 五、开发检查清单

### 新增 UI 组件时

- [ ] 组件是否只负责渲染，不存储业务状态？
- [ ] 是否使用信号进行通信？
- [ ] 异步方法是否使用 `@asyncSlot()`？
- [ ] 是否在主线程执行所有异步操作？

### 新增控制器时

- [ ] 职责是否单一明确？
- [ ] 是否提供回调接口而非直接调用 UI？
- [ ] 数据是否通过 Manager/单一数据源管理？
- [ ] SDK 调用是否正确配置？

### 会话相关修改时

- [ ] 消息是否持久化到 SessionManager？
- [ ] 多轮迭代后消息是否完整？
- [ ] 切换会话时历史是否正确加载？
- [ ] UI 是否从 SessionManager 获取数据？

### 异步操作时

- [ ] 是否使用 `@asyncSlot()` 而非 QThread？
- [ ] 是否在主线程的 QEventLoop 运行？
- [ ] 是否正确声明信号参数类型？

### Qt 布局调试时

- [ ] 是否理解 stretch vs sizePolicy 的区别？
- [ ] 是否检查 minimumSizeHint()？
- [ ] 是否需要用 maximumHeight/minimumHeight 硬约束？
- [ ] 是否打印布局信息调试？

### 使用 Qt 组件时

- [ ] 是否优先使用 Qt 内置组件？
- [ ] 是否检查布局类型（QVBoxLayout vs QGridLayout）？
- [ ] 是否查阅官方 API 文档确认签名？
- [ ] 是否考虑使用 QFileSystemModel 等内置模型？

---

## 六、参考资源

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [qasync GitHub](https://github.com/CabbageDevelopment/qasync)
- [Harness SDK 文档](../../sdk/docs/)
- [编程技能规范](../../sdk/docs/programmer_skill.md)
- [lessons.md](../../../lessons.md) - 全项目经验教训