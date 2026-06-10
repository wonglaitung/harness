# 03 - 控制器详解

## 概述

控制器层是客户端的核心业务逻辑层，负责协调 UI 和 SDK。每个控制器专注于一个特定领域，提供清晰的职责划分。

## 控制器架构

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Sidebar  │  │  Chat    │  │  Right   │  │ Settings │   │
│  │  Panel   │  │  Panel   │  │  Panel   │  │  Dialog  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
        ↓             ↓             ↓             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Controller Layer                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Session Manager                       │  │
│  │            (Single Source of Truth)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↑                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Chat    │  │   MCP    │  │  Skill   │  │  Memory  │   │
│  │Controller│  │Controller│  │Controller│  │Controller│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
        ↓             ↓             ↓             ↓
┌─────────────────────────────────────────────────────────────┐
│                      Harness SDK                             │
│  AgentHarness   MCPManager   SkillRegistry   MemoryManager  │
└─────────────────────────────────────────────────────────────┘
```

## ChatController

核心控制器，管理对话交互。

### 职责

- 创建和管理 AgentHarness 实例
- 发送消息并接收流式响应
- 管理会话状态
- 处理进度事件
- 集成 MCP 工具

### 配置

```python
@dataclass
class ChatConfig:
    """聊天配置"""
    
    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: str = "auto"
    max_iterations: int = 10
    temperature: float = 0.3
    tool_result_role: str = "tool"  # "tool" 或 "user"
    system_prompt: str = "..."
```

### 核心方法

#### 初始化

```python
async def initialize(self, mcp_tools: list = None):
    """
    初始化 AgentHarness。
    
    Args:
        mcp_tools: 可选的 MCP 工具列表
    """
    sdk_config = HarnessConfig(
        model=self.config.model,
        api_key=self.config.api_key or None,
        provider=self.config.provider,
        base_url=self.config.base_url or None,
        context_window=self.config.context_window,
        max_iterations=self.config.max_iterations,
        temperature=self.config.temperature,
        tool_result_role=self.config.tool_result_role,
        system_prompt=self.config.system_prompt,
        sandbox_workspace=str(self.work_dir),
        memory_md_path=get_config_dir() / "MEMORY.md",  # 全局记忆
    )
    
    tools = [
        ReadTool(),
        WriteTool(),
        GlobTool(),
        GrepTool(),
        BashTool(),
    ]
    
    # 添加 MCP 工具
    if mcp_tools:
        tools.extend(mcp_tools)
    
    self.agent = AgentHarness(config=sdk_config, tools=tools)
```

#### 发送消息

```python
async def send_message(self, message: str) -> AsyncIterator[str]:
    """
    发送消息并返回流式响应。
    
    Args:
        message: 用户消息
        
    Yields:
        响应文本块
    """
    if not self.agent:
        await self.initialize()
    
    # 先缓存用户消息
    self.session_manager.add_message_to_current("user", message)
    
    try:
        # 设置进度回调
        def on_progress(event: ProgressEvent):
            if event.type == ProgressEventType.TOOL_CALL:
                self._on_tool_call(event.data["tool"], event.data["arguments"])
            elif event.type == ProgressEventType.TOOL_RESULT:
                self._on_tool_result(event.data["tool"], event.data["result"], event.data["success"])
        
        # 调用 Agent
        result = await self.agent.run(
            message,
            session_id=self.session_manager.current_id,
            on_progress=on_progress,
        )
        
        # 缓存助手响应
        self.session_manager.add_message_to_current("assistant", result.content)
        
        yield result.content
        
    except Exception as e:
        yield f"❌ 错误: {type(e).__name__}: {str(e)}"
```

### 回调机制

```python
def set_tool_call_callback(self, callback: Callable[[str, dict], None]):
    """设置工具调用回调"""
    self._on_tool_call = callback

def set_tool_result_callback(self, callback: Callable[[str, str, bool], None]):
    """设置工具结果回调"""
    self._on_tool_result = callback

def set_thinking_callback(self, callback: Callable[[str], None]):
    """设置思考状态回调"""
    self._on_thinking = callback

def set_confirm_callback(self, callback: Callable[[str, dict], ConfirmationResult]):
    """设置危险操作确认回调

    Args:
        callback: 返回 ConfirmationResult(confirmed, trust_session)
    """
    self._confirm_callback = callback
```

### 危险操作确认集成

ChatController 集成 ConfirmationHook 进行危险操作确认：

```python
async def initialize(self, mcp_tools: list = None):
    # ... 创建 AgentHarness ...

    if self._confirm_callback:
        # 信任检查回调
        def is_trusted(trust_key: str) -> bool:
            session = self.session_manager.get_current()
            return session.is_command_trusted(trust_key) if session else False

        # 信任设置回调
        def on_trust(trust_key: str) -> None:
            session = self.session_manager.get_current()
            if session:
                session.trust_command(trust_key)

        # 注册 ConfirmationHook
        self.agent.add_hook(ConfirmationHook(
            on_confirm=self._async_confirm,
            is_trusted=is_trusted,
            on_trust=on_trust,
        ))
```

## SessionManager

会话状态管理器，是会话数据的单一数据源。

### 设计原则

**单一数据源 (Single Source of Truth)**：所有会话状态存储在 SessionManager 中，UI 组件只负责渲染。

### 会话模型

```python
@dataclass
class ClientSession:
    """客户端会话"""

    id: str
    name: str = "新会话"
    messages: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    token_usage: dict = field(default_factory=lambda: {"input": 0, "output": 0})
    trusted_commands: set[str] = field(default_factory=set)  # 会话级信任缓存
```

### 会话信任管理

每个会话维护独立的信任缓存，用户确认一次命令后可选择信任整个会话：

```python
# 信任键格式
# - write, edit → "write", "edit"
# - bash 命令 → "bash:{命令名}" (如 "bash:ls", "bash:rm")

session.trust_command("bash:ls")      # 信任 ls 命令
session.trust_command("write")         # 信任 write 工具

session.is_command_trusted("bash:ls")  # → True
session.is_command_trusted("bash:rm")  # → False (需单独信任)

session.clear_trust()  # 清空信任缓存
```

### 核心方法

```python
class SessionManager:
    def __init__(self, max_sessions: int = 50):
        self._sessions: OrderedDict[str, ClientSession] = OrderedDict()
        self._current_id: str | None = None
        self._max_sessions = max_sessions
    
    def create(self, session_id: str = None) -> ClientSession:
        """创建新会话"""
        
    def get_current(self) -> ClientSession | None:
        """获取当前会话"""
        
    def switch_to(self, session_id: str) -> bool:
        """切换到指定会话"""
        
    def delete(self, session_id: str) -> bool:
        """删除会话"""
        
    def archive_current(self) -> None:
        """归档当前会话（不删除，只是取消选中）"""
        
    def add_message_to_current(self, role: str, content: str):
        """向当前会话添加消息"""
        
    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """更新 token 使用统计"""
```

### 数据流

```
用户发送消息
    │
    ↓
ChatController.send_message()
    │
    ├── session_manager.add_message_to_current("user", message)  # 先缓存
    │
    ├── agent.run()
    │
    └── session_manager.add_message_to_current("assistant", response)  # 后缓存
    │
    ↓
UI 从 SessionManager 读取消息显示
```

## MCPController

MCP 服务器管理控制器。

### 职责

- 添加/删除 MCP 服务器配置
- 连接/断开服务器
- 获取已连接服务器的工具列表
- 加载/保存配置文件

### 服务器信息模型

```python
@dataclass
class MCPServerInfo:
    """MCP 服务器信息"""
    
    name: str
    transport: str  # "stdio" 或 "http"
    status: str = "未连接"  # 未连接, 已连接, 错误
    tools_count: int = 0
    error_message: str = ""
```

### 核心方法

```python
class MCPController:
    def __init__(self):
        self.manager = MCPManager()  # SDK 组件
        self.servers: dict[str, MCPServerInfo] = {}
    
    async def connect_server(self, name: str) -> bool:
        """连接服务器"""
        
    async def disconnect_server(self, name: str) -> bool:
        """断开服务器"""
        
    async def connect_all(self) -> dict[str, bool]:
        """连接所有服务器"""
        
    def get_tools(self) -> list:
        """获取所有已连接服务器的工具"""
        
    def load_config(self, path: Path) -> list[MCPServerConfig]:
        """从文件加载配置"""
        
    def save_config(self, path: Path):
        """保存配置到文件"""
```

### 配置文件格式

`~/.harness/mcp.json`:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "transport": "stdio",
      "command": "mcp-filesystem",
      "args": ["/path/to/workspace"],
      "env": {}
    },
    {
      "name": "github",
      "transport": "stdio",
      "command": "mcp-github",
      "env": {
        "GITHUB_TOKEN": "your-token"
      }
    }
  ]
}
```

## SkillController

技能管理控制器。

### 职责

- 加载技能目录
- 获取技能列表
- 匹配用户输入的技能

### 核心方法

```python
class SkillController:
    def __init__(self):
        self._skills: list[Skill] = []
    
    def load_skills(self, directory: Path) -> int:
        """从目录加载技能"""
        
    def get_skills(self) -> list[dict]:
        """获取技能列表（用于 UI 显示）"""
        
    def get_skill(self, name: str) -> Skill | None:
        """获取指定技能"""
        
    def create_skill(self, name: str, description: str, content: str) -> bool:
        """创建新技能"""
        
    def update_skill(self, name: str, content: str) -> bool:
        """更新技能内容"""
        
    def delete_skill(self, name: str) -> bool:
        """删除技能"""
```

## MemoryController

全局记忆管理控制器。

### 职责

- 管理 `~/.harness/MEMORY.md` 文件
- 提供 CRUD 操作
- 与 SDK MemoryFileManager 集成

### 核心方法

```python
class MemoryController(QObject):
    memory_changed = pyqtSignal()  # 记忆变化信号
    
    def __init__(self):
        self._memory_root = get_config_dir()
        self._manager = MemoryFileManager(self._memory_root)
    
    def get_sections(self) -> MemorySections:
        """加载所有记忆章节"""
        
    def get_entries(self, category: MemoryCategory) -> list[str]:
        """获取指定类别的条目"""
        
    def add_entry(self, category: MemoryCategory, content: str):
        """添加新条目"""
        
    def update_entry(self, category: MemoryCategory, index: int, content: str) -> bool:
        """更新条目"""
        
    def remove_entry(self, category: MemoryCategory, index: int) -> bool:
        """删除条目"""
        
    def clear_all(self):
        """清空所有记忆"""
        
    def exists(self) -> bool:
        """检查 MEMORY.md 是否存在"""
```

### 与 ChatController 集成

```python
# ChatController.initialize() 中配置
sdk_config = HarnessConfig(
    ...
    memory_md_path=get_config_dir() / "MEMORY.md",  # 传递给 SDK
)
```

### 即时更新

MEMORY.md 文件在每次 `run()` 调用时重新读取，UI 中的修改立即生效：

```python
# UI 中修改记忆
self.memory_controller.add_entry(MemoryCategory.USER_PROFILE, "使用 Windows")

# 下一次消息发送时自动加载更新后的记忆
result = await self.chat_controller.send_message("帮我...")
```

## 最佳实践

### 1. 控制器分离

每个控制器专注于一个领域：

```python
# ✓ 正确：每个控制器有明确的职责
self.chat_controller = ChatController()      # 对话
self.mcp_controller = MCPController()        # MCP 服务器
self.skill_controller = SkillController()    # 技能
self.memory_controller = MemoryController()  # 记忆

# ✗ 错误：一个控制器处理所有事情
self.controller = AllInOneController()  # 职责不清晰
```

### 2. 回调模式

使用回调机制解耦 UI 和控制器：

```python
# 控制器定义回调接口
def set_tool_call_callback(self, callback: Callable):
    self._on_tool_call = callback

# UI 设置回调
self.chat_controller.set_tool_call_callback(self._show_tool_call)

# 控制器调用回调
if self._on_tool_call:
    self._on_tool_call(tool_name, arguments)
```

### 3. UI 过渡效果

客户端 UI 侧会对展示层做轻量动画增强，但不把动画逻辑下沉到控制器：

- ChatPanel 负责流式消息追加后的平滑滚动
- Tool call / result 的状态样式仍由 UI 渲染层控制
- RightPanel 的折叠/展开过渡也保留在 UI 层

控制器继续只负责数据与回调，不承担渲染细节。

### 4. 信号机制

使用 PyQt 信号进行组件间通信：

```python
class MemoryController(QObject):
    memory_changed = pyqtSignal()  # 定义信号
    
    def add_entry(self, ...):
        ...
        self.memory_changed.emit()  # 发射信号

# UI 连接信号
self.memory_controller.memory_changed.connect(self._on_memory_changed)
```
