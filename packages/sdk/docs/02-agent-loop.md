# 02 - Agent Loop 详解

## 概述

Agent Loop 是 Harness 的核心执行引擎，实现了 ReAct（Reasoning + Acting）模式。它负责管理 LLM 交互循环、工具调用、上下文构建、安全检查和错误处理。

## 核心流程

### ReAct 循环

```
while not finished:
    1. 构建上下文（ContextBuilder 组装系统提示 + 记忆 + 技能）
    2. 调用 LLM
    3. 解析响应
    4. 如果有工具调用 → 执行工具 → 结果追加到消息 → 继续
    5. 如果完成 → 返回 LoopResult
```

### 循环保护机制

| 机制 | 配置字段 | 说明 |
|------|----------|------|
| **最大步数** | `max_iterations` (默认 10) | 限制循环次数（业界标准：OpenAI Agents SDK: 10, LangChain: 10-15） |
| **迭代提醒** | 内置 | 接近迭代上限时注入提示让模型优雅收尾 |
| **工具超时** | `timeout_per_tool` (默认 30.0s) | 每个工具调用的超时时间 |
| **熔断器** | `enable_circuit_breaker` (默认 True) | 相同工具+参数重复 3 次时中断 |
| **卡住检测** | `max_stuck_feedbacks` (默认 2) | 检测重复输出或无进展状态 |
| **成本控制** | `enable_cost_control` (默认 True) | 累计成本超限时中断 |
| **步骤预算** | `step_budget_config` | 限制单次 LLM 响应的工具调用数和任务总调用数 |
| **并行工具** | `enable_parallel_tools` (默认 True) | 启用并行工具调用 |
| **错误重试** | `retry_on_error` (默认 3) | API 错误自动重试次数 |

#### 迭代提醒机制

当接近迭代上限（剩余 2 步）时，Agent Loop 会自动注入提醒消息：

```python
# agent_loop.py 核心逻辑
remaining_steps = self.config.max_iterations - iteration
if remaining_steps <= 2 and iteration > 0:
    session.add_message(Message(
        role="user",
        content=f"[系统提示] 还有 {remaining_steps} 步达到迭代上限。请立即总结当前进展并给出最终回答。",
        metadata={"type": "remaining_steps_hint", "injected": True},
    ))
```

这使模型有机会在达到硬性限制前优雅地完成任务或给出当前进展摘要。

#### 达到迭代上限时的响应恢复

如果达到 `max_iterations`，Agent Loop 会尝试从 session 中提取最后的助手消息作为回复：

```python
# 从 session 中提取有意义的回复
final_response = None
for msg in reversed(session.messages):
    if msg.role == "assistant" and msg.content:
        final_response = msg.content
        break

return LoopResult(
    status=LoopState.ERROR,
    final_response=final_response,  # 尽可能提供回复
    error="Max iterations reached",
)
```

这确保即使模型没有主动给出最终回复，用户也能看到之前的助手消息。

## AgentLoop 类

```python
from harness.core.agent_loop import AgentLoop, LoopResult, LoopConfig
from harness.llm.base import LLMClient
from harness.tools.executor import ToolExecutor
from harness.memory.context_builder import ContextBuilder
from harness.memory.session_manager import SessionManager

class AgentLoop:
    def __init__(
        self,
        llm_client: LLMClient,           # LLM 客户端
        tool_executor: ToolExecutor,      # 工具执行器
        context_builder: ContextBuilder,  # 上下文构建器
        session_manager: SessionManager,  # 会话管理器
        config: LoopConfig | None = None, # 循环配置
    )

    async def run(
        self,
        messages: list[dict],
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
    ) -> LoopResult:
        """执行 Agent 循环，返回 LoopResult"""

### LoopConfig

Agent Loop 的配置通过 `LoopConfig` 类管理：

```python
from harness.core.agent_loop import LoopConfig

@dataclass
class LoopConfig:
    """Configuration for agent loop.

    Attributes:
        max_iterations: Maximum number of iterations (LLM calls).
            - Simple tasks (read files, answer questions): 2-3
            - Medium tasks (code analysis, multi-step reasoning): 5-7
            - Complex tasks (code generation, research): 10-15
            Default is 10 (industry standard: OpenAI Agents SDK, LangChain).
    """
    max_iterations: int = 10         # 业界标准（OpenAI Agents SDK: 10, LangChain: 10-15）
    timeout_per_tool: float = 30.0               # 每个工具调用的超时时间（秒）
    enable_parallel_tools: bool = True           # 是否启用并行工具调用
    retry_on_error: int = 3                      # 错误重试次数
    enable_progress: bool = True                 # 是否启用进度事件
    enable_circuit_breaker: bool = True          # 是否启用熔断器
    enable_cost_control: bool = True             # 是否启用成本控制
    cost_config: CostConfig | None = None        # 成本控制配置
    security_config: SecurityConfig | None = None # 安全配置
    working_directory: str | None = None         # 工具执行的工作目录

    # 卡住检测配置
    max_stuck_feedbacks: int = 2                 # 最大反馈注入尝试次数
    stuck_min_iterations: int = 3                # 卡住检测前的最小迭代次数
    stuck_consecutive_failures: int = 3          # 触发卡住检测的连续失败次数
    stuck_detector_config: StuckDetectorConfig | None = None  # 语义检测配置

    # 工具输出卸载配置 (Phase 24)
    offload_config: OffloadConfig | None = None  # 输出卸载配置
    enable_offload: bool = True                  # 是否启用输出卸载

    # 步骤预算配置 (Phase 25)
    step_budget_config: StepBudgetConfig | None = None  # 步骤预算配置
    enable_step_budget: bool = True              # 是否启用步骤预算控制
```

### LoopState

```python
from harness.types import LoopState

class LoopState(Enum):
    """Agent 循环状态机状态"""
    IDLE = "idle"                    # 空闲，等待输入
    BUILDING_CONTEXT = "building"    # 构建上下文
    CALLING_LLM = "calling"          # 调用 LLM
    PARSING_RESPONSE = "parsing"     # 解析响应
    EXECUTING_TOOLS = "executing"    # 执行工具
    COMPLETED = "completed"          # 完成
    ERROR = "error"                  # 错误状态
    INTERRUPTED = "interrupted"      # 被中断
    STUCK = "stuck"                  # 陷入停滞
```

### LoopResult

```python
from harness.types import LoopResult, LoopState, TokenUsage
from harness.memory.session import Session
from harness.types import Message

@dataclass
class LoopResult:
    status: LoopState                  # 循环状态
    session: Session                   # 当前会话
    messages: list[Message] = field(default_factory=list)  # 消息列表
    final_response: str | None = None  # 最终响应内容
    iterations: int = 0                # 实际循环次数
    error: str | None = None           # 错误信息（如果有）
    token_usage: TokenUsage = field(default_factory=TokenUsage)  # token 使用统计

    @property
    def content(self) -> str:
        """获取最终文本内容"""
        return self.final_response or ""
    
    @property
    def is_success(self) -> bool:
        """检查循环是否成功完成"""
        return self.status == LoopState.COMPLETED
```

## 消息处理流程

Agent Loop 在处理用户消息时遵循"Session 作为单一数据源"原则，确保消息在多轮迭代中不丢失。

### 核心原则

1. **Session 是单一数据源**：所有消息都存储在 `session.messages` 中
2. **消息持久化**：用户消息在第一次迭代时被持久化到 session
3. **ContextBuilder 只读取**：上下文构建器从 session 读取消息，不修改 session

### 消息流

```
┌──────────────────────────────────────────────────────────────────┐
│                        First Iteration                            │
│                                                                   │
│  用户输入 → session.add_message(Message(role="user", content))   │
│                          ↓                                        │
│           ContextBuilder.build(session) ← 从 session 读取         │
│                          ↓                                        │
│                    LLM 调用                                       │
│                          ↓                                        │
│           session.add_message(Message(role="assistant"))         │
│           session.add_message(Message(role="tool"))              │
├──────────────────────────────────────────────────────────────────┤
│                      Second Iteration                             │
│                                                                   │
│           ContextBuilder.build(session)                           │
│                          ↓                                        │
│           messages = [user, assistant, tool, tool]  ← 完整上下文  │
│                          ↓                                        │
│                    LLM 调用                                       │
└──────────────────────────────────────────────────────────────────┘
```

### 代码实现

```python
# agent_loop.py 核心逻辑
while iteration < self.config.max_iterations:
    # 第一次迭代时持久化用户消息
    if iteration == 0 and prompt:
        session.add_message(Message(role="user", content=prompt))
    
    # 从 session 构建上下文（包含所有历史消息）
    context = self.context.build(session)
    
    # 调用 LLM
    response = await self.llm.call(
        messages=context.messages,
        tools=tools,
        system=context.system_prompt,
    )
    
    # 添加 assistant 消息
    if response.content:
        session.add_message(Message(role="assistant", content=response.content))
    
    # 执行工具并添加 tool 消息
    if response.is_tool_use:
        tool_results = await self._execute_tools(response.tool_calls, session)
        for result in tool_results:
            session.add_message(Message(
                role="tool",
                content=result.content,
                metadata={"tool_call_id": result.tool_call_id, ...}
            ))
    
    iteration += 1
```

### 注意事项

- **不要临时添加消息**：所有消息都应该通过 `session.add_message()` 持久化
- **ContextBuilder 不修改 session**：上下文构建器只负责读取和窗口裁剪
- **工具结果也持久化**：tool message 同样存储在 session 中

## Lifecycle Hooks

Agent Loop 在关键执行点触发生命周期钩子，允许外部代码拦截、修改或注入行为。

### HookPoint 枚举

```python
from harness.types import HookPoint

class HookPoint(Enum):
    """
    Points in the agent loop where hooks can be triggered.
    
    Hooks allow custom logic to be injected at key points:
    - Before/after LLM calls
    - Before/after tool execution
    - On errors
    - On loop start/end
    - On exit attempts (for Ralph Loop)
    """
    BEFORE_LLM_CALL = "before_llm_call"        # LLM 调用前
    AFTER_LLM_CALL = "after_llm_call"          # LLM 调用后
    BEFORE_TOOL_EXECUTE = "before_tool_execute"  # 工具执行前
    AFTER_TOOL_EXECUTE = "after_tool_execute"    # 工具执行后
    ON_ERROR = "on_error"                      # 错误发生时
    ON_LOOP_START = "on_loop_start"            # 循环开始
    ON_LOOP_END = "on_loop_end"                # 循环结束
    ON_EXIT_ATTEMPT = "on_exit_attempt"        # 尝试退出时（Ralph Loop）
```

### HookContext

```python
from harness.types import HookContext

@dataclass
class HookContext:
    hook_point: HookPoint          # 当前钩子点
    session_id: str                # 当前会话 ID
    iteration: int = 0             # 当前迭代次数
    tool_name: str | None = None   # 工具名称（用于工具钩子）
    tool_args: dict[str, Any] | None = None  # 工具参数（用于 BEFORE_TOOL_EXECUTE）
    tool_result: ToolResult | None = None    # 工具结果（用于 AFTER_TOOL_EXECUTE）
    llm_response: LLMResponse | None = None  # LLM 响应（用于 AFTER_LLM_CALL）
    error: Exception | None = None           # 错误（用于 ON_ERROR）
    messages: list[Message] | None = None    # 当前消息（可选）
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加元数据
```

### 注册钩子

钩子通过继承 `LifecycleHook` 类并实现 `hook_points` 和 `execute` 方法来创建，然后通过 `agent.add_hook()` 注册。

```python
from harness import AgentHarness
from harness.core.hooks import LifecycleHook
from harness.types import HookPoint, HookContext, HookResult

# 创建自定义钩子
class MyPermissionHook(LifecycleHook):
    @property
    def hook_points(self) -> list[HookPoint]:
        # 订阅 BEFORE_TOOL_EXECUTE 钩子点
        return [HookPoint.BEFORE_TOOL_EXECUTE]
    
    async def execute(self, context: HookContext) -> HookResult:
        # 检查工具权限
        if context.tool_name == "bash":
            if self._is_dangerous(context.tool_args):
                # 阻止执行危险命令
                return HookResult.abort("Dangerous command blocked")
        return HookResult.continue_()
    
    def _is_dangerous(self, args: dict) -> bool:
        command = args.get("command", "")
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777"]
        return any(pattern in command for pattern in dangerous_patterns)

# 注册钩子到 Agent（使用公开 API）
agent = AgentHarness()
permission_hook = MyPermissionHook()
agent.add_hook(permission_hook)

# 或者使用内置钩子
from harness.core.hooks import LoggingHook, AbortOnDangerousToolHook, MaxToolCallsHook

# 添加日志钩子（记录所有钩子事件）
agent.add_hook(LoggingHook())

# 添加危险工具拦截钩子
agent.add_hook(AbortOnDangerousToolHook())

# 添加最大工具调用限制钩子
agent.add_hook(MaxToolCallsHook(tool_name="bash", max_calls=10))
```

### 钩子执行顺序

同一钩子点的多个处理器按注册顺序依次执行。每个处理器通过返回 `HookResult` 来控制后续行为：

| 动作 | 说明 |
|------|------|
| **CONTINUE** | 正常继续执行 |
| **ABORT** | 立即停止执行 |
| **RETRY** | 重试当前操作 |
| **INJECT_MESSAGE** | 向上下文注入消息 |
| **MODIFY_ARGS** | 修改工具参数（BEFORE_TOOL_EXECUTE 钩子） |
| **MODIFY_RESULT** | 修改工具结果（AFTER_TOOL_EXECUTE 钩子） |
| **REINJECT** | 清除上下文并重新注入提示（Ralph Loop 使用） |

### ON_EXIT_ATTEMPT 钩子

`ON_EXIT_ATTEMPT` 是特殊钩子，在循环准备退出时触发。可以用于：
- 阻止过早退出（要求 Agent 继续工作）
- 添加最终检查或验证
- 注入总结指令

```python
from harness.core.hooks import LifecycleHook
from harness.types import HookPoint, HookContext, HookResult, Message

class PreventEarlyExitHook(LifecycleHook):
    @property
    def hook_points(self) -> list[HookPoint]:
        return [HookPoint.ON_EXIT_ATTEMPT]
    
    async def execute(self, context: HookContext) -> HookResult:
        """如果任务未完成，阻止 Agent 退出"""
        if not self._is_task_complete(context):
            # 注入消息让 Agent 继续工作
            message = Message(role="user", content="任务尚未完成，请继续工作。")
            return HookResult.inject_message(message)
        return HookResult.continue_()
    
    def _is_task_complete(self, context: HookContext) -> bool:
        # 实现任务完成检测逻辑
        # 例如：检查消息中是否包含完成关键词
        if context.messages:
            last_message = context.messages[-1]
            if "task complete" in last_message.content.lower():
                return True
        return False

# 注册钩子
agent = AgentHarness()
agent.add_hook(PreventEarlyExitHook())
```

## Stuck Detection（卡住检测）

Agent Loop 内置卡住检测机制，采用两级检测策略：

### 检测策略

| 策略 | 说明 | 成本 |
|------|------|------|
| **空/错误检测** | 连续 N 次空结果或错误响应 | 零成本 |
| **语义检测** | 基于 embedding 的相似度检测，捕捉重复输出模式 | 需要模型 |

### 检测模式

| 模式 | 检测方法 |
|------|----------|
| **空结果** | 连续 N 次工具返回空内容 |
| **错误循环** | 连续 N 次工具返回错误 |
| **语义重复** | 连续 N 轮输出高度相似（相似度 ≥ 阈值） |

### 配置选项

```python
from harness.core.agent_loop import LoopConfig
from harness.core.stuck_detector import StuckDetectorConfig

# 基础配置（空/错误检测，零依赖）
config = LoopConfig(
    max_stuck_feedbacks=2,           # 最大反馈注入次数
    stuck_min_iterations=3,          # 最小迭代次数后开始检测
    stuck_consecutive_failures=3,    # 连续失败次数阈值
)

# 启用语义检测（需要安装依赖）
config = LoopConfig(
    stuck_detector_config=StuckDetectorConfig(
        enable_semantic=True,            # 启用语义检测
        similarity_threshold=0.92,       # 相似度阈值（0.0-1.0）
        consecutive_rounds=3,            # 连续相似轮数阈值
        window_size=6,                   # 对比窗口大小
        min_chars=30,                    # 最小文本长度
    ),
)
```

### 安装依赖

语义检测需要安装可选依赖：

```bash
pip install harness-ai[stuck]
```

默认使用 `bge-small-zh-v1.5` 模型（中文优化，约 100MB）。

### 检测后行为

检测到卡住状态后，Agent Loop 会：

1. **注入反馈消息**：提醒 Agent 尝试不同方法
2. **清除检测状态**：避免误判
3. **最终中断**：反馈次数耗尽后终止循环

### 反馈消息示例

```python
# 第一次检测到语义重复
"[循环检测] 检测到重复的输出模式（相似度 95%）。
你的方法似乎在原地打转，请尝试完全不同的策略。"

# 第二次检测（最后机会）
"[循环检测 - 最后机会] 重复模式仍在继续（相似度 93%）。
请立即承认无法继续或采用根本性不同的方法。"
```

### 自动降级

如果 `sentence-transformers` 未安装，语义检测自动禁用，退回空/错误检测。不会影响 Agent 正常运行。

## Ralph Loop（长任务循环）

Ralph Loop 是专为长时间运行任务设计的循环模式，解决"上下文焦虑"问题——当任务步骤过多时，LLM 倾向于草率完成。它通过 `RalphLoopHook` 实现，该钩子拦截退出尝试并在任务未真正完成时触发继续执行。

### RalphLoopHook

```python
from harness.core.hooks import LifecycleHook
from harness.core.ralph_loop import RalphLoopHook, RalphLoopConfig
from harness import AgentHarness

# 创建 Ralph Loop 钩子
config = RalphLoopConfig(
    max_loops=5,  # 最大继续循环次数
    task_complete_check=lambda response: "done" in response.lower(),  # 自定义完成检测
)
ralph_hook = RalphLoopHook(config)

# 注册到 Agent
agent = AgentHarness()
agent.add_hook(ralph_hook)

# 执行长任务 - Ralph Loop 会自动处理继续执行
result = await agent.run("重构整个认证模块，添加 OAuth2 支持")
```

### RalphLoopConfig

```python
@dataclass
class RalphLoopConfig:
    max_loops: int = 5                    # 最大继续循环次数
    task_complete_check: callable | None = None  # 自定义任务完成检测函数
    progress_dir: Path | None = None      # 进度保存目录
    continuation_prompt_template: str = (  # 继续提示模板
        "[任务继续] 之前的上下文已达到限制，但任务尚未完成。\n\n"
        "请继续之前的工作。以下是最后一步的输出摘要：\n\n"
        "{previous_response}\n\n"
        "请继续执行，直到任务完全完成。"
    )
    context_threshold: float = 0.6        # 触发上下文阈值（最大 token 的比例）
```

### 工作原理

1. **拦截退出尝试**：当 Agent 准备退出时，`ON_EXIT_ATTEMPT` 钩子被触发
2. **任务完成检测**：检查 LLM 响应是否表明任务真正完成
   - 默认检测完成关键词：`task complete`, `all done`, `finished successfully` 等
   - 可自定义检测函数
3. **触发继续执行**：如果任务未完成：
   - 增加循环计数
   - 构建继续提示
   - 返回 `REINJECT` 动作，清除上下文并注入继续指令
4. **循环限制**：防止无限循环（默认最多 5 次继续）

### Ralph Loop vs 标准 Agent Loop

| 特性 | 标准 Agent Loop | Ralph Loop |
|------|----------------|------------|
| **适用场景** | 短任务（< 10 步） | 长任务（可能 50+ 步） |
| **退出策略** | 完成/出错即退出 | 防止草率完成，检测真正完成状态 |
| **上下文管理** | 简单追加 | 自动上下文重置（REINJECT 动作） |
| **继续机制** | 无 | 自动检测未完成任务并继续 |
| **配置方式** | 无 | 通过 `RalphLoopHook` 钩子配置 |

### 使用方式

```python
from harness import AgentHarness
from harness.core.ralph_loop import RalphLoopHook

# 简单使用：添加默认 Ralph Loop 钩子
agent = AgentHarness()
agent.add_hook(RalphLoopHook())

# 自定义配置：设置最大循环次数和完成检测
from harness.core.ralph_loop import RalphLoopConfig

config = RalphLoopConfig(
    max_loops=3,
    task_complete_check=lambda response: any(
        phrase in response.lower()
        for phrase in ["task complete", "all done", "finished"]
    ),
)
agent.add_hook(RalphLoopHook(config))

# 执行长任务
result = await agent.run("重构整个代码库，添加类型注解和测试")
```

## Sub-Agent 管理

Sub-Agent 允许主 Agent 创建子代理来处理子任务，实现任务分解和并行执行。`SubAgentManager` 管理子代理的生命周期。

### SubAgentConfig

```python
from harness.core.subagent import SubAgentConfig

@dataclass
class SubAgentConfig:
    name: str  # 子代理唯一名称
    task: str  # 任务描述
    tools: list[str] | None = None  # 可用工具列表（None = 继承父代理所有工具）
    max_iterations: int = 20  # 最大迭代次数
    inherit_context: bool = False  # 是否继承父代理上下文
    report_format: Literal["summary", "full", "structured"] = "summary"  # 结果格式
```

**工具过滤说明**：

当指定 `tools` 参数时，子代理只会继承父代理中名称匹配的工具。支持常用别名：

| 别名 | 实际工具名 |
|------|-----------|
| `read` | `read` |
| `write` | `write_file` |
| `edit` | `edit_file` |
| `glob` | `glob` |
| `grep` | `grep` |
| `bash` | `bash` |

```python
# 子代理只继承读取类工具
config = SubAgentConfig(
    name="reader",
    task="只读分析",
    tools=["read", "glob", "grep"],  # 只允许读取操作
)

# 子代理继承所有父代理工具
config = SubAgentConfig(
    name="full-access",
    task="完整访问",
    tools=None,  # None = 继承所有
)
```

### SubAgentResult

```python
from harness.core.subagent import SubAgentResult, SubAgentStatus

@dataclass
class SubAgentResult:
    name: str  # 子代理名称
    success: bool  # 是否成功完成
    status: SubAgentStatus  # 状态（PENDING, RUNNING, COMPLETED, FAILED, CANCELLED）
    summary: str | None = None  # 结果摘要（summary 格式）
    full_response: str | None = None  # 完整响应（full 格式）
    structured_result: dict[str, Any] | None = None  # 结构化结果（structured 格式）
    iterations: int = 0  # 使用的迭代次数
    token_usage: dict[str, int] = field(default_factory=dict)  # token 使用统计
    error: str | None = None  # 错误信息（如果失败）
```

### SubAgentManager

```python
from harness.core.subagent import SubAgentManager
from harness import AgentHarness

# 创建父代理和子代理管理器
parent = AgentHarness(model="claude-sonnet-4-6")
manager = SubAgentManager(parent)

# 创建子代理配置
config1 = SubAgentConfig(
    name="core_analyzer",
    task="Analyze src/core directory for code quality issues",
    tools=["read", "grep"],
    max_iterations=15,
)

config2 = SubAgentConfig(
    name="security_analyzer",
    task="Check for security vulnerabilities in src/ directory",
    tools=["read", "grep", "bash"],
    max_iterations=20,
)

# 创建子代理
await manager.spawn(config1)
await manager.spawn(config2)

# 并行运行所有子代理
results = await manager.run_all()

# 处理结果
for name, result in results.items():
    if result.success:
        print(f"{name}: {result.summary}")
    else:
        print(f"{name} failed with status: {result.status}")
```

### 子代理状态

```python
class SubAgentStatus(Enum):
    PENDING = "pending"      # 等待运行
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 成功完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 被取消
```

### 使用场景

```python
# 复杂任务分解为多个子任务并行执行
agent = AgentHarness()
manager = SubAgentManager(agent)

# 创建多个子代理分析不同模块
configs = [
    SubAgentConfig(
        name=f"module_{i}",
        task=f"Analyze module {i} for performance issues",
        tools=["read", "grep"],
        report_format="summary"
    )
    for i in range(5)
]

# 创建所有子代理
for config in configs:
    await manager.spawn(config)

# 并行运行
results = await manager.run_all()

# 聚合结果
aggregated_summary = "\n".join(
    f"{name}: {result.summary}"
    for name, result in results.items()
    if result.success
)
```

## Self-Verification（自验证）

自验证钩子实现了 `write-code → run-tests → fix-errors` 的自动验证循环。`SelfVerificationHook` 在代码修改后自动运行测试，并将失败结果注入回上下文供 LLM 修复。

### SelfVerificationConfig

```python
from harness.core.self_verification import SelfVerificationConfig

@dataclass
class SelfVerificationConfig:
    test_command: str = "pytest"  # 测试命令
    test_args: list[str] = field(default_factory=lambda: ["-x", "--tb=short"])  # 测试参数
    trigger_tools: list[str] = field(default_factory=lambda: ["write", "edit", "write_file", "edit_file"])  # 触发验证的工具
    working_directory: Path | None = None  # 工作目录
    timeout: float = 60.0  # 超时时间（秒）
    max_retries: int = 3  # 最大重试次数
    verify_on_change: bool = True  # 是否每次代码修改都验证
    skip_if_no_tests: bool = True  # 无测试文件时是否跳过
    test_pattern: str = "test_*.py"  # 测试文件模式
```

### SelfVerificationHook

```python
from harness.core.self_verification import SelfVerificationHook
from harness.core.hooks import LifecycleHook
from harness import AgentHarness

# 创建自验证钩子
config = SelfVerificationConfig(
    test_command="pytest",
    test_args=["-x", "-v", "--tb=short"],
    max_retries=3,
    verify_on_change=True,
)
verification_hook = SelfVerificationHook(config)

# 注册到 Agent
agent = AgentHarness()
agent.add_hook(verification_hook)

# 现在代码修改后会自动运行测试
result = await agent.run("Fix the bug in src/main.py")
```

### 工作原理

1. **触发条件**：当 `AFTER_TOOL_EXECUTE` 钩子触发且工具名在 `trigger_tools` 列表中时
2. **测试检测**：检查当前目录是否存在测试文件（匹配 `test_pattern`）
3. **测试执行**：运行配置的测试命令
4. **结果处理**：
   - 测试通过：继续正常执行
   - 测试失败：注入错误消息到上下文，要求 LLM 修复
   - 超时/错误：记录日志并继续
5. **重试限制**：防止无限重试（默认最多 3 次）

### 使用示例

```python
from harness import AgentHarness
from harness.core.self_verification import SelfVerificationHook, SelfVerificationConfig

# 创建带自验证的 Agent
agent = AgentHarness()

# 配置自验证（使用 pytest 测试）
config = SelfVerificationConfig(
    test_command="pytest",
    test_args=["-x", "--tb=short", "--disable-warnings"],
    max_retries=2,
    verify_on_change=True,
    skip_if_no_tests=True,
)
verification = SelfVerificationHook(config)

# 添加钩子
agent.add_hook(verification)

# 执行任务 - 代码修改后会自动运行测试
result = await agent.run(
    "Refactor the authentication module to use JWT tokens. "
    "Update tests accordingly."
)

# 如果测试失败，Agent 会自动收到错误信息并修复
```

### 高级配置

```python
# 自定义触发工具
config = SelfVerificationConfig(
    trigger_tools=["write", "edit"],  # 只对 write 和 edit 工具触发
    test_command="python -m unittest",  # 使用 unittest
    test_args=["discover", "-s", "tests", "-p", "test_*.py"],
    verify_on_change=False,  # 只在任务完成时验证
)

# 多个测试命令
config = SelfVerificationConfig(
    test_command="bash",  # 使用 bash 执行复杂测试脚本
    test_args=["-c", "pytest && mypy . && black --check ."],
    timeout=120.0,  # 更长超时时间
)
```

## Tool Output Offload（工具输出卸载）

当工具输出过大时（如读取大型文件、目录列表等），会导致上下文膨胀，增加成本并可能超出模型限制。Output Offload 机制自动检测大型输出并将其卸载到临时文件，上下文中只保留引用。

### OffloadConfig

```python
from harness.core.output_offload import OffloadConfig

@dataclass
class OffloadConfig:
    """Configuration for tool output offloading."""
    size_threshold_chars: int = 5000        # 触发卸载的最小输出大小（字符数）
    size_threshold_tokens: int = 1250       # Token 阈值（~4 chars/token）
    max_outputs_per_session: int = 50       # 每会话最大卸载数量
    cleanup_on_session_end: bool = False    # 会话结束时是否清理文件（默认保留）
    preview_length: int = 200               # 上下文中保留的预览长度
    summary_prompt: str | None = None       # 可选的摘要生成提示
    temp_dir: Path | None = None            # 卸载文件存储目录（默认 .harness/offload）
```

### OffloadedOutput

```python
from harness.core.output_offload import OffloadedOutput

@dataclass
class OffloadedOutput:
    """Record of an offloaded tool output."""
    file_path: Path           # 卸载文件路径
    tool_name: str            # 产生此输出的工具名
    tool_call_id: str         # 工具调用 ID
    original_size: int        # 原始输出大小（字符）
    preview: str              # 预览内容（保留在上下文中）
    summary: str | None       # 可选摘要
    created_at: datetime      # 创建时间
    session_id: str           # 所属会话 ID
```

### 使用示例

```python
from harness import AgentHarness
from harness.core.output_offload import OffloadConfig

# 配置卸载
config = OffloadConfig(
    size_threshold_chars=10000,   # 超过 10KB 的输出将被卸载
    max_outputs_per_session=20,   # 每会话最多 20 个卸载文件
    preview_length=300,           # 保留 300 字符预览
)

agent = AgentHarness(offload_config=config)

# 正常使用 - 大型输出会自动卸载
result = await agent.run("读取并分析所有源代码文件")
```

### 卸载后的上下文引用

当输出被卸载后，上下文中会包含类似以下的引用：

```
[Output from read_file (15000 chars)]
Preview: #!/usr/bin/env python3
"""Main module..."""
Full output saved to: .harness/offload/session_abc123_read_file_call_456.txt
```

**注意**：卸载文件默认存储在当前工作目录的 `.harness/offload/` 下，确保 sandbox 可以访问。LLM 可以根据需要使用 Read 工具加载完整内容。

## Step Budget（步骤预算）

步骤预算控制每个任务的迭代次数和工具调用次数，防止无限循环或过度消耗资源。与 CostController（基于 Token）不同，StepBudget 基于"步骤"计数。

### StepBudgetConfig

```python
from harness.core.step_budget import StepBudgetConfig

@dataclass
class StepBudgetConfig:
    """Configuration for step-based budget control."""
    max_iterations_per_task: int = 50    # 每任务最大迭代次数
    max_tool_calls_per_step: int = 10    # 每步（单次 LLM 响应）最大工具调用数
    max_tool_calls_per_task: int = 200   # 每任务最大工具调用总数
    warning_threshold: float = 0.8       # 警告阈值（使用率）
    critical_threshold: float = 0.95     # 临界阈值（使用率）
    action_on_exceed: str = "stop"       # 超限动作：stop | warn | throttle
    throttle_ratio: float = 0.5          # 节流时使用的剩余预算比例
```

### BudgetLevel

```python
from harness.core.step_budget import BudgetLevel

class BudgetLevel(Enum):
    """Budget status levels."""
    NORMAL = "normal"       # 正常范围内
    WARNING = "warning"     # 接近限制（>= warning_threshold）
    CRITICAL = "critical"   # 临近限制（>= critical_threshold）
    EXCEEDED = "exceeded"   # 超出限制（>= 1.0）
```

### 使用示例

```python
from harness import AgentHarness
from harness.core.step_budget import StepBudgetConfig

# 配置步骤预算
budget_config = StepBudgetConfig(
    max_iterations_per_task=30,      # 最多 30 次迭代
    max_tool_calls_per_step=5,       # 每次 LLM 响应最多 5 个工具调用
    max_tool_calls_per_task=100,     # 总共最多 100 次工具调用
    action_on_exceed="stop",         # 超限时停止
)

agent = AgentHarness(step_budget_config=budget_config)

# 执行任务 - 预算会在每次迭代和工具调用前检查
result = await agent.run("分析代码库并生成报告")
```

### 预算检查时机

1. **每次迭代前**：检查迭代次数是否超限
2. **每次工具调用前**：检查工具调用次数是否超限
3. **每步工具调用限制**：防止单次 LLM 响应触发过多工具调用

### 超限动作

| 动作 | 行为 |
|------|------|
| `stop` | 立即停止执行，返回错误 |
| `warn` | 记录警告但继续执行 |
| `throttle` | 启用节流模式，限制后续工具调用数量 |

## Cost Controller（成本控制）

Agent Loop 内置成本控制机制，防止意外的高额 API 费用。

```python
from harness.core.cost_controller import CostController, BudgetStatus, UserBudgetStatus, GlobalBudgetStatus
from harness.types import CostConfig, TokenUsage

class CostController:
    def __init__(
        self,
        config: CostConfig | None = None,  # 成本配置
        storage: "CostStorage | None" = None,  # 存储后端
        on_progress: "ProgressCallback | None" = None,  # 进度回调
    )

    def check(self, usage: TokenUsage) -> BudgetStatus:
        """检查当前成本状态，返回 BudgetStatus"""
        
    def check_user(self, user_id: str, usage: UserUsage) -> UserBudgetStatus:
        """检查用户级别成本状态"""
        
    def check_global(self) -> GlobalBudgetStatus:
        """检查全局成本状态"""
```

### BudgetStatus

```python
@dataclass
class BudgetStatus:
    """当前预算状态"""
    is_within_budget: bool          # 是否在预算内
    usage: TokenUsage               # token 使用统计
    config: CostConfig              # 成本配置
    warning_message: str | None = None  # 警告信息
    should_compress: bool = False   # 是否应该压缩上下文
    should_downgrade: bool = False  # 是否应该降级模型
    usage_ratio: float = 0.0        # 使用率（0.0-1.0）

    @property
    def is_warning(self) -> bool:
        """检查是否处于警告状态"""
        return self.warning_message is not None and self.is_within_budget

    @property
    def remaining_tokens(self) -> int:
        """预算内剩余 token 数"""
        return max(0, self.config.max_tokens_per_session - self.usage.total_tokens)

    @property
    def remaining_tool_calls(self) -> int:
        """预算内剩余工具调用次数"""
        return max(0, self.config.max_tool_calls_per_session - self.usage.tool_calls)
```

## 流式输出

Agent Loop 支持流式输出，允许逐步接收 LLM 的响应。

```python
# 方式 1：通过 AgentHarness.stream()
async for chunk in agent.stream("分析这段代码"):
    print(chunk.content, end="")

# 方式 2：在 AgentLoop 中使用
result = await agent_loop.run(messages, stream=True)
```

流式输出遵循背压控制：如果消费者处理速度慢于生产速度，LLM 读取会被自动暂停。

## 错误处理

### 重试策略

| 错误类型 | 处理方式 |
|----------|----------|
| API 限流 (429) | 指数退避重试 |
| API 错误 (5xx) | 重试最多 `retry_on_error` 次（默认 3） |
| 工具执行错误 | 返回错误信息给 LLM |
| 上下文超长 | 触发压缩或截断 |
| 成本超限 | 中断并返回结果 |

### LLM 重试策略

Agent Loop 使用配置化的重试策略，支持指数退避和随机抖动：

```python
# 重试次数从配置读取
max_llm_retries = self.config.retry_on_error or 3

# 重试延迟策略
if decision.delay_seconds > 0:
    # 优先使用 ErrorHandler 返回的延迟（如 rate limit 的 Retry-After）
    delay = decision.delay_seconds
else:
    # 指数退避 + 随机抖动（防止重试风暴）
    import random
    base_backoff = min(2 ** llm_attempt, 30)  # 上限 30s
    jitter = random.uniform(0, 0.5)           # 随机抖动
    delay = base_backoff + jitter
```

**设计原则**：
- 配置化：重试次数可通过 `LoopConfig.retry_on_error` 调整
- ErrorHandler 优先：尊重 API 返回的重试建议（如 Retry-After header）
- 指数退避：避免短时间大量重试
- 随机抖动：防止多客户端同时重试（惊群效应）

### 熔断器

熔断器用于检测和防止无限循环，遵循 **Bitter Lesson** 原则：简单规则优于复杂启发式。

**检测机制**：
- 只检测"相同工具 + 相同参数"重复调用
- 默认阈值：`same_args_threshold = 3`（调用 3 次触发熔断）
- 不检测复杂的序列模式（避免误报）

```python
from harness.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# 默认配置
cb = CircuitBreaker()

# 自定义阈值
cb = CircuitBreaker(CircuitBreakerConfig(
    same_args_threshold=3,      # 相同工具+参数重复次数
    error_threshold=5,          # 错误次数阈值
    error_window_seconds=60,    # 错误统计窗口
    recovery_timeout_seconds=30, # 恢复超时
))

# 记录调用
cb.record_call("read", {"path": "test.txt"})

# 检查状态
if cb.is_open():
    print(f"熔断器已打开: {cb.get_reason()}")
```

**设计原则**：
1. **简单规则**：只检测明显的重复行为
2. **信任模型**：通过 system prompt 指导模型何时停止
3. **避免误报**：不干预并行工具调用等正常行为

### 工具执行超时

Agent Loop 使用 `asyncio.wait_for` 强制执行工具超时，防止病态工具阻塞整个执行：

```python
# 工具执行超时保护
try:
    result = await asyncio.wait_for(
        self.tools.execute(tool_call, context),
        timeout=self.config.timeout_per_tool,  # 默认 30s
    )
except asyncio.TimeoutError:
    # 超时后返回错误结果，而不是无限等待
    result = ToolResult(
        tool_call_id=tool_call.id,
        success=False,
        error=f"Tool execution timed out after {self.config.timeout_per_tool}s",
    )
```

**配置**：
- `LoopConfig.timeout_per_tool`: 单个工具的超时时间（默认 30.0 秒）

**注意**：超时后工具执行会被取消，Agent 会收到错误信息并可以决定下一步操作。

### Step Budget 资源清理

Agent Loop 使用 `finally` 块确保 `StepBudgetController.end_task()` 总是被调用，防止资源泄漏：

```python
# 确保 step_budget 在任何情况下都被清理
try:
    # 主循环...
    while iteration < self.config.max_iterations:
        # ... 执行循环
finally:
    # 无论成功、失败、中断，都确保清理
    if self._step_budget:
        try:
            self._step_budget.end_task()
        except Exception:
            logger.exception("Error while ending step budget task")
```

**设计原则**：
- 资源清理必须放在 `finally` 块中
- 清理操作本身需要捕获异常，避免掩盖原始错误

## 完整流程图

```
用户输入
    │
    ↓
┌─────────────────────────────────────────────────┐
│ ON_LOOP_START Hook                               │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Context Builder                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ 1. 加载系统提示（SystemPromptBuilder）       │ │
│ │ 2. 加载技能（ProgressiveSkillLoader）        │ │
│ │ 3. 加载记忆（MemoryManager）                 │ │
│ │ 4. 组装 AGENTS.md（如有）                    │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Agent Loop                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │              Loop Body                       │ │
│ │                                              │ │
│ │  ┌─────────────┐                            │ │
│ │  │BEFORE_LLM_ │                            │ │
│ │  │CALL Hook    │                            │ │
│ │  │Hook         │                            │ │
│ │  └──────┬──────┘                            │ │
│ │         ↓                                   │ │
│ │  ┌───────────┐    ┌───────────┐            │ │
│ │  │   LLM     │───→│AFTER_LLM_ │            │ │
│ │  │   Call    │    │CALL Hook  │            │ │
│ │  └───────────┘    │           │            │ │
│ │                    └─────┬─────┘            │ │
│ │                          ↓                  │ │
│ │              ┌───────────────────┐          │ │
│ │              ↓                   ↓          │ │
│ │        ┌──────────┐      ┌──────────┐      │ │
│ │        │Tool Call │      │  Finish  │      │ │
│ │        │          │      │          │      │ │
│ │        └────┬─────┘      └────┬─────┘      │ │
│ │             ↓                 │            │ │
│ │  ┌──────────────┐             │            │ │
│ │  │BEFORE_TOOL_ │             │            │ │
│ │  │EXECUTE Hook │             │            │ │
│ │  └──────┬───────┘             │            │ │
│ │         ↓                     │            │ │
│ │  ┌──────────┐                 │            │ │
│ │  │ Execute  │                 │            │ │
│ │  │  Tool    │                 │            │ │
│ │  └────┬─────┘                 │            │ │
│ │       ↓                       │            │ │
│ │  ┌───────────────┐            │            │ │
│ │  │AFTER_TOOL_   │            │            │ │
│ │  │EXECUTE Hook  │            │            │ │
│ │  └───────┬───────┘            │            │ │
│ │          │                    │            │ │
│ │          ↓                    ↓            │ │
│ │     Back to LLM          ┌──────────┐      │ │
│ │                          │ON_EXIT_  │      │ │
│ │                          │ATTEMPT   │      │ │
│ │                          │Hook      │      │ │
│ │                          └──────────┘      │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│  熔断器 | 卡住检测 | 成本控制                     │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Memory Update                                    │
└─────────────────────────────────────────────────┘
    │
    ↓
LoopResult
```
