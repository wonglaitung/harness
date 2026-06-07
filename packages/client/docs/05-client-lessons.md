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

### 1. QThread + qasync 静默崩溃（2026-05-31）

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

### 2. 会话状态分散问题（2026-05-31）

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

### 3. QListWidgetItem 未设置数据（2026-05-31）

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

### 4. 用户消息在第二轮迭代丢失（2026-06-06）

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

### 5. 达到迭代上限返回空回复（2026-06-07）

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

---

## 六、参考资源

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [qasync GitHub](https://github.com/CabbageDevelopment/qasync)
- [Harness SDK 文档](../../sdk/docs/)
- [编程技能规范](../../sdk/docs/programmer_skill.md)
- [lessons.md](../../../lessons.md) - 全项目经验教训