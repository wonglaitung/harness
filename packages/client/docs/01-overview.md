# 01 - 客户端概述与架构

## 项目背景

### 问题陈述

Harness SDK 提供了强大的 AI Agent 能力，但作为纯 Python SDK，用户需要自行构建用户界面。对于非技术用户或希望开箱即用的场景，缺少一个直观的图形界面。

### 解决方案

**Harness Client** 是一个 Windows 桌面客户端，提供：

- 友好的图形用户界面（PyQt6）
- 开箱即用的 AI Agent 体验
- 可视化的 MCP 服务器管理
- 技能系统可视化管理
- 全局记忆管理
- 多会话支持
- **会话持久化**：自动保存会话历史，重启后恢复

## 核心公式

```
Client = PyQt6 UI + Harness SDK + Controllers
```

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        HARNESS CLIENT                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     UI Layer (PyQt6)                        │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Sidebar  │  │  Chat    │  │  Right   │  │ Settings │   │ │
│  │  │  Panel   │  │  Panel   │  │  Panel   │  │  Dialog  │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Controller Layer                          │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │  Chat    │  │   MCP    │  │  Skill   │  │  Memory  │   │ │
│  │  │Controller│  │Controller│  │Controller│  │Controller│   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              Session Manager                          │  │ │
│  │  │         (Single Source of Truth for Sessions)         │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Harness SDK                              │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │  Agent   │  │   MCP    │  │  Skill   │  │  Memory  │   │ │
│  │  │ Harness  │  │ Manager  │  │ Registry │  │  System  │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Configuration                             │ │
│  │                                                              │ │
│  │  ~/.harness/                                                │ │
│  │  ├── settings.json     # 应用设置                           │ │
│  │  ├── mcp.json          # MCP 服务器配置                     │ │
│  │  ├── MEMORY.md         # 全局记忆                           │ │
│  │  └── skills/           # 技能目录                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 三栏布局

```
┌─────────────────────────────────────────────────────────────────┐
│                        Header Bar                                │
│  [Model Selector] [Provider] [Token Usage]        [Settings]    │
├──────────┬───────────────────────────────────┬─────────────────┤
│          │                                   │                 │
│ Sidebar  │          Chat Panel               │   Right Panel   │
│          │                                   │                 │
│ ○ 新会话 │  [User Message]                   │ ▼ 记忆          │
│ ○ 会话1  │                                   │   - 用户偏好    │
│ ○ 会话2  │  [Assistant Response]             │                 │
│          │                                   │ ▼ 技能          │
│          │  ...                              │   - skill-1     │
│          │                                   │                 │
│          │  ┌─────────────────────────────┐  │ ▼ MCP           │
│          │  │ Input Area                  │  │   - server-1    │
│          │  │ [/] for skills...           │  │                 │
│          │  └─────────────────────────────┘  │ ▼ 文件树        │
│          │                                   │                 │
├──────────┴───────────────────────────────────┴─────────────────┤
│                        Status Bar                                │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **MainWindow** | `ui/main_window.py` | 主窗口，协调所有组件 |
| **SidebarPanel** | `ui/sidebar.py` | 左侧导航栏，会话列表 |
| **ChatPanel** | `ui/chat_panel.py` | 中央对话面板 |
| **RightPanel** | `ui/right_panel.py` | 右侧面板（记忆/技能/MCP/文件树，可折叠并支持淡入淡出过渡） |

| **SettingsDialog** | `ui/settings_dialog.py` | 设置对话框 |
| **ChatController** | `controllers/chat_controller.py` | 管理 AgentHarness 和对话 |
| **SessionManager** | `controllers/session_manager.py` | 会话状态管理（单一数据源） |
| **MCPController** | `controllers/mcp_controller.py` | MCP 服务器管理 |
| **SkillController** | `controllers/skill_controller.py` | 技能管理 |
| **MemoryController** | `controllers/memory_controller.py` | 全局记忆管理 |

## 数据流

### 消息发送流程

```
用户输入
    │
    ↓
ChatPanel.message_sent (Signal)
    │
    ↓
MainWindow._on_message_sent (asyncSlot)
    │
    ↓
ChatController.send_message (async)
    │
    ├── SessionManager.add_message_to_current (缓存用户消息)
    │
    ├── AgentHarness.run (SDK)
    │   │
    │   ├── ContextBuilder.build (构建上下文)
    │   │   └── 加载全局记忆 (MEMORY.md)
    │   │
    │   ├── LLM Call
    │   │
    │   └── Tool Execution
    │
    └── SessionManager.add_message_to_current (缓存助手响应)
    │
    ↓
UI Update (yield streaming response)
```

### 会话管理数据流

```
SessionManager (单一数据源)
    │
    ├── create() → 新建会话
    ├── switch_to() → 切换会话
    ├── delete() → 删除会话（同步删除磁盘文件）
    ├── get_current() → 获取当前会话
    │
    └── 持久化操作
        ├── _load_sessions() → 启动时加载历史会话
        ├── _save_session() → 自动保存到 ~/.harness/sessions/
        └── _delete_session_file() → 删除时同步删除文件
    │
    ↓
MainWindow._refresh_session_list()
    │
    ↓
SidebarPanel.update_sessions() (纯渲染，不存状态)
```

### MCP 连接流程

```
用户点击"添加 MCP 服务器"
    │
    ↓
MCPDialog.show()
    │
    ↓
用户填写配置 → on_accept
    │
    ↓
MCPController.add_server_config()
    │
    ├── MCPManager.add_server() (SDK)
    │
    └── servers dict 更新
    │
    ↓
callback → MainWindow._on_mcp_changed()
    │
    ↓
RightPanel.update_mcp_servers() (UI 更新)
    │
    ↓
用户点击"连接" → MCPController.connect_server()
    │
    ↓
工具加载完成 → ChatController.set_mcp_tools()
```

## 设计原则

### 1. 单一数据源 (Single Source of Truth)

所有会话状态存储在 `SessionManager` 中，UI 组件只负责渲染，不存储状态。

```python
# ✓ 正确：从 SessionManager 获取状态
session = self.session_manager.get_current()
messages = session.messages

# ✗ 错误：UI 组件自己存储状态
self._messages = []  # 不要这样做
```

### 2. 控制器模式 (Controller Pattern)

控制器封装业务逻辑，UI 组件只处理渲染和用户交互。

```
UI Layer (PyQt6)
    ↓ 信号/槽
Controller Layer
    ↓ 方法调用
SDK Layer
```

### 3. 异步优先 (Async-First)

所有可能耗时的操作都使用 async/await，避免阻塞 UI。

```python
from qasync import asyncSlot

class MainWindow(QMainWindow):
    @asyncSlot(str)
    async def _on_message_sent(self, message: str):
        async for chunk in self.controller.send_message(message):
            response = chunk
```

### 4. 信号驱动 (Signal-Driven)

使用 PyQt6 信号机制解耦组件：

```python
# 定义信号
message_sent = pyqtSignal(str)

# 连接信号
self.chat_panel.message_sent.connect(self._on_message_sent)

# 发射信号
self.message_sent.emit(message)
```

## 配置管理

### 配置目录结构

```
~/.harness/
├── settings.json     # 应用设置（API Key、模型等）
├── mcp.json          # MCP 服务器配置
├── MEMORY.md         # 全局记忆文件
├── sessions/         # 会话持久化目录
│   ├── abc12345.json # 单个会话文件
│   └── ...
├── skills/           # 全局技能目录
│   └── my-skill/
│       └── skill.md
└── audit/            # 审计日志
```

### 配置迁移

客户端支持从旧版本配置目录自动迁移：

| 旧位置 | 新位置 |
|--------|--------|
| Windows: `%LOCALAPPDATA%\HarnessClient` | `~/.harness` |
| macOS: `~/Library/Application Support/HarnessClient` | `~/.harness` |
| Linux: `~/.config/HarnessClient` | `~/.harness` |

## 与 SDK 的关系

### 依赖关系

```
Client
  │
  ├── harness (SDK)
  │     ├── AgentHarness
  │     ├── HarnessConfig
  │     ├── MCPManager
  │     ├── SkillRegistry
  │     └── MemoryFileManager
  │
  ├── PyQt6 (UI Framework)
  │
  └── qasync (Async/Qt Integration)
```

### 关键集成点

| 客户端组件 | SDK 组件 | 说明 |
|------------|----------|------|
| ChatController | AgentHarness | 核心对话能力 |
| MCPController | MCPManager | MCP 服务器管理 |
| SkillController | SkillRegistry | 技能注册和匹配 |
| MemoryController | MemoryFileManager | 记忆文件管理 |
| ChatConfig | HarnessConfig | 配置转换 |

## 技术选型

### PyQt6 + qasync

选择 PyQt6 作为 UI 框架，qasync 作为异步集成层。

**优势**：
- PyQt6 成熟稳定，文档丰富
- qasync 允许在 Qt 事件循环中运行 asyncio
- 支持流式响应的平滑渲染

**注意事项**：
- 所有异步操作必须在主线程的 QEventLoop 中运行
- 使用 `@asyncSlot` 装饰器连接信号
- **禁止**在 QThread 中创建新的 event loop

```python
# ✓ 正确：使用 asyncSlot
@asyncSlot(str)
async def _on_message_sent(self, message: str):
    async for chunk in self.controller.send_message(message):
        ...

# ✗ 错误：在 QThread 中创建 event loop
class MyThread(QThread):
    def run(self):
        asyncio.run(my_async_func())  # 会导致崩溃
```

## 参考资源

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [qasync GitHub](https://github.com/CabbageDevelopment/qasync)
- [Harness SDK Documentation](../../sdk/docs/)

## 下一步

- [02-ui-components.md](./02-ui-components.md) - 了解 UI 组件
- [03-controllers.md](./03-controllers.md) - 了解控制器
- [development_guide.md](./development_guide.md) - 开发经验总结
