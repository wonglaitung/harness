"""
Harness SDK 功能演示 - 开箱即用案例

这个文件展示了 Harness SDK 的主要功能，帮助你快速了解项目能力。

运行方式:
    python examples/third_party_api_example.py

功能模块 (32 个演示):
    演示 1:  基础对话 - 简单问答
    演示 2:  文件工具 - ReadTool, GlobTool, GrepTool
    演示 3:  多轮对话 - Session 会话管理
    演示 4:  成本控制 - CostConfig, CostController
    演示 5:  进度追踪 - ProgressEvent, ProgressEventType
    演示 6:  自定义工具 - @agent.tool() 装饰器
    演示 7:  Mock 测试 - MockHarness, MockResponse
    演示 8:  Skills 技能系统 - Skill, SkillRegistry, SkillTrigger
    演示 9:  Skill 注入 - SkillInjector, SkillLoader
    演示 10: MCP 服务器 - MCPServerConfig, Stdio/HTTP Transport
    演示 11: Security 安全 - PromptInjectionDetector, LightweightSandbox, AuditLogger
    演示 12: Observability - ObservabilityManager, OpenTelemetry
    演示 13: 多级成本控制 - InMemoryCostStorage, 用户级/全局预算
    演示 14: 中断恢复 - LoopSnapshot
    演示 15: 配置管理 - HarnessConfig, Model presets
    演示 16: 完整工作流 - 综合示例
    演示 17: Lifecycle Hooks - 工具执行前后的钩子系统 (P0)
    演示 18: 动态系统提示 - SystemPromptBuilder, AGENTS.md (P0)
    演示 19: Ralph Loop - 长任务循环，防止上下文焦虑 (P1)
    演示 20: Sub-Agent 管理 - 创建子代理处理子任务 (P1)
    演示 21: 自验证钩子 - 代码修改后自动运行测试 (P2)
    演示 22: 渐进式技能加载 - 三级加载优化上下文 (P2)
    演示 23: MEMORY.md 标准 - 持久记忆文件管理 (P2)
    演示 24: 向量检索 - 语义搜索历史对话 (P2)
    演示 25: 语义卡住检测 - 基于相似度检测重复输出 (P2)
    演示 26: Guardrails - PII 检测和内容安全 (P2)
    演示 27: CPU Router - 成本优化的请求路由 (P2)
    演示 28: Guardrails 进阶 - LLM Judge、流式拦截、中文姓名识别、异常处理 (P2)
    演示 29: Loop Engineering - 基础用法：目标驱动执行 (P2)
    演示 30: Loop Engineering - 自定义验证器 (P2)
    演示 31: Loop Engineering - Automation 定时调度 (P2)
    演示 32: Loop Engineering - 并行 Worktree 执行 (P2)

作者: Harness Team
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径（用于开发测试）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ============================================================================
# 导入 Harness SDK 的主要组件
# ============================================================================

# 主入口 - 创建 AI Agent 的核心类
# 配置类 - 自定义 Agent 行为
# 内置工具 - 开箱即用的文件操作工具
# 成本控制 - 管理 Token 消耗
# 进度追踪 - 监控执行过程
# 会话管理 - 持久化对话
# 类型定义
# Skills 技能系统 - 模块化能力单元
# MCP 支持 - 连接外部工具服务器
# Observability 可观测性 - OpenTelemetry 集成
# Security 安全系统 - 保护 Agent 免受攻击
# 多级成本存储
# Lifecycle Hooks - 工具执行前后的钩子系统 (P0)
# 动态系统提示组装 (P0)
# Ralph Loop - 长任务循环 (P1)
# Sub-Agent 管理 (P1)
# 自验证钩子 (P2)
# 渐进式技能加载 (P2)
# MEMORY.md 标准 (P2)
# 向量检索 (P2)
from harness import (
    AbortOnDangerousToolHook,  # 阻止危险工具钩子
    AgentHarness,
    CostConfig,  # 成本配置
    CostController,  # 成本控制器
    GlobTool,  # 文件名搜索 (类似 find)
    GrepTool,  # 文件内容搜索 (类似 grep)
    HarnessConfig,
    HookAction,  # 钩子动作
    HookContext,  # 钩子上下文
    HookManager,  # 钩子管理器
    HookPoint,  # 钩子触发点
    HookResult,  # 钩子结果
    InjectionConfig,  # 注入配置
    InMemoryCostStorage,  # 内存存储
    LifecycleHook,  # 钩子基类
    LoggingHook,  # 日志钩子
    MaxToolCallsHook,  # 限制工具调用次数钩子
    MCPManager,  # MCP 管理器
    MCPServerConfig,  # MCP 服务器配置
    MemoryCategory,  # 记忆分类
    MemoryEntry,  # 记忆条目
    MemoryFileManager,  # MEMORY.md 文件管理器
    MemorySource,  # 记忆来源
    MockEmbeddingModel,  # Mock 嵌入模型
    ObservabilityConfig,  # 配置
    ObservabilityManager,  # 可观测性管理器
    ProgressEvent,  # 进度事件
    ProgressEventType,  # 事件类型
    ProgressiveSkillLoader,  # 渐进式技能加载器
    RalphLoopConfig,  # Ralph Loop 配置
    RalphLoopHook,  # Ralph Loop 钩子
    ReadTool,  # 读取文件
    SecurityConfig,  # 安全配置（新增）
    SelfVerificationConfig,  # 自验证配置
    SelfVerificationHook,  # 自验证钩子
    SimpleInMemoryVectorStore,  # 简单内存向量存储
    Skill,  # 技能定义
    SkillInjector,  # 技能注入器
    SkillLoader,  # 技能加载器
    SkillRegistry,  # 技能注册表
    SkillTools,  # 工具权限配置
    SkillTrigger,  # 触发条件
    SubAgentConfig,  # 子代理配置
    SubAgentManager,  # 子代理管理器
    SubAgentResult,  # 子代理结果
    SystemPromptBuilder,  # 系统提示构建器
    SystemPromptConfig,  # 系统提示配置
    SystemPromptSource,  # 系统提示源
    VectorMemoryConfig,  # 向量配置
    VectorMemoryStore,  # 向量记忆存储
    create_default_memory,  # 创建默认记忆
    discover_project_context,  # 发现项目上下文
    )

# 语义卡住检测 (P2)
from harness.core import (
    StuckDetector,  # 卡住检测器
    StuckDetectorConfig,  # 检测配置
)

# Loop Engineering - 目标驱动执行 (P2)
from harness.loop import (
    Automation,  # 自动化任务
    GoalResult,  # 目标执行结果
    GoalStatus,  # 目标状态
    )

# Mock 测试 - 不需要真实 API 的测试
from harness.testing import MockHarness, MockResponse

# ============================================================================
# 配置区 - 修改这里使用你的 API
# ============================================================================

# 方式 1: 使用第三方 OpenAI 兼容 API（如智谱 GLM）
# 设置环境变量: OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
BASE_URL = os.environ.get("OPENAI_BASE_URL")
API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
PROVIDER = "openai"  # 第三方 API 使用 openai 协议

# 方式 2: 使用官方 Anthropic API
# BASE_URL = None
# API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # 或设置 ANTHROPIC_API_KEY 环境变量
# MODEL = "claude-sonnet-4-6"
# PROVIDER = "anthropic"

# 方式 3: 使用官方 OpenAI API
# BASE_URL = None
# API_KEY = os.environ.get("OPENAI_API_KEY")  # 或设置 OPENAI_API_KEY 环境变量
# MODEL = "gpt-4o"
# PROVIDER = "openai"


# ============================================================================
# 演示 1: 基础对话功能
# ============================================================================

async def demo_basic_conversation():
    """
    演示 1: 基础对话功能

    功能:
    - 创建 Agent
    - 发送简单问题
    - 获取响应

    学习要点:
    - AgentHarness 是主入口
    - run() 是异步方法
    - result.content 获取最终响应
    """
    print("\n" + "=" * 70)
    print("演示 1: 基础对话功能")
    print("=" * 70)

    # 创建 Agent（最简单的方式）
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
    )

    # 发送问题并获取响应
    print("\n用户: 你好，请用一句话介绍自己。")

    result = await agent.run("你好，请用一句话介绍自己。")

    # 打印响应
    print(f"\nAgent: {result.content}")
    print(f"\n执行状态: {result.status.value}")
    print(f"迭代次数: {result.iterations}")
    print(
        f"Token 使用: 输入 {result.token_usage.input_tokens}, "
        f"输出 {result.token_usage.output_tokens}"
    )


# ============================================================================
# 演示 2: 工具系统 - 文件操作
# ============================================================================

async def demo_file_tools():
    """
    演示 2: 工具系统 - 文件操作

    功能:
    - 注册内置工具
    - Agent 自动选择工具完成任务
    - 观察工具调用过程

    学习要点:
    - tools 参数添加工具
    - verbose=True 显示执行过程
    - Agent 会自动判断何时使用工具
    """
    print("\n" + "=" * 70)
    print("演示 2: 工具系统 - 文件操作")
    print("=" * 70)

    # 创建带工具的 Agent
    # 注意：添加 system_prompt 指导模型何时停止调用工具
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        system_prompt="""你是一个有帮助的 AI 助手。

## 核心规则

**一次完成任务**：只做用户明确要求的事，完成后立即给出最终回答。

## 必须立即停止的情况

1. **信息已足够**：你已有了回答所需的信息 → 立即回答
2. **任务已完成**：用户请求的操作已完成 → 立即回答
3. **工具失败两次**：同一工具失败两次 → 停止并报告错误

## 禁止的行为

- 不要"顺便"做其他事
- 不要"继续探索"
- 不要重复调用同一工具""",
        tools=[
            ReadTool(),   # 读取文件
            GlobTool(),   # 文件名搜索
            GrepTool(),   # 内容搜索
        ],
    )

    # 让 Agent 使用工具完成任务
    print("\n用户: 请列出当前目录下所有的 Python 文件名称，然后读取 pyproject.toml 的前 20 行。")
    print("-" * 70)

    result = await agent.run(
        "请列出当前目录下所有的 Python 文件名称，然后读取 pyproject.toml 的前 20 行。",
        verbose=True,  # 显示执行过程
    )

    print("-" * 70)
    print(f"\n最终响应:\n{result.content[:500]}...")
    print(f"\n迭代次数: {result.iterations} (每次工具调用算一次迭代)")


# ============================================================================
# 演示 3: 多轮对话 - 会话管理
# ============================================================================

async def demo_multi_turn_conversation():
    """
    演示 3: 多轮对话 - 会话管理

    功能:
    - 保持对话上下文
    - 同一 session_id 延续对话
    - 不同 session_id 隔离对话

    学习要点:
    - session_id 参数控制会话
    - 相同 session_id 共享历史消息
    - Agent 能记住之前说过的话
    """
    print("\n" + "=" * 70)
    print("演示 3: 多轮对话 - 会话管理")
    print("=" * 70)

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
    )

    session_id = "demo-session-001"

    # 第一轮对话
    print(f"\n[Session: {session_id}]")
    print("用户: 我的名字叫小明。")
    result1 = await agent.run("我的名字叫小明。", session_id=session_id)
    print(f"Agent: {result1.content}")

    # 第二轮对话 - Agent 会记住名字
    print(f"\n[Session: {session_id}]")
    print("用户: 你还记得我叫什么名字吗？")
    result2 = await agent.run("你还记得我叫什么名字吗？", session_id=session_id)
    print(f"Agent: {result2.content}")

    # 新会话 - Agent 不知道名字
    new_session_id = "demo-session-002"
    print(f"\n[Session: {new_session_id} - 新会话]")
    print("用户: 你知道我是谁吗？")
    result3 = await agent.run("你知道我是谁吗？", session_id=new_session_id)
    print(f"Agent: {result3.content}")

    print("\n注意: 新会话的 Agent 不知道之前对话的内容")


# ============================================================================
# 演示 4: 成本控制 - Token 预算管理
# ============================================================================

async def demo_cost_control():
    """
    演示 4: 成本控制 - Token 预算管理

    功能:
    - 设置会话级 Token 限制
    - 超限自动停止
    - 监控 Token 使用量

    学习要点:
    - CostConfig 配置预算
    - BudgetExceededError 处理超限
    - TokenUsage 追踪使用量
    """
    print("\n" + "=" * 70)
    print("演示 4: 成本控制 - Token 预算管理")
    print("=" * 70)

    # 配置成本限制
    cost_config = CostConfig(
        max_tokens_per_session=1000,  # 会话最多 1000 tokens
        max_iterations_per_request=5,  # 每次请求最多 5 次迭代
        warning_threshold=0.8,  # 80% 时发出警告
    )

    print("成本配置:")
    print(f"  - 会话 Token 限制: {cost_config.max_tokens_per_session}")
    print(f"  - 最大迭代次数: {cost_config.max_iterations_per_request}")
    print(f"  - 警告阈值: {cost_config.warning_threshold * 100}%")

    # 创建带成本控制的配置
    config = HarnessConfig(
        model=MODEL,
        api_key=API_KEY,
        provider=PROVIDER,
        base_url=BASE_URL,
        max_iterations=cost_config.max_iterations_per_request,
    )

    agent = AgentHarness(config=config)

    # 执行任务并监控 Token
    print("\n执行任务...")
    result = await agent.run("请用 100 字介绍 Python 编程语言。")

    print(f"\n响应: {result.content[:200]}...")
    print("\nToken 使用统计:")
    print(f"  - 输入 tokens: {result.token_usage.input_tokens}")
    print(f"  - 输出 tokens: {result.token_usage.output_tokens}")
    print(f"  - 总计: {result.token_usage.total_tokens}")


# ============================================================================
# 演示 5: 进度追踪 - 实时监控执行
# ============================================================================

async def demo_progress_tracking():
    """
    演示 5: 进度追踪 - 实时监控执行

    功能:
    - 监控每次 LLM 调用
    - 追踪工具执行
    - 记录状态变化

    学习要点:
    - on_progress 回调接收事件
    - ProgressEventType 定义事件类型
    - 可以集成到 UI 或日志系统
    """
    print("\n" + "=" * 70)
    print("演示 5: 进度追踪 - 实时监控执行")
    print("=" * 70)

    # 自定义进度回调
    events_log = []

    def on_progress(event: ProgressEvent):
        """处理进度事件"""
        events_log.append(event)

        # 根据事件类型显示不同信息
        if event.type == ProgressEventType.LOOP_START:
            print("\n🚀 开始执行...")
        elif event.type == ProgressEventType.LLM_CALL:
            print("📡 调用 LLM...")
        elif event.type == ProgressEventType.LLM_RESPONSE:
            duration = event.duration_ms or 0
            print(f"✅ LLM 响应 ({duration:.0f}ms)")
        elif event.type == ProgressEventType.TOOL_CALL:
            tool_name = event.data.get("tool", "unknown")
            print(f"🔧 调用工具: {tool_name}")
        elif event.type == ProgressEventType.TOOL_RESULT:
            success = event.data.get("success", False)
            status = "✅" if success else "❌"
            print(f"📋 工具结果: {status}")
        elif event.type == ProgressEventType.LOOP_END:
            print("🏁 执行完成")

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    # 使用自定义进度回调
    print("\n用户: 列出所有 Markdown 文件并读取 README.md")
    result = await agent.run(  # noqa: F841
        "使用 glob 工具列出所有 *.md 文件，然后读取 README.md 的前 10 行。",
        on_progress=on_progress,
    )

    print("\n事件统计:")
    event_counts = {}
    for event in events_log:
        event_counts[event.type.value] = event_counts.get(event.type.value, 0) + 1
    for event_type, count in event_counts.items():
        print(f"  - {event_type}: {count}")


# ============================================================================
# 演示 6: 自定义工具
# ============================================================================

async def demo_custom_tool():
    """
    演示 6: 自定义工具

    功能:
    - 创建自定义工具类
    - 使用装饰器快速定义工具
    - 工具可以执行任意 Python 代码

    学习要点:
    - 继承 Tool 类创建工具
    - @agent.tool() 装饰器更简单
    - 工具可以有复杂的输入 schema
    """
    print("\n" + "=" * 70)
    print("演示 6: 自定义工具")
    print("=" * 70)

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
    )

    # 方式 1: 使用装饰器快速定义工具
    @agent.tool(description="计算两个数字的和")
    def add_numbers(a: int, b: int) -> str:
        """计算 a + b 的结果"""
        result = a + b
        return f"{a} + {b} = {result}"

    @agent.tool(description="获取当前时间")
    def get_current_time() -> str:
        """返回当前的日期和时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n已注册工具: add_numbers, get_current_time")

    # 使用自定义工具
    print("\n用户: 帮我计算 123 + 456 等于多少")
    result = await agent.run("帮我计算 123 + 456 等于多少？", verbose=True)
    print(f"\nAgent: {result.content}")


# ============================================================================
# 演示 7: Mock 测试 - 无需真实 API
# ============================================================================

async def demo_mock_testing():
    """
    演示 7: Mock 测试 - 无需真实 API

    功能:
    - 模拟 LLM 响应
    - 测试 Agent 行为
    - 录制和回放真实交互

    学习要点:
    - MockHarness 用于测试
    - MockResponse 定义响应
    - 可以录制真实交互用于测试
    """
    print("\n" + "=" * 70)
    print("演示 7: Mock 测试 - 无需真实 API")
    print("=" * 70)

    # 创建 Mock Harness
    mock = MockHarness(
        responses=[
            MockResponse(content="这是一个模拟的响应，不需要真实的 API 调用。"),
            MockResponse(content="这是第二个模拟响应，用于测试多轮对话。"),
        ]
    )

    # 第一次调用
    print("\n用户: 你好")
    result1 = await mock.run("你好")
    print(f"Agent: {result1.content}")

    # 第二次调用
    print("\n用户: 再介绍一下自己")
    result2 = await mock.run("再介绍一下自己")
    print(f"Agent: {result2.content}")

    print("\n✅ Mock 测试完成，无需消耗真实 API 额度")


# ============================================================================
# 演示 8: Skills 技能系统
# ============================================================================

async def demo_skills_system():
    """
    演示 8: Skills 技能系统

    功能:
    - 创建自定义技能
    - 定义触发条件
    - 配置工具权限
    - 注册和激活技能
    - 在 Agent 运行时使用技能

    学习要点:
    - Skill 是模块化的能力单元
    - 包含触发条件、工具权限、执行内容
    - 通过 SkillInjector 注入到 system prompt
    - 可以从文件加载或代码创建
    """
    print("\n" + "=" * 70)
    print("演示 8: Skills 技能系统")
    print("=" * 70)

    # 1. 创建一个代码审查技能
    #
    # 匹配方式说明：
    # - keywords: 子字符串匹配（大小写不敏感）
    # - patterns: 正则表达式匹配
    #
    # 最佳实践：写更精确的 patterns 而非过于宽泛的 keywords
    #
    # 示例：
    #   ❌ keywords=["review"]           # 太宽泛，"don't review" 也会匹配
    #   ✅ patterns=[r"please\s+review", r"review\s+(this|my)\s+code"]  # 更精确
    #
    code_review_skill = Skill(
        name="code-review",
        description="代码审查技能，帮助审查和改进代码质量",
        content="""
你是一个专业的代码审查专家。当审查代码时，请：

1. **代码质量**: 检查代码是否清晰、可读、符合最佳实践
2. **潜在问题**: 识别可能的 bug、安全漏洞、性能问题
3. **改进建议**: 提供具体的改进建议

请用结构化的方式输出审查结果。
""",
        triggers=SkillTrigger(
            keywords=["review", "审查", "检查代码"],
            patterns=[r"review\s+(this|my|the)\s+code", r"审查.*代码", r"代码.*审查"],
        ),
        tools=SkillTools(
            allowed=["read", "glob", "grep"],  # 只允许读取类工具
            restricted=["bash", "write", "edit"],  # 禁止修改类工具
        ),
        version="1.0.0",
        author="Demo",
    )

    # 2. 创建技能注册表并注册技能
    registry = SkillRegistry()
    registry.register(code_review_skill)

    print(f"\n已注册技能: {list(registry.list_skills())}")

    # 3. 查找匹配的技能
    test_input = "请 review 这段代码"
    matches = registry.find_matching_skills(test_input)
    print(f"\n输入: '{test_input}'")
    print(f"匹配的技能: {[s.name for s in matches]}")

    # 4. 创建技能注入器
    injector = SkillInjector(registry)

    # 5. 演示如何将技能注入到 system prompt
    base_prompt = "你是一个有帮助的 AI 助手。"
    user_input = "请 review 这段代码"

    # 注入技能
    enhanced_prompt = injector.inject_skills(base_prompt, user_input)

    print("\n--- 原始 system prompt ---")
    print(base_prompt)
    print("\n--- 注入技能后的 system prompt ---")
    print(enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt)

    # 6. 实际使用技能与 Agent
    # 创建配置时使用增强后的 system prompt
    config_with_skill = HarnessConfig(
        model=MODEL,
        api_key=API_KEY,
        provider=PROVIDER,
        base_url=BASE_URL,
        system_prompt=enhanced_prompt,  # 使用注入了技能的 prompt
        max_iterations=3,
    )

    agent_with_skill = AgentHarness(config=config_with_skill)

    # 7. 实际运行使用技能的 Agent
    print("\n--- 使用技能运行 Agent ---")
    print(f"用户输入: {user_input}")

    result = await agent_with_skill.run(user_input)
    print("\nAgent 响应:")
    print("-" * 40)
    print(result.content[:800] if len(result.content) > 800 else result.content)

    # 8. 预览注入效果
    preview = injector.get_injection_preview(base_prompt, user_input)
    print("\n注入预览:")
    print(f"  - 匹配的技能: {preview['matching_skills']}")
    print(f"  - 将注入的技能数: {preview['total_to_inject']}")
    print(f"  - 原始 prompt 长度: {preview['original_prompt_length']}")
    print(f"  - 注入后长度: {preview['estimated_injected_length']}")

    # 8. 创建一个翻译技能
    translate_skill = Skill(
        name="translator",
        description="多语言翻译技能",
        content="你是一个专业的翻译专家，可以准确地在中文和英文之间进行翻译。",
        triggers=SkillTrigger(
            keywords=["translate", "翻译", "translate to"],
        ),
        tools=SkillTools(default_permission="allow"),
    )

    registry.register(translate_skill)
    print(f"\n注册翻译技能后，共有 {len(list(registry.list_skills()))} 个技能")

    # 9. 技能可以保存到文件
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "code-review.md"
        code_review_skill.to_file(skill_path)
        print(f"\n技能已保存到: {skill_path}")

        # 从文件加载
        loaded_skill = Skill.from_file(skill_path)
        print(f"从文件加载的技能: {loaded_skill.name}")
        print(f"触发关键词: {loaded_skill.triggers.keywords}")

    print("\n✅ Skills 技能系统演示完成")


# ============================================================================
# 演示 9: Skill 注入与批量加载
# ============================================================================

async def demo_skill_injection():
    """
    演示 9: Skill 注入与批量加载

    功能:
    - SkillInjector 将技能注入到 system prompt
    - SkillLoader 从目录批量加载技能
    - 自动匹配用户输入触发技能

    学习要点:
    - 技能可以动态注入到 prompt 中
    - 支持从目录批量加载 .md 文件
    - 根据用户输入自动匹配相关技能
    """
    print("\n" + "=" * 70)
    print("演示 9: Skill 注入与批量加载")
    print("=" * 70)

    # 1. 创建注册表和注入器
    registry = SkillRegistry()
    injector = SkillInjector(
        registry=registry,
        config=InjectionConfig(
            max_skills_per_prompt=3,
            inject_method="append",
        ),
    )

    # 2. 注册一些技能
    skill1 = Skill(
        name="code-review",
        description="代码审查",
        content="你是代码审查专家，请仔细检查代码质量。",
        triggers=SkillTrigger(keywords=["review", "审查"]),
    )
    skill2 = Skill(
        name="translator",
        description="翻译专家",
        content="你是翻译专家，可以准确翻译各种语言。",
        triggers=SkillTrigger(keywords=["翻译", "translate"]),
    )

    registry.register(skill1)
    registry.register(skill2)

    # 3. 测试技能注入
    system_prompt = "你是一个有帮助的 AI 助手。"
    user_input = "请 review 这段代码"

    injected_prompt = injector.inject_skills(system_prompt, user_input)

    print("\n原始 system prompt:")
    print(f"  {system_prompt}")
    print("\n用户输入:")
    print(f"  {user_input}")
    print("\n注入后的 prompt (包含匹配的技能):")
    print("-" * 40)
    print(injected_prompt[:500] + "..." if len(injected_prompt) > 500 else injected_prompt)

    # 4. SkillLoader 从目录加载
    loader = SkillLoader(registry)

    print("\n默认技能搜索路径:")
    from harness.skills.loader import DEFAULT_SKILL_PATHS
    for path in DEFAULT_SKILL_PATHS:
        exists = "✓" if path.exists() else "✗"
        print(f"  [{exists}] {path}")

    # 5. 从文件加载示例
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建技能目录
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # 创建技能文件
        skill_file = skills_dir / "test-skill.md"
        skill_file.write_text("""
---
name: test-skill
description: 测试技能
triggers:
  keywords:
    - test
    - 测试
---

你是一个测试专家，帮助用户进行测试。
""")

        # 从目录加载
        count = loader.load_from_dir(skills_dir)
        print(f"\n从目录加载了 {count} 个技能")
        print(f"已加载的技能: {list(registry.list_skills())}")

    # 6. 使用注入后的 prompt 运行 Agent
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        system_prompt=injected_prompt,
    )
    result = await agent.run(user_input)
    print(f"\nAgent 响应: {result.content[:200]}...")

    print("\n✅ Skill 注入与批量加载演示完成")



# ============================================================================
# 演示 10: MCP 服务器连接
# ============================================================================

async def demo_mcp_integration():
    """
    演示 10: MCP (Model Context Protocol) 服务器连接

    功能:
    - 配置 MCP 服务器
    - Stdio 和 HTTP 传输方式
    - 自动发现和注册工具
    - 与 AgentHarness 集成使用

    学习要点:
    - MCP 让 Agent 可以使用外部工具服务器
    - 支持 Stdio (本地进程) 和 HTTP (网络) 两种传输
    - 工具自动注册到 Agent
    """
    print("\n" + "=" * 70)
    print("演示 10: MCP (Model Context Protocol) 服务器连接")
    print("=" * 70)

    # 1. 配置 Stdio MCP 服务器 (本地进程)
    stdio_config = MCPServerConfig(
        name="local-tools",
        transport="stdio",
        command="python",
        args=["-m", "my_mcp_server"],  # 你的 MCP 服务器模块
        env={"DEBUG": "1"},
        enabled=True,
    )

    print("\nStdio MCP 配置:")
    print(f"  - 名称: {stdio_config.name}")
    print(f"  - 命令: {stdio_config.command} {' '.join(stdio_config.args)}")

    # 2. 配置 HTTP MCP 服务器 (网络服务)
    http_config = MCPServerConfig(
        name="remote-tools",
        transport="http",
        url="http://localhost:8080/mcp",
        headers={"Authorization": "Bearer your-token"},
        timeout=60.0,
    )

    print("\nHTTP MCP 配置:")
    print(f"  - 名称: {http_config.name}")
    print(f"  - URL: {http_config.url}")

    # 3. 创建 MCP 管理器
    manager = MCPManager()

    # 4. 添加服务器配置
    manager.add_server(stdio_config)
    print("\nMCP 管理器配置:")
    print("  - 默认配置路径: .mcp.json 或 ~/.harness/mcp.json")
    print(f"  - 已添加服务器: {[c.name for c in manager.list_server_configs()]}")

    # 5. 配置文件格式示例
    config_example = """
# .mcp.json 配置文件示例
{
    "mcpServers": {
        "filesystem": {
            "command": "mcp-filesystem",
            "args": ["/path/to/allowed/dir"]
        },
        "database": {
            "url": "http://localhost:8080/mcp",
            "headers": {
                "Authorization": "Bearer token"
            }
        }
    }
}
"""
    print("\n配置文件示例:")
    print(config_example)

    # -------------------------------------------------------------------------
    # 6. 与 AgentHarness 集成的完整示例
    # -------------------------------------------------------------------------
    print("\n--- 与 AgentHarness 集成 ---")
    print("""
    MCP 工具需要先连接服务器获取，然后注册到 AgentHarness：

    ┌─────────────────────────────────────────────────────────────┐
    │  1. MCPManager.connect_server()  → 获取 MCP 工具           │
    │    ↓                                                        │
    │  2. AgentHarness(tools=mcp_tools)  → 注册到 Agent          │
    │    ↓                                                        │
    │  3. agent.run("使用工具完成任务")  → Agent 自动调用 MCP 工具│
    └─────────────────────────────────────────────────────────────┘
    """)

    # 完整的集成代码示例
    print("\n--- 完整集成代码 ---")
    print("""
    import asyncio
    from harness import AgentHarness, MCPManager, MCPServerConfig

    async def run_with_mcp():
        # Step 1: 创建 MCP 管理器并连接服务器
        manager = MCPManager()

        # 方式 A: 从配置文件加载
        manager.load_from_file(".mcp.json")

        # 方式 B: 手动添加配置
        manager.add_server(MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="mcp-filesystem",
            args=["/allowed/path"],
        ))

        # Step 2: 连接到 MCP 服务器
        try:
            await manager.connect_server("filesystem")
            print("✅ 已连接到 MCP 服务器")
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return

        # Step 3: 获取 MCP 服务器提供的工具
        mcp_tools = manager.get_server_tools("filesystem")
        print(f"可用工具: {[t.name for t in mcp_tools]}")

        # Step 4: 创建 Agent 并注册 MCP 工具
        agent = AgentHarness(
            model=MODEL,
            tools=mcp_tools,  # 将 MCP 工具注册到 Agent
        )

        # Step 5: Agent 自动使用 MCP 工具
        result = await agent.run("读取 /allowed/path/config.json 的内容")
        print(f"结果: {result.content}")

        # Step 6: 清理 - 断开所有连接
        await manager.disconnect_all()

    asyncio.run(run_with_mcp())
    """)

    # -------------------------------------------------------------------------
    # 7. 高级集成：混合使用内置工具和 MCP 工具
    # -------------------------------------------------------------------------
    print("\n--- 高级集成：混合使用内置工具和 MCP 工具 ---")
    print("""
    from harness import AgentHarness, ReadTool, GlobTool, MCPManager

    async def run_with_mixed_tools():
        manager = MCPManager()
        await manager.connect_server("database")  # 假设有数据库 MCP

        # 内置工具 + MCP 工具
        all_tools = [
            ReadTool(),      # 内置：文件读取
            GlobTool(),      # 内置：文件搜索
        ] + manager.get_server_tools("database")  # MCP：数据库操作

        agent = AgentHarness(
            model=MODEL,
            tools=all_tools,
        )

        # Agent 可以同时使用内置工具和 MCP 工具
        result = await agent.run('''
            1. 读取 config.json 获取数据库配置
            2. 连接数据库查询用户表
            3. 输出结果
        ''')

        await manager.disconnect_all()
        return result
    """)

    print("\n✅ MCP 与 AgentHarness 集成演示完成")
    print("   注意: 实际连接需要运行 MCP 服务器")


# ============================================================================
# 演示 11: Security 安全系统 - 开箱即用
# ============================================================================

async def demo_security_system():
    """
    演示 10: Security 安全系统 - 开箱即用

    功能:
    - 通过 SecurityConfig 自动启用所有安全功能
    - 输入验证（含 Prompt 注入检测）
    - 输出脱敏
    - 审计日志
    - 沙箱执行

    学习要点:
    - 只需配置 SecurityConfig，安全功能自动生效
    - 默认启用所有安全特性，开箱即用
    - 无需手动集成各个组件
    """
    print("\n" + "=" * 70)
    print("演示 11: Security 安全系统 - 开箱即用")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 开箱即用：通过 SecurityConfig 自动启用安全功能
    # -------------------------------------------------------------------------
    print("\n--- SecurityConfig 自动启用安全功能 ---")
    print("""
    ✅ 安全组件现已自动整合到 AgentHarness 中！

    ┌─────────────────────────────────────────────────────────────┐
    │  用户输入 → AgentHarness.run()                              │
    │    ↓                                                        │
    │  自动: InputValidator.validate()  ← 验证输入，过滤注入      │
    │    ↓                                                        │
    │  自动: BashTool + LightweightSandbox  ← 沙箱执行命令        │
    │    ↓                                                        │
    │  自动: ResultSanitizer.sanitize()  ← 输出脱敏               │
    │    ↓                                                        │
    │  自动: AuditLogger.log()  ← 记录操作审计                    │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 使用 SecurityConfig 配置安全选项
    from harness import HarnessConfig

    security_config = SecurityConfig(
        # 输入验证
        enable_input_validation=True,      # 输入验证（默认启用）
        check_prompt_injection=True,       # Prompt 注入检测（默认启用）
        max_input_length=100000,           # 最大输入长度

        # 输出脱敏
        enable_output_sanitization=True,   # 输出脱敏（默认启用）
        max_output_length=100000,          # 最大输出长度

        # 审计日志
        enable_audit_log=True,             # 审计日志（默认启用）
        audit_log_dir="~/.harness/audit",  # 审计日志目录
        audit_retention_days=30,           # 审计日志保留天数

        # 沙箱配置
        enable_sandbox=True,               # 沙箱执行（默认启用）
        sandbox_max_execution_time=30.0,   # 最大执行时间（秒）
        sandbox_max_output_size=1_000_000, # 最大输出大小（字节）
        sandbox_blocked_commands=[         # 阻止的命令
            "rm -rf /",
            "sudo",
            "chmod -R 777",
            "mkfs",
        ],
        sandbox_blocked_patterns=[         # 阻止的命令模式
            "rm -rf",
            "curl | bash",
            "wget | bash",
        ],
        sandbox_allowed_commands=None,     # None = 允许所有非阻止命令
        sandbox_allowed_env_vars=[         # 允许传递的环境变量
            "PATH", "HOME", "USER", "LANG",
        ],
    )

    print("\n安全配置:")
    print(f"  - 输入验证: {security_config.enable_input_validation}")
    print(f"  - Prompt 注入检测: {security_config.check_prompt_injection}")
    print(f"  - 输出脱敏: {security_config.enable_output_sanitization}")
    print(f"  - 审计日志: {security_config.enable_audit_log}")
    print(f"  - 沙箱: {security_config.enable_sandbox}")
    print(f"  - 沙箱最大执行时间: {security_config.sandbox_max_execution_time}s")

    # 创建带安全配置的 Agent
    secure_agent = AgentHarness(
        config=HarnessConfig(
            model=MODEL,
            api_key=API_KEY,
            provider=PROVIDER,
            base_url=BASE_URL,
            security=security_config,  # 传入安全配置
        ),
        tools=[ReadTool(), GlobTool()],
    )

    print("\n✅ Agent 已自动启用所有安全功能！")

    # 测试自动安全功能
    print("\n测试自动安全运行:")
    test_input = "读取 pyproject.toml 文件的前 10 行"
    print(f"  用户输入: {test_input}")

    result = await secure_agent.run(test_input, session_id="security-demo")
    print(f"\n  Agent 响应:\n  {result.content[:200]}...")

    # 查看审计日志
    print("\n审计日志已自动记录到 ~/.harness/audit/")

    # -------------------------------------------------------------------------
    # 禁用部分安全功能示例
    # -------------------------------------------------------------------------
    print("\n--- 禁用部分安全功能 ---")
    print("""
    # 如果需要禁用某些安全功能，只需设置对应配置项：

    security_config = SecurityConfig(
        enable_input_validation=False,  # 禁用输入验证
        enable_audit_log=False,         # 禁用审计日志
    )

    # 或者完全禁用所有安全功能：
    agent = AgentHarness(
        config=HarnessConfig(security=None),  # 不传 security 配置
    )
    """)

    print("\n✅ Security 安全系统演示完成")


# ============================================================================
# 演示 12: Observability 可观测性
# ============================================================================

async def demo_observability():
    """
    演示 12: Observability 可观测性

    功能:
    - OpenTelemetry 集成
    - 配置追踪导出
    - Span 构建和使用
    - 与 AgentHarness 集成追踪

    学习要点:
    - 集成 Jaeger、Datadog 等观测平台
    - 追踪 Agent 执行过程
    - 调试和性能分析
    - 在 Agent 运行时收集追踪数据
    """
    print("\n" + "=" * 70)
    print("演示 12: Observability 可观测性")
    print("=" * 70)

    # 1. 检查 OpenTelemetry 是否可用
    from harness.core.observability import OTEL_AVAILABLE

    print(f"\nOpenTelemetry 可用: {OTEL_AVAILABLE}")

    if not OTEL_AVAILABLE:
        print("  提示: 安装 opentelemetry-api 和 opentelemetry-sdk 启用此功能")
        print("  pip install opentelemetry-api opentelemetry-sdk")

    # 2. 配置可观测性
    config = ObservabilityConfig(
        service_name="harness-demo",
        service_version="1.0.0",
        enabled=True,
        export_console=True,  # 输出到控制台用于调试
        export_otlp=False,    # 导出到 OTLP 端点（需要 Jaeger 等）
        sample_rate=1.0,
    )

    print("\n配置:")
    print(f"  - 服务名称: {config.service_name}")
    print(f"  - 控制台输出: {config.export_console}")
    print(f"  - OTLP 导出: {config.export_otlp}")

    # 3. 快速初始化
    manager = ObservabilityManager(config=config)
    print("\n可观测性管理器已创建")
    print(f"  - 已启用: {manager.is_enabled}")

    # -------------------------------------------------------------------------
    # 4. 开箱即用：与 AgentHarness 自动集成
    # -------------------------------------------------------------------------
    print("\n--- 4. 开箱即用：与 AgentHarness 自动集成 ---")
    print("""
    ✅ 可观测性现已可通过配置自动启用！

    ┌─────────────────────────────────────────────────────────────┐
    │  AgentHarness(config=HarnessConfig(                        │
    │      observability=ObservabilityConfig(                    │
    │          enabled=True,                                      │
    │          export_otlp=True,                                  │
    │          otlp_endpoint="http://jaeger:4317",              │
    │      )                                                     │
    │  ))                                                         │
    │    ↓                                                        │
    │  自动启用 OpenTelemetry 追踪                               │
    │    ↓                                                        │
    │  agent.run() → 自动记录 LLM 调用、工具执行、Token 使用     │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 使用 HarnessConfig + ObservabilityConfig
    from harness import HarnessConfig

    obs_config = ObservabilityConfig(
        enabled=True,
        service_name="harness-demo",
        export_console=True,
        export_otlp=False,  # 设置为 True 并配置 otlp_endpoint 连接 Jaeger
    )

    # 创建带可观测性的 Agent
    if OTEL_AVAILABLE:
        print("\n创建带可观测性的 Agent:")
        traced_agent = AgentHarness(
            config=HarnessConfig(
                model=MODEL,
                api_key=API_KEY,
                provider=PROVIDER,
                base_url=BASE_URL,
                observability=obs_config,  # 传入可观测性配置
            ),
            tools=[ReadTool()],
        )

        print("  ✅ Agent 已自动启用 OpenTelemetry 追踪！")

        # 运行 Agent（自动追踪）
        result = await traced_agent.run("你好，请简单介绍你自己。")
        print(f"\n  响应: {result.content[:100]}...")
        print("  ✅ 追踪数据已自动记录")
    else:
        print("\nOpenTelemetry 未安装，显示配置示例:")
        print("""
    # 安装: pip install opentelemetry-api opentelemetry-sdk

    from harness import AgentHarness, HarnessConfig, ObservabilityConfig

    # 创建带可观测性的 Agent
    agent = AgentHarness(
        model=MODEL,  # 使用你配置的模型
        config=HarnessConfig(
            observability=ObservabilityConfig(
                enabled=True,               # 启用追踪
                service_name="my-agent",    # 服务名称
                export_console=True,        # 控制台输出（调试）
                export_otlp=True,           # 导出到 OTLP
                otlp_endpoint="http://jaeger:4317",  # Jaeger 端点
            ),
        ),
        tools=[ReadTool()],
    )

    # 运行 Agent，追踪自动生效
    result = await agent.run("分析项目结构")
    # 追踪数据会自动导出到 Jaeger/Datadog
    """)

    # -------------------------------------------------------------------------
    # 5. 高级集成：自定义追踪
    # -------------------------------------------------------------------------
    print("\n--- 高级集成：自定义追踪 ---")
    print("""
    from harness.core.observability import get_tracer

    tracer = get_tracer("my-app")

    # 自定义追踪逻辑
    with tracer.start_as_current_span("custom.operation") as span:
        span.set_attribute("user.id", "user-001")
        span.add_event("开始处理")

        result = await agent.run("任务")

        span.add_event("处理完成")
        span.set_attribute("result.length", len(result.content))
    """)

    print("\n✅ Observability 与 AgentHarness 集成演示完成")


# ============================================================================
# 演示 13: 多级成本控制与异步存储
# ============================================================================

async def demo_advanced_cost_control():
    """
    演示 13: 多级成本控制与异步存储

    功能:
    - InMemoryCostStorage 内存存储
    - 用户级预算追踪
    - 全局预算追踪
    - 与 AgentHarness 集成控制成本

    学习要点:
    - 多进程场景使用 SQLite 存储
    - 追踪每个用户的使用量
    - 设置全局预算限制
    - 在 Agent 运行前后检查和控制预算
    """
    print("\n" + "=" * 70)
    print("演示 13: 多级成本控制与异步存储")
    print("=" * 70)

    # 1. 内存成本存储
    storage = InMemoryCostStorage()

    # 记录用户使用量
    user1_usage = storage.record_user_usage("user-001", input_tokens=1000, output_tokens=500)
    user2_usage = storage.record_user_usage("user-002", input_tokens=2000, output_tokens=1000)

    print("\n用户使用量:")
    print(f"  user-001: {user1_usage.daily_tokens} tokens")
    print(f"  user-002: {user2_usage.daily_tokens} tokens")

    # 记录全局使用量
    global_usage = storage.record_global_usage(cost_usd=0.05, tokens=4500)
    print("\n全局使用量:")
    print(f"  每日成本: ${global_usage.daily_cost_usd:.4f}")
    print(f"  每日 tokens: {global_usage.daily_tokens}")

    # 2. 多级预算配置
    cost_config = CostConfig(
        max_tokens_per_session=10000,      # 会话级
        max_iterations_per_request=20,
        daily_token_limit=100000,          # 用户级
        hourly_request_limit=100,
        global_daily_budget_usd=50.0,      # 全局级
    )

    print("\n多级预算配置:")
    print(f"  会话级: {cost_config.max_tokens_per_session} tokens/会话")
    print(f"  用户级: {cost_config.daily_token_limit} tokens/天")
    print(f"  全局级: ${cost_config.global_daily_budget_usd}/天")

    # -------------------------------------------------------------------------
    # 3. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 与 AgentHarness 集成 ---")
    print("""
    多级成本控制与 AgentHarness 的集成方式：

    ┌─────────────────────────────────────────────────────────────┐
    │  用户请求                                                    │
    │    ↓                                                        │
    │  检查用户预算 (daily_token_limit)                           │
    │    ↓ 通过                                                   │
    │  检查全局预算 (global_daily_budget_usd)                     │
    │    ↓ 通过                                                   │
    │  agent.run() 执行                                           │
    │    ↓                                                        │
    │  记录 Token 使用到 storage                                  │
    │    ↓                                                        │
    │  检查是否超限，超限则阻止后续请求                           │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 4. 实际集成代码
    print("\n--- 实际集成代码 ---")

    # 创建成本控制器

    controller = CostController(config=cost_config, storage=storage)  # noqa: F841

    # 创建 Agent
    cost_controlled_agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
    )

    # 定义带预算控制的运行函数
    user_id = "user-001"

    async def run_with_budget_control(user_input: str, user_id: str) -> str:
        """带预算控制的 Agent 运行"""

        # Step 1: 检查用户预算
        user_usage = storage.get_user_usage(user_id)
        if user_usage.daily_tokens >= cost_config.daily_token_limit:
            return f"❌ 用户 {user_id} 今日预算已用尽"

        # Step 2: 检查全局预算
        global_usage = storage.get_global_usage()
        if global_usage.daily_cost_usd >= cost_config.global_daily_budget_usd:
            return "❌ 系统全局预算已用尽，请明天再试"

        # Step 3: 运行 Agent
        result = await cost_controlled_agent.run(user_input, session_id=f"session-{user_id}")

        # Step 4: 记录使用量
        storage.record_user_usage(
            user_id,
            input_tokens=result.token_usage.input_tokens,
            output_tokens=result.token_usage.output_tokens,
        )
        storage.record_global_usage(
            cost_usd=result.token_usage.total_tokens * 0.00001,  # 假设价格
            tokens=result.token_usage.total_tokens,
        )

        # Step 5: 检查是否需要警告
        new_usage = storage.get_user_usage(user_id)
        remaining = cost_config.daily_token_limit - new_usage.daily_tokens
        if remaining < cost_config.daily_token_limit * 0.1:
            print(f"  ⚠️ 警告: 用户 {user_id} 剩余预算不足 10%")

        return result.content

    # 测试预算控制运行
    print(f"\n测试预算控制运行 (用户: {user_id}):")
    test_input = "你好，请用 50 字介绍一下 Python"
    print(f"  输入: {test_input}")

    response = await run_with_budget_control(test_input, user_id)
    print(f"  响应: {response[:100]}...")

    # 显示当前使用量
    final_usage = storage.get_user_usage(user_id)
    print(f"\n用户 {user_id} 今日累计使用:")
    print(f"  - Tokens: {final_usage.daily_tokens}")
    print(f"  - 剩余: {cost_config.daily_token_limit - final_usage.daily_tokens}")

    # -------------------------------------------------------------------------
    # 5. 异步 SQLite 存储（生产环境推荐）
    # -------------------------------------------------------------------------
    print("\n--- 异步 SQLite 存储（生产环境推荐）---")
    print("""
    # 创建异步存储（WAL 模式 + 连接池）
    store = AsyncSQLiteSessionStore(
        db_path="~/.harness/sessions.db",
        pool_size=5,
        timeout=30.0,
    )

    # 异步保存会话
    await store.save(session)

    # 异步加载会话
    session = await store.load("session-id")

    # 关闭连接池
    await store.close()
    """)

    # -------------------------------------------------------------------------
    # 6. 完整集成示例
    # -------------------------------------------------------------------------
    print("\n--- 完整集成示例：多租户成本控制 ---")
    print("""
    class TenantAwareAgent:
        def __init__(self, storage: InMemoryCostStorage, config: CostConfig):
            self.storage = storage
            self.config = config
            self.agent = AgentHarness(model=MODEL)

        async def run(self, user_id: str, prompt: str) -> str:
            # 预检查
            if not self._check_budget(user_id):
                raise BudgetExceededError(f"用户 {user_id} 预算已用尽")

            # 执行
            result = await self.agent.run(prompt, session_id=user_id)

            # 后记录
            self._record_usage(user_id, result.token_usage)

            return result.content

        def _check_budget(self, user_id: str) -> bool:
            usage = self.storage.get_user_usage(user_id)
            return usage.daily_tokens < self.config.daily_token_limit

        def _record_usage(self, user_id: str, usage: TokenUsage):
            self.storage.record_user_usage(
                user_id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )

    # 使用
    tenant_agent = TenantAwareAgent(storage, cost_config)
    result = await tenant_agent.run("user-001", "你好")
    """)

    print("\n✅ 多级成本控制与 AgentHarness 集成演示完成")


# ============================================================================
# 演示 14: 中断与恢复
# ============================================================================

async def demo_interrupt_and_resume():
    """
    演示 14: 中断与恢复

    功能:
    - 中断长时间运行的任务
    - 保存执行状态
    - 从中断点恢复执行
    - 与 AgentHarness 集成

    学习要点:
    - agent.interrupt() 中断执行
    - LoopSnapshot 保存状态
    - resume_from_snapshot() 恢复
    - 快照持久化用于断点续传
    """
    print("\n" + "=" * 70)
    print("演示 14: 中断与恢复")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 与 AgentHarness 集成概述
    # -------------------------------------------------------------------------
    print("\n--- 与 AgentHarness 集成 ---")
    print("""
    中断与恢复功能与 AgentHarness 的集成方式：

    ┌─────────────────────────────────────────────────────────────┐
    │  场景 1: 超时中断                                           │
    │  ───────────────────                                        │
    │  agent.run() → 超时 → agent.interrupt() → 保存快照         │
    │                                                              │
    │  场景 2: 用户取消                                           │
    │  ───────────────────                                        │
    │  用户点击取消 → agent.interrupt() → 返回部分结果            │
    │                                                              │
    │  场景 3: 断点续传                                           │
    │  ───────────────────                                        │
    │  保存快照 → 存储到文件 → 下次加载 → 恢复执行                │
    └─────────────────────────────────────────────────────────────┘
    """)

    # -------------------------------------------------------------------------
    # 2. 基本使用
    # -------------------------------------------------------------------------
    print("\n--- 2. 基本使用 ---")

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool()],
    )

    # 正常执行任务
    print("\n执行任务...")
    result = await agent.run("读取 pyproject.toml 文件，告诉我项目名称是什么。")

    print(f"\n响应: {result.content[:200]}...")

    # -------------------------------------------------------------------------
    # 3. 创建快照（用于恢复）
    # -------------------------------------------------------------------------
    print("\n--- 3. 创建快照 ---")


    # 使用公开 API 创建快照（需要先有 session）
    snapshot = agent.create_snapshot(
        session_id="demo-session",
        iteration=result.iterations,
    )

    print("\n已创建执行快照:")
    print(f"  - Session ID: {snapshot.session_id}")
    print(f"  - 消息数: {len(snapshot.messages)}")
    print(f"  - 迭代次数: {snapshot.current_iteration}")

    # 快照可以序列化保存
    snapshot_dict = snapshot.to_dict()
    print(f"\n快照可以序列化为 JSON，大小: {len(str(snapshot_dict))} 字节")

    # -------------------------------------------------------------------------
    # 4. 中断执行的集成代码
    # -------------------------------------------------------------------------
    print("\n--- 4. 中断执行集成代码 ---")
    print("""
    import asyncio
    from harness import AgentHarness, LoopSnapshot

    async def run_with_timeout(agent: AgentHarness, prompt: str, timeout: float):
        '''带超时中断的运行'''

        async def run_task():
            return await agent.run(prompt)

        async def interrupt_after():
            await asyncio.sleep(timeout)
            agent.interrupt()
            print("⏰ 任务超时，已中断")

        # 并行运行任务和超时检查
        task = asyncio.create_task(run_task())
        timeout_task = asyncio.create_task(interrupt_after())

        try:
            result = await task
            timeout_task.cancel()
            return result
        except asyncio.CancelledError:
            # 创建快照用于恢复（使用公开 API）
            snapshot = agent.create_snapshot(session_id="timeout-session")
            print(f"已保存快照: {snapshot.session_id}")
            return None

    # 使用
    agent = AgentHarness(model=MODEL, tools=[ReadTool()])
    result = await run_with_timeout(agent, "复杂任务...", timeout=30.0)
    """)

    # -------------------------------------------------------------------------
    # 5. 快照持久化
    # -------------------------------------------------------------------------
    print("\n--- 5. 快照持久化 ---")
    print("""
    import json
    from pathlib import Path

    # 保存快照到文件
    def save_snapshot(snapshot: LoopSnapshot, path: str):
        data = snapshot.to_dict()
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"快照已保存到: {path}")

    # 从文件加载快照
    def load_snapshot(path: str) -> LoopSnapshot:
        data = json.loads(Path(path).read_text())
        return LoopSnapshot.from_dict(data)

    # 使用场景：断点续传
    async def resume_from_file(agent: AgentHarness, snapshot_path: str):
        snapshot = load_snapshot(snapshot_path)
        # 使用公开 API 恢复执行
        return await agent.restore_from_snapshot(snapshot)
    """)

    print("\n✅ 中断与恢复与 AgentHarness 集成演示完成")


# ============================================================================
# 演示 15: 配置管理
# ============================================================================

async def demo_configuration():
    """
    演示 15: 配置管理

    功能:
    - 使用 HarnessConfig 配置所有参数
    - 从文件加载配置
    - 自动检测模型参数

    学习要点:
    - HarnessConfig 集中配置
    - context_window 自动设置
    - 可以保存为文件共享配置
    """
    print("\n" + "=" * 70)
    print("演示 15: 配置管理")
    print("=" * 70)

    # 创建详细配置
    config = HarnessConfig(
        model=MODEL,
        api_key=API_KEY,
        provider=PROVIDER,
        base_url=BASE_URL,

        # 上下文设置
        context_window="auto",  # 自动根据模型设置
        max_tokens="auto",      # 自动根据模型设置

        # 行为设置
        max_iterations=20,
        temperature=0.7,

        # 记忆设置
        memory_dir=".harness/memory",
        session_window=50,

        # 系统提示
        system_prompt="你是一个专业的编程助手。",
    )

    print("配置详情:")
    print(f"  - 模型: {config.model}")
    print(f"  - Provider: {config.provider}")
    print(f"  - 上下文窗口: {config.get_context_window()} tokens")
    print(f"  - 输出限制: {config.get_max_tokens()} tokens")
    print(f"  - 最大迭代: {config.max_iterations}")
    print(f"  - 温度: {config.temperature}")

    # 使用配置创建 Agent
    agent = AgentHarness(config=config)

    result = await agent.run("你好，请简单介绍一下你自己。")
    print(f"\n响应: {result.content}")


# ============================================================================
# 演示 16: 完整工作流
# ============================================================================

async def demo_complete_workflow():
    """
    演示 16: 完整工作流

    功能:
    - 结合所有功能
    - 实际场景模拟
    - 端到端演示

    学习要点:
    - 真实使用场景
    - 各功能如何配合
    - 最佳实践
    """
    print("\n" + "=" * 70)
    print("演示 16: 完整工作流 - 代码分析助手")
    print("=" * 70)

    # 1. 配置 Agent
    config = HarnessConfig(
        model=MODEL,
        api_key=API_KEY,
        provider=PROVIDER,
        base_url=BASE_URL,
        max_iterations=10,
        system_prompt="你是一个代码分析专家，帮助用户理解代码结构和功能。",
    )

    # 2. 创建带工具的 Agent
    agent = AgentHarness(
        config=config,
        tools=[
            ReadTool(),
            GlobTool(),
            GrepTool(),
        ],
    )

    # 3. 定义进度追踪
    events = []
    def track_progress(event: ProgressEvent):
        events.append(event)

    # 4. 执行任务
    print("\n任务: 分析项目结构")
    result = await agent.run(
        "请分析这个项目:\n"
        "1. 使用 glob 找到所有 Python 文件\n"
        "2. 读取 src/harness/__init__.py 了解导出的 API\n"
        "3. 总结这个项目的主要功能",
        on_progress=track_progress,
    )

    # 5. 输出结果
    print("\n" + "-" * 70)
    print("分析结果:")
    print("-" * 70)
    print(result.content[:1000])

    # 6. 统计
    print("\n" + "-" * 70)
    print("执行统计:")
    print(f"  - 总迭代次数: {result.iterations}")
    print(f"  - 总 Token 消耗: {result.token_usage.total_tokens}")
    print(f"  - 工具调用次数: {sum(1 for e in events if e.type == ProgressEventType.TOOL_CALL)}")
    print(f"  - 执行状态: {result.status.value}")


# ============================================================================
# 演示 17: Lifecycle Hooks - 工具执行前后的钩子系统 (P0)
# ============================================================================

async def demo_lifecycle_hooks():
    """
    演示 17: Lifecycle Hooks - 工具执行前后的钩子系统 (P0)

    功能:
    - 创建自定义 LifecycleHook 子类
    - 使用 HookManager 注册和管理钩子
    - 展示内置钩子: LoggingHook, AbortOnDangerousToolHook, MaxToolCallsHook
    - 与 AgentHarness 集成使用钩子

    学习要点:
    - HookPoint 定义钩子触发时机 (BEFORE_TOOL, AFTER_TOOL 等)
    - HookAction 控制钩子行为 (CONTINUE, ABORT, MODIFY)
    - 钩子可以拦截、修改或阻止工具调用
    - 内置钩子提供常见的安全和日志功能
    """
    print("\n" + "=" * 70)
    print("演示 17: Lifecycle Hooks - 工具执行前后的钩子系统 (P0)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 自定义钩子 - 继承 LifecycleHook
    # -------------------------------------------------------------------------
    print("\n--- 1. 自定义钩子 ---")

    class TimingHook(LifecycleHook):
        """记录工具执行时间的钩子"""

        def __init__(self):
            self._start_times = {}
            self.timings = {}

        async def execute(self, context: HookContext) -> HookResult:
            """钩子执行逻辑"""
            if context.hook_point == HookPoint.BEFORE_TOOL_EXECUTE:
                tool_name = context.tool_name
                self._start_times[tool_name] = asyncio.get_event_loop().time()
                print(f"  ⏱️ 开始执行工具: {tool_name}")
                return HookResult(action=HookAction.CONTINUE)

            elif context.hook_point == HookPoint.AFTER_TOOL_EXECUTE:
                tool_name = context.tool_name
                start = self._start_times.get(tool_name, 0)
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                self.timings[tool_name] = elapsed
                print(f"  ⏱️ 工具 {tool_name} 执行完成，耗时: {elapsed:.1f}ms")
                return HookResult(action=HookAction.CONTINUE)

            return HookResult(action=HookAction.CONTINUE)

    timing_hook = TimingHook()
    print("已创建自定义钩子: TimingHook")

    # -------------------------------------------------------------------------
    # 2. 内置钩子 - LoggingHook
    # -------------------------------------------------------------------------
    print("\n--- 2. 内置钩子 ---")

    # 日志钩子 - 记录所有工具调用
    logging_hook = LoggingHook()
    print("日志钩子: LoggingHook")

    # 阻止危险工具钩子 - 阻止 bash, write 等危险操作
    abort_hook = AbortOnDangerousToolHook(
        blocked_tools=["bash", "write_file", "edit_file"],
    )
    print("阻止危险工具钩子: AbortOnDangerousToolHook")

    # 限制工具调用次数钩子（需要指定工具名称）
    max_calls_hook = MaxToolCallsHook(tool_name="bash", max_calls=10)
    print("限制调用次数钩子: MaxToolCallsHook (工具 'bash' 最多 10 次)")

    # -------------------------------------------------------------------------
    # 3. 使用 HookManager 管理钩子
    # -------------------------------------------------------------------------
    print("\n--- 3. HookManager 管理钩子 ---")

    hook_manager = HookManager()
    hook_manager.register(
        timing_hook,
        points=[HookPoint.BEFORE_TOOL_EXECUTE, HookPoint.AFTER_TOOL_EXECUTE],
    )
    hook_manager.register(logging_hook)
    hook_manager.register(abort_hook, points=[HookPoint.BEFORE_TOOL_EXECUTE])
    hook_manager.register(max_calls_hook, points=[HookPoint.BEFORE_TOOL_EXECUTE])

    # 检查哪些 HookPoint 有注册的钩子
    print("已注册钩子到 HookManager:")
    for point in HookPoint:
        if hook_manager.has_hooks(point):
            print(f"  - {point.value}: 有钩子")

    # -------------------------------------------------------------------------
    # 4. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 4. 与 AgentHarness 集成 ---")
    print("""
    Lifecycle Hooks 与 AgentHarness 的集成方式：

    ┌─────────────────────────────────────────────────────────────┐
    │  AgentHarness.run("用户输入")                               │
    │    ↓                                                        │
    │  AgentLoop 执行循环                                         │
    │    ↓                                                        │
    │  LLM 返回工具调用 → on_before_tool()                        │
    │    ↓  HookAction.CONTINUE                                   │
    │  执行工具 → on_after_tool()                                 │
    │    ↓  HookAction.CONTINUE                                   │
    │  继续循环...                                                │
    │                                                             │
    │  如果 HookAction.ABORT → 跳过工具执行                       │
    │  如果 HookAction.MODIFY → 修改工具参数                      │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 创建带钩子的 Agent
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    # 注册钩子到 Agent 的循环
    for hook in [timing_hook, logging_hook, max_calls_hook]:
        agent.add_hook(hook)

    print("已注册钩子到 Agent 的循环")

    # 运行 Agent
    print("\n用户: 列出所有 Python 文件")
    result = await agent.run(
        "使用 glob 工具列出所有 *.py 文件。",
        verbose=False,
    )
    print(f"\n响应: {result.content[:200]}...")

    # 查看计时结果
    if timing_hook.timings:
        print("\n工具执行计时:")
        for tool, elapsed in timing_hook.timings.items():
            print(f"  - {tool}: {elapsed:.1f}ms")

    # -------------------------------------------------------------------------
    # 5. HookPoint 触发时机说明
    # -------------------------------------------------------------------------
    print("\n--- 5. HookPoint 触发时机 ---")
    print("""
    HookPoint 定义了钩子的触发时机：

    - BEFORE_TOOL_EXECUTE:  工具执行前 (可拦截、修改参数)
    - AFTER_TOOL_EXECUTE:   工具执行后 (可修改结果)
    - ON_LOOP_START:        Agent 循环开始
    - ON_LOOP_END:          Agent 循环结束
    - ON_ERROR:             发生错误时
    - ON_EXIT_ATTEMPT:      尝试退出时 (Ralph Loop 使用)
    """)

    print("\n✅ Lifecycle Hooks 演示完成")


# ============================================================================
# 演示 18: 动态系统提示 - SystemPromptBuilder (P0)
# ============================================================================

async def demo_dynamic_system_prompt():
    """
    演示 18: 动态系统提示 - SystemPromptBuilder (P0)

    功能:
    - 使用 SystemPromptBuilder 从多个源组装系统提示
    - 定义 SystemPromptSource (文本、文件、回调)
    - 使用 discover_project_context 发现项目上下文
    - 与 AgentHarness 集成使用动态提示

    学习要点:
    - 系统提示可以从多个源组合，按优先级排列
    - 文件源可以引用 AGENTS.md 等项目文件
    - content 可以是字符串或 Callable，支持动态生成
    - discover_project_context 自动发现项目信息
    """
    print("\n" + "=" * 70)
    print("演示 18: 动态系统提示 - SystemPromptBuilder (P0)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 SystemPromptBuilder
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 SystemPromptBuilder ---")

    config = SystemPromptConfig(
        base_prompt="你是一个有帮助的 AI 助手。",  # 基础系统提示
        auto_discover=True,          # 自动发现项目中的 AGENTS.md、MEMORY.md
        project_root=Path("."),      # 项目根目录（用于自动发现）
        section_separator="\n\n---\n\n",  # 各源之间的分隔符
    )

    builder = SystemPromptBuilder(config=config)
    print("已创建 SystemPromptBuilder")
    print(f"  - 基础提示: '{config.base_prompt}'")
    print(f"  - 自动发现: {config.auto_discover}")

    # -------------------------------------------------------------------------
    # 2. 添加不同类型的 SystemPromptSource
    # -------------------------------------------------------------------------
    print("\n--- 2. 添加不同类型的提示源 ---")

    # 文本源 - 直接提供内容
    builder.add_source(SystemPromptSource(
        name="base-role",
        content="你是一个专业的编程助手，擅长 Python 开发。",
        priority=100,  # 优先级越高越靠前
    ))
    print("  ✅ 添加文本源: base-role (priority=100)")

    # 回调源 - content 为 Callable，动态生成内容
    import datetime
    def get_time_context() -> str:
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M')}，请根据当前时间回答。"

    builder.add_source(SystemPromptSource(
        name="time-context",
        content=get_time_context,  # content 可以是字符串或 Callable
        priority=50,
    ))
    print("  ✅ 添加回调源: time-context (priority=50)")

    # 文件源 - 从文件读取内容
    # 如果存在 AGENTS.md，会自动加载项目说明
    builder.add_source(SystemPromptSource(
        name="agents-md",
        file_path=Path("AGENTS.md"),
        priority=80,
        required=False,  # 文件不存在时不报错
    ))
    print("  ✅ 添加文件源: agents-md (priority=80, 可选)")

    # -------------------------------------------------------------------------
    # 3. 构建系统提示
    # -------------------------------------------------------------------------
    print("\n--- 3. 构建系统提示 ---")

    system_prompt = builder.build()
    print(f"构建的系统提示长度: {len(system_prompt)} 字符")

    # 查看可用的源
    available_sources = builder.get_available_sources()
    print(f"可用源: {available_sources}")

    print("\n系统提示内容预览:")
    print("-" * 40)
    preview = system_prompt[:600] + "..." if len(system_prompt) > 600 else system_prompt
    print(preview)

    # -------------------------------------------------------------------------
    # 4. discover_project_context - 发现项目上下文
    # -------------------------------------------------------------------------
    print("\n--- 4. discover_project_context ---")

    project_context = discover_project_context()
    print("发现的项目上下文:")
    for key, value in project_context.items():
        if value:
            val_str = str(value)[:100]
            print(f"  - {key}: {val_str}")
    if not project_context:
        print("  (未发现 AGENTS.md、MEMORY.md 或 CLAUDE.md)")

    # -------------------------------------------------------------------------
    # 5. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 5. 与 AgentHarness 集成 ---")

    # 方式 1: 使用构建好的系统提示
    config_with_prompt = HarnessConfig(
        model=MODEL,
        api_key=API_KEY,
        provider=PROVIDER,
        base_url=BASE_URL,
        system_prompt=system_prompt,
        max_iterations=3,
    )

    agent = AgentHarness(config=config_with_prompt)

    result = await agent.run("你好，请介绍一下你自己，包括你的专长领域。")
    print(f"\nAgent 响应:\n{result.content[:300]}...")

    # -------------------------------------------------------------------------
    # 6. 动态更新系统提示
    # -------------------------------------------------------------------------
    print("\n--- 6. 动态更新系统提示 ---")
    print("""
    SystemPromptBuilder 支持动态更新：

    # 添加新的源
    builder.add_source(SystemPromptSource(
        name="user-preference",
        content="用户偏好使用中文回答。",
        priority=90,
    ))

    # 重新构建
    new_prompt = builder.build()

    # content 为 Callable 的源每次 build() 都会重新调用
    # 适合注入运行时信息（如时间、用户状态等）

    # 移除某个源
    builder.remove_source("time-context")
    """)

    print("\n✅ 动态系统提示演示完成")


# ============================================================================
# 演示 19: Ralph Loop - 长任务循环 (P1)
# ============================================================================

async def demo_ralph_loop():
    """
    演示 19: Ralph Loop - 长任务循环 (P1)

    功能:
    - 配置 RalphLoopConfig 控制循环行为
    - 创建 RalphLoopHook 注册到 Agent
    - 自定义 task_complete_check 判断任务是否完成
    - 防止长任务中的上下文焦虑

    学习要点:
    - Ralph Loop 适用于需要多步迭代的复杂任务
    - context_threshold 控制何时压缩上下文
    - task_complete_check 可以自定义完成条件
    - continuation_prompt_template 自定义继续循环的提示
    """
    print("\n" + "=" * 70)
    print("演示 19: Ralph Loop - 长任务循环 (P1)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 RalphLoopConfig
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 RalphLoopConfig ---")

    def check_complete(result_content: str) -> bool:
        """自定义完成检查：响应中包含 DONE 标记时视为完成"""
        return "DONE" in result_content or "完成" in result_content

    ralph_config = RalphLoopConfig(
        max_loops=5,                     # 最大循环次数
        context_threshold=0.8,           # 上下文使用率超 80% 时压缩
        task_complete_check=check_complete,  # 自定义完成检查
        continuation_prompt_template=(
            "以下是之前的进展摘要：\n{previous_response}\n\n请继续完成任务。"
        ),
        progress_dir=None,               # 进度保存目录（None 则不持久化）
    )

    print("Ralph Loop 配置:")
    print(f"  - 最大循环次数: {ralph_config.max_loops}")
    print(f"  - 上下文阈值: {ralph_config.context_threshold * 100}%")
    print(f"  - 自定义完成检查: {'是' if ralph_config.task_complete_check else '否'}")

    # -------------------------------------------------------------------------
    # 2. 创建 RalphLoopHook
    # -------------------------------------------------------------------------
    print("\n--- 2. 创建 RalphLoopHook ---")

    ralph_hook = RalphLoopHook(config=ralph_config)
    print("已创建 RalphLoopHook")

    # -------------------------------------------------------------------------
    # 3. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 3. 与 AgentHarness 集成 ---")
    print("""
    Ralph Loop 工作流程：

    ┌─────────────────────────────────────────────────────────────┐
    │  用户输入: "请重构整个项目的错误处理"                       │
    │    ↓                                                        │
    │  第 1 轮: Agent 分析项目，制定计划                          │
    │    ↓  task_complete_check → False                           │
    │  第 2 轮: Agent 修改第一个模块                              │
    │    ↓  上下文接近阈值 → 自动压缩历史                        │
    │  第 3 轮: Agent 继续修改其他模块                            │
    │    ↓  task_complete_check → True (包含"完成")               │
    │  输出最终结果                                               │
    └─────────────────────────────────────────────────────────────┘
    """)

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    # 注册 Ralph Loop Hook 到 Agent
    agent.add_hook(ralph_hook)
    print("已注册 RalphLoopHook 到 Agent")

    # 运行一个简单的任务
    print("\n用户: 列出项目中的 Python 文件并总结项目结构")
    result = await agent.run(
        "请使用 glob 工具列出所有 *.py 文件，然后简要总结项目结构。最后说'完成'。",
        verbose=False,
    )
    print(f"\n响应: {result.content[:300]}...")
    print(f"迭代次数: {result.iterations}")

    # -------------------------------------------------------------------------
    # 4. 使用场景说明
    # -------------------------------------------------------------------------
    print("\n--- 4. 使用场景 ---")
    print("""
    Ralph Loop 适合以下场景：

    1. 大规模代码重构 - 需要修改多个文件
    2. 自动化测试 - 需要多轮修复和验证
    3. 文档生成 - 需要分析大量文件后生成文档
    4. 数据迁移 - 需要分步处理大量数据

    关键参数调优：
    - max_loops: 根据任务复杂度设置 (通常 5-20)
    - context_threshold: 根据模型上下文窗口设置 (0.6-0.9)
    - task_complete_check: 根据任务定义完成标志
    - continuation_prompt_template: 自定义继续执行的提示模板
    """)

    print("\n✅ Ralph Loop 演示完成")


# ============================================================================
# 演示 20: Sub-Agent 管理 (P1)
# ============================================================================

async def demo_sub_agent():
    """
    演示 20: Sub-Agent 管理 (P1)

    功能:
    - 创建 SubAgentConfig 配置子代理
    - 使用 SubAgentManager 创建和管理子代理
    - 并行执行多个子代理任务
    - 收集子代理结果

    学习要点:
    - 子代理可以执行独立的子任务
    - 支持并行执行提高效率
    - SubAgentResult 包含执行结果和状态
    - 子代理可以有独立的系统提示和工具集
    """
    print("\n" + "=" * 70)
    print("演示 20: Sub-Agent 管理 (P1)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建主代理和 SubAgentManager
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建主代理和 SubAgentManager ---")

    parent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
    )

    manager = SubAgentManager(parent_agent=parent)
    print("已创建 SubAgentManager (基于主代理)")

    # -------------------------------------------------------------------------
    # 2. 创建 SubAgentConfig
    # -------------------------------------------------------------------------
    print("\n--- 2. 创建 SubAgentConfig ---")

    # 子代理 1: 代码分析
    config1 = SubAgentConfig(
        name="code-analyzer",
        task="分析代码结构和质量",
        system_prompt="你是一个代码分析专家，请简洁地分析代码。",
        tools=["read", "glob", "grep"],  # 允许的工具名
        max_iterations=3,
    )

    # 子代理 2: 文档生成
    config2 = SubAgentConfig(
        name="doc-generator",
        task="根据分析结果生成文档",
        system_prompt="你是一个技术文档专家，请根据给定的信息生成文档。",
        tools=["read"],  # 只读权限
        max_iterations=2,
        report_format="summary",  # 结果报告格式: summary, full, structured
    )

    print("子代理配置:")
    print(f"  - {config1.name}: {config1.task}")
    print(f"  - {config2.name}: {config2.task}")

    # -------------------------------------------------------------------------
    # 3. 创建和运行子代理
    # -------------------------------------------------------------------------
    print("\n--- 3. 创建和运行子代理 ---")

    # 创建子代理（spawn 返回配置中的名称）
    sub_agent_name_1 = await manager.spawn(config1)
    sub_agent_name_2 = await manager.spawn(config2)

    print(f"已创建子代理: {manager.list_sub_agents()}")
    print(f"  - spawn() 返回值即 config.name: '{sub_agent_name_1}', '{sub_agent_name_2}'")

    # 运行单个子代理（使用配置中的名称）
    print(f"\n运行子代理 '{config1.name}'...")
    result1: SubAgentResult = await manager.run(config1.name)
    print("子代理结果:")
    print(f"  - 名称: {result1.name}")
    print(f"  - 成功: {result1.success}")
    print(f"  - 状态: {result1.status.value}")
    if result1.summary:
        print(f"  - 概要: {result1.summary[:200]}...")
    print(f"  - 迭代次数: {result1.iterations}")

    # -------------------------------------------------------------------------
    # 4. 并行执行多个子代理
    # -------------------------------------------------------------------------
    print("\n--- 4. 并行执行多个子代理 ---")
    print("""
    SubAgentManager 支持并行执行多个子代理：

    ┌─────────────────────────────────────────────────────────────┐
    │  主代理                                                      │
    │    ├── SubAgent 1: 分析代码  ──→ SubAgentResult 1            │
    │    ├── SubAgent 2: 生成文档  ──→ SubAgentResult 2            │
    │    └── SubAgent 3: 运行测试  ──→ SubAgentResult 3            │
    │    ↓                                                        │
    │  汇总所有子代理结果                                          │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 并行运行所有待执行的子代理
    print("并行运行所有待执行的子代理...")
    results: dict[str, SubAgentResult] = await manager.run_all()
    print(f"\n并行执行完成，共 {len(results)} 个结果:")
    for name, result in results.items():
        status = "✅" if result.success else "❌"
        summary = result.summary[:100] if result.summary else "无概要"
        print(f"  - {name}: {status} {summary}")

    # -------------------------------------------------------------------------
    # 5. 子代理状态和结果
    # -------------------------------------------------------------------------
    print("\n--- 5. 子代理状态和结果 ---")
    print("""
    SubAgentStatus 状态:
    - PENDING:   等待执行
    - RUNNING:   正在执行
    - COMPLETED: 执行完成
    - FAILED:    执行失败
    - CANCELLED: 已取消

    SubAgentResult 包含:
    - name:             子代理名称
    - success:          是否成功
    - status:           执行状态
    - summary:          结果概要 (report_format="summary")
    - full_response:    完整响应 (report_format="full")
    - structured_result: 结构化结果 (report_format="structured")
    - iterations:       迭代次数
    - token_usage:      Token 使用量
    - error:            错误信息 (如果失败)
    """)

    print("\n✅ Sub-Agent 管理演示完成")


# ============================================================================
# 演示 21: 自验证钩子 (P2)
# ============================================================================

async def demo_self_verification():
    """
    演示 21: 自验证钩子 (P2)

    功能:
    - 创建 SelfVerificationConfig 配置验证规则
    - 创建 SelfVerificationHook 注册到 Agent
    - 代码修改后自动运行测试验证
    - 验证失败时自动注入错误信息供 LLM 修复

    学习要点:
    - 自验证适用于代码修改场景
    - trigger_tools 指定哪些工具触发验证
    - verify_on_change 控制是否每次修改都验证
    - 通过 Hook 机制无缝集成到 Agent 循环
    """
    print("\n" + "=" * 70)
    print("演示 21: 自验证钩子 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 SelfVerificationConfig
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 SelfVerificationConfig ---")

    verify_config = SelfVerificationConfig(
        # 测试命令
        test_command="pytest",
        test_args=["-x", "--tb=short"],  # pytest 参数

        # 验证触发条件：当使用 write 或 edit 工具后触发验证
        trigger_tools=["write", "edit", "write_file", "edit_file"],

        # 验证超时时间（秒）
        timeout=60.0,

        # 最大重试次数（测试失败后最多重试几次）
        max_retries=3,

        # 是否在每次代码修改后都验证
        verify_on_change=True,

        # 如果没有测试文件是否跳过
        skip_if_no_tests=True,

        # 测试文件匹配模式
        test_pattern="test_*.py",
    )

    print("自验证配置:")
    print(f"  - 测试命令: {verify_config.test_command} {' '.join(verify_config.test_args)}")
    print(f"  - 触发工具: {verify_config.trigger_tools}")
    print(f"  - 超时时间: {verify_config.timeout}s")
    print(f"  - 最大重试: {verify_config.max_retries}")
    print(f"  - 每次修改后验证: {verify_config.verify_on_change}")

    # -------------------------------------------------------------------------
    # 2. 创建 SelfVerificationHook
    # -------------------------------------------------------------------------
    print("\n--- 2. 创建 SelfVerificationHook ---")

    verify_hook = SelfVerificationHook(config=verify_config)
    print(f"已创建自验证钩子: {verify_hook}")

    # -------------------------------------------------------------------------
    # 3. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 3. 与 AgentHarness 集成 ---")
    print("""
    自验证钩子工作流程：

    ┌─────────────────────────────────────────────────────────────┐
    │  Agent 执行 edit 工具修改文件                                │
    │    ↓                                                        │
    │  SelfVerificationHook.execute() 触发                        │
    │  (hook_point = AFTER_TOOL_EXECUTE)                          │
    │    ↓                                                        │
    │  运行 test_command (如 pytest)                              │
    │    ↓                                                        │
    │  检查结果:                                                  │
    │    ✅ 测试通过 → HookAction.CONTINUE                        │
    │    ❌ 测试失败 → 注入错误信息，LLM 自动修复                 │
    │    ❌ 超过 max_retries → 停止验证，继续执行                │
    └─────────────────────────────────────────────────────────────┘
    """)

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    # 注册自验证钩子到 Agent
    agent.add_hook(verify_hook)
    print("已注册自验证钩子到 Agent")

    # 运行 Agent（当前只读操作，不会触发验证）
    result = await agent.run("请列出当前目录下的 Python 文件。")
    print(f"\n响应: {result.content[:200]}...")
    print("  (只读操作不会触发自验证)")

    # -------------------------------------------------------------------------
    # 4. 使用场景说明
    # -------------------------------------------------------------------------
    print("\n--- 4. 使用场景 ---")
    print("""
    自验证钩子适合以下场景：

    1. 代码修改 - 修改后自动运行 pytest
    2. 配置文件更新 - 验证配置格式正确
    3. 文档更新 - 检查链接和格式
    4. 数据库迁移 - 验证迁移脚本可执行

    最佳实践：
    - 设置 verify_on_change=True 在开发时实时验证
    - 配置合理的 timeout 避免长时间等待
    - 使用 max_retries 限制修复循环次数
    - 使用 skip_if_no_tests=True 在无测试时自动跳过
    - trigger_tools 只包含会修改代码的工具
    """)

    print("\n✅ 自验证钩子演示完成")


# ============================================================================
# 演示 22: 渐进式技能加载 (P2)
# ============================================================================

async def demo_progressive_skills():
    """
    演示 22: 渐进式技能加载 (P2)

    功能:
    - 创建 ProgressiveSkillLoader 三级加载
    - 使用 SkillMetadata 管理技能元信息
    - 根据用户输入匹配相关技能
    - 按需加载技能内容，优化上下文使用

    学习要点:
    - L1 (discover): 只加载名称和描述，用于匹配
    - L2 (load): 加载完整技能内容
    - L3 (with_references): 加载技能和关联的参考文档
    - 估算 token 使用量避免超出上下文窗口
    """
    print("\n" + "=" * 70)
    print("演示 22: 渐进式技能加载 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 ProgressiveSkillLoader
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 ProgressiveSkillLoader ---")

    import tempfile
    tmpdir = tempfile.mkdtemp()
    skills_dir = Path(tmpdir)

    # 创建一些技能文件用于演示
    (skills_dir / "code-review.md").write_text("""---
name: code-review
description: 代码审查技能，帮助审查和改进代码质量
triggers:
  keywords:
    - review
    - 审查
    - 代码
---

你是一个代码审查专家，请检查代码质量、潜在问题和改进建议。
""")
    (skills_dir / "testing.md").write_text("""---
name: testing
description: 测试技能，帮助编写和运行测试
triggers:
  keywords:
    - test
    - 测试
    - unit test
---

你是一个测试专家，请帮助编写全面的单元测试和集成测试。
""")
    (skills_dir / "deployment.md").write_text("""---
name: deployment
description: 部署技能，帮助配置和部署应用
triggers:
  keywords:
    - deploy
    - 部署
    - ci/cd
---

你是一个部署专家，请帮助配置 CI/CD 流水线和部署策略。
""")

    loader = ProgressiveSkillLoader(cache_size=50)
    print("已创建 ProgressiveSkillLoader")

    # -------------------------------------------------------------------------
    # 2. Level 1: 发现技能 - 只加载元信息
    # -------------------------------------------------------------------------
    print("\n--- 2. Level 1: 发现技能 (只加载元信息) ---")

    # Level 1: 发现技能（只加载元信息，不加载内容）
    discovered = loader.discover_skills(skills_dir)
    print(f"Level 1 - 发现了 {len(discovered)} 个技能:")
    for skill_meta in discovered:
        print(f"  - {skill_meta.name}: {skill_meta.description}")

    # -------------------------------------------------------------------------
    # 3. 匹配技能 - 根据用户输入筛选相关技能
    # -------------------------------------------------------------------------
    print("\n--- 3. 匹配技能 ---")

    user_input = "请 review 我的代码"
    matched = loader.match_skills(user_input, discovered)
    print(f"用户输入: '{user_input}'")
    print(f"匹配的技能: {[m.name for m in matched]}")

    # 另一个输入
    user_input2 = "帮我写单元测试"
    matched2 = loader.match_skills(user_input2, discovered)
    print(f"\n用户输入: '{user_input2}'")
    print(f"匹配的技能: {[m.name for m in matched2]}")

    # -------------------------------------------------------------------------
    # 4. Level 2: 加载完整内容
    # -------------------------------------------------------------------------
    print("\n--- 4. Level 2: 加载完整技能内容 ---")

    # 加载匹配技能的完整内容
    for meta in matched:
        skill = loader.load_full_content(meta)
        print(f"  ✅ 已加载 '{skill.name}' 的完整内容")
        print(f"     内容长度: {len(skill.content)} 字符")

    # -------------------------------------------------------------------------
    # 5. 构建技能选择提示 & Token 估算
    # -------------------------------------------------------------------------
    print("\n--- 5. 构建技能选择提示 & Token 估算 ---")

    # 构建技能列表提示（用于让 LLM 选择使用哪个技能）
    prompt = loader.build_skill_selection_prompt(discovered, format_style="list")
    print("技能选择提示 (list 格式):")
    print(f"  {prompt[:200]}")

    # Token 估算
    l1_tokens = loader.estimate_tokens(discovered, level=1)
    l2_tokens = loader.estimate_tokens(discovered, level=2)
    print("\nToken 估算:")
    print(f"  - Level 1 (元信息): ~{l1_tokens} tokens")
    print(f"  - Level 2 (完整内容): ~{l2_tokens} tokens")

    # -------------------------------------------------------------------------
    # 6. Level 3: 加载技能和参考文档
    # -------------------------------------------------------------------------
    print("\n--- 6. Level 3: 加载技能和参考文档 ---")

    if matched:
        skill, refs = loader.load_with_references(matched[0])
        print(f"  已加载 '{skill.name}' 及其引用")
        print(f"  引用文件数: {len(refs)}")

    # -------------------------------------------------------------------------
    # 7. 三级加载对比
    # -------------------------------------------------------------------------
    print("\n--- 7. 三级加载对比 ---")
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  Level 1 (DISCOVER): 名称 + 描述 + 触发条件                │
    │  用途: 快速匹配相关技能                                      │
    │  Token: ~50-100 / 技能                                      │
    │                                                             │
    │  Level 2 (LOAD): 完整技能内容                               │
    │  用途: 提供详细的执行指令                                    │
    │  Token: ~200-1000 / 技能                                    │
    │                                                             │
    │  Level 3 (WITH_REFERENCES): 内容 + 参考文档                │
    │  用途: 提供完整的上下文信息                                  │
    │  Token: ~500-3000 / 技能                                    │
    └─────────────────────────────────────────────────────────────┘
    """)

    print("\n✅ 渐进式技能加载演示完成")


# ============================================================================
# 演示 23: MEMORY.md 标准 (P2)
# ============================================================================

async def demo_memory_md():
    """
    演示 23: MEMORY.md 标准 (P2)

    功能:
    - 创建 MemoryFileManager 管理 MEMORY.md 文件
    - 使用 MemoryEntry 添加记忆条目
    - 使用 MemoryCategory 分类记忆
    - 保存/加载和导出为 LLM 上下文

    学习要点:
    - MEMORY.md 是持久化记忆的标准格式
    - 支持多种分类: USER_PROFILE, KEY_DECISIONS, LEARNED_PATTERNS, PROJECT_CONTEXT
    - 可以与 Agent 的系统提示集成
    - 记忆文件可以在多个会话间共享
    """
    print("\n" + "=" * 70)
    print("演示 23: MEMORY.md 标准 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 MemoryFileManager
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 MemoryFileManager ---")

    import tempfile
    tmpdir = tempfile.mkdtemp()
    project_root = Path(tmpdir)

    manager = MemoryFileManager(project_root=project_root)
    print(f"已创建 MemoryFileManager，路径: {project_root / 'MEMORY.md'}")

    # -------------------------------------------------------------------------
    # 2. 添加记忆条目
    # -------------------------------------------------------------------------
    print("\n--- 2. 添加记忆条目 ---")

    # 用户信息
    manager.add_entry(MemoryEntry(
        category=MemoryCategory.USER_PROFILE,
        content="用户是 Python 后端开发者，熟悉 FastAPI 和 SQLAlchemy。",
        source=MemorySource.USER_INPUT,
    ))
    print("  ✅ 添加用户信息 (USER_PROFILE)")

    # 关键决策
    manager.add_entry(MemoryEntry(
        category=MemoryCategory.KEY_DECISIONS,
        content="使用分层架构: routes → services → models，数据库用 PostgreSQL。",
        source=MemorySource.AGENT_OBSERVATION,
    ))
    print("  ✅ 添加关键决策 (KEY_DECISIONS)")

    # 学到的模式
    manager.add_entry(MemoryEntry(
        category=MemoryCategory.LEARNED_PATTERNS,
        content="用户偏好使用类型注解，不偏好过多的注释。",
        source=MemorySource.USER_INPUT,
    ))
    print("  ✅ 添加学到模式 (LEARNED_PATTERNS)")

    # 项目上下文
    manager.add_entry(MemoryEntry(
        category=MemoryCategory.PROJECT_CONTEXT,
        content="项目 API 文档在 /docs/api/ 目录下，使用 OpenAPI 格式。",
        source=MemorySource.AGENT_OBSERVATION,
    ))
    print("  ✅ 添加项目上下文 (PROJECT_CONTEXT)")

    # -------------------------------------------------------------------------
    # 3. 保存和加载
    # -------------------------------------------------------------------------
    print("\n--- 3. 保存和加载 ---")

    # add_entry 会自动保存，读取文件内容确认
    memory_file = project_root / "MEMORY.md"
    print(f"记忆已保存到: {memory_file}")
    print(f"文件大小: {memory_file.stat().st_size} 字节")

    # 读取文件内容
    file_content = memory_file.read_text(encoding="utf-8")
    print("\nMEMORY.md 内容预览:")
    print("-" * 40)
    print(file_content[:600] + "..." if len(file_content) > 600 else file_content)

    # 从文件加载
    loaded_manager = MemoryFileManager(project_root=project_root)
    sections = loaded_manager.load()
    print("\n从文件加载了记忆:")
    print(f"  - 用户信息: {sections.user_profile}")
    print(f"  - 关键决策: {len(sections.key_decisions)} 条")
    print(f"  - 学到模式: {len(sections.learned_patterns)} 条")
    print(f"  - 项目上下文: {len(sections.project_context)} 条")

    # -------------------------------------------------------------------------
    # 4. 导出为 LLM 上下文
    # -------------------------------------------------------------------------
    print("\n--- 4. 导出为 LLM 上下文 ---")

    # 转换为可注入系统提示的文本
    context_str = manager.to_context_string()
    print(f"上下文字符串长度: {len(context_str)} 字符")
    print("\n上下文内容:")
    print("-" * 40)
    print(context_str[:500] + "..." if len(context_str) > 500 else context_str)

    # -------------------------------------------------------------------------
    # 5. create_default_memory - 创建默认记忆
    # -------------------------------------------------------------------------
    print("\n--- 5. create_default_memory ---")

    default_root = Path(tempfile.mkdtemp())
    create_default_memory(project_root=default_root)  # 创建默认模板，返回 None
    print(f"已创建默认 MEMORY.md 到: {default_root / 'MEMORY.md'}")

    # 加载查看内容
    default_manager = MemoryFileManager(project_root=default_root)
    default_sections = default_manager.load()
    print("默认记忆内容:")
    print(f"  - 用户信息: {default_sections.user_profile}")
    print(f"  - 项目上下文: {default_sections.project_context}")

    # -------------------------------------------------------------------------
    # 6. MemoryCategory 和 MemorySource 说明
    # -------------------------------------------------------------------------
    print("\n--- 6. MemoryCategory 和 MemorySource ---")
    print("""
    MemoryCategory 分类:
    - USER_PROFILE:      用户信息和偏好
    - KEY_DECISIONS:     项目关键决策
    - LEARNED_PATTERNS:  从交互中学到的模式
    - PROJECT_CONTEXT:   项目特定上下文

    MemorySource 来源:
    - USER_INPUT:        用户直接输入
    - AGENT_OBSERVATION: Agent 观察到的事实
    - EXPLICIT_SAVE:     用户明确要求保存

    与 AgentHarness 集成方式：

    ┌─────────────────────────────────────────────────────────────┐
    │  方式 1: 注入到系统提示                                     │
    │  ─────────────────────                                      │
    │  context = manager.to_context_string()                      │
    │  system_prompt = f"你是助手。\\n\\n{context}"                 │
    │  agent = AgentHarness(config=HarnessConfig(                 │
    │      system_prompt=system_prompt,                           │
    │  ))                                                         │
    │                                                             │
    │  方式 2: 使用 SystemPromptBuilder                           │
    │  ─────────────────────────                  │
    │  builder.add_source(SystemPromptSource(                     │
    │      name="memory",                                         │
    │      content=lambda: manager.to_context_string(),           │
    │  ))                                                         │
    └─────────────────────────────────────────────────────────────┘
    """)

    print("\n✅ MEMORY.md 标准演示完成")


# ============================================================================
# 演示 24: 向量检索 (P2)
# ============================================================================

async def demo_vector_search():
    """
    演示 24: 向量检索 (P2)

    功能:
    - 创建 VectorMemoryStore 语义搜索
    - 使用 MockEmbeddingModel 无需外部依赖
    - 存储和搜索文档
    - 使用 SimpleInMemoryVectorStore 进行内存存储

    学习要点:
    - 向量检索支持语义匹配而非关键词匹配
    - MockEmbeddingModel 使用简单哈希，生产环境应替换为真实嵌入模型
    - VectorMemoryStore 封装了嵌入生成和搜索
    - SimpleInMemoryVectorStore 适合开发测试
    """
    print("\n" + "=" * 70)
    print("演示 24: 向量检索 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 VectorMemoryStore
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 VectorMemoryStore ---")

    config = VectorMemoryConfig(
        embedding_model="mock",    # 使用 Mock 嵌入模型
        embedding_dimension=64,    # 嵌入维度 (Mock 使用小维度)
        collection_name="demo",
    )

    # 使用 MockEmbeddingModel（无需外部 API）
    store = VectorMemoryStore(
        config=config,
        embedding_model=MockEmbeddingModel(dimension=config.embedding_dimension),
    )
    print("已创建 VectorMemoryStore")
    print("  - 嵌入模型: mock")
    print(f"  - 嵌入维度: {config.embedding_dimension}")

    # -------------------------------------------------------------------------
    # 2. 添加和搜索文档
    # -------------------------------------------------------------------------
    print("\n--- 2. 添加和搜索文档 ---")

    # 添加文档
    await store.add(
        id="doc-001",
        content=(
            "Harness SDK 是一个可内嵌的 Python AI Agent SDK，"
            "支持工具调用、会话管理和技能系统。"
        ),
        metadata={"type": "documentation", "topic": "overview"},
    )
    await store.add(
        id="doc-002",
        content="Agent Loop 是 SDK 的核心循环，负责调用 LLM、解析响应、执行工具的迭代过程。",
        metadata={"type": "documentation", "topic": "agent-loop"},
    )
    await store.add(
        id="doc-003",
        content="MCP 协议允许 Agent 连接外部工具服务器，扩展可用工具集。",
        metadata={"type": "documentation", "topic": "mcp"},
    )
    print("已添加 3 条文档记录")

    # 语义搜索
    results = await store.search(
        query="如何扩展 Agent 的工具能力",
        top_k=3,
    )
    print("\n搜索 '如何扩展 Agent 的工具能力' 结果:")
    for r in results:
        print(f"  - 相似度: {r.score:.3f}, ID: {r.id}")
        print(f"    内容: {r.content[:80]}...")

    # -------------------------------------------------------------------------
    # 3. 批量添加
    # -------------------------------------------------------------------------
    print("\n--- 3. 批量添加 ---")

    await store.add_batch(
        ids=["conv-001", "conv-002", "conv-003"],
        contents=[
            "用户询问如何使用 FastAPI 创建 REST API",
            "Python 虚拟环境创建方法：python -m venv myenv",
            "FastAPI 中使用 SQLAlchemy 进行数据库操作",
        ],
        metadatas=[
            {"type": "conversation", "session": "s1"},
            {"type": "conversation", "session": "s2"},
            {"type": "conversation", "session": "s3"},
        ],
    )
    print("已批量添加 3 条对话记录")

    # 搜索对话
    conv_results = await store.search(
        query="FastAPI 开发 API",
        top_k=2,
        filter={"type": "conversation"},
    )
    print("\n搜索 'FastAPI 开发 API' (仅对话) 结果:")
    for r in conv_results:
        print(f"  - 相似度: {r.score:.3f}, ID: {r.id}")
        print(f"    内容: {r.content[:80]}...")

    # -------------------------------------------------------------------------
    # 4. SimpleInMemoryVectorStore
    # -------------------------------------------------------------------------
    print("\n--- 4. SimpleInMemoryVectorStore ---")

    simple_store = SimpleInMemoryVectorStore()
    print("已创建 SimpleInMemoryVectorStore (更轻量的底层存储)")

    # 添加数据
    mock_model = MockEmbeddingModel(dimension=64)
    embeddings = await mock_model.embed(["简单的向量存储示例"])
    await simple_store.add(
        ids=["simple-001"],
        embeddings=embeddings,
        documents=["简单的向量存储示例"],
    )
    print("已添加 1 条记录到 SimpleInMemoryVectorStore")

    # 搜索
    query_embeddings = await mock_model.embed(["向量存储"])
    search_results = await simple_store.search(
        query_embedding=query_embeddings[0],
        top_k=1,
    )
    print(f"搜索结果: {len(search_results)} 条")
    for r in search_results:
        print(f"  - 相似度: {r.score:.3f}, 内容: {r.content}")

    # -------------------------------------------------------------------------
    # 5. VectorSearchResult 说明
    # -------------------------------------------------------------------------
    print("\n--- 5. VectorSearchResult 结构 ---")
    print("""
    VectorSearchResult 包含以下字段：

    - id: 条目唯一标识
    - content: 匹配的文本内容
    - score: 相似度分数 (0.0 - 1.0)
    - metadata: 附加元数据

    与 AgentHarness 集成：

    ┌─────────────────────────────────────────────────────────────┐
    │  用户输入 → 向量搜索历史对话和技能                           │
    │    ↓                                                        │
    │  将搜索结果注入 system prompt                               │
    │    ↓                                                        │
    │  Agent 可以参考相关的历史上下文                              │
    │    ↓                                                        │
    │  执行后，将新对话存入向量存储                                │
    └─────────────────────────────────────────────────────────────┘

    生产环境建议：
    - 替换 MockEmbeddingModel 为真实嵌入模型 (OpenAI / sentence-transformers)
    - 替换 SimpleInMemoryVectorStore 为持久化存储 (ChromaDB / FAISS)
    - 设置合理的 embedding_dimension (通常 384 或 1536)
    """)

    print("\n✅ 向量检索演示完成")


# ============================================================================
# 演示 25: 语义卡住检测 (P2)
# ============================================================================

async def demo_semantic_stuck_detection():
    """
    演示 25: 语义卡住检测 (P2)

    功能:
    - 创建 StuckDetector 检测重复输出模式
    - 使用 StuckDetectorConfig 配置检测参数
    - 支持空/错误检测和语义相似度检测
    - 与 AgentHarness 集成使用

    学习要点:
    - 两级检测策略：空/错误检测（零成本）+ 语义检测
    - 语义检测需要安装 sentence-transformers
    - 检测到卡住后注入反馈消息
    - 可配置相似度阈值和连续轮数
    """
    print("\n" + "=" * 70)
    print("演示 25: 语义卡住检测 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 StuckDetector
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 StuckDetector ---")

    # 基础配置（仅空/错误检测，零依赖）
    basic_config = StuckDetectorConfig(
        enable_semantic=False,  # 禁用语义检测
    )
    detector_basic = StuckDetector(config=basic_config)
    print("已创建基础检测器（仅空/错误检测）")

    # 完整配置（包含语义检测）
    semantic_config = StuckDetectorConfig(
        enable_semantic=True,          # 启用语义检测
        similarity_threshold=0.92,     # 相似度阈值
        consecutive_rounds=3,          # 连续相似轮数触发
        window_size=6,                 # 对比窗口大小
        min_chars=30,                  # 最小文本长度
    )
    detector_semantic = StuckDetector(config=semantic_config)  # noqa: F841
    print("已创建语义检测器（需要 sentence-transformers）")

    # -------------------------------------------------------------------------
    # 2. 模拟检测场景
    # -------------------------------------------------------------------------
    print("\n--- 2. 模拟检测场景 ---")

    from harness.types import Message

    # 模拟重复的空结果
    empty_messages = [
        Message(role="tool", content=""),
        Message(role="tool", content=""),
        Message(role="tool", content=""),
    ]

    # 模拟重复的错误
    error_messages = [
        Message(role="tool", content="Error: File not found"),
        Message(role="tool", content="Error: File not found"),
        Message(role="tool", content="Error: File not found"),
    ]

    # 模拟语义重复（需要启用语义检测）
    semantic_repeat_messages = [
        Message(role="tool", content="未找到相关结果，请尝试其他搜索词。"),
        Message(role="tool", content="未找到相关的结果，建议使用其他关键词搜索。"),
        Message(role="tool", content="没有找到相关内容，请换一个搜索词试试。"),
    ]

    print("模拟消息:")
    print(f"  - 空结果: {len(empty_messages)} 条")
    print(f"  - 错误结果: {len(error_messages)} 条")
    print(f"  - 语义重复: {len(semantic_repeat_messages)} 条")

    # -------------------------------------------------------------------------
    # 3. 检测空结果
    # -------------------------------------------------------------------------
    print("\n--- 3. 检测空结果 ---")

    # 使用基础检测器检查空结果
    result_empty = await detector_basic.check(
        session_id="test-empty",
        messages=empty_messages,
        iteration=5,
    )
    print(f"空结果检测: is_stuck={result_empty.is_stuck}, reason={result_empty.reason}")

    # -------------------------------------------------------------------------
    # 4. 检测错误
    # -------------------------------------------------------------------------
    print("\n--- 4. 检测错误 ---")

    result_error = await detector_basic.check(
        session_id="test-error",
        messages=error_messages,
        iteration=5,
    )
    print(f"错误检测: is_stuck={result_error.is_stuck}, reason={result_error.reason}")

    # -------------------------------------------------------------------------
    # 5. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 5. 与 AgentHarness 集成 ---")
    print("""
    语义卡住检测与 AgentHarness 的集成方式：

    ┌─────────────────────────────────────────────────────────────┐
    │  AgentHarness(config=HarnessConfig(                        │
    │      stuck_detector_config=StuckDetectorConfig(            │
    │          enable_semantic=True,                              │
    │          similarity_threshold=0.92,                         │
    │      ),                                                     │
    │  ))                                                         │
    │    ↓                                                        │
    │  AgentLoop 执行工具                                         │
    │    ↓                                                        │
    │  检查是否卡住（两级策略）                                   │
    │    ↓                                                        │
    │  如果卡住 → 注入反馈消息                                    │
    │    ↓                                                        │
    │  继续执行或终止                                             │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 创建带卡住检测的 Agent
    from harness.core.agent_loop import LoopConfig

    loop_config = LoopConfig(  # noqa: F841
        max_iterations=20,
        stuck_detector_config=semantic_config,
        max_stuck_feedbacks=2,
    )

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    print("已创建带语义卡住检测的 Agent")
    print(f"  - 语义检测: {semantic_config.enable_semantic}")
    print(f"  - 相似度阈值: {semantic_config.similarity_threshold}")
    print(f"  - 连续轮数: {semantic_config.consecutive_rounds}")

    # 运行 Agent 演示
    result = await agent.run("你好，请简单介绍你自己。")
    print(f"\nAgent 响应: {result.content[:200]}...")
    print(f"迭代次数: {result.iterations}")

    # -------------------------------------------------------------------------
    # 6. 安装依赖说明
    # -------------------------------------------------------------------------
    print("\n--- 6. 安装依赖 ---")
    print("""
    语义检测需要安装可选依赖：

    pip install harness-sdk[stuck]

    这会安装：
    - sentence-transformers: 嵌入模型库
    - 默认模型: bge-small-zh-v1.5 (中文优化)

    如果未安装依赖，语义检测自动禁用，退回空/错误检测。
    """)

    # -------------------------------------------------------------------------
    # 7. 配置参数说明
    # -------------------------------------------------------------------------
    print("\n--- 7. 配置参数说明 ---")
    print("""
    StuckDetectorConfig 参数：

    - enable_semantic:        是否启用语义检测（默认 False）
    - similarity_threshold:   相似度阈值（0.0-1.0，默认 0.92）
    - consecutive_rounds:     连续相似轮数触发（默认 3）
    - window_size:            对比窗口大小（默认 6）
    - min_chars:              最小文本长度（默认 30）

    检测策略：

    1. 空/错误检测（零成本）：
       - 连续 N 次空工具结果
       - 连续 N 次错误结果

    2. 语义检测（需要模型）：
       - 计算 embedding 相似度
       - 连续 N 轮高相似度触发
    """)

    print("\n✅ 语义卡住检测演示完成")


# ============================================================================
# 演示 26: Guardrails PII 检测和内容安全 (P2)
# ============================================================================

async def demo_guardrails():
    """
    演示 26: Guardrails PII 检测和内容安全 (P2)

    功能:
    - Layer 1: PII 规则检测（手机号、身份证、银行卡等）
    - Layer 2: LLM Judge 语义检测（可选）
    - 流式输出拦截和 PII 过滤
    - 与 AgentHarness 集成

    学习要点:
    - 两级检测策略：规则检测（<1ms）+ 语义检测（~100ms）
    - 中文 PII 使用正则表达式 + 姓氏库，无额外依赖
    - 支持多种 PII 类型：手机、身份证、银行卡、护照等
    - 流式拦截器实时过滤输出中的 PII
    """
    print("\n" + "=" * 70)
    print("演示 26: Guardrails PII 检测和内容安全 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 基础 PII 检测
    # -------------------------------------------------------------------------
    print("\n--- 1. 基础 PII 检测 ---")

    from harness.guardrails import (
        GuardrailConfig,
        check_pii,
        redact_pii,
        redact_pii_traditional,
        scan_pii,
    )

    # 测试文本（包含多种 PII）
    test_text = """
    用户张三的手机号是 13812345678，身份证号是 110101199001011234。
    银行卡号：6222021234567890123
    邮箱：zhangsan@example.com
    """

    # 检测 PII (返回 tuple: safe_text, entities, has_pii)
    safe_text, entities, has_pii = check_pii(test_text)
    print(f"检测到 PII: {has_pii}")
    print(f"PII 类型: {[e.entity_type for e in entities]}")

    # 扫描 PII（返回详细信息, 也是 tuple）
    _, scan_entities, _ = scan_pii(test_text)
    print("\nPII 实体详情:")
    for entity in scan_entities:
        print(
        f"  - 类型: {entity.entity_type}, 值: {entity.text}, "
        f"位置: {entity.start}-{entity.end}"
    )

    # -------------------------------------------------------------------------
    # 2. PII 脱敏
    # -------------------------------------------------------------------------
    print("\n--- 2. PII 脱敏 ---")

    # 传统脱敏（替换为星号）
    redacted = redact_pii_traditional(test_text)
    print(f"脱敏后文本:\n{redacted}")

    # 智能脱敏（替换为占位符）
    redacted_smart = redact_pii(test_text)
    print(f"\n智能脱敏后:\n{redacted_smart}")

    # -------------------------------------------------------------------------
    # 3. GuardrailConfig 配置
    # -------------------------------------------------------------------------
    print("\n--- 3. GuardrailConfig 配置 ---")

    # 仅 Layer 1（PII 规则检测）
    config_layer1 = GuardrailConfig(
        enabled=True,
        layer1_enabled=True,
        layer2_enabled=False,
    )
    print(f"Layer 1 配置: {config_layer1}")

    # Layer 1 + Layer 2（PII + LLM Judge）
    config_full = GuardrailConfig(  # noqa: F841
        enabled=True,
        layer1_enabled=True,
        layer2_enabled=True,
        judge_endpoint="http://localhost:8001/v1/chat/completions",
        judge_timeout=5.0,
    )
    print("完整配置: Layer 1 + Layer 2")

    # -------------------------------------------------------------------------
    # 4. 与 AgentHarness 集成
    # -------------------------------------------------------------------------
    print("\n--- 4. 与 AgentHarness 集成 ---")

    print("""
    集成流程：

    ┌─────────────────────────────────────────────────────────────┐
    │  AgentHarness(                                              │
    │      model="claude-sonnet-4-6",                            │
    │      guardrails=GuardrailConfig(                           │
    │          enabled=True,                                     │
    │          layer1_enabled=True,                              │
    │          layer2_enabled=False,  # 仅规则检测               │
    │      ),                                                    │
    │  )                                                         │
    │    ↓                                                        │
    │  用户输入 → PII 检测 → 脱敏 → Agent 处理                    │
    │    ↓                                                        │
    │  Agent 输出 → PII 检测 → 脱敏 → 返回用户                    │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 创建带 Guardrails 的 Agent
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        guardrails=config_layer1,
    )

    print("已创建带 PII 检测的 Agent")

    # 运行 Agent 演示
    result = await agent.run("你好，请简单介绍你自己。")
    print(f"\nAgent 响应: {result.content[:200]}...")
    print(f"迭代次数: {result.iterations}")

    # -------------------------------------------------------------------------
    # 5. 流式拦截器
    # -------------------------------------------------------------------------
    print("\n--- 5. 流式拦截器 ---")

    from harness.guardrails import StreamInterceptConfig, StreamInterceptor
    from harness.guardrails.config import JudgeConfig
    from harness.guardrails.judge import ComplianceJudge

    # 创建拦截器（需要 ComplianceJudge）
    interceptor_config = StreamInterceptConfig(
        enabled=True,
        check_interval=10,        # 每 10 个 token 检测一次
        safety_threshold=0.3,     # 安全阈值
        min_tokens_before_check=5,  # 检测前最小 token 数
    )

    # 创建 Judge（可选，用于 Layer 2 检测）
    judge_config = JudgeConfig(enabled=False, endpoint="", timeout=5.0)
    judge = ComplianceJudge(config=judge_config)
    interceptor = StreamInterceptor(judge=judge, config=interceptor_config)  # noqa: F841
    print("已创建流式拦截器")

    # 模拟流式输出
    print("\n模拟流式输出:")
    print("  (流式拦截器需要与 AgentLoop 集成使用，这里仅展示配置)")

    # -------------------------------------------------------------------------
    # 6. 支持的 PII 类型
    # -------------------------------------------------------------------------
    print("\n--- 6. 支持的 PII 类型 ---")

    print("""
    中国大陆：
    - 手机号（11位）
    - 身份证号（18位）
    - 银行卡号（16-19位）
    - 护照号
    - 统一社会信用代码
    - 车牌号
    - 邮箱
    - IP 地址

    香港地区：
    - 手机号（8位）
    - 身份证号
    - 英文姓名

    特点：
    - 中文姓名识别：基于姓氏库 + N-gram
    - 无需安装 zh_core_web_sm 等 spaCy 中文模型
    - 检测速度 < 1ms
    """)

    # -------------------------------------------------------------------------
    # 7. 安装依赖
    # -------------------------------------------------------------------------
    print("\n--- 7. 安装依赖 ---")
    print("""
    # 方式一：安装可选依赖（推荐）
    pip install harness-sdk[guardrails]

    # 方式二：手动安装
    pip install presidio-analyzer>=2.2.0
    pip install presidio-anonymizer>=2.2.0

    # Layer 2 (Judge) - 如果启用
    pip install httpx>=0.24.0
    pip install cachetools>=5.3.0  # 可选，用于结果缓存
    """)

    print("\n✅ Guardrails PII 检测演示完成")


# ============================================================================
# 演示 27: CPU Router - 成本优化的请求路由 (P2)
# ============================================================================

async def demo_cpu_router():
    """
    演示 27: CPU Router - 成本优化的请求路由

    功能:
    - 使用轻量级 CPU 模型 (如 Qwen3.5-0.8B) 作为路由器
    - 根据请求复杂度路由到不同的下游模型
    - 支持 provider/api_key/base_url 独立配置
    - 复用 model_presets.py 自动检测 provider

    适用场景:
    - 高/低档模型混合使用，降低成本
    - 简单请求走低成本模型，复杂请求走高性能模型
    """
    print("\n" + "=" * 70)
    print("演示 27: CPU Router - 成本优化的请求路由 (P2)")
    print("=" * 70)


    # -------------------------------------------------------------------------
    # 1. RoutingConfig 基础配置
    # -------------------------------------------------------------------------
    print("\n--- 1. RoutingConfig 基础配置 ---")

    print("""
    RoutingConfig 支持以下配置:

    下游模型配置:
    - high_model: 高性能模型 (复杂任务)
    - high_provider: "auto" 或显式指定 ("anthropic"/"openai")
    - high_api_key: 可选，覆盖全局 api_key
    - high_base_url: 可选，覆盖全局 base_url

    - low_model: 低成本模型 (简单任务)
    - low_provider: "auto" 或显式指定
    - low_api_key: 可选
    - low_base_url: 可选

    路由器配置:
    - router_model_path: GGUF 文件路径 (嵌入式)
    - router_url: 或使用 HTTP 服务
    - router_context_window: 上下文大小，支持 "auto" 或整数
    """)

    # -------------------------------------------------------------------------
    # 2. 使用示例
    # -------------------------------------------------------------------------
    print("\n--- 2. 使用示例 ---")

    print("""
    # 示例 1: 自动检测 provider
    routing = RoutingConfig(
        high_model="claude-sonnet-4-6",  # 自动检测 → anthropic
        low_model="qwen-plus",           # 自动检测 → openai
        router_model_path="models/qwen3.5-0.8b.gguf",
    )

    # 示例 2: 不同服务商
    routing = RoutingConfig(
        high_model="gpt-4o",
        high_api_key="sk-openai-xxx",
        low_model="deepseek-chat",
        low_api_key="sk-deepseek-xxx",
        low_base_url="https://api.deepseek.com/v1",
        router_model_path="models/qwen3.5-0.8b.gguf",
    )

    # 示例 3: 自定义路由器上下文
    routing = RoutingConfig(
        high_model="gpt-4o",
        low_model="gpt-4o-mini",
        router_model_path="models/qwen3.5-0.8b.gguf",
        router_context_window=4096,  # 或 "auto"
    )

    # 完整 Agent 配置
    agent = AgentHarness(
        routing=routing,
        tools=[ReadTool()],
    )
    """)

    # -------------------------------------------------------------------------
    # 3. provider 自动检测
    # -------------------------------------------------------------------------
    print("\n--- 3. provider 自动检测 ---")

    from harness.model_presets import get_model_preset

    models = ["claude-sonnet-4-6", "gpt-4o", "qwen-plus", "deepseek-chat"]
    print("模型名 → provider 检测结果:")
    for model in models:
        preset = get_model_preset(model)
        print(f"  {model} → {preset.provider}")

    # -------------------------------------------------------------------------
    # 4. context_window 自动检测
    # -------------------------------------------------------------------------
    print("\n--- 4. context_window 自动检测 ---")


    print("""
    EmbeddedLlamaClient 支持从 GGUF 文件名推断模型:

    文件名 → 模型名推断:
      qwen3.5-0.8b-instruct-q4_k_m.gguf → qwen3.5-0.8b
      qwen2.5-1.5b-chat-q5_k_m.gguf → qwen2.5-1.5b

    未知模型默认使用 2048 (路由任务足够)
    """)

    # -------------------------------------------------------------------------
    # 5. 路由判断逻辑
    # -------------------------------------------------------------------------
    print("\n--- 5. 路由判断逻辑 ---")

    print("""
    默认路由判断标准:
    - 需要多步推理 → high
    - 需要调用多个工具 → high
    - 需要代码生成或修改 → high
    - 需要深度分析或报告 → high
    - 简单问答、查询、翻译 → low

    重要: 当不确定时，选择 high。宁可浪费也不要牺牲质量。
    """)

    print("\n✅ CPU Router 演示完成")


# ============================================================================
# 演示 28: Guardrails 进阶 - LLM Judge、流式拦截、中文姓名、异常处理 (P2)
# ============================================================================

async def demo_guardrails_advanced():
    """
    演示 28: Guardrails 进阶 - LLM Judge、流式拦截、中文姓名、异常处理 (P2)

    功能:
    - Layer 2: LLM Judge 语义安全检测
    - 流式拦截器 (StreamInterceptor)
    - 中文姓名识别 (ChineseNameRecognizer)
    - 异常处理 (JudgeTimeoutException / JudgeUnavailableException)
    - 快速安全分数 (Quick Score)

    学习要点:
    - Layer 1 是规则检测，Layer 2 是 LLM 语义判断
    - Judge 需要独立的 LLM 端点（Qwen3Guard-8B-Stream 或任意兼容 API）
    - 流式拦截在 Agent 流式输出时实时过滤风险内容
    - 中文姓名识别基于姓氏库 + N-gram，无需 spaCy
    """
    print("\n" + "=" * 70)
    print("演示 28: Guardrails 进阶 - LLM Judge、流式拦截、中文姓名、异常 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Layer 2: LLM Judge 语义检测
    # -------------------------------------------------------------------------
    print("\n--- 1. Layer 2: LLM Judge 语义检测 ---")

    from harness.guardrails import (
        JudgeConfig,
    )
    from harness.guardrails.judge import RiskLevel

    # 创建 Judge 配置
    judge_config = JudgeConfig(
        enabled=True,
        endpoint="http://localhost:8001/v1/chat/completions",
        model="qwen3-guard-8b-stream",
        timeout=5.0,
    )

    print(f"""
    JudgeConfig 配置:
    - endpoint: {judge_config.endpoint}
    - model: {judge_config.model}
    - timeout: {judge_config.timeout}s
    - 支持缓存 (cachetools): 减少重复 API 调用

    风险等级: {", ".join(level.value for level in RiskLevel)}

    Judge 检测内容类型:
    - prompt_injection: 提示注入攻击
    - harmful_content: 有害内容
    - pii_leakage: 隐私信息泄露
    - bias_discrimination: 偏见与歧视
    - illegal_content: 非法内容
    - other: 其他风险
    """)

    # -------------------------------------------------------------------------
    # 2. 流式拦截器 (StreamInterceptor)
    # -------------------------------------------------------------------------
    print("\n--- 2. 流式拦截器 (StreamInterceptor) ---")

    from harness.guardrails import (
        StreamInterceptConfig,
    )

    # 拦截器配置
    stream_config = StreamInterceptConfig(
        enabled=True,
        check_interval=15,              # 每 15 个 token 检测一次
        safety_threshold=0.4,           # 安全阈值 < 0.4 则拦截
        min_tokens_before_check=10,     # 至少 10 个 token 后才检测
        max_check_attempts=3,           # 最大重试次数
    )

    print(f"""
    StreamInterceptConfig 配置:
    - check_interval: {stream_config.check_interval} tokens/次
    - safety_threshold: {stream_config.safety_threshold}
    - min_tokens_before_check: {stream_config.min_tokens_before_check}
    - max_check_attempts: {stream_config.max_check_attempts}

    拦截结果类型 (InterceptResult):
    - safe: 内容安全，继续流式输出
    - blocked: 内容被拦截，停止流式输出
    - warning: 有轻微风险，标记警告但不中断
    """)

    # -------------------------------------------------------------------------
    # 3. 中文姓名识别器
    # -------------------------------------------------------------------------
    print("\n--- 3. 中文姓名识别器 ---")

    from harness.guardrails.chinese_name_recognizer import (
        COMMON_SURNAMES,
        COMPOUND_SURNAMES,
        ChineseNameRecognizer,
        extract_chinese_names,
    )

    # 测试中文姓名识别
    test_text = """
    我叫张三，我的同事是李四和王五。
    我们的领导是欧阳修先生，他的秘书是张婉儿。
    另外，陈小明和刘姥姥也参加了今天的会议。
    """

    # 创建姓名识别器
    name_recognizer = ChineseNameRecognizer()  # noqa: F841
    names = extract_chinese_names(test_text)

    print(f"测试文本:\n  {test_text.strip()}")
    print(f"\n识别到的中文姓名: {[n.matched_text for n in names]}")
    print(f"姓氏数量: {len(COMMON_SURNAMES)} (单姓) + {len(COMPOUND_SURNAMES)} (复姓)")
    print(f"复姓包括: {', '.join(COMPOUND_SURNAMES[:5])}...")

    # -------------------------------------------------------------------------
    # 4. 异常处理
    # -------------------------------------------------------------------------
    print("\n--- 4. 异常处理 ---")


    print("""
    Guardrails 定义了以下异常:

    1. JudgeTimeoutException:
       - 触发: Judge 服务在 timeout 内未响应
       - 处理: 捕获异常后降级为仅 Layer 1，或重试
       - 示例:
           try:
               result = await judge.judge(content)
           except JudgeTimeoutException as e:
               print(f"Judge 超时 ({e.timeout}s)，使用降级策略")

    2. JudgeUnavailableException:
       - 触发: Judge 服务不可达（HTTP 错误、网络错误）
       - 处理: 捕获异常后关闭 Layer 2，回退到 Layer 1
       - 示例:
           except JudgeUnavailableException as e:
               print(f"Judge 不可用: {e.detail}，已降级")

    3. StreamInterruptException:
       - 触发: 流式拦截检测到高风险内容，强制中断输出
       - 处理: 在流式输出循环中捕获，清理资源
    """)

    # -------------------------------------------------------------------------
    # 5. 完整集成配置
    # -------------------------------------------------------------------------
    print("\n--- 5. 完整 Guardrails 集成 ---")

    print("""
    完整 Guardrails 配置（Layer 1 + Layer 2 + 流式拦截）:

    guardrails = GuardrailConfig(
        enabled=True,
        layer1_enabled=True,        # PII 规则检测
        layer2_enabled=True,        # LLM Judge 语义检测
        layer1_mode="pass_through",  # 检测到 PII 时脱敏后继续
        judge_config=JudgeConfig(
            endpoint="http://localhost:8001/v1/chat/completions",
            model="qwen3-guard-8b-stream",
            timeout=5.0,
        ),
        stream_intercept_config=StreamInterceptConfig(
            enabled=True,
            check_interval=15,
            safety_threshold=0.4,
        ),
    )

    agent = AgentHarness(
        model="claude-sonnet-4-6",
        guardrails=guardrails,
    )
    """)

    print("\n✅ Guardrails 进阶演示完成")


# ============================================================================
# 演示 29: Loop Engineering - 基础用法：目标驱动执行 (P2)
# ============================================================================

async def demo_loop_engineering_basic():
    """
    演示 29: Loop Engineering - 基础用法：目标驱动执行 (P2)

    功能:
    - 使用 run_goal() 让 Agent 自主运行直到目标达成
    - GoalStatus 判断执行结果状态
    - max_iterations 控制最大迭代次数

    学习要点:
    - Loop Engineering 是目标驱动执行范式
    - Agent 会持续运行直到目标达成或达到限制
    - GoalStatus 包含: ACHIEVED, MAX_ITERATIONS, TIMEOUT, ERROR 等
    """
    print("\n" + "=" * 70)
    print("演示 29: Loop Engineering - 基础用法：目标驱动执行 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 基础用法
    # -------------------------------------------------------------------------
    print("\n--- 1. 基础用法 ---")

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    print("""
    目标驱动执行的工作流程:

    ┌─────────────────────────────────────────────────────────────┐
    │  用户: "修复所有类型错误"                                    │
    │    ↓                                                        │
    │  Agent 执行第 1 轮: 分析代码，找出问题                       │
    │    ↓ 验证: 目标未达成                                        │
    │  Agent 执行第 2 轮: 修复第一个问题                           │
    │    ↓ 验证: 目标未达成                                        │
    │  Agent 执行第 N 轮: 修复最后一个问题                         │
    │    ↓ 验证: 目标达成 (所有测试通过)                           │
    │  返回 GoalResult(status=ACHIEVED)                           │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 运行一个简单的目标
    print("执行目标: 列出项目结构并总结项目类型\n")
    result = await agent.run_goal(
        goal="使用 glob 列出所有 .py 文件，然后简要总结这是什么类型的项目。完成后说'目标完成'。",
        max_iterations=10,
    )

    print(f"目标状态: {result.status.value}")
    print(f"迭代次数: {result.total_iterations}")
    print(f"执行时长: {result.duration_seconds:.1f}秒")
    print(f"Token 使用: 输入 {result.total_tokens['input']}, 输出 {result.total_tokens['output']}")

    if result.status == GoalStatus.ACHIEVED:
        print("\n✅ 目标达成！")
    elif result.status == GoalStatus.MAX_ITERATIONS:
        print("\n⚠️ 达到最大迭代次数")
    elif result.status == GoalStatus.TIMEOUT:
        print("\n⏰ 执行超时")
    elif result.status == GoalStatus.ERROR:
        print(f"\n❌ 执行错误: {result.error}")

    print(f"\n最终响应:\n{result.final_response[:500]}...")

    # -------------------------------------------------------------------------
    # 2. GoalStatus 状态说明
    # -------------------------------------------------------------------------
    print("\n--- 2. GoalStatus 状态 ---")

    print("""
    GoalStatus 包含以下状态:

    - ACHIEVED: 目标已达成
    - MAX_ITERATIONS: 达到最大迭代次数
    - TIMEOUT: 执行超时
    - MAX_RESETS: 上下文重置次数过多
    - ERROR: Agent 执行错误
    - VERIFIER_FAULT: 验证器故障
    - CANCELLED: 用户取消
    """)

    # -------------------------------------------------------------------------
    # 3. GoalResult 结果详情
    # -------------------------------------------------------------------------
    print("\n--- 3. GoalResult 结果详情 ---")

    print(f"""
    GoalResult 包含以下字段:

    - goal: 目标描述
    - status: 执行状态
    - total_iterations: 总迭代次数
    - context_resets: 上下文重置次数
    - total_tokens: Token 使用量
    - duration_seconds: 执行时长
    - final_response: 最终响应
    - verification_log: 验证日志
    - error: 错误详情 (如果有)

    当前执行结果:
    - goal: {result.goal[:50]}...
    - status: {result.status.value}
    - total_iterations: {result.total_iterations}
    - context_resets: {result.context_resets}
    """)

    print("\n✅ Loop Engineering 基础用法演示完成")


# ============================================================================
# 演示 30: Loop Engineering - 自定义验证器 (P2)
# ============================================================================

async def demo_loop_engineering_verifier():
    """
    演示 30: Loop Engineering - 自定义验证器 (P2)

    功能:
    - 使用 custom_verifier 参数提供自定义验证函数
    - 根据外部条件判断目标是否达成
    - 验证函数可以是同步或异步

    学习要点:
    - 自定义验证器允许根据业务逻辑判断目标完成
    - 验证器接收 GoalResult 返回 bool
    - 适用于需要外部检查的场景（测试覆盖率、构建状态等）
    """
    print("\n" + "=" * 70)
    print("演示 30: Loop Engineering - 自定义验证器 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建自定义验证器
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建自定义验证器 ---")

    # 定义一个简单的验证器：检查响应中是否包含特定关键词
    async def check_completion(result: GoalResult) -> bool:
        """检查目标是否完成的验证器"""
        # 检查最终响应中是否包含"完成"或"done"
        response = result.final_response.lower()
        return "完成" in response or "done" in response or "目标达成" in response

    print("""
    自定义验证器示例:

    async def check_completion(result: GoalResult) -> bool:
        '''检查目标是否完成的验证器'''
        response = result.final_response.lower()
        return "完成" in response or "done" in response

    验证器接收 GoalResult 参数，返回 bool 表示目标是否达成。
    """)

    # -------------------------------------------------------------------------
    # 2. 使用自定义验证器
    # -------------------------------------------------------------------------
    print("\n--- 2. 使用自定义验证器 ---")

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    print("执行带自定义验证器的目标...\n")

    result = await agent.run_goal(
        goal="列出当前目录下的 Python 文件，并说明有多少个。最后说'任务完成'。",
        custom_verifier=check_completion,
        max_iterations=5,
    )

    print(f"目标状态: {result.status.value}")
    print(f"迭代次数: {result.total_iterations}")

    # -------------------------------------------------------------------------
    # 3. 验证器工作流程
    # -------------------------------------------------------------------------
    print("\n--- 3. 验证器工作流程 ---")

    print("""
    自定义验证器工作流程:

    ┌─────────────────────────────────────────────────────────────┐
    │  Agent 执行一轮                                             │
    │    ↓                                                        │
    │  GoalVerifier 调用 custom_verifier(result)                  │
    │    ↓                                                        │
    │  如果返回 True: 目标达成，结束循环                           │
    │  如果返回 False: 继续下一轮执行                              │
    │    ↓                                                        │
    │  达到 max_iterations: 返回 MAX_ITERATIONS                   │
    └─────────────────────────────────────────────────────────────┘

    常见验证器场景:

    1. 测试覆盖率验证:
       async def check_coverage(result) -> bool:
           proc = await asyncio.create_subprocess_exec(
               "pytest", "--cov", "--cov-report=term",
               stdout=asyncio.subprocess.PIPE,
           )
           stdout, _ = await proc.communicate()
           return "80%" in stdout.decode()

    2. 构建状态验证:
       async def check_build(result) -> bool:
           proc = await asyncio.create_subprocess_exec("npm", "run", "build")
           return await proc.wait() == 0

    3. 文件存在验证:
       def check_file_exists(result) -> bool:
           return Path("output.txt").exists()
    """)

    # -------------------------------------------------------------------------
    # 4. GoalConfig 完整配置
    # -------------------------------------------------------------------------
    print("\n--- 4. GoalConfig 完整配置 ---")

    print("""
    GoalConfig 支持以下配置:

    config = GoalConfig(
        description="实现用户认证模块",   # 目标描述
        success_criteria="所有测试通过",  # 成功标准（可选）
        workspace_dir="./src/auth",       # 工作目录

        # 迭代控制
        max_iterations=50,                # 最大迭代次数
        max_context_resets=5,             # 最大上下文重置次数
        timeout_seconds=3600,             # 超时时间（秒）

        # 成本控制
        max_tokens=500000,                # 最大 token 数
        max_cost_usd=10.0,                # 最大成本（美元）

        # 验证配置
        custom_verifier=check_coverage,   # 自定义验证函数
    )

    result = await agent.run_goal(config)
    """)

    print("\n✅ Loop Engineering 自定义验证器演示完成")


# ============================================================================
# 演示 31: Loop Engineering - Automation 定时调度 (P2)
# ============================================================================

async def demo_loop_engineering_automation():
    """
    演示 31: Loop Engineering - Automation 定时调度 (P2)

    功能:
    - 创建 Automation 定时任务
    - 使用 cron 表达式或固定间隔触发
    - 与 AgentHarness 集成自动执行

    学习要点:
    - Automation 支持 cron 和 interval 两种触发方式
    - 可以启动、停止、查询状态
    - 适用于定时报告、健康检查等场景
    """
    print("\n" + "=" * 70)
    print("演示 31: Loop Engineering - Automation 定时调度 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. 创建 Automation 配置
    # -------------------------------------------------------------------------
    print("\n--- 1. 创建 Automation 配置 ---")

    # Cron 定时任务：每天 9:00 执行
    cron_automation = Automation(  # noqa: F841
        name="daily-report",
        schedule="0 9 * * *",  # 每天 9:00
        goal="分析昨日 Git 提交，生成工作日报",
    )

    print("""
    Cron 定时任务:

    Automation(
        name="daily-report",
        schedule="0 9 * * *",  # 每天 9:00
        goal="分析昨日 Git 提交，生成工作日报",
    )

    Cron 表达式格式: 分 时 日 月 周
    - "0 9 * * *"     → 每天 9:00
    - "*/30 * * * *"  → 每 30 分钟
    - "0 9 * * 1-5"   → 工作日 9:00
    """)

    # 间隔任务：每 5 分钟执行
    interval_automation = Automation(  # noqa: F841
        name="health-check",
        interval_seconds=300,  # 每 5 分钟
        goal="检查系统健康状态，如有异常发送告警",
    )

    print("""
    间隔任务:

    Automation(
        name="health-check",
        interval_seconds=300,  # 每 5 分钟
        goal="检查系统健康状态，如有异常发送告警",
    )
    """)

    # -------------------------------------------------------------------------
    # 2. Automation 使用示例
    # -------------------------------------------------------------------------
    print("\n--- 2. Automation 使用示例 ---")

    print("""
    启动 Automation:

    import asyncio
    from harness import AgentHarness
    from harness.loop import Automation

    async def main():
        agent = AgentHarness(model="claude-sonnet-4-6")

        # 创建自动化任务
        automation = Automation(
            name="daily-report",
            schedule="0 9 * * *",
            goal="生成每日报告",
        )

        # 启动
        await automation.start(agent)

        # 运行一段时间
        await asyncio.sleep(3600)

        # 停止
        await automation.stop()

    asyncio.run(main())
    """)

    # -------------------------------------------------------------------------
    # 3. Automation 状态管理
    # -------------------------------------------------------------------------
    print("\n--- 3. Automation 状态管理 ---")

    print("""
    Automation 支持以下操作:

    - start(agent): 启动自动化任务
    - stop(): 停止自动化任务
    - status: 获取当前状态 (running/stopped)

    状态转换:

    ┌─────────────────────────────────────────────────────────────┐
    │  Automation 创建 (status=stopped)                           │
    │    ↓ start(agent)                                           │
    │  Automation 运行中 (status=running)                         │
    │    ↓ 触发时间到达                                           │
    │  Agent 执行目标                                             │
    │    ↓ 执行完成                                               │
    │  等待下次触发                                               │
    │    ↓ stop()                                                 │
    │  Automation 停止 (status=stopped)                           │
    └─────────────────────────────────────────────────────────────┘
    """)

    # -------------------------------------------------------------------------
    # 4. 多个 Automation 管理
    # -------------------------------------------------------------------------
    print("\n--- 4. 多个 Automation 管理 ---")

    print("""
    管理多个自动化任务:

    automations = [
        Automation(name="daily-report", schedule="0 9 * * *", goal="..."),
        Automation(name="health-check", interval_seconds=300, goal="..."),
        Automation(name="weekly-summary", schedule="0 9 * * 1", goal="..."),
    ]

    # 启动所有
    for automation in automations:
        await automation.start(agent)

    # 停止所有
    for automation in automations:
        await automation.stop()
    """)

    print("\n✅ Loop Engineering Automation 定时调度演示完成")


# ============================================================================
# 演示 32: Loop Engineering - 并行 Worktree 执行 (P2)
# ============================================================================

async def demo_loop_engineering_worktree():
    """
    演示 32: Loop Engineering - 并行 Worktree 执行 (P2)

    功能:
    - 使用 WorktreeOrchestrator 并行执行多个目标
    - 每个目标在独立的 git worktree 中运行
    - 支持合并成功的分支

    学习要点:
    - Worktree 提供隔离的执行环境
    - 并行执行可以显著提高效率
    - 适用于多功能并行开发场景
    """
    print("\n" + "=" * 70)
    print("演示 32: Loop Engineering - 并行 Worktree 执行 (P2)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. WorktreeOrchestrator 概述
    # -------------------------------------------------------------------------
    print("\n--- 1. WorktreeOrchestrator 概述 ---")

    print("""
    Worktree 允许在同一仓库中并行执行多个任务:

    ┌─────────────────────────────────────────────────────────────┐
    │  主仓库 (main)                                               │
    │    ├── worktree-a/  → Agent A 执行 "实现功能 A"              │
    │    ├── worktree-b/  → Agent B 执行 "实现功能 B"              │
    │    └── worktree-c/  → Agent C 执行 "编写测试"                │
    │    ↓                                                        │
    │  所有任务并行完成                                            │
    │    ↓                                                        │
    │  合并成功的分支                                              │
    └─────────────────────────────────────────────────────────────┘

    优势:
    - 隔离执行，互不干扰
    - 并行运行，提高效率
    - 自动创建和清理 worktree
    """)

    # -------------------------------------------------------------------------
    # 2. WorktreeConfig 配置
    # -------------------------------------------------------------------------
    print("\n--- 2. WorktreeConfig 配置 ---")

    print("""
    定义并行任务:

    from harness.loop import WorktreeConfig

    tasks = [
        WorktreeConfig(
            name="feature-auth",
            goal="实现用户认证功能",
            base_branch="main",
        ),
        WorktreeConfig(
            name="feature-api",
            goal="实现 REST API 端点",
            base_branch="main",
        ),
        WorktreeConfig(
            name="feature-tests",
            goal="编写集成测试",
            base_branch="main",
        ),
    ]
    """)

    # -------------------------------------------------------------------------
    # 3. 并行执行示例
    # -------------------------------------------------------------------------
    print("\n--- 3. 并行执行示例 ---")

    print("""
    完整的并行执行代码:

    import asyncio
    from harness import AgentHarness
    from harness.loop import WorktreeOrchestrator, WorktreeConfig

    async def main():
        agent = AgentHarness(model="claude-sonnet-4-6")

        orchestrator = WorktreeOrchestrator(agent, workspace_dir=".")

        # 定义并行任务
        tasks = [
            WorktreeConfig(
                name="feature-a",
                goal="实现功能 A",
                base_branch="main",
            ),
            WorktreeConfig(
                name="feature-b",
                goal="实现功能 B",
                base_branch="main",
            ),
        ]

        # 并行执行
        results = await orchestrator.run_parallel(tasks)

        # 查看结果
        for name, result in results.items():
            print(f"{name}: {result.status}")

        # 合并成功的分支
        for name, result in results.items():
            if result.status == "completed":
                await orchestrator.merge(name)
                print(f"已合并: {name}")

    asyncio.run(main())
    """)

    # -------------------------------------------------------------------------
    # 4. WorktreeResult 结果
    # -------------------------------------------------------------------------
    print("\n--- 4. WorktreeResult 结果 ---")

    print("""
    WorktreeResult 包含以下字段:

    - name: Worktree 名称
    - status: 执行状态 (pending/running/completed/failed)
    - goal_result: GoalResult 对象（执行完成后）
    - worktree_path: Worktree 路径
    - branch_name: 分支名称
    - error: 错误信息（如果失败）

    结果处理:

    for name, result in results.items():
        if result.status == "completed":
            print(f"✅ {name} 完成")
            print(f"   迭代次数: {result.goal_result.total_iterations}")
        else:
            print(f"❌ {name} 失败: {result.error}")
    """)

    # -------------------------------------------------------------------------
    # 5. 使用场景
    # -------------------------------------------------------------------------
    print("\n--- 5. 使用场景 ---")

    print("""
    Worktree 并行执行适合以下场景:

    1. 多功能并行开发
       - 不同功能独立开发，最后合并

    2. 代码重构 + 测试
       - 一个 Agent 重构代码
       - 另一个 Agent 同步更新测试

    3. 多模块文档生成
       - 每个模块独立生成文档
       - 最后合并文档

    4. A/B 测试方案
       - 不同 Agent 实现不同方案
       - 对比效果后选择最优

    注意事项:
    - 确保 base_branch 是干净的
    - 并行任务之间不要有依赖
    - 合并前检查是否有冲突
    """)

    print("\n✅ Loop Engineering 并行 Worktree 演示完成")


# ============================================================================
# 主函数 - 运行所有演示
# ============================================================================

async def main():
    """运行所有功能演示"""

    print("\n" + "=" * 70)
    print("Harness SDK 功能演示")
    print("=" * 70)
    print(f"\n使用模型: {MODEL}")
    print(f"API 端点: {BASE_URL}")

    try:
        # 基础功能
        await demo_basic_conversation()

        # 工具系统
        await demo_file_tools()

        # 会话管理
        await demo_multi_turn_conversation()

        # 成本控制
        await demo_cost_control()

        # 进度追踪
        await demo_progress_tracking()

        # 自定义工具
        await demo_custom_tool()

        # Mock 测试
        await demo_mock_testing()

        # Skills 技能系统
        await demo_skills_system()

        # Skill 注入与批量加载
        await demo_skill_injection()

        # MCP 服务器连接
        await demo_mcp_integration()

        # Security 安全系统
        await demo_security_system()

        # Observability 可观测性
        await demo_observability()

        # 多级成本控制与异步存储
        await demo_advanced_cost_control()

        # 中断恢复
        await demo_interrupt_and_resume()

        # 配置管理
        await demo_configuration()

        # 完整工作流
        await demo_complete_workflow()

        # Lifecycle Hooks (P0)
        await demo_lifecycle_hooks()

        # 动态系统提示 (P0)
        await demo_dynamic_system_prompt()

        # Ralph Loop (P1)
        await demo_ralph_loop()

        # Sub-Agent 管理 (P1)
        await demo_sub_agent()

        # 自验证钩子 (P2)
        await demo_self_verification()

        # 渐进式技能加载 (P2)
        await demo_progressive_skills()

        # MEMORY.md 标准 (P2)
        await demo_memory_md()

        # 向量检索 (P2)
        await demo_vector_search()

        # 语义卡住检测 (P2)
        await demo_semantic_stuck_detection()

        # Guardrails PII 检测 (P2)
        await demo_guardrails()

        # CPU Router 成本优化 (P2)
        await demo_cpu_router()

        # Guardrails 进阶 (P2)
        await demo_guardrails_advanced()

        # Loop Engineering 基础用法 (P2)
        await demo_loop_engineering_basic()

        # Loop Engineering 自定义验证器 (P2)
        await demo_loop_engineering_verifier()

        # Loop Engineering Automation 定时调度 (P2)
        await demo_loop_engineering_automation()

        # Loop Engineering 并行 Worktree 执行 (P2)
        await demo_loop_engineering_worktree()

        print("\n" + "=" * 70)
        print("✅ 所有演示完成!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
