# Harness

An embeddable AI Agent SDK for Python.

## Installation

```bash
pip install harness-ai
```

### 可选扩展

```bash
pip install "harness-ai[openai]"        # OpenAI 支持
pip install "harness-ai[observability]" # OpenTelemetry 可观测性
pip install "harness-ai[sqlite]"        # SQLite 会话存储
pip install "harness-ai[web]"           # Web 抓取工具
pip install "harness-ai[guardrails]"    # PII 检测和内容安全

# 安装多个扩展
pip install "harness-ai[openai,sqlite,web,guardrails]"
```

### 开发模式

```bash
pip install -e ".[dev]"                    # 开发依赖
pip install -e ".[dev,openai,observability]"  # 开发 + 所有扩展
```

## Quick Start

```python
from harness import AgentHarness, ReadTool, GlobTool

# Create agent
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), GlobTool()],
)

# Run agent
result = await agent.run("Analyze the Python files in this directory")
print(result.content)
```

## LLM Configuration

### 第三方 OpenAI 格式接口（推荐）

Harness 支持任何兼容 OpenAI API 格式的第三方接口，只需提供 `base_url`、`api_key` 和 `model`：

```python
from harness import AgentHarness, ReadTool, GlobTool

agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",  # 第三方接口 URL
    api_key="your-api-key",                        # API Key
    model="your-model-name",                       # 模型名称
    provider="openai",                             # 使用 OpenAI 格式
    tools=[ReadTool(), GlobTool()],
)

result = await agent.run("你的问题")
```

#### 环境变量配置

也可以通过环境变量配置：

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.your-provider.com/v1
```

```python
from harness import AgentHarness, ReadTool

# 自动读取环境变量
agent = AgentHarness(
    model="your-model-name",
    provider="openai",
    tools=[ReadTool()],
)
```

#### 配置文件方式

创建 `config.yaml`：

```yaml
model: your-model-name
provider: openai
base_url: https://api.your-provider.com/v1
api_key: your-api-key
max_tokens: 4096
temperature: 0.7
system_prompt: "你是一个有帮助的助手。"
```

```python
agent = AgentHarness.from_config("config.yaml")
```

### 其他 LLM 提供商

<details>
<summary>Anthropic Claude</summary>

```python
from harness import AgentHarness, ReadTool

# 环境变量: ANTHROPIC_API_KEY
agent = AgentHarness(
    model="claude-sonnet-4-6",
    provider="anthropic",
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>OpenAI 官方</summary>

```python
from harness import AgentHarness, ReadTool

# 环境变量: OPENAI_API_KEY
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>Ollama 本地模型</summary>

```python
from harness import AgentHarness, ReadTool

agent = AgentHarness(
    model="llama3",
    provider="openai",
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama 不需要真实的 key
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>自定义 LLM 客户端</summary>

```python
from harness import AgentHarness, LLMClient, LLMConfig, ReadTool
from harness.types import LLMResponse, StopReason, TokenUsage

class MyCustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-custom-llm"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # 实现你的 LLM 逻辑
        return LLMResponse(
            content="Response",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

    async def stream(self, messages, tools=None, system=None, on_chunk=None, **kwargs):
        yield "Response"

agent = AgentHarness(
    llm_client=MyCustomLLM(LLMConfig(model="my-custom-llm")),
    tools=[ReadTool()],
)
```

</details>

## 完整配置参数

```python
from harness import AgentHarness, HarnessConfig, ReadTool

config = HarnessConfig(
    # LLM 配置
    model="your-model-name",           # 模型名称
    provider="openai",                 # 提供商: "anthropic" 或 "openai"
    base_url="https://api.xxx.com/v1", # 自定义 API 地址
    api_key="your-api-key",            # API Key
    context_window="auto",             # 上下文窗口: "auto", "32k", "64k", "128k", "200k" 或具体数值
    max_tokens="auto",                 # 输出 token: "auto" 或具体数值
    temperature=0.7,                   # 温度参数

    # Agent 配置
    max_iterations=100,                # 最大迭代次数
    tool_timeout=30.0,                 # 工具超时时间（秒）
    system_prompt="你是一个助手",      # 系统提示词

    # Memory 配置
    memory_dir=".harness/memory",      # 会话存储目录
)

agent = AgentHarness(config=config, tools=[ReadTool()])
```

### 模型上下文窗口自动适配

Harness 内置主流模型预设，自动配置上下文窗口：

```python
from harness import AgentHarness

# 自动检测（推荐）
agent = AgentHarness(model="glm-5")  # 自动使用 64K 上下文

# 手动指定
agent = AgentHarness(
    model="unknown-model",
    context_window="64k",  # 可选: "32k", "64k", "128k", "200k"
)
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `ReadTool` | 读取文件内容 |
| `WriteTool` | 写入文件 |
| `EditTool` | 编辑文件（查找替换） |
| `GlobTool` | 按模式查找文件 |
| `GrepTool` | 搜索文件内容 |
| `BashTool` | 执行 shell 命令 |
| `WebSearchTool` | Web 搜索（DuckDuckGo 免费API） |
| `WebFetchTool` | 获取网页内容 |
| `WebToMarkdownTool` | 获取网页并转换为 Markdown |

### Web Tools 示例

```python
from harness import AgentHarness, WebSearchTool, WebFetchTool, WebToMarkdownTool

agent = AgentHarness(
    model="your-model",
    provider="openai",
    tools=[WebSearchTool(), WebFetchTool(), WebToMarkdownTool()],
)

# Web 搜索
result = await agent.run("搜索 Python asyncio 最佳实践")

# 获取网页内容
result = await agent.run("获取 https://docs.python.org/3/library/asyncio.html 的内容")

# 获取网页并转换为 Markdown
result = await agent.run("将 https://blog.python.org 转换为 Markdown 格式")
```

**依赖**：
```bash
pip install aiohttp beautifulsoup4
```

## 自定义工具

```python
from harness import AgentHarness

agent = AgentHarness(model="your-model", provider="openai")

@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b

result = await agent.run("计算 5 + 3")
```

## 测试

### MockHarness（推荐）

使用 `MockHarness` 进行单元测试，无需真实 API 调用：

```python
from harness.testing import MockHarness, MockResponse
from harness.types import StopReason, ToolCall

# 简单测试
mock = MockHarness(responses=[
    MockResponse(content="这是模拟响应"),
])

result = await mock.run("测试问题")
assert result.content == "这是模拟响应"

# 模拟工具调用
mock = MockHarness(responses=[
    MockResponse(
        tool_calls=[ToolCall(id="1", name="read", arguments={"path": "/test.txt"})],
        stop_reason=StopReason.TOOL_USE,
    ),
    MockResponse(content="文件内容: test data"),
])
mock.add_tool_result("read", "test data")

result = await mock.run("读取文件")
assert "test data" in result.content
```

### RecordingHarness（录制真实交互）

录制真实交互用于回放测试：

```python
from harness.testing import RecordingHarness, RecordingConfig
from harness import AgentHarness

# 录制
agent = AgentHarness(model="claude-sonnet-4-6")
recorder = RecordingHarness(agent)

result = await recorder.run("复杂任务")
recorder.save_recording("test_fixture")

# 回放
mock = MockHarness()
mock.load_recording("test_fixture.json")

result = await mock.run("复杂任务")  # 无需真实 API
```

### MockLLMClient（传统方式）

```python
from harness import AgentHarness, ReadTool
from harness.llm import MockLLMClient, LLMConfig
from harness.llm.mock import MockResponse, create_tool_use_mock

# 创建模拟客户端
mock_client = MockLLMClient(
    model="mock-model",
    responses=[
        MockResponse(content="这是模拟响应"),
    ]
)

# 使用模拟客户端创建 agent
agent = AgentHarness(
    llm_client=mock_client,
    tools=[ReadTool()],
)

# 测试
result = await agent.run("测试问题")
assert result.content == "这是模拟响应"
```

## Guardrails (PII 检测和内容安全)

Guardrails 提供两层安全防护：

- **Layer 1: PII 规则检测** - 快速（<1ms），使用正则表达式 + 姓氏库
- **Layer 2: LLM Judge** - 语义检测（~100ms），可选

### 快速开始

```python
from harness import AgentHarness, ReadTool
from harness.guardrails import GuardrailConfig

# 只启用 Layer 1（PII 过滤）
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool()],
    guardrails=GuardrailConfig(
        enabled=True,
        layer1_enabled=True,
        layer2_enabled=False,
    ),
)

result = await agent.run("我的手机号是13812345678")
# PII 被脱敏为: "我的手机号是<手机号>"
```

### 支持的 PII 类型

| 类型 | 正则示例 | 占位符 |
|------|---------|--------|
| 中国大陆手机号 | 13812345678 | `<手机号>` |
| 中国身份证号 | 110101199001011234 | `<身份证号>` |
| 银行卡号 | 6222021234567890123 | `<银行卡号>` |
| 护照号码 | G12345678 | `<护照号>` |
| 统一社会信用代码 | 91110000000000000X | `<信用代码>` |
| 车牌号码 | 京A12345 | `<车牌号>` |
| 电子邮件 | test@example.com | `<邮箱>` |
| IP 地址 | 192.168.1.1 | `<IP地址>` |
| 香港手机号 | 5123 4567 | `<香港手机号>` |
| 香港身份证 | A123456(7) | `<香港身份证>` |
| 中文姓名 | 张三、欧阳锋 | `<姓名>` |

### 多语言支持

```python
# 简体中文（默认）
agent = AgentHarness(
    guardrails=GuardrailConfig(
        enabled=True,
        language="zh",
        placeholders={"手机号": "[REDACTED_PHONE]"},
    ),
)

# 繁体中文
agent = AgentHarness(
    guardrails=GuardrailConfig(
        enabled=True,
        language="zh-tw",
        placeholders={"手機號": "[REDACTED_PHONE]"},
    ),
)

# 英文
agent = AgentHarness(
    guardrails=GuardrailConfig(
        enabled=True,
        language="en",
        placeholders={"手机号": "[PHONE]"},
    ),
)
```

### Layer 2: LLM Judge

启用语义层面的安全检测（需要外部 Judge 服务）：

```python
agent = AgentHarness(
    model="claude-sonnet-4-6",
    guardrails=GuardrailConfig(
        enabled=True,
        layer1_enabled=True,
        layer2_enabled=True,
        judge_endpoint="http://localhost:8001/v1/chat/completions",
        judge_timeout=5.0,
    ),
)
```

### 依赖安装

```bash
# 只需要这两个包，不需要 spaCy 中文模型
pip install presidio-analyzer>=2.2.0
pip install presidio-anonymizer>=2.2.0

# 或使用可选依赖
pip install "harness-ai[guardrails]"
```

**注意**：不需要安装 `zh_core_web_sm` 或其他 spaCy 中文模型。中文 PII 使用正则表达式 + 姓氏库实现，更精准且无额外依赖。

### 直接使用 PII 过滤

```python
from harness.guardrails import UniversalPIIGuardrail, redact_pii

# 快速过滤
text = "我叫张三，手机号13812345678，身份证110101199001011234"
redacted = redact_pii(text)
# "我叫<姓名>，手机号<手机号>，身份证<身份证号>"

# 使用完整 API
guardrail = UniversalPIIGuardrail(min_score=0.5)
result = guardrail.detect(text)
print(result.entities)  # 检测到的 PII 实体
print(result.redacted)  # 脱敏后的文本
```

## Features

- **多 LLM 支持**: Anthropic Claude、OpenAI、第三方 OpenAI 格式接口、自定义 LLM
- **Agent Loop**: ReAct 风格的执行循环，支持进度事件追踪
- **Loop Engineering (Phase 1-5 全部实现)**:
  - Phase 1: Goal-Driven Execution - 目标驱动执行
  - Phase 2: Automations - 定时触发/调度
  - Phase 3: Worktrees - 并行隔离执行
  - Phase 4: Connectors - 外部系统集成（Slack、GitHub、Webhook）
  - Phase 5: Orchestrator - 工作流编排（支持 YAML 定义）
- **Streaming**: 流式输出与背压控制
- **Interrupt/Recovery**: 中断恢复，支持从快照继续执行
- **Tool System**: 内置工具 + 自定义工具 + JSON Schema 参数验证
- **Memory**: 会话管理、SQLite 持久化存储、异步 WAL 模式
- **Guardrails**: PII 检测 + LLM Judge 内容安全（简/繁/英文）
- **Cost Control**: 多层级预算控制（会话级、用户级、全局级）
- **Observability**: OpenTelemetry 集成，支持 Jaeger、Datadog、Langfuse
- **Testing**: MockHarness + RecordingHarness 完整测试工具链
- **SDK**: 简洁的 Python API
- **Progress Events**: 执行过程可视化，支持 UI 展示和调试

## Loop Engineering

**Loop Engineering** 是一种新的 Agent 编排范式：不再逐轮手动提示，而是设计自动化循环系统驱动 Agent 自主运行。

### Goal-Driven Execution（目标驱动执行）

让 Agent 自主运行直到目标达成：

```python
from harness import AgentHarness, GoalStatus

agent = AgentHarness(model="claude-sonnet-4-6")

# 基础用法
result = await agent.run_goal("修复所有类型错误")

# 检查结果
if result.status == GoalStatus.ACHIEVED:
    print(f"目标达成！共 {result.total_iterations} 轮迭代")
```

### Automations（定时触发）

定时或按间隔触发 Agent 执行：

```python
from harness.loop import Automation

# Cron 定时任务
automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",  # 每天 9:00
    goal="生成每日报告",
)

# 间隔任务
health_check = Automation(
    name="health-check",
    interval_seconds=300,  # 每 5 分钟
    goal="检查系统健康状态",
)

await automation.start(agent)
```

### Worktrees（并行隔离执行）

在独立的 git worktree 中并行执行多个 Goal：

```python
from harness.loop import WorktreeOrchestrator, WorktreeConfig

orchestrator = WorktreeOrchestrator(agent, ".")

# 并行执行多个任务
results = await orchestrator.run_parallel([
    WorktreeConfig(name="feature-a", goal="实现功能 A"),
    WorktreeConfig(name="feature-b", goal="实现功能 B"),
])

# 合并成功的分支
merge_result = await orchestrator.merge_successful(results)
```

### Connectors（外部系统集成）

与 Slack、GitHub 等外部系统双向交互：

```python
from harness.connectors import ConnectorManager, SlackConnector, SlackConfig

manager = ConnectorManager(trigger_manager)

slack = SlackConnector(config=SlackConfig(
    bot_token="xoxb-...",
    app_token="xapp-...",
))
manager.register_connector(slack)

await manager.start()
```

### Orchestrator（工作流编排）

#### 声明式工作流

```python
from harness.orchestrator import LoopOrchestrator, WorkflowConfig, WorkflowStep

orchestrator = LoopOrchestrator(agent)

workflow = WorkflowConfig(
    name="code-review",
    steps=[
        WorkflowStep(name="analyze", goal="分析代码结构"),
        WorkflowStep(name="lint", goal="运行 lint 检查"),
        WorkflowStep(name="review", goal="代码审查", depends_on=["analyze", "lint"]),
    ],
)

result = await orchestrator.run_workflow("code-review")
```

#### YAML 工作流

```yaml
# cicd.yaml
name: cicd
default_mode: parallel

steps:
  - name: lint
    goal: "运行 ruff check"
  - name: test
    goal: "运行 pytest"
  - name: deploy
    goal: "部署"
    depends_on: [lint, test]
```

```python
result = await orchestrator.run_workflow("cicd.yaml")
```

#### 多 Agent 团队协作

```python
from harness.orchestrator import TeamConfig, AgentRole, CoordinationMode

team = TeamConfig(
    name="dev-team",
    roles=[
        AgentRole(name="architect", description="系统设计", skills=["architecture"]),
        AgentRole(name="developer", description="实现", skills=["coding"]),
    ],
    coordination_mode=CoordinationMode.SEQUENTIAL,
)

result = await orchestrator.run_team("dev-team", "实现登录功能")
```

### 详细配置

提供自定义验证函数判断目标是否达成：

```python
async def check_coverage(result):
    """检查测试覆盖率是否达到 80%"""
    proc = await asyncio.create_subprocess_exec(
        "pytest", "--cov", "--cov-report=term",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return "TOTAL.*80%" in stdout.decode()

result = await agent.run_goal(
    goal="将测试覆盖率提升到 80%",
    custom_verifier=check_coverage,
    max_iterations=50,
)
```

### 配置参数

```python
result = await agent.run_goal(
    goal="你的目标",
    success_criteria="成功标准描述",   # 可选
    max_iterations=50,                # 最大迭代次数
    max_context_resets=5,             # 最大上下文重置次数
    timeout_seconds=3600,             # 超时时间（秒）
    on_progress=my_callback,          # 进度回调
)
```

### 目标状态

| 状态 | 说明 |
|------|------|
| `ACHIEVED` | 目标达成 |
| `TIMEOUT` | 超时 |
| `MAX_ITERATIONS` | 达到最大迭代次数 |
| `MAX_RESETS` | 达到最大上下文重置次数 |
| `ERROR` | Agent 执行错误 |
| `VERIFIER_FAULT` | 验证器基础设施故障 |
| `CANCELLED` | 用户取消 |

## Documentation

详细设计文档见 `docs/` 目录。

## License

MIT
