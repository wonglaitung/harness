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
│       │             │             │             │          │
│       └─────────────┼─────────────┼─────────────┘          │
│                     ↓             ↓                        │
│              ┌──────────────────────────┐                  │
│              │  MonitoringController    │                  │
│              │  (指标 + 执行日志)         │                  │
│              └──────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
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

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 JSON 存储）"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientSession":
        """从字典反序列化"""
```

### 会话持久化

SessionManager 支持将会话持久化到磁盘，应用重启后自动恢复历史会话。

#### 存储位置

会话存储在 `~/.harness/sessions/` 目录，每个会话一个 JSON 文件：

```
~/.harness/sessions/
├── abc12345.json
├── def67890.json
└── ...
```

#### 存储格式

```json
{
  "id": "abc12345",
  "name": "Hello, this is a tes...",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "created_at": "2026-06-15T11:35:00",
  "updated_at": "2026-06-15T11:36:00",
  "token_usage": {"input": 100, "output": 50},
  "trusted_commands": []
}
```

#### 持久化机制

```python
class SessionManager:
    def __init__(self, max_sessions: int = 50, storage_dir: Path | None = None):
        self._sessions: OrderedDict[str, ClientSession] = OrderedDict()
        self._current_id: str | None = None
        self._max_sessions = max_sessions
        self._storage_dir = storage_dir or get_config_dir() / "sessions"
        self._loaded = False  # 延迟加载标记

    def _ensure_loaded(self) -> None:
        """延迟加载：首次访问时从磁盘加载历史会话"""

    def _load_sessions(self) -> None:
        """按修改时间倒序加载所有会话文件"""

    def _save_session(self, session: ClientSession) -> None:
        """保存会话到 JSON 文件"""

    def _delete_session_file(self, session_id: str) -> None:
        """删除会话文件"""
```

#### 自动保存时机

- `add_message_to_current()` - 添加消息后自动保存
- `archive_current()` - 切换会话时保存当前会话
- `update_token_usage()` - 更新 token 使用量后保存
- `delete()` - 删除会话时同步删除文件

#### 会话数量限制

默认最多保存 50 个会话，超过限制时自动清理最旧的会话：

```python
# archive_current() 中的清理逻辑
while len(self._sessions) > self._max_sessions:
    oldest_id = next(iter(self._sessions))
    if oldest_id != self._current_id:
        self._delete_session_file(oldest_id)
        del self._sessions[oldest_id]
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
    def __init__(self, max_sessions: int = 50, storage_dir: Path | None = None):
        self._sessions: OrderedDict[str, ClientSession] = OrderedDict()
        self._current_id: str | None = None
        self._max_sessions = max_sessions
        self._storage_dir = storage_dir  # 持久化存储目录
    
    def create(self, session_id: str = None) -> ClientSession:
        """创建新会话"""
        
    def get_current(self) -> ClientSession | None:
        """获取当前会话"""
        
    def get(self, session_id: str) -> ClientSession | None:
        """获取指定会话"""
        
    def switch_to(self, session_id: str) -> bool:
        """切换到指定会话"""
        
    def delete(self, session_id: str) -> bool:
        """删除会话（同时删除磁盘文件）"""
        
    def archive_current(self) -> None:
        """归档当前会话（保存到磁盘）"""
        
    def add_message_to_current(self, role: str, content: str):
        """向当前会话添加消息（自动保存）"""
        
    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """更新 token 使用统计（自动保存）"""
        
    def save_current(self) -> bool:
        """手动保存当前会话"""
        
    def get_history_list(self) -> list[ClientSession]:
        """获取历史会话列表（按更新时间倒序）"""
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

## ScheduleController

排程管理控制器，管理定时任务。

### 职责

- 管理 ScheduleConfig 配置
- 提供 CRUD 操作
- 集成 SDK TriggerManager（未来）
- 持久化到 JSON 文件

### 配置模型

```python
@dataclass
class ScheduleConfig:
    """排程配置"""
    
    id: str                           # 唯一标识
    name: str                         # 排程名称
    goal: str                         # 任务目标
    trigger_type: str                 # "cron" 或 "interval"
    trigger_value: str                # Cron 表达式或间隔秒数
    enabled: bool = True              # 是否启用
    max_iterations: int = 50          # 最大迭代次数
    timeout_seconds: int = 3600       # 超时时间（秒）
    skills: list[str] = field(default_factory=list)  # 关联技能
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    status: str = "idle"              # idle, running, paused, error
    error_message: str = ""
```

### 核心方法

```python
class ScheduleController:
    def __init__(self):
        self._schedules: dict[str, ScheduleConfig] = {}
        self._config_path: Optional[Path] = None
    
    def get_schedule_list(self) -> list[ScheduleConfig]:
        """获取所有排程"""
        
    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """获取指定排程"""
        
    def add_schedule(self, config: ScheduleConfig) -> bool:
        """添加新排程"""
        
    def update_schedule(self, schedule_id: str, updates: dict) -> bool:
        """更新排程"""
        
    def delete_schedule(self, schedule_id: str) -> bool:
        """删除排程"""
        
    def toggle_schedule(self, schedule_id: str) -> bool:
        """切换启停状态"""
        
    def validate_cron(self, expression: str) -> tuple[bool, str]:
        """验证 Cron 表达式
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        
    def get_next_run_times(self, expression: str, count: int = 5) -> list[datetime]:
        """获取下次运行时间列表"""
        
    def load_from_file(self, path: Path):
        """从 JSON 文件加载配置"""
        
    def save_to_file(self, path: Path):
        """保存配置到 JSON 文件"""
```

### Cron 表达式验证

```python
def validate_cron(self, expression: str) -> tuple[bool, str]:
    """验证 Cron 表达式"""
    try:
        from croniter import croniter
        croniter(expression)
        return True, ""
    except ImportError:
        # croniter 未安装，做基本验证
        parts = expression.split()
        if len(parts) != 5:
            return False, "Cron 表达式必须包含 5 个字段"
        return True, ""
    except Exception as e:
        return False, f"无效的 Cron 表达式: {str(e)}"
```

### 与 TriggerManager 集成（未来）

```python
async def start(self):
    """启动 TriggerManager"""
    from harness import TriggerManager
    
    self._trigger_manager = TriggerManager(self._agent)
    await self._trigger_manager.start()
    
    # 注册所有启用的排程
    for config in self._schedules.values():
        if config.enabled:
            self._register_trigger(config)

async def stop(self):
    """停止 TriggerManager"""
    if self._trigger_manager:
        await self._trigger_manager.stop()
```

## MonitoringController

可观测性控制器，管理会话指标和执行日志。

### 职责

- 接收 SDK ProgressEvent 事件
- 统计 Token 使用、迭代次数、工具调用
- 估算 API 成本
- 管理执行日志
- 提供 PyQt 信号通知 UI 更新

### 数据模型

#### SessionMetrics

```python
@dataclass
class SessionMetrics:
    """当前会话的指标数据"""

    # Token 使用
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    # 执行统计
    iterations: int = 0
    tool_calls: int = 0
    tool_success: int = 0
    tool_errors: int = 0
    errors: int = 0

    # 时间
    start_time: datetime | None = None
    end_time: datetime | None = None
    last_update: datetime | None = None
    llm_call_start: float | None = None
    total_llm_duration_ms: float = 0.0

    # 成本估算 (美元)
    cost_usd: float = 0.0

    # 历史记录 (最近 N 次请求的 token 总数)
    token_history: list[int] = field(default_factory=list)

    def total_tokens(self) -> int:
        """总 token 数"""
        return self.input_tokens + self.output_tokens

    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.input_tokens + self.cache_read_tokens
        if total == 0:
            return 0.0
        return self.cache_read_tokens / total

    def duration_seconds(self) -> float:
        """会话持续时间（秒）"""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
```

#### LogEntry

```python
@dataclass
class LogEntry:
    """执行日志条目"""

    timestamp: datetime
    type: str  # "llm_call", "tool_call", "tool_result", "iteration", "error"
    message: str
    details: dict = field(default_factory=dict)
```

### 核心方法

```python
class MonitoringController(QObject):
    """可观测性控制器"""

    # PyQt 信号
    metrics_updated = pyqtSignal()  # 指标更新
    log_entry_added = pyqtSignal(object)  # 新日志条目 (LogEntry)

    def __init__(self):
        self._metrics = SessionMetrics()
        self._log_entries: list[LogEntry] = []
        self._max_log_entries = 100  # 最大日志条目数

    def handle_progress_event(self, event: ProgressEvent):
        """处理 SDK ProgressEvent，更新指标

        Args:
            event: SDK 发出的进度事件
        """
        # 根据 event.type 更新对应指标
        if event.type == ProgressEventType.LLM_CALL:
            self._metrics.llm_call_start = time.time()
            self._add_log("llm_call", "LLM 调用")

        elif event.type == ProgressEventType.LLM_RESPONSE:
            if self._metrics.llm_call_start:
                duration = (time.time() - self._metrics.llm_call_start) * 1000
                self._metrics.total_llm_duration_ms += duration
            self._add_log("llm_response", f"响应 ({duration:.0f}ms)")

        elif event.type == ProgressEventType.TOOL_CALL:
            self._metrics.tool_calls += 1
            tool_name = event.data.get("tool", "unknown")
            self._add_log("tool_call", f"工具调用: {tool_name}")

        elif event.type == ProgressEventType.TOOL_RESULT:
            success = event.data.get("success", True)
            if success:
                self._metrics.tool_success += 1
            else:
                self._metrics.tool_errors += 1
            self._add_log("tool_result", f"工具结果: {'成功' if success else '失败'}")

        elif event.type == ProgressEventType.ITERATION:
            self._metrics.iterations += 1
            iteration = event.data.get("iteration", 0)
            self._add_log("iteration", f"迭代 {iteration}")

        elif event.type == ProgressEventType.TOKEN_USAGE:
            input_tokens = event.data.get("input_tokens", 0)
            output_tokens = event.data.get("output_tokens", 0)
            self._metrics.input_tokens += input_tokens
            self._metrics.output_tokens += output_tokens
            self._metrics.update_cost()
            # 更新历史记录
            self._metrics.token_history.append(input_tokens + output_tokens)

        self.metrics_updated.emit()

    def get_metrics(self) -> SessionMetrics:
        """获取当前指标"""
        return self._metrics

    def get_log_entries(self) -> list[LogEntry]:
        """获取所有日志条目"""
        return self._log_entries

    def reset_metrics(self):
        """重置指标（新会话时调用）"""
        self._metrics.reset()
        self._log_entries.clear()
        self.metrics_updated.emit()
```

### 与 ChatController 集成

```python
# MainWindow 中连接回调
self.chat_controller.set_progress_callback(
    self.monitoring_controller.handle_progress_event
)
```

### 成本估算

成本估算基于主流 LLM 提供商的定价：

```python
def update_cost(self, input_cost_per_1m: float = 3.0, output_cost_per_1m: float = 15.0):
    """
    更新成本估算

    Args:
        input_cost_per_1m: 每 1M input token 的成本（美元）
        output_cost_per_1m: 每 1M output token 的成本（美元）

    默认使用 Claude Sonnet 4 定价: $3/$15 per 1M tokens
    """
    self.cost_usd = (
        self.input_tokens * input_cost_per_1m / 1_000_000 +
        self.output_tokens * output_cost_per_1m / 1_000_000
    )
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
self.schedule_controller = ScheduleController()  # 排程

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

## 下一步

- [01-overview.md](./01-overview.md) - 了解客户端整体架构
- [02-ui-components.md](./02-ui-components.md) - 了解 UI 组件设计（含 SchedulePanel）
- [04-configuration.md](./04-configuration.md) - 了解配置管理（含 schedules.json）
