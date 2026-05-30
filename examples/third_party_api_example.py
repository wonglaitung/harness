"""
Harness SDK 功能演示 - 开箱即用案例

这个文件展示了 Harness SDK 的主要功能，帮助你快速了解项目能力。

运行方式:
    python examples/third_party_api_example.py

功能模块 (16 个演示):
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

作者: Harness Team
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径（用于开发测试）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ============================================================================
# 导入 Harness SDK 的主要组件
# ============================================================================

# 主入口 - 创建 AI Agent 的核心类
from harness import AgentHarness

# 配置类 - 自定义 Agent 行为
from harness import HarnessConfig

# 内置工具 - 开箱即用的文件操作工具
from harness import (
    ReadTool,      # 读取文件
    WriteTool,     # 写入文件
    EditTool,      # 编辑文件
    GlobTool,      # 文件名搜索 (类似 find)
    GrepTool,      # 文件内容搜索 (类似 grep)
    BashTool,      # 执行 Shell 命令
    WebSearchTool, # 网络搜索
    WebFetchTool,  # 网页抓取
)

# 成本控制 - 管理 Token 消耗
from harness import (
    CostConfig,        # 成本配置
    CostController,    # 成本控制器
    TokenUsage,        # Token 使用量
    BudgetExceededError,  # 预算超限异常
)

# 进度追踪 - 监控执行过程
from harness import (
    ProgressEvent,     # 进度事件
    ProgressEventType, # 事件类型
    create_progress_handler,  # 创建进度处理器
)

# 会话管理 - 持久化对话
from harness import (
    Session,           # 会话对象
    SQLiteSessionStore, # SQLite 存储
)

# 类型定义
from harness import (
    LoopResult,  # 执行结果
    LoopState,   # 执行状态
    Message,     # 消息
    ToolResult,  # 工具执行结果
)

# Mock 测试 - 不需要真实 API 的测试
from harness.testing import MockHarness
from harness.testing.mock_harness import MockResponse

# Skills 技能系统 - 模块化能力单元
from harness import (
    Skill,          # 技能定义
    SkillTrigger,   # 触发条件
    SkillTools,     # 工具权限配置
    SkillRegistry,  # 技能注册表
    SkillInjector,  # 技能注入器
    SkillLoader,    # 技能加载器
    InjectionConfig, # 注入配置
)

# MCP 支持 - 连接外部工具服务器
from harness import (
    MCPManager,       # MCP 管理器
    MCPServerConfig,  # MCP 服务器配置
    StdioTransport,   # 标准输入输出传输
    HTTPTransport,    # HTTP 传输
)

# Observability 可观测性 - OpenTelemetry 集成
from harness import (
    ObservabilityManager,  # 可观测性管理器
    ObservabilityConfig,   # 配置
    setup_observability,   # 快速初始化函数
)


# Security 安全系统 - 保护 Agent 免受攻击
from harness import (
    LightweightSandbox,    # 轻量沙箱
    InputValidator,        # 输入验证器
    PromptInjectionDetector,  # 提示注入检测
    AuditLogger,           # 审计日志
    SecurityConfig,        # 安全配置（新增）
)


# 多级成本存储
from harness import (
    InMemoryCostStorage,   # 内存存储
    AsyncSQLiteSessionStore,  # 异步 SQLite 存储
    CostControlConfig,     # 成本控制配置（新增）
    StorageConfig,         # 存储配置（新增）
)


# ============================================================================
# 配置区 - 修改这里使用你的 API
# ============================================================================

# 方式 1: 使用第三方 OpenAI 兼容 API（如智谱 GLM）
BASE_URL = "http://47.115.141.152:8080/v2/coding"
API_KEY = "bce-v3/ALTAKSP-SVgAJ9aJuetewQXvUZLtt/608fe88fd13b29ffff4cb6aa0dfe8a6440e7e8d8"
MODEL = "glm-5"
PROVIDER = "openai"  # 第三方 API 使用 openai 协议

# 方式 2: 使用官方 Anthropic API
# BASE_URL = None
# API_KEY = "your-anthropic-api-key"  # 或设置 ANTHROPIC_API_KEY 环境变量
# MODEL = "claude-sonnet-4-6"
# PROVIDER = "anthropic"

# 方式 3: 使用官方 OpenAI API
# BASE_URL = None
# API_KEY = "your-openai-api-key"  # 或设置 OPENAI_API_KEY 环境变量
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
    print(f"Token 使用: 输入 {result.token_usage.input_tokens}, 输出 {result.token_usage.output_tokens}")


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
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[
            ReadTool(),   # 读取文件
            GlobTool(),   # 文件名搜索
            GrepTool(),   # 内容搜索
        ],
    )

    # 让 Agent 使用工具完成任务
    print("\n用户: 请列出当前目录下所有的 Python 文件，然后读取 pyproject.toml 的前 20 行。")
    print("-" * 70)

    result = await agent.run(
        "请使用 glob 工具列出当前目录下所有的 Python 文件（*.py），"
        "然后读取 pyproject.toml 文件的前 20 行内容。",
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

    print(f"成本配置:")
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
    print(f"\nToken 使用统计:")
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
            print(f"\n🚀 开始执行...")
        elif event.type == ProgressEventType.LLM_CALL:
            print(f"📡 调用 LLM...")
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
            print(f"🏁 执行完成")

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool(), GlobTool()],
    )

    # 使用自定义进度回调
    print("\n用户: 列出所有 Markdown 文件并读取 README.md")
    result = await agent.run(
        "使用 glob 工具列出所有 *.md 文件，然后读取 README.md 的前 10 行。",
        on_progress=on_progress,
    )

    print(f"\n事件统计:")
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
    print(f"\n注入预览:")
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
    print(f"  - 默认配置路径: .mcp.json 或 ~/.harness/mcp.json")
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
    from harness import SecurityConfig, HarnessConfig

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
        sandbox_allowed_commands=None,     # None = 允许所有非阻止命令
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

    print(f"\n配置:")
    print(f"  - 服务名称: {config.service_name}")
    print(f"  - 控制台输出: {config.export_console}")
    print(f"  - OTLP 导出: {config.export_otlp}")

    # 3. 快速初始化
    manager = ObservabilityManager(config=config)
    print(f"\n可观测性管理器已创建")
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
    from harness import HarnessConfig, ObservabilityConfig

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
    print(f"\n全局使用量:")
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

    print(f"\n多级预算配置:")
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
    from harness import CostController

    controller = CostController(config=cost_config, storage=storage)

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
    print(f"\n--- 异步 SQLite 存储（生产环境推荐）---")
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

    from harness import LoopSnapshot

    snapshot = agent._loop.create_snapshot(
        session=result.session,
        iteration=result.iterations,
    )

    print(f"\n已创建执行快照:")
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
            # 创建快照用于恢复
            snapshot = agent._loop.create_snapshot(
                session=agent._loop.session,
                iteration=agent._loop.current_iteration,
            )
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
        # 恢复 session 状态
        agent._loop.restore_from_snapshot(snapshot)
        # 继续执行
        return await agent.run("请继续...")
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
