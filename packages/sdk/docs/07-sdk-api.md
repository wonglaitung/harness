# 07 - SDK API 参考

## 概述

本文档提供 Harness SDK 的完整 API 参考。SDK 以 `harness` 包名发布，所有公共 API 通过 `harness/__init__.py` 导出。

## 公共 API 导出

```python
from harness import (
    # 核心 SDK
    AgentHarness,
    HarnessConfig,
    SecurityConfig,
    CostControlConfig,
    ObservabilityConfig,
    StorageConfig,

    # 模型预设
    ModelPreset,
    MODEL_PRESETS,
    CONTEXT_LEVELS,
    DEFAULT_PRESET,
    get_model_preset,
    parse_context_window,
    get_default_output_tokens,

    # LLM
    LLMClient,
    LLMConfig,
    AnthropicClient,
    OpenAIClient,
    MockLLMClient,

    # 内置工具
    ReadTool,
    WriteTool,
    EditTool,
    GlobTool,
    GrepTool,
    BashTool,
    WebSearchTool,
    WebFetchTool,

    # 核心类型
    Message,
    Session,
    ToolCall,
    ToolResult,
    TokenUsage,
    LoopResult,
    LoopSnapshot,
    LoopState,

    # 成本控制
    CostConfig,
    CostController,
    CostStorage,
    InMemoryCostStorage,
    BudgetStatus,
    UserBudgetStatus,
    GlobalBudgetStatus,
    UserUsage,
    BudgetExceededError,
    UserBudgetExceededError,
    GlobalBudgetExceededError,

    # 进度事件
    ProgressEvent,
    ProgressEventType,
    ProgressCallback,
    ProgressFormatter,
    create_progress_handler,

    # 技能
    Skill,
    SkillTrigger,
    SkillTools,
    SkillRegistry,
    SkillInjector,
    SkillLoader,
    InjectionConfig,
    ProgressiveSkillLoader,
    SkillMetadata,
    LoadingLevel,

    # 安全
    SandboxExecutor,
    LightweightSandbox,
    InputValidator,
    PromptInjectionDetector,
    AuditLogger,
    AuditLogEntry,
    ResultSanitizer,
    SanitizationRule,

    # MCP
    MCPTransport,
    StdioTransport,
    HTTPTransport,
    MCPClient,
    MCPTool,
    MCPServerInfo,
    MCPManager,
    MCPServerConfig,
    MCPToolWrapper,

    # 会话存储
    SessionStore,
    FileSessionStore,
    SQLiteSessionStore,
    AsyncSQLiteSessionStore,

    # 可观测性
    ObservabilityManager,
    ObservabilityConfig,
    setup_observability,

    # 生命周期钩子 (P0)
    HookPoint,
    HookAction,
    HookContext,
    HookResult,
    LifecycleHook,
    HookManager,
    LoggingHook,
    AbortOnDangerousToolHook,
    MaxToolCallsHook,

    # 动态系统提示 (P0)
    SystemPromptSource,
    SystemPromptConfig,
    SystemPromptBuilder,
    discover_project_context,

    # Ralph Loop (P1)
    RalphLoopConfig,
    RalphLoopHook,

    # Sub-Agent 管理 (P1)
    SubAgentConfig,
    SubAgentStatus,
    SubAgentResult,
    SubAgentManager,

    # 自验证 (P2)
    SelfVerificationConfig,
    SelfVerificationHook,

    # MEMORY.md 标准 (P2)
    MemoryFileManager,
    MemoryEntry,
    MemoryCategory,
    MemorySource,
    MemorySections,
    create_default_memory,

    # 向量存储 (P2)
    VectorMemoryStore,
    VectorMemoryConfig,
    VectorSearchResult,
    SimpleInMemoryVectorStore,
    MockEmbeddingModel,
)
```

## AgentHarness

AgentHarness 是 SDK 的主入口，提供完整的 Agent 运行时。

### 构造函数

```python
class AgentHarness:
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",    # 模型名称
        api_key: str | None = None,           # API 密钥（或设置环境变量）
        provider: str = "anthropic",          # LLM 提供商 - "anthropic", "openai", 或 "custom"
        base_url: str | None = None,          # 自定义 API 端点（用于本地 LLM、Azure 等）
        tools: list[Tool] | None = None,      # 可用的工具列表
        config: HarnessConfig | None = None,  # 完整配置对象
        llm_client: LLMClient | None = None,  # 自定义 LLM 客户端实例（覆盖提供商检测）
        **kwargs,                             # 其他配置选项
    )
```

### Provider 自动检测

如果不指定 `provider`，SDK 根据 `model` 名称自动检测：

| model 前缀 | provider |
|------------|----------|
| `claude-*` | `anthropic` |
| `gpt-*`, `o1-*`, `o3-*` | `openai` |
| 其他 | `openai`（通过 `base_url` 使用兼容 API） |

### 核心方法

#### run() - 执行任务

```python
async def run(
    self,
    prompt: str,                     # 用户输入
    session_id: str | None = None,   # 会话 ID（用于对话连续性）
    on_progress: ProgressCallback | None = None, # 进度事件回调
    verbose: bool = False,           # 如果为 True，在控制台打印进度
    **kwargs,                        # 其他选项
) -> LoopResult:
    """执行 Agent 任务，返回 LoopResult"""
```

#### stream() - 流式执行

```python
async def stream(
    self,
    prompt: str,                     # 用户输入
    session_id: str | None = None,   # 会话 ID（用于对话连续性）
    on_chunk: Callable[[str], None] | None = None, # 每个文本块的回调
    on_progress: ProgressCallback | None = None, # 进度事件回调
    verbose: bool = False,           # 如果为 True，在控制台打印进度
) -> AsyncIterator[str]:
    """流式执行 Agent 任务，逐步返回内容
    
    注意：工具调用在内部处理，不会流式传输。
    """
```

#### tool() - 注册工具装饰器

```python
def tool(
    self,
    name: str | None = None,          # 工具名称（默认使用函数名）
    description: str | None = None,   # 工具描述（默认使用函数文档字符串）
) -> Callable:
    """装饰器：将函数注册为工具
    
    示例：
        @agent.tool(description="Say hello")
        def hello(name: str) -> str:
            return f"Hello, {name}!"
    """
```

#### 钩子注册说明

钩子通过继承 `LifecycleHook` 类并使用 `add_hook()` 方法注册：

```python
from harness.core.hooks import LifecycleHook, HookPoint, HookContext, HookResult

class MyHook(LifecycleHook):
    @property
    def hook_points(self):
        return [HookPoint.BEFORE_TOOL_EXECUTE]
    
    async def execute(self, ctx: HookContext) -> HookResult:
        # 钩子逻辑
        return HookResult.continue_()

# 注册钩子（使用公开 API）
agent.add_hook(MyHook())
```

#### add_hook() - 注册生命周期钩子

```python
def add_hook(
    self,
    hook: LifecycleHook,
    points: list[HookPoint] | None = None,
) -> None:
    """注册生命周期钩子

    钩子允许在关键执行点注入自定义逻辑：
    - LLM 调用前后
    - 工具执行前后
    - 错误发生时
    - 循环开始/结束时

    Args:
        hook: 钩子实例（LifecycleHook 子类）
        points: 指定钩子点（默认使用 hook.hook_points）
    """
```

#### remove_hook() - 移除生命周期钩子

```python
def remove_hook(self, hook: LifecycleHook) -> None:
    """移除已注册的生命周期钩子"""
```

#### create_snapshot() - 创建执行快照

```python
def create_snapshot(
    self,
    session_id: str | None = None,
    iteration: int = 0,
) -> LoopSnapshot:
    """创建当前循环状态的快照

    快照可用于保存进度并稍后恢复执行。

    Args:
        session_id: 会话 ID（None 则使用当前会话）
        iteration: 当前迭代次数

    Returns:
        LoopSnapshot 捕获当前状态

    Example:
        snapshot = agent.create_snapshot(session_id="my-session")
        snapshot_dict = snapshot.to_dict()  # 可序列化保存
    """
```

#### restore_from_snapshot() - 从快照恢复执行

```python
async def restore_from_snapshot(
    self,
    snapshot: LoopSnapshot,
    on_progress: ProgressCallback | None = None,
) -> LoopResult:
    """从快照恢复执行

    允许继续之前中断的执行。

    Args:
        snapshot: 要恢复的快照
        on_progress: 进度回调

    Returns:
        LoopResult 恢复执行的结果

    Example:
        # 从保存的快照恢复
        snapshot = LoopSnapshot.from_dict(saved_data)
        result = await agent.restore_from_snapshot(snapshot)
    """
```

#### register_tool() - 注册工具

```python
def register_tool(
    self,
    tool: Tool,
) -> None:
    """注册 Tool 实例"""
```

### MCP 方法

```python
def add_mcp_server(
    self,
    name: str,
    command: str | None = None,  # Stdio 传输
    url: str | None = None,       # HTTP 传输
    config: dict | None = None,   # 服务器配置
) -> None:
    """添加 MCP 服务器"""

def remove_mcp_server(self, name: str) -> None:
    """移除 MCP 服务器"""
```

### 技能方法

```python
def load_skill(self, path: str) -> None:
    """加载单个技能文件"""

def add_skill_dir(self, dir_path: str) -> None:
    """添加技能搜索目录"""
```

### 配置方法

```python
@classmethod
def from_config(cls, path: str) -> AgentHarness:
    """从 YAML 配置文件创建"""

@classmethod
def from_env(cls) -> AgentHarness:
    """从环境变量创建（HARNESS_* 前缀）"""
```

## HarnessConfig

```python
from harness.sdk.config import HarnessConfig

class HarnessConfig:
    # LLM 配置
    model: str = "claude-sonnet-4-6"
    provider: str | None = None      # 自动检测
    api_key: str | None = None
    base_url: str | None = None
    context_window: int = 200000     # 模型上下文窗口大小
    max_tokens: int = 4096           # 最大输出 token（0 = 自动）

    # Agent Loop 配置
    max_iterations: int = 50
    max_input_tokens: int = 100000

    # 成本控制
    max_cost_per_run: float = 10.0   # USD
    max_tokens_per_run: int = 1000000

    # 记忆配置
    memory_dir: str = ".harness/memory"
    vector_store: bool = False

    # 技能配置
    skill_dirs: list[str] = field(default_factory=list)

    # 安全配置
    sandbox_enabled: bool = True
    bash_timeout: int = 30000        # 毫秒
    bash_blacklist: list[str] = field(default_factory=lambda: [
        "rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:",
    ])

    # 模型预设
    model_presets: dict[str, dict] = field(default_factory=dict)
```

### 模型预设

```python
config = HarnessConfig(
    model_presets={
        "fast": {"model": "claude-haiku-4-5", "max_tokens": 2048},
        "standard": {"model": "claude-sonnet-4-6", "max_tokens": 4096},
        "powerful": {"model": "claude-opus-4-6", "max_tokens": 8192},
    }
)

agent = AgentHarness(config=config)
```

### max_tokens 自动模式

当 `max_tokens = 0` 时，SDK 根据模型自动设置：

| 模型 | max_tokens |
|------|------------|
| claude-opus-4-6 | 8192 |
| claude-sonnet-4-6 | 8192 |
| claude-haiku-4-5 | 8192 |
| gpt-4o | 4096 |
| gpt-4o-mini | 4096 |
| 其他 | 4096 |

### 从 YAML 加载

```yaml
# harness.yaml
model: claude-sonnet-4-6
max_iterations: 100
memory_dir: .harness/memory
vector_store: true
skill_dirs:
  - .harness/skills
sandbox_enabled: true
bash_timeout: 60000
```

```python
agent = AgentHarness.from_config("harness.yaml")
```

## LLM 客户端

### LLMClient 接口

```python
from harness.llm.base import LLMClient, LLMResponse

class LLMClient(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""

    @abstractmethod
    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """调用 LLM"""
```

### LLMResponse

```python
@dataclass
class LLMResponse:
    content: str | None             # 文本内容
    tool_calls: list[dict] | None   # 工具调用列表
    usage: TokenUsage               # token 使用统计
    stop_reason: str                # 停止原因
    raw: dict | None = None         # 原始响应
```

### TokenUsage

```python
@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
```

### AnthropicClient

```python
from harness.llm.anthropic import AnthropicClient

client = AnthropicClient(
    api_key="sk-ant-...",
    model="claude-sonnet-4-6",
)
```

### OpenAIClient

```python
from harness.llm.openai import OpenAIClient

client = OpenAIClient(
    api_key="sk-...",
    model="gpt-4o",
    base_url="https://api.openai.com/v1",  # 可自定义
)
```

### 自定义 LLM 客户端

```python
from harness.llm.base import LLMClient, LLMResponse
from harness import AgentHarness

class MyLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-model"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # 实现自定义 LLM 调用逻辑
        ...

# 直接传入
agent = AgentHarness(llm_client=MyLLM())
```

## 类型定义

### MessageRole

```python
class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

### LoopStatus

```python
class LoopStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED_MAX_ITERATIONS = "stopped_max_iterations"
    STOPPED_COST_LIMIT = "stopped_cost_limit"
    STOPPED_ERROR = "stopped_error"
    STOPPED_STUCK = "stopped_stuck"
    STOPPED_BY_HOOK = "stopped_by_hook"
```

### LoopResult

```python
@dataclass
class LoopResult:
    content: str                      # 最终文本内容
    tool_calls: list[ToolCallRecord]  # 工具调用记录
    total_tokens: int                 # 总 token 使用量
    total_cost: float                 # 总成本（USD）
    iterations: int                   # 实际循环次数
    stopped_reason: str               # 停止原因（LoopStatus 值）
```

### ToolCallRecord

```python
@dataclass
class ToolCallRecord:
    name: str               # 工具名称
    arguments: dict         # 调用参数
    result: str             # 执行结果
    error: str | None       # 错误信息
    duration_ms: int        # 执行耗时
```
