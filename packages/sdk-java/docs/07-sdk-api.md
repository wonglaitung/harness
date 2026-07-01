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
    RoutingConfig,  # CPU Router 配置

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
    EmbeddedLlamaClient,  # 嵌入式 Llama 客户端
    RoutingLLMClient,     # 路由 LLM 客户端

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
    ConfirmationHook,
    ConfirmationResult,
    get_trust_key,

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

    # Loop Engineering (P0)
    GoalConfig,
    GoalResult,
    GoalStatus,
    GoalVerifier,
    GoalLoop,
    VerificationMethod,
    VerificationRecord,
    VerificationResult,

    # Automation (P0 - Phase 2)
    Automation,
    AutomationConfig,
    AutomationResult,
    AutomationStatus,

    # Trigger System (P0 - Phase 2)
    Trigger,
    CronTrigger,
    IntervalTrigger,
    TriggerManager,
    TriggerType,
    TriggerState,
    TriggerEvent,
    TriggerAction,
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

#### run_sync() - 同步执行

```python
def run_sync(
    self,
    prompt: str,
    session_id: str | None = None,
    **kwargs,
) -> LoopResult:
    """同步版本的 run()

    注意：不能在 async 上下文中调用。如果需要异步执行，使用 await agent.run()
    """
```

**事件循环检测**：使用语义化 API 检测运行中的事件循环：

```python
# 内部实现
try:
    asyncio.get_running_loop()
except RuntimeError:
    # 无运行中的循环 → 安全执行
    return asyncio.run(self.run(...))
else:
    # 有运行中的循环 → 禁止同步调用
    raise RuntimeError("run_sync() cannot be called from async context")
```

**注意**：不要依赖字符串匹配检测事件循环（如检查异常消息），这在不同 Python 版本中可能不稳定。

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

#### run_goal() - 目标驱动执行

```python
async def run_goal(
    self,
    goal: str | GoalConfig,          # 目标描述或配置
    custom_verifier: Callable | None = None,  # 自定义验证函数
    max_iterations: int = 50,        # 最大迭代次数
    max_context_resets: int = 5,     # 最大上下文重置次数
    timeout_seconds: int = 3600,     # 超时时间（秒）
    workspace_dir: str = ".",        # 工作目录
    **kwargs,                        # 其他 GoalConfig 选项
) -> GoalResult:
    """目标驱动执行：Agent 自主运行直到目标达成
    
    示例：
        result = await agent.run_goal("修复所有类型错误")
        if result.status == GoalStatus.ACHIEVED:
            print(f"目标达成，共 {result.total_iterations} 轮迭代")
    """
```

详见 [15-loop-engineering.md](./15-loop-engineering.md)。

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
def load_skills_from_dir(self, directory: Path) -> int:
    """从指定目录加载技能

    Args:
        directory: 包含技能文件的目录路径

    Returns:
        加载的技能数量
    """

def activate_skill(self, skill_name: str) -> bool:
    """激活指定技能

    激活的技能会在后续的 run() 调用中被注入到 system prompt。

    Args:
        skill_name: 技能名称

    Returns:
        True 如果激活成功，False 如果技能不存在
    """

def deactivate_skill(self, skill_name: str) -> bool:
    """停用指定技能

    Args:
        skill_name: 技能名称

    Returns:
        True 如果停用成功，False 如果技能未激活
    """

def get_matching_skills(self, user_input: str) -> list:
    """获取匹配用户输入的技能

    根据技能定义的 triggers（keywords/patterns）匹配用户输入。

    Args:
        user_input: 用户输入文本

    Returns:
        匹配的技能列表
    """
```

#### 技能自动注入

`AgentHarness.run()` 会自动将匹配的技能注入到 system prompt：

```python
from harness import AgentHarness

agent = AgentHarness(api_key="...")

# 技能自动匹配和注入
# 如果用户输入匹配某个技能的 triggers，该技能内容会被注入到 system prompt
result = await agent.run("将 README.md 转换为 Word 文档")

# 手动激活技能（即使不匹配 triggers 也会注入）
agent.activate_skill("code-review")
result = await agent.run("检查这段代码")
```

#### 完整示例

```python
from pathlib import Path
from harness import AgentHarness

agent = AgentHarness(api_key="...")

# 加载自定义技能目录
agent.load_skills_from_dir(Path(".harness/skills"))

# 查看匹配的技能
matching = agent.get_matching_skills("review this code")
print(f"匹配的技能: {[s.name for s in matching]}")

# 手动激活技能
agent.activate_skill("security-audit")

# 运行（技能会自动注入）
result = await agent.run("检查安全问题")

# 停用技能
agent.deactivate_skill("security-audit")
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

    # 兼容性配置
    tool_result_role: str = "tool"   # 工具结果角色："tool" (原生) 或 "user" (兼容模式)

    # Agent Loop 配置
    max_iterations: int = 10         # 最大迭代次数（业界标准：OpenAI Agents SDK: 10, LangChain: 10-15）
    max_input_tokens: int = 100000

    # 成本控制
    max_cost_per_run: float = 10.0   # USD
    max_tokens_per_run: int = 1000000

    # 步骤预算控制（限制迭代和工具调用次数）
    step_budget: StepBudgetConfig | None = None

    # 记忆配置
    memory_dir: str = ".harness/memory"
    memory_md_path: Path | None = None  # 全局 MEMORY.md 文件路径
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

### step_budget 步骤预算控制

使用 `StepBudgetConfig` 限制单次任务的迭代次数和工具调用次数，防止模型过度探索。

```python
from harness.sdk.config import HarnessConfig, StepBudgetConfig

config = HarnessConfig(
    max_iterations=3,  # 最大迭代次数
    step_budget=StepBudgetConfig(
        max_iterations_per_task=3,     # 任务最大迭代次数
        max_tool_calls_per_step=5,     # 单次 LLM 响应最大工具调用数
        max_tool_calls_per_task=10,    # 任务最大工具调用总数
        action_on_exceed="stop",        # 超限时的动作："stop" | "warn" | "throttle"
    ),
)

agent = AgentHarness(config=config, tools=[...])
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `max_iterations_per_task` | int | 50 | 任务最大迭代次数 |
| `max_tool_calls_per_step` | int | 10 | 单次 LLM 响应最大工具调用数 |
| `max_tool_calls_per_task` | int | 200 | 任务最大工具调用总数 |
| `warning_threshold` | float | 0.8 | 触发警告的阈值比例 |
| `critical_threshold` | float | 0.95 | 触发严重警告的阈值比例 |
| `action_on_exceed` | str | "stop" | 超限时的动作："stop", "warn", "throttle" |

#### 推荐值

| 任务类型 | max_iterations | max_tool_calls_per_step | max_tool_calls_per_task |
|---------|----------------|------------------------|------------------------|
| 简单任务（读文件、回答问题） | 2-3 | 2-3 | 5 |
| 中等任务（代码分析、多步推理） | 5-7 | 5 | 10-15 |
| 复杂任务（代码生成、研究） | 10-15 | 10 | 50-100 |

### tool_result_role 兼容模式

Anthropic API 要求工具结果以特定格式发送：`role: "user"` + `tool_result` blocks。SDK 内部使用 `role: "tool"` 作为抽象，在发送到 API 前自动转换。

某些代理 API（如 OpenAI 格式的 proxy）不支持 `tool_result` blocks。使用 `tool_result_role="user"` 可将工具结果转换为普通用户消息。

#### 配置示例

```python
# 原生 Anthropic API（默认）- 使用 tool_result blocks
config = HarnessConfig(tool_result_role="tool")

# 兼容模式 - 适用于不支持 tool_result blocks 的 proxy API
config = HarnessConfig(
    tool_result_role="user",
    base_url="https://your-proxy-api.com/v1",
)

agent = AgentHarness(config=config)
```

#### 消息格式对比

**原生模式 (`tool_result_role="tool"`)**：
```python
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_123",
            "content": "文件内容..."
        }
    ]
}
```

**兼容模式 (`tool_result_role="user"`)**：
```python
{
    "role": "user",
    "content": "[TOOL RESULT - read_file]\nTool call ID: toolu_123...\nStatus: SUCCESS\n\n文件内容..."
}
```

兼容模式会包含工具名称和调用 ID，帮助模型识别这是哪个工具的返回结果。

#### 注意事项

- OpenAI provider 不需要此设置（直接使用 `role: "tool"`）
- 仅 Anthropic provider 需要配置此项
- 如果代理 API 支持 `tool_result` blocks，优先使用原生模式 (`tool_result_role="tool"`)

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

支持所有 OpenAI 兼容 API（DeepSeek、硅基流动、本地 vLLM 等）。

```python
from harness.llm.openai import OpenAIClient

client = OpenAIClient(
    api_key="sk-...",
    model="gpt-4o",
    base_url="https://api.openai.com/v1",  # 可自定义
)
```

#### 第三方 API 兼容性

OpenAIClient 已处理部分第三方 API 的非标准响应：

```python
# 自动处理非标准错误响应
# 某些 API 在错误时返回字符串而非标准响应对象
if isinstance(response, str):
    raise ValueError(f"API returned non-standard response: {response[:200]}")
```

**常见第三方 API**：

| 提供者 | base_url | 说明 |
|-------|----------|------|
| DeepSeek | `https://api.deepseek.com/v1` | ~0.01元/千token |
| 硅基流动 | `https://api.siliconflow.cn/v1` | 多模型支持 |
| 本地 vLLM | `http://localhost:8000/v1` | 本地推理 |
| 本地 Ollama | `http://localhost:11434/v1` | 本地推理 |

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `api_key` | str | 必填 | API Key |
| `model` | str | 必填 | 模型名称 |
| `base_url` | str | OpenAI URL | API 基础 URL |
| `max_tokens` | int | 8192 | 最大输出 token |
| `temperature` | float | 1.0 | 生成温度 |
| `timeout` | float | 120.0 | 请求超时（秒） |

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

## CPU Router（成本优化的 LLM 路由）

CPU Router 使用轻量级 CPU 模型（如 Qwen2.5-1.5B）作为路由器，根据请求复杂度路由到不同的下游模型，实现成本优化。

### 架构

```
User Request → Router (CPU) → high/low label → Downstream LLM
```

### RoutingConfig

```python
from harness.sdk.config import RoutingConfig

class RoutingConfig:
    # 下游模型配置（高性能模型）
    high_model: str = ""              # 模型名称
    high_provider: str = "auto"       # "auto" 自动检测
    high_api_key: str | None = None   # 可选，覆盖全局 api_key
    high_base_url: str | None = None  # 可选，覆盖全局 base_url
    high_description: str = "高级模型，适合复杂任务"

    # 下游模型配置（低成本模型）
    low_model: str = ""
    low_provider: str = "auto"
    low_api_key: str | None = None
    low_base_url: str | None = None
    low_description: str = "基础模型，适合简单任务"

    # 路由器配置（二选一）
    router_model_path: str | None = None  # 嵌入式：GGUF 文件路径
    router_url: str | None = None         # HTTP：llama-server URL
    router_context_window: int | str = "auto"  # 上下文大小

    # 路由行为
    default_route: Literal["high", "low"] = "high"  # 路由失败时的默认路由
    router_timeout: float = 0.2                     # 路由超时（秒）
    history_window: int = 5                         # 考虑的历史消息数

    # 自定义路由 prompt
    route_prompt_template: str | None = None
```

### 使用示例

#### 基础配置

```python
from harness import AgentHarness
from harness.sdk.config import RoutingConfig

agent = AgentHarness(
    routing=RoutingConfig(
        high_model="gpt-4o",
        low_model="gpt-4o-mini",
        router_model_path="models/qwen2.5-1.5b.gguf",
    ),
    tools=[ReadTool()],
)
```

#### 自动检测 provider

```python
# provider 自动检测（复用 model_presets.py）
routing = RoutingConfig(
    high_model="claude-sonnet-4-6",  # 自动检测 → anthropic
    low_model="qwen-plus",           # 自动检测 → openai
    router_model_path="models/qwen3.5-0.8b.gguf",
)
```

#### 不同服务商

```python
routing = RoutingConfig(
    high_model="gpt-4o",
    high_api_key="sk-openai-xxx",
    low_model="deepseek-chat",
    low_api_key="sk-deepseek-xxx",
    low_base_url="https://api.deepseek.com/v1",
    router_model_path="models/qwen3.5-0.8b.gguf",
)
```

### EmbeddedLlamaClient

嵌入式 Llama 客户端，使用 llama-cpp-python 加载 GGUF 模型。

```python
from harness.llm.llama_cpp import EmbeddedLlamaClient

client = EmbeddedLlamaClient(
    model_path="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    context_window="auto",  # 从文件名推断
    n_gpu_layers=0,         # 0 = CPU only
)
```

#### context_window 自动推断

从 GGUF 文件名推断模型名称并设置上下文大小：

| 文件名 | 推断模型名 | 默认 context_window |
|--------|-----------|-------------------|
| `qwen3.5-0.8b-instruct-q4_k_m.gguf` | `qwen3.5-0.8b` | 2048（路由任务足够） |
| `qwen2.5-1.5b-chat-q5_k_m.gguf` | `qwen2.5-1.5b` | 2048 |

未知模型默认使用 2048，足够路由任务使用。

### RoutingLLMClient

路由 LLM 客户端，实现请求路由逻辑。

```python
from harness.llm.routing import RoutingLLMClient
from harness.sdk.config import RoutingConfig

config = RoutingConfig(
    high_model="gpt-4o",
    low_model="gpt-4o-mini",
    router_model_path="models/qwen2.5-1.5b.gguf",
)

client = RoutingLLMClient(
    config=config,
    high_client=OpenAIClient(model="gpt-4o"),
    low_client=OpenAIClient(model="gpt-4o-mini"),
)

response = await client.call(messages)
```

### 路由判断逻辑

默认路由判断标准：

| 判断条件 | 路由目标 |
|---------|---------|
| 需要多步推理 | high |
| 需要调用多个工具 | high |
| 需要代码生成或修改 | high |
| 需要深度分析或报告 | high |
| 简单问答、查询、翻译 | low |

**重要**：当不确定时，选择 high。宁可浪费也不要牺牲质量。

### 进度事件

路由决策会触发 `ProgressEventType.ROUTER_DECISION` 事件：

```python
from harness import AgentHarness, ProgressEvent, ProgressEventType

def on_progress(event: ProgressEvent):
    if event.type == ProgressEventType.ROUTER_DECISION:
        print(f"路由到: {event.data['route']}")
        print(f"目标模型: {event.data['target_model']}")
        print(f"路由延迟: {event.data['router_latency_ms']:.1f}ms")

agent = AgentHarness(routing=routing)
result = await agent.run("帮我分析这段代码", on_progress=on_progress)
```

### 依赖安装

```bash
# 安装 llama-cpp-python（嵌入式模式）
pip install llama-cpp-python

# 或安装预编译版本（推荐）
# macOS (Apple Silicon)
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

# Linux (CUDA)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
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

### GoalStatus

```python
from harness.loop import GoalStatus

class GoalStatus(Enum):
    ACHIEVED = "achieved"               # 目标达成
    TIMEOUT = "timeout"                 # 超时
    MAX_ITERATIONS = "max_iterations"   # 达到最大迭代
    MAX_RESETS = "max_resets"           # 达到最大重置次数
    ERROR = "error"                     # Agent 执行错误
    VERIFIER_FAULT = "verifier_fault"   # 验证器故障
    CANCELLED = "cancelled"             # 用户取消
```

### GoalConfig

```python
from harness.loop import GoalConfig

@dataclass
class GoalConfig:
    description: str                    # 目标描述
    session_id: str | None = None       # 会话 ID（用于对话连续性）
    success_criteria: str | None = None # 成功标准
    workspace_dir: str = "."            # 工作目录
    max_iterations: int = 50            # 最大迭代次数
    max_context_resets: int = 5         # 最大上下文重置次数
    timeout_seconds: int = 3600         # 超时时间（秒）
    custom_verifier: Callable | None = None  # 自定义验证函数
    max_tokens: int | None = None       # 最大 token 数
    max_cost_usd: float | None = None   # 最大成本（美元）
```

### GoalResult

```python
from harness.loop import GoalResult

@dataclass
class GoalResult:
    goal: str                           # 目标描述
    status: GoalStatus                  # 执行状态
    total_iterations: int               # 总迭代次数
    context_resets: int                 # 上下文重置次数
    total_tokens: TokenUsage            # Token 使用量
    duration_seconds: float             # 执行时长
    final_response: str                 # 最终响应
    verification_log: list[VerificationRecord]  # 验证日志
    error: str | None = None            # 错误详情
```

详见 [15-loop-engineering.md](./15-loop-engineering.md)。

## Automation API

Automation 是 Loop Engineering Phase 2 的核心 API，整合 Trigger + GoalConfig 实现自动化执行。

### Automation

```python
from harness.loop import Automation, AutomationStatus

# 创建定时任务
automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",           # cron 表达式：每天 9:00
    goal="生成每日报告并发送到 Slack",
    skills=["report-generation"],
)

# 创建间隔任务
health_check = Automation(
    name="health-check",
    interval_seconds=300,           # 每 5 分钟
    goal="检查系统健康状态",
)

# 启动
await automation.start(agent)

# 查看状态
print(f"状态: {automation.status}")  # RUNNING

# 停止
await automation.stop()
```

### AutomationConfig

```python
from harness.loop import AutomationConfig

@dataclass
class AutomationConfig:
    name: str                              # 自动化名称
    goal: str                              # 目标描述

    # 触发方式（三选一）
    schedule: str | None = None            # cron 表达式
    interval_seconds: int | None = None    # 间隔秒数
    trigger: Trigger | None = None         # 自定义 Trigger

    # Goal 配置
    workspace_dir: str = "."
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None

    # 输出配置
    skills: list[str] = field(default_factory=list)
```

### AutomationStatus

```python
class AutomationStatus(Enum):
    PENDING = "pending"     # 等待启动
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 已暂停
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误状态
```

### AutomationResult

```python
@dataclass
class AutomationResult:
    automation_name: str
    status: AutomationStatus
    goal_result: GoalResult | None = None
    last_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0
    error_message: str | None = None
```

详见 [06-triggers.md](./06-triggers.md)。

## Trigger System API

Trigger System 提供触发器基础设施，支持时间、事件驱动的自动化执行。

### CronTrigger

```python
from harness.triggers import CronTrigger, TriggerAction

trigger = CronTrigger(
    schedule="0 9 * * *",  # 每天 9:00
    action=TriggerAction(
        goal="生成每日报告",
        skills=["report-generation"],
    ),
    timezone="Asia/Shanghai",
    jitter_seconds=60,     # 添加随机延迟避免同时触发
)

# 查看下次运行时间
next_runs = trigger.get_next_runs(5)
for run_time in next_runs:
    print(f"下次运行: {run_time}")

# 启动
await trigger.start(callback=my_callback)

# 停止
await trigger.stop()
```

### IntervalTrigger

```python
from harness.triggers import IntervalTrigger

trigger = IntervalTrigger(
    interval_seconds=300,  # 每 5 分钟
    action=TriggerAction(
        goal="检查系统健康状态",
    ),
    start_immediately=False,  # 是否立即触发第一次
)

# 最小间隔为 1 秒
# trigger = IntervalTrigger(interval_seconds=0.1)  # ValueError!
```

### TriggerAction

```python
from harness.triggers import TriggerAction, TriggerEvent

action = TriggerAction(
    goal="修复所有类型错误",           # 目标描述
    workspace_dir=".",                # 工作目录
    max_iterations=50,                # 最大迭代
    timeout_seconds=3600,             # 超时时间
    custom_verifier=None,             # 自定义验证器
    skills=["typescript"],            # 激活的技能
)

# 转换为 GoalConfig
event = TriggerEvent(trigger_type=TriggerType.CRON, trigger_id="trigger-1")
goal_config = action.to_goal_config(event)
```

### TriggerManager

```python
from harness.triggers import TriggerManager, TriggerType
from harness import AgentHarness

agent = AgentHarness()
manager = TriggerManager(agent)

# 注册触发器
trigger_id = manager.register(
    trigger=CronTrigger(schedule="0 9 * * *", action=action),
    enabled=True,
)

# 列出所有触发器
triggers = manager.list_triggers()
for t in triggers:
    print(f"ID: {t['id']}, Type: {t['type']}, Enabled: {t['enabled']}")

# 启动所有触发器
await manager.start()

# 停止所有触发器
await manager.stop()

# 注销触发器
manager.unregister(trigger_id)
```

### TriggerType & TriggerState

```python
from harness.triggers import TriggerType, TriggerState

class TriggerType(Enum):
    CRON = "cron"           # 定时触发
    INTERVAL = "interval"   # 间隔触发
    WEBHOOK = "webhook"     # HTTP webhook
    HEARTBEAT = "heartbeat" # 心跳
    FILE_WATCH = "file_watch"  # 文件变化
    EVENT = "event"         # 事件总线

class TriggerState(Enum):
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 已暂停
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误
```

详见 [06-triggers.md](./06-triggers.md)。

## Service 模块 (Spring Cloud 集成)

`harness.service` 模块提供 FastAPI 服务包装，用于 Spring Cloud 微服务集成。

### 安装

```bash
# 基础服务
pip install harness-sdk[service]

# Prometheus 指标
pip install harness-sdk[prometheus]

# Redis 分布式存储
pip install harness-sdk[redis]

# Nacos 服务发现
pip install harness-sdk[nacos]
```

### 快速启动

```python
from harness.service import app

# 使用 uvicorn 运行
# uvicorn harness.service:app --port 8000
```

### FastAPI 应用

```python
from harness.service import app

# 可用端点：
# GET  /health              - 健康检查
# GET  /metrics             - Prometheus 指标
# POST /api/run             - 同步执行 Agent
# GET  /api/sessions/{id}   - 获取会话
# DELETE /api/sessions/{id} - 清除会话
# WebSocket /ws/run         - 流式执行
```

### TracingMiddleware

从 Spring Cloud Gateway 提取 W3C TraceContext：

```python
from harness.service import TracingMiddleware
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(TracingMiddleware)
```

**支持的 Header 格式**：
- `traceparent` (W3C TraceContext)
- `X-B3-TraceId` (Zipkin/Sleuth)
- `X-Trace-Id` (自定义)

### MetricsCollector

Prometheus 指标收集器：

```python
from harness.service import MetricsCollector, MetricsConfig, get_metrics_collector

# 使用全局收集器
collector = get_metrics_collector()
collector.setup()

# 记录指标
collector.record_iteration()
collector.record_tool_call("bash", success=True, duration_seconds=0.5)
collector.record_token_usage(usage)

# 导出 Prometheus 格式
metrics_data = collector.export()
```

**导出的指标**：

| 指标名 | 类型 | 说明 |
|-------|------|------|
| `harness_loop_iterations_total` | Counter | 总循环迭代次数 |
| `harness_tool_calls_total` | Counter | 工具调用次数 |
| `harness_llm_tokens_total` | Counter | Token 使用量 |
| `harness_session_duration_seconds` | Histogram | 会话持续时间 |
| `harness_active_sessions` | Gauge | 当前活跃会话数 |

### RedisSessionStore

分布式会话存储：

```python
from harness.service import RedisSessionStore, RedisSessionConfig

# 创建存储
store = RedisSessionStore("redis://localhost:6379")

# 或使用配置对象
config = RedisSessionConfig(
    redis_url="redis://localhost:6379",
    key_prefix="harness:session",
    ttl_seconds=3600,
)
store = RedisSessionStore(config=config)

# 操作
await store.save(session)
session = await store.load("session-123")
await store.delete("session-123")
```

**特点**：
- JSON 序列化（非 pickle），跨语言兼容
- Schema 版本管理
- TTL 自动清理

### RedisDistributedLock

分布式锁：

```python
from harness.service import RedisDistributedLock

lock = RedisDistributedLock("redis://localhost:6379")

# 获取锁
token = await lock.acquire("my-resource", timeout=30)
if token:
    try:
        # 执行需要锁保护的操作
        pass
    finally:
        await lock.release("my-resource", token)
```

### 服务发现

```python
from harness.service import (
    NacosServiceRegistry,
    EurekaServiceRegistry,
    ServiceInstance,
    get_service_instance,
    get_pod_ip,
)

# 创建服务实例（自动检测 IP）
instance = get_service_instance("harness-agent", 8000)

# Nacos 注册
registry = NacosServiceRegistry("nacos:8848")
await registry.register(instance)
await registry.deregister(instance)

# Eureka 注册
registry = EurekaServiceRegistry("http://eureka:8761")
await registry.register(instance)
```

### 错误处理

统一错误响应格式：

```python
from harness.service import ErrorCode, create_error_response

# 创建错误响应
error = create_error_response(
    ErrorCode.INVALID_INPUT,
    "Invalid parameter value",
    trace_id="abc123",
)

# 返回 JSON
# {
#     "errorCode": "AGENT_400_001",
#     "errorMessage": "Invalid parameter value",
#     "traceId": "abc123",
#     "timestamp": "2026-06-16T10:00:00Z"
# }
```

**错误码定义**：

| 错误码 | HTTP 状态 | 说明 |
|-------|----------|------|
| `AGENT_400_001` | 400 | 输入参数无效 |
| `AGENT_401_001` | 401 | 未授权 |
| `AGENT_403_001` | 403 | 禁止访问 |
| `AGENT_404_001` | 404 | 资源不存在 |
| `AGENT_500_001` | 500 | 内部错误 |
| `AGENT_502_001` | 502 | LLM 服务错误 |
| `AGENT_502_002` | 502 | 工具执行错误 |
| `AGENT_400_002` | 400 | 预算超限 |
| `AGENT_400_003` | 400 | 迭代次数超限 |
| `AGENT_400_004` | 400 | 检测到死循环 |

### 可选依赖状态

运行时检测可选依赖是否可用：

```python
from harness.service import (
    PROMETHEUS_AVAILABLE,  # prometheus-client
    REDIS_AVAILABLE,       # redis
    NACOS_AVAILABLE,       # nacos-sdk-python
    EUREKA_AVAILABLE,      # 始终 True (HTTP API)
)
```

## 下一步

- [02-agent-loop.md](./02-agent-loop.md) - 了解 Agent Loop
- [06-triggers.md](./06-triggers.md) - 了解 Trigger System
- [08-security.md](./08-security.md) - 了解安全设计
- [09-mcp-integration.md](./09-mcp-integration.md) - MCP 协议集成
- [15-loop-engineering.md](./15-loop-engineering.md) - Loop Engineering 完整指南
