# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ 重要原则：PyQt6 开发

**我对 PyQt6 不熟悉，禁止凭经验猜测！** 涉及 PyQt6 的任何改动必须先查文档：

- **必须使用 Context7 或 Qt 官方文档查阅 API 行为**
- **写最小测试验证假设**，不要假设组件行为
- **不确定时先问用户**，不要自作主张

**参考文档**：https://doc.qt.io/qt-6/ 或使用 Context7 查阅

**关键教训**（详见 `lessons.md`）：
- `QSizePolicy.Fixed` 阻止布局扩展：如果 widget 不应该扩展，必须显式设置 `Fixed` policy
- `QTextBrowser` 不支持 flexbox/grid：复杂布局用 `<table>` + `valign`
- `QLabel.sizeHint()` 比 `QTextBrowser.sizeHint()` 更可靠：静态文本优先用 QLabel
- `setWidgetResizable(True)` 会覆盖 sizePolicy 和 setAlignment
- **禁止在 `__init__` 中缓存主题颜色**：paintEvent 必须动态调用 `get_theme()`

---

## ⚠️ 重要原则：Java SDK 禁止简化实现

**Java SDK 必须与 Python SDK 功能完全同步！**

- **严禁使用 placeholder、stub、mock 实现替代真实功能**
- **严禁跳过功能实现**，即使框架差异也必须找到等效方案
- **严禁"简化实现"**，必须实现完整功能逻辑

**唯一允许的差异**：
- Python 测试框架特有功能（如 `pytest_plugin`）
- 异步/同步 API 差异（如 `AsyncSQLiteSessionStore` → Java 使用同步 JDBC）

**当前同步率**：**99.5%**

**代码审查重点**：
- 发现 `throw new UnsupportedOperationException()` 或 `// TODO` 必须立即修复
- 发现简化实现（如固定返回值、空方法体）必须立即补全
- 新增 Python SDK 功能时，必须同步实现 Java 版本

---

## 快速参考

| 文档 | 用途 |
|------|------|
| `packages/sdk/docs/` | SDK 详细设计文档 |
| `packages/sdk/design/` | Loop Engineering 等设计文档 |
| `lessons.md` | 关键警告和最佳实践 |
| `packages/sdk/docs/programmer_skill.md` | 开发流程、系统设计决策 |
| `progress.txt` | 项目当前进展 |
| `packages/client/docs/development_guide.md` | 桌面客户端开发规范与踩坑总结 |

---

## 项目概述

Harness 是一个 **Monorepo** 项目，包含：

| 包 | 路径 | 说明 |
|---|------|------|
| `harness-sdk` | `packages/sdk/` | 可内嵌的 Python AI Agent SDK（跨平台） |
| `harness-sdk-java` | `packages/sdk-java/` | Java SDK（嵌入式库，99.5% 功能同步） |
| `harness-client` | `packages/client/` | Windows 桌面客户端（PyQt6） |
| `harness-cloud` | `packages/cloud/` | Docker 沙箱云服务 |
| `harness-scraper` | `packages/scraper/` | AI 情报/港股 Alpha 提取系统 |

**核心公式**：`Agent = Model + Harness`

---

## MCP Tools: code-review-graph

本项目集成了 **code-review-graph** MCP 服务器，提供代码知识图谱能力：

| 工具 | 用途 |
|------|------|
| `mcp__code-review-graph__get_minimal_context_tool` | 获取超紧凑上下文（~100 tokens），**任何任务前先调用** |
| `mcp__code-review-graph__detect_changes_tool` | 分析代码变更影响，风险评分 |
| `mcp__code-review-graph__semantic_search_nodes_tool` | 语义搜索代码实体 |
| `mcp__code-review-graph__traverse_graph_tool` | 从匹配节点开始遍历依赖 |
| `mcp__code-review-graph__get_hub_nodes_tool` | 找到架构热点（高连接节点） |
| `mcp__code-review-graph__get_bridge_nodes_tool` | 找到架构瓶颈（关键桥接节点） |
| `mcp__code-review-graph__list_communities_tool` | 列出代码社区（模块聚类） |

**使用场景**：
- **代码审查前**：`get_minimal_context_tool` 获取变更范围和风险评分
- **理解代码结构**：`list_communities_tool` 查看模块划分
- **定位关键代码**：`get_hub_nodes_tool` 找到核心组件
- **评估变更影响**：`detect_changes_tool` 分析影响范围

---

## 常用命令

### SDK 开发

```bash
# 安装所有包
uv sync --all-packages

# 运行 SDK 测试
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/ -v

# 运行单个测试文件
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/test_phase0.py -v

# 代码检查
uv run ruff check packages/sdk/src/
uv run ruff format packages/sdk/src/
```

### Java SDK 开发

```bash
# 使用 snap 版本的 gradle（不要使用项目自带的 gradlew）
cd packages/sdk-java
snap run gradle build

# 运行测试
snap run gradle test

# 发布到 Maven Local
snap run gradle publishToMavenLocal
```

**重要**：Java SDK 使用 snap 安装的 gradle，不要使用 `./gradlew`。

### 客户端开发

```powershell
# Windows 上运行客户端
cd packages\client
uv run python -m harness_client

# 打包为 EXE
uv run python build.py
```

**qasync 异步注意事项**：所有异步操作必须在主线程的 `QEventLoop` 中运行，使用 `@asyncSlot()` 装饰器。**禁止**在 `QThread` 中创建新的 event loop（会导致静默崩溃）。

**主题感知**：继承 `ThemeAwareWidget` 响应主题切换，`paintEvent` 中动态调用 `get_theme()` 获取当前颜色。

### Cloud 开发

```bash
cd packages/cloud
./scripts/build.sh  # 构建 + 启动 Docker 服务

# 本地开发（无 Docker）
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000
uv run uvicorn harness_cloud.gateway.main:app --reload --port 8080
```

### Scraper 开发

```bash
cd packages/scraper
uv run harness-scraper --skill ai-intelligence  # AI 情报抽取
uv run harness-scraper --skill hk-stocks-alpha   # 港股 Alpha 监控
uv run harness-scraper agent "抓取 HN 上关于 MCP 的讨论"  # 自定义 prompt
```

**技能驱动设计**：工具选择、判断标准、输出模板全部由 `skills/*.md` 定义，新领域只需创建 skill 文件。

---

## 架构

### SDK 核心组件

```
packages/sdk/src/harness/
├── sdk/                     # 主入口与配置
│   ├── harness.py          # AgentHarness - 主入口
│   └── config.py           # HarnessConfig - 配置类
├── core/                    # 核心执行引擎
│   ├── agent_loop.py       # ReAct 执行循环
│   ├── step_budget.py      # 步骤预算控制
│   ├── cost_controller.py  # 成本控制
│   └── streaming.py        # 流式背压控制
├── loop/                    # Loop Engineering (目标驱动执行)
│   ├── types.py            # GoalConfig, GoalResult, GoalStatus
│   ├── goal.py             # GoalVerifier (无状态验证)
│   ├── goal_loop.py        # GoalLoop (目标驱动执行)
│   ├── worktree_orchestrator.py  # 并行 worktree 编排
│   ├── parallel_executor.py      # 并行执行引擎
│   └── automation.py       # Automation 高级 API
├── llm/                     # LLM 客户端
│   ├── base.py             # LLMClient 接口
│   ├── anthropic.py        # Claude
│   └── openai.py           # OpenAI/兼容接口
├── tools/                   # 工具系统
│   ├── base.py             # Tool 抽象类
│   ├── builtins.py         # 内置工具 (Read/Write/Edit/Bash/Glob/Grep/WebSearch/等)
│   └── executor.py         # 工具执行器
├── mcp/                     # MCP 协议集成
│   ├── manager.py          # MCP 服务器管理
│   ├── client.py           # MCP 客户端
│   ├── transport.py        # Stdio/HTTP 传输
│   └── tool_wrapper.py     # MCP 工具包装器
├── skills/                  # 技能系统
│   ├── base.py             # Skill 基类
│   ├── registry.py         # SkillRegistry
│   ├── injector.py         # SkillInjector (系统提示注入)
│   ├── loader.py           # SkillLoader
│   └── progressive.py      # ProgressiveSkillLoader (渐进式加载)
├── memory/                  # 记忆系统
│   ├── session.py          # SessionManager
│   ├── store.py            # FileSessionStore / SQLiteSessionStore
│   ├── vector_store.py     # VectorMemoryStore (语义搜索)
│   ├── context_builder.py  # ContextBuilder
│   ├── manager.py          # MemoryManager (跨会话持久化)
│   └── compressor.py       # ContextCompressor
├── guardrails/              # 安全护栏 (PII 检测)
│   ├── chinese_guardrail.py     # 中文 PII 过滤核心
│   ├── chinese_pii_recognizers.py  # 国内手机/身份证/银行卡等识别器
│   ├── chinese_name_recognizer.py  # 中文姓名识别
│   ├── judge.py             # LLM Judge (Layer 2 语义检测)
│   ├── hook.py              # GuardrailHook
│   ├── stream_interceptor.py # 流式输出拦截
│   └── config.py            # GuardrailConfig
├── triggers/                # 触发器系统
│   ├── base.py             # 触发器基类
│   ├── cron.py             # CronTrigger
│   ├── interval.py         # IntervalTrigger
│   └── manager.py          # TriggerManager
├── connectors/              # 外部连接器
│   ├── base.py             # Connector 接口
│   ├── slack.py            # Slack 集成
│   ├── github.py           # GitHub 集成
│   ├── webhook.py          # Webhook
│   └── manager.py          # ConnectorManager
├── orchestrator/            # 多 Agent 编排
│   ├── team_orchestrator.py # TeamOrchestrator (多角色协作)
│   ├── workflow_engine.py  # WorkflowEngine (多步骤工作流)
│   ├── dependency_graph.py # 依赖解析
│   └── monitor.py          # 执行监控
├── service/                 # 微服务模式
│   ├── discovery.py        # 服务发现
│   ├── error_handler.py    # 错误处理
│   ├── metrics.py          # Prometheus 指标
│   ├── tracing.py          # OpenTelemetry 跟踪
│   └── store_redis.py      # Redis 存储
├── security/                # 安全
│   ├── sandbox.py          # 沙箱执行
│   └── validation.py       # 输入验证
└── testing/                 # 测试工具
    ├── mock_harness.py     # MockHarness
    ├── recording.py        # 录制/回放
    └── pytest_plugin.py    # Pytest 插件
```

### 客户端架构

```
packages/client/src/harness_client/
├── ui/                       # PyQt6 组件（纯渲染，不存状态）
│   ├── main_window.py        # 主窗口（三栏布局）
│   ├── chat_panel.py         # 中央对话面板
│   ├── sidebar.py            # 左侧可折叠导航栏
│   ├── right_panel.py        # 右侧面板（记忆/技能/MCP/文件树）
│   ├── settings_dialog.py    # 设置对话框
│   ├── mcp_panel.py          # MCP 配置面板
│   └── memory_panel.py       # 记忆管理面板
└── controllers/              # 控制器（数据层）
    ├── chat_controller.py    # 管理 AgentHarness
    ├── session_manager.py    # 会话状态管理（单一数据源）
    ├── mcp_controller.py     # 管理 MCP 服务器
    ├── skill_controller.py   # 管理技能
    └── memory_controller.py  # 管理全局记忆
```

**界面布局**：三栏结构
- **左侧栏**：可折叠导航（COLLAPSED_WIDTH=56px, EXPANDED_WIDTH=220px）
- **中央区**：对话面板（Markdown 渲染 + 流式输出）
- **右侧面板**：可折叠区块（**记忆**/技能/MCP 服务器/文件树）

**会话管理数据流**：
```
SessionManager (单一数据源)
    ↓
MainWindow._refresh_session_list()
    ↓
SidebarPanel.update_sessions() (纯渲染)
```

### Loop Engineering（目标驱动执行）

让 Agent 自主运行直到目标达成，而不是逐轮手动提示：

```python
from harness import AgentHarness, GoalStatus

agent = AgentHarness(model="claude-sonnet-4-6")

# 基础用法
result = await agent.run_goal("修复所有类型错误")

# 自定义验证
async def check_coverage(result):
    proc = await asyncio.create_subprocess_exec("pytest", "--cov")
    return proc.returncode == 0

result = await agent.run_goal(
    goal="测试覆盖率达到 80%",
    custom_verifier=check_coverage,
    max_iterations=50,
)

if result.status == GoalStatus.ACHIEVED:
    print(f"目标达成，共 {result.total_iterations} 轮迭代")
```

**设计原则**：
- **GoalVerifier 无状态**：所有上下文通过参数传递，支持并发执行
- **上下文自动重置**：防止 "context anxiety"（token 接近模型限制时自动重置）
- **VERIFIER_FAULT**：区分基础设施故障和 Agent 执行错误

### Cloud 架构

```
Client (WebSocket)
    ↓ JWT Token
Gateway (FastAPI)
    ├─ Container Manager (DockerManager)
    ├─ Rate Limiter (Redis)
    └─ Auth (JWT, 测试模式)
    ↓ Docker API
Agent Container (FastAPI)
    ├─ SDK Bridge (asyncio)
    └─ AgentHarness
```

**双网络设计**：
- `cloud-net`: Gateway ↔ Redis（内部通信）
- `harness-net`: Gateway ↔ Agent（可访问外网 LLM API）

### Java SDK 架构差异

Python SDK 和 Java SDK 定位不同：

| SDK | 模式 | 说明 |
|-----|------|------|
| Python | Sidecar 微服务 | 提供 FastAPI HTTP 端点，独立部署 |
| Java | 嵌入式库 | 无 HTTP 端点，应用直接调用 AgentHarness |

**功能同步率 99.5%**，未实现的 0.5% 是框架依赖差异（如 Java 用同步 JDBC，无 AsyncSQLiteSessionStore）。

### Java SDK 模块

```
packages/sdk-java/
├── harness-sdk-core          # 核心：AgentLoop, HarnessConfig, CostController
├── harness-sdk-llm           # LLM 客户端 (Anthropic, OpenAI)
├── harness-sdk-tools         # 工具系统 (ReadTool, WriteTool, BashTool, WebSearchTool 等)
├── harness-sdk-mcp           # MCP 协议集成 (McpManager, McpClient)
├── harness-sdk-memory        # 记忆系统 (SessionManager, VectorStore)
├── harness-sdk-skills        # 技能系统 (SkillRegistry, SkillInjector, ProgressiveLoader)
├── harness-sdk-triggers      # 触发器 (CronTrigger, IntervalTrigger)
├── harness-sdk-connectors    # 连接器 (Slack, GitHub, Webhook)
├── harness-sdk-orchestrator  # 多 Agent 编排 (TeamOrchestrator, WorkflowEngine)
├── harness-sdk-loop          # Loop Engineering (GoalLoop, Automation)
├── harness-sdk-guardrails    # 安全护栏 (Chinese PII, ComplianceJudge)
├── harness-sdk-security      # 安全 (沙箱, 验证)
├── harness-sdk-integration   # 集成入口 (AgentHarness, AgentLoop)
└── harness-sdk-all           # Shadow JAR 聚合模块
```

**构建方式**：使用 snap 安装的 gradle，不要使用 `./gradlew`。

---

## 关键开发原则

> 详细规范见 `packages/sdk/docs/programmer_skill.md`

- **🔴 Bitter Lesson 原则**：利用计算的通用方法击败手工编码的人类知识。提供健壮的原子工具，让模型自己规划和决策，避免过度工程化控制流
- **修改完即测试**：每次修改后立即验证，避免累积错误
- **简洁优先**：用最少的代码解决问题，不过度工程化
- **精准修改**：只碰必须碰的，不重构没坏的东西
- **需求分析优先**：编码前深入理解需求，不假设、不猜测；**API 和框架代码必须查阅官方文档**
- **消息结构固定**：LLM API 消息有固定格式要求，Session 是单一数据源，用户消息必须持久化到 session
- **测试多轮迭代**：任何涉及消息处理的代码，都要测试第二轮迭代是否正常

---

## 关键陷阱与规范

### asyncio 同步原语禁止在 `__init__` 中创建

**问题**：qasync 可能切换 event loop，导致 `asyncio.Queue`、`asyncio.Event` 等同步原语绑定到旧 loop 后失效。

```python
# ❌ 禁止：在 __init__ 中创建
class MyController:
    def __init__(self):
        self._queue = asyncio.Queue()  # RuntimeError: bound to a different event loop

# ✅ 正确：在方法中动态创建
class MyController:
    def __init__(self):
        self._queue: deque = deque()  # 存储层用 deque
        self._notifier: asyncio.Event | None = None
    
    async def get_notifier(self) -> asyncio.Event:
        if self._notifier is None:
            self._notifier = asyncio.Event()  # 在当前 event loop 创建
        return self._notifier
```

### Tool 包装器必须实现完整接口

新增 Tool 包装器时，必须实现所有接口方法，**包括 `to_definition()`**：

```python
class MyToolWrapper:
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def input_schema(self) -> dict: ...
    async def execute(self, args, ctx) -> ToolResult: ...
    def validate_arguments(self, args) -> tuple[bool, str | None]: ...
    
    # ⚠️ 容易遗漏！
    def to_definition(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}
```

### 技能文档必须包含 LLM 执行指令

技能文件（SKILL.md）必须告诉 LLM 脚本位置和执行方式：

```markdown
## ⚡ 执行指令（LLM 必读）

**当用户请求 [功能] 时，你必须：**

1. **直接运行脚本**：
   ```bash
   python ~/.harness/skills/[skill-name]/scripts/script.py [args]
   ```

**⚠️ 重要提示**：
- 不要尝试创建新脚本，脚本已经存在
- 直接使用 bash 工具运行上述命令
```

### 客户端必须注册 BashTool

如果技能涉及运行脚本，客户端必须注册 `BashTool`：

```python
from harness.tools.builtins import ReadTool, WriteTool, EditTool, GlobTool, GrepTool, BashTool

def _init_tools(self) -> list[Tool]:
    return [ReadTool(), WriteTool(), EditTool(), GlobTool(), GrepTool(), BashTool()]  # BashTool 必需
```

---

## 开发指南

### 添加 LLM Provider

```python
# packages/sdk/src/harness/llm/my_llm.py
class MyLLM(LLMClient):
    @property
    def model_name(self) -> str: ...

    async def call(self, messages, tools=None, system=None) -> LLMResponse:
        ...

# 直接传入 AgentHarness
agent = AgentHarness(llm_client=MyLLM(...))
```

### 添加工具

```python
# 方式 1：继承 Tool 类
class MyTool(Tool):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def input_schema(self) -> dict: ...  # JSON Schema 格式
    async def execute(self, args, ctx) -> ToolResult: ...

    # 可选：参数验证（默认使用 jsonschema）
    def validate_arguments(self, args) -> tuple[bool, str | None]:
        ...

# 方式 2：装饰器
@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b
```

### 第三方 OpenAI 格式 API

```python
agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",
    api_key="your-api-key",
    model="your-model-name",
    provider="openai",
)
```

### PII 便捷函数

```python
from harness.guardrails import check_pii, scan_pii, redact_pii, PIIEntity

# check_pii() 返回元组：(safe_text, entities, has_pii)
safe_text, entities, has_pii = check_pii("我的手机号是13812345678")

# PIIEntity 属性
for entity in entities:
    print(f"Type: {entity.entity_type}")  # "PHONE_NUMBER"
    print(f"Text: {entity.text}")          # "13812345678"

# 快速脱敏
redacted = redact_pii(text)  # "我的手机号是<手机号>"
```

**注意**：`check_pii()` 返回元组而非对象，使用元组解包获取结果。

### 测试使用 MockHarness

```python
from harness.testing import MockHarness, MockResponse

mock = MockHarness(responses=[
    MockResponse(content="模拟响应"),
])
result = await mock.run("测试")
```

---

## 发布

### 发布 SDK 到 PyPI

```bash
cd packages/sdk
uv build
uv publish
```

### 打包客户端

```powershell
cd packages\client
uv run python build.py
# 输出: dist/HarnessClient.exe
```

---

## 📝 会话工作流

**会话开始时**：
- 读取 `progress.txt`（优先关注最后 50 行了解最新进展）
- 审查 `lessons.md` 检查已记录的错误
- 检查 `/home/marcowong/.claude/plans/` 目录看是否有未完成的计划

**功能更新后**：
- 更新 `progress.txt` 记录进展
- 如有新学习心得更新 `lessons.md`

**提交规范**：遵循 Conventional Commits（`feat:`、`fix:`、`refactor:`、`docs:`、`chore:` 等）

---

## 文档规范

**技术规范先于问题记录**：文档应指导开发，而非只是事后记录问题。参考 `packages/client/docs/development_guide.md` 的格式：
- 核心原则（强制性语言：禁止、必须）
- 规范章节（按类别组织）
- 检查清单（便于合规审计）
- 问题参考降级为附录
