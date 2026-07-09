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

> **📚 详细文档**：完整指南请查看 `packages/sdk/docs/` 目录
> **📐 设计文档**：`packages/sdk/design/` - Loop Engineering 等设计文档
> **⚠️ 经验教训**：关键警告和最佳实践请参阅 `lessons.md`
> **🔧 编程规范**：开发流程、系统设计决策请遵守 `packages/sdk/docs/programmer_skill.md`
> **📅 进度跟踪**：`progress.txt` - 项目当前进展

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

**集成测试**：
- 位置：`packages/sdk-java/harness-sdk-integration/`
- 运行真实 LLM API 测试：`snap run gradle :harness-sdk-integration:test`
- 示例代码：`packages/sdk-java/examples/SimpleTest.java`

### 客户端开发

```powershell
# Windows 上运行客户端
cd packages\client
uv run python -m harness_client

# 打包为 EXE
uv run python build.py
```

**qasync 异步注意事项**：

客户端使用 qasync 集成 PyQt6 和 asyncio。所有异步操作必须在主线程的 `QEventLoop` 中运行：

```python
from qasync import asyncSlot

class MainWindow(QMainWindow):
    @asyncSlot(str)
    async def _on_message_sent(self, message: str):
        """信号连接的异步方法必须使用 @asyncSlot()，参数类型要与信号一致"""
        async for chunk in self.controller.send_message(message):
            response = chunk
```

**禁止**：不要在 `QThread` 中创建新的 event loop，这会导致程序静默崩溃。

**主题感知组件**：

继承 `ThemeAwareWidget` 确保组件响应主题切换：

```python
from harness_client.ui.theme_aware import ThemeAwareWidget

class MyPanel(ThemeAwareWidget):
    def _apply_theme_style(self) -> None:
        """主题切换时自动调用"""
        theme = self.theme()
        self.setStyleSheet(f"background-color: {theme.PANEL};")
```

**paintEvent 必须动态获取主题**：在 `paintEvent` 中调用 `get_theme()` 获取当前颜色，不能在初始化时缓存。

### 安装可选依赖

```bash
uv sync --all-packages --extra openai --extra observability --extra sqlite
```

### Cloud 开发

```bash
# 构建 + 启动 Docker 服务
cd packages/cloud
./scripts/build.sh

# 测试
python test_auto.py YOUR_API_KEY --provider openai --base-url YOUR_URL --model YOUR_MODEL

# 本地开发（无 Docker）
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000
uv run uvicorn harness_cloud.gateway.main:app --reload --port 8080
```

**重要**：修改代码后必须重新运行 `./scripts/build.sh` 重建镜像。

### Scraper 开发

```bash
# 运行 AI 情报抽取
cd packages/scraper
uv run harness-scraper --skill ai-intelligence

# 运行港股 Alpha 监控
uv run harness-scraper --skill hk-stocks-alpha

# 创建配置文件
uv run harness-scraper config

# 自定义 prompt
uv run harness-scraper agent "抓取 HN 上关于 MCP 的讨论"
```

**技能驱动设计**：
- 工具选择、判断标准、输出模板全部由 `skills/*.md` 定义
- Agent 是通用的，base prompt 不包含具体工作流程
- 新领域只需创建 skill 文件，无需改代码

---

## 架构

### SDK 核心组件

```
packages/sdk/src/harness/
├── sdk/
│   ├── harness.py          # AgentHarness - 主入口
│   └── config.py           # HarnessConfig - 配置类
├── core/
│   ├── agent_loop.py       # ReAct 执行循环
│   ├── step_budget.py      # 步骤预算控制
│   ├── cost_controller.py  # 成本控制
│   └── streaming.py        # 流式背压控制
├── loop/                    # Loop Engineering (P0)
│   ├── types.py            # GoalConfig, GoalResult, GoalStatus
│   ├── goal.py             # GoalVerifier (无状态验证)
│   └── goal_loop.py        # GoalLoop (目标驱动执行)
├── llm/
│   ├── base.py             # LLMClient 接口
│   ├── anthropic.py        # Claude
│   └── openai.py           # OpenAI/兼容接口
├── tools/
│   ├── base.py             # Tool 抽象类
│   ├── builtins.py         # 内置工具
│   └── executor.py         # 工具执行器
├── mcp/
│   ├── manager.py          # MCP 服务器管理
│   ├── client.py           # MCP 客户端
│   ├── transport.py        # Stdio/HTTP 传输
│   └── tool_wrapper.py     # MCP 工具包装器
└── security/
    ├── sandbox.py          # 沙箱执行
    └── validation.py       # 输入验证
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

**会话开始时**：读取 `progress.txt` 了解项目进展，审查 `lessons.md` 检查错误

**功能更新后**：更新 `progress.txt` 记录进展，如有新学习心得更新 `lessons.md`
