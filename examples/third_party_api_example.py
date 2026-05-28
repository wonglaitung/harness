"""
Harness SDK 功能演示 - 全面测试案例

这个文件展示了 Harness SDK 的所有主要功能，帮助你快速了解项目能力。

运行方式:
    python examples/third_party_api_example.py

功能模块:
    1. 基础对话 - 简单问答、多轮对话
    2. 工具系统 - 文件操作、搜索、自定义工具
    3. 成本控制 - 预算限制、Token 追踪
    4. 进度追踪 - 实时监控执行过程
    5. 会话管理 - 持久化、恢复对话
    6. 高级功能 - 中断恢复、Mock 测试

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
)

# MCP 支持 - 连接外部工具服务器
from harness import (
    MCPManager,       # MCP 管理器
    MCPServerConfig,  # MCP 服务器配置
    StdioTransport,   # 标准输入输出传输
    HTTPTransport,    # HTTP 传输
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

    学习要点:
    - Skill 是模块化的能力单元
    - 包含触发条件、工具权限、执行内容
    - 可以从文件加载或代码创建
    """
    print("\n" + "=" * 70)
    print("演示 8: Skills 技能系统")
    print("=" * 70)

    # 1. 创建一个代码审查技能
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
            keywords=["review", "审查", "检查代码", "code check"],
            patterns=[r"review\s+(this\s+)?code", r"审查.*代码"],
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

    # 4. 创建一个翻译技能
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

    # 5. 技能可以保存到文件
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
# 演示 9: MCP 服务器连接
# ============================================================================

async def demo_mcp_integration():
    """
    演示 9: MCP (Model Context Protocol) 服务器连接

    功能:
    - 配置 MCP 服务器
    - Stdio 和 HTTP 传输方式
    - 自动发现和注册工具

    学习要点:
    - MCP 让 Agent 可以使用外部工具服务器
    - 支持 Stdio (本地进程) 和 HTTP (网络) 两种传输
    - 工具自动注册到 Agent

    注意: 此演示只展示配置方式，不实际连接服务器
    """
    print("\n" + "=" * 70)
    print("演示 9: MCP (Model Context Protocol) 服务器连接")
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

    # 4. 添加服务器配置（不实际启动）
    print("\nMCP 管理器配置:")
    print(f"  - 默认配置路径: .mcp.json 或 ~/.harness/mcp.json")

    # 5. 配置文件格式示例
    config_example = """
# .mcp.json 配置文件示例
{
    "servers": {
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

    print("\n✅ MCP 配置演示完成")
    print("   注意: 实际连接需要运行 MCP 服务器")


# ============================================================================
# 演示 11: 中断与恢复
# ============================================================================

async def demo_interrupt_and_resume():
    """
    演示 11: 中断与恢复

    功能:
    - 中断长时间运行的任务
    - 保存执行状态
    - 从中断点恢复执行

    学习要点:
    - agent.interrupt() 中断执行
    - LoopSnapshot 保存状态
    - resume_from_snapshot() 恢复
    """
    print("\n" + "=" * 70)
    print("演示 8: 中断与恢复")
    print("=" * 70)

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider=PROVIDER,
        tools=[ReadTool()],
    )

    # 演示中断功能
    print("\n开始执行一个复杂任务...")
    print("(在实际场景中，可以通过 agent.interrupt() 中断)")

    result = await agent.run("读取 pyproject.toml 文件，告诉我项目名称是什么。")

    print(f"\n响应: {result.content[:200]}...")

    # 创建快照（用于恢复）
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


# ============================================================================
# 演示 11: 配置管理
# ============================================================================

async def demo_configuration():
    """
    演示 11: 配置管理

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
    print("演示 11: 配置管理")
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
# 演示 12: 完整工作流
# ============================================================================

async def demo_complete_workflow():
    """
    演示 12: 完整工作流

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
    print("演示 12: 完整工作流 - 代码分析助手")
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

        # MCP 服务器连接
        await demo_mcp_integration()

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
