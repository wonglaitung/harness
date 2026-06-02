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
| **最大步数** | `max_iterations` (默认 100) | 限制循环次数 |
| **工具超时** | `timeout_per_tool` (默认 30.0s) | 每个工具调用的超时时间 |
| **熔断器** | `enable_circuit_breaker` (默认 True) | 连续失败时中断循环 |
| **卡住检测** | `max_stuck_feedbacks` (默认 2) | 检测重复输出或无进展状态 |
| **成本控制** | `enable_cost_control` (默认 True) | 累计成本超限时中断 |
| **并行工具** | `enable_parallel_tools` (默认 True) | 启用并行工具调用 |
| **错误重试** | `retry_on_error` (默认 3) | API 错误自动重试次数 |

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
    """Configuration for agent loop."""
    max_iterations: int = 100                    # 最大迭代次数
    timeout_per_tool: float = 30.0               # 每个工具调用的超时时间（秒）
    enable_parallel_tools: bool = True           # 是否启用并行工具调用
    retry_on_error: int = 3                      # 错误重试次数
    enable_progress: bool = True                 # 是否启用进度事件
    enable_circuit_breaker: bool = True          # 是否启用熔断器
    same_tool_threshold: int = 5                 # 熔断器阈值（相同工具连续调用次数）
    enable_cost_control: bool = True             # 是否启用成本控制
    cost_config: CostConfig | None = None        # 成本控制配置
    security_config: SecurityConfig | None = None # 安全配置
    
    # 卡住检测配置
    max_stuck_feedbacks: int = 2                 # 最大反馈注入尝试次数
    stuck_min_iterations: int = 3                 # 卡住检测前的最小迭代次数
    stuck_consecutive_failures: int = 3           # 触发卡住检测的连续失败次数
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

Agent Loop 内置卡住检测机制，识别以下模式：

| 模式 | 检测方法 |
|------|----------|
| **重复输出** | 连续 N 次相同或高度相似的 LLM 输出 |
| **循环工具调用** | 相同工具 + 相同参数被重复调用 |
| **无进展** | 多次迭代后状态未改变 |

检测到卡住状态后，Agent Loop 会：
1. 在上下文中注入提醒消息
2. 如果继续卡住，触发 `ON_ERROR` 钩子
3. 最终中断循环

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
| API 错误 (5xx) | 重试最多 3 次 |
| 工具执行错误 | 返回错误信息给 LLM |
| 上下文超长 | 触发压缩或截断 |
| 成本超限 | 中断并返回结果 |

### 熔断器

```python
# 熔断器在连续失败时中断循环
# 默认：连续 5 次失败触发熔断
# 可通过 HarnessConfig 配置
```

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
