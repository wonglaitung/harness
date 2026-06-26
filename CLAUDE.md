# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ 重要原则：PyQt6 开发

**我对 PyQt6 不熟悉，禁止凭经验猜测！** 涉及 PyQt6 的任何改动必须先查文档：

- **必须使用 Context7 或 Qt 官方文档查阅 API 行为**
- **写最小测试验证假设**，不要假设组件行为
- **不确定时先问用户**，不要自作主张

**参考文档**：https://doc.qt.io/qt-6/ 或使用 Context7 查阅

---

## 快速参考

> **📚 详细文档**：完整指南请查看 `packages/sdk/docs/` 目录
> **⚠️ 经验教训**：关键警告和最佳实践请参阅 `lessons.md`
> **🔧 编程规范**：开发流程、系统设计决策请遵守 `packages/sdk/docs/programmer_skill.md`
> **📅 进度跟踪**：`progress.txt` - 项目当前进展

---

## 项目概述

Harness 是一个 **Monorepo** 项目，包含：

| 包 | 路径 | 说明 |
|---|------|------|
| `harness-sdk` | `packages/sdk/` | 可内嵌的 Python AI Agent SDK（跨平台） |
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

**QTextBrowser HTML/CSS 限制**：

QTextBrowser 只支持有限的 CSS 属性和 HTML 标签（参考 https://doc.qt.io/qt-6/richtext-html-subset.html）：

- **支持的 CSS**：`background-color`, `color`, `font-*`, `margin-*`, `padding-*`, `border-*`, `vertical-align`, `text-align`, `line-height`
- **不支持**：`flexbox`, `grid`, `position`, `float`, `display: flex/grid`, CSS 变量
- **布局方案**：复杂布局必须用 `<table>` + `valign="top"` 替代 flexbox

```html
<!-- 错误：flexbox 在 QTextBrowser 中不工作 -->
<div style="display: flex; align-items: flex-start;">...</div>

<!-- 正确：使用 table 布局 -->
<table width="100%" style="border: none; border-spacing: 0;">
    <tr>
        <td width="40" valign="top">头像</td>
        <td valign="top">内容</td>
    </tr>
</table>
```

**矢量图标绘制**：

使用 `QPainter` + `QPixmap` 绘制矢量图标，避免 Unicode 字符图标模糊问题：

```python
def create_play_icon(size: int = 24, color: QColor = QColor("#FFFFFF")) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)  # 注意：PyQt6 使用小写 transparent
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(color))
    # 绘制三角形
    triangle = [QPointF(x1, y1), QPointF(x2, y2), QPointF(x3, y3)]
    painter.drawPolygon(QPolygonF(triangle))
    painter.end()
    return QIcon(pixmap)
```

**自定义绘制组件**：

对于需要精细视觉控制的组件（如滑动条、进度条），使用 `QWidget` + `paintEvent` 自定义绘制：

```python
class ImportanceSlider(QWidget):
    """自定义绘制的滑动条，支持颜色渐变和手柄放大效果"""

    valueChanged = pyqtSignal(float)

    def __init__(self, initial_value: float = 0.5, parent=None):
        super().__init__(parent)
        self._value = initial_value
        self._hover = False
        self.setFixedHeight(20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = get_theme()  # 动态获取当前主题
        # 绘制轨道、进度、手柄...

    def mousePressEvent(self, event):
        # 处理拖拽交互
```

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

### Monorepo 结构

```
harness/
├── packages/
│   ├── sdk/                      # harness-sdk 包
│   │   ├── src/harness/          # SDK 核心代码
│   │   ├── tests/                # 测试文件
│   │   ├── examples/             # 示例代码
│   │   └── docs/                 # 文档
│   │
│   ├── client/                   # harness-client 包
│   │   ├── src/harness_client/
│   │   │   ├── ui/               # PyQt6 UI 组件
│   │   │   └── controllers/      # 控制器（连接 SDK）
│   │   ├── resources/            # 样式、模板
│   │   └── harness-client.spec   # PyInstaller 配置
│   │
│   └── cloud/                    # harness-cloud 包
│       ├── src/harness_cloud/
│       │   ├── agent/            # 容器内 Agent 服务
│       │   ├── gateway/          # Gateway 控制层
│       │   └── common/           # 共享消息定义
│       ├── docker/               # Dockerfile
│       ├── scripts/              # 构建脚本
│       ├── frontend/             # Vue 前端
│       └── docker-compose.yml
│
│   └── scraper/                  # harness-scraper 包
│       ├── src/harness_scraper/
│       │   ├── agent.py          # IntelAgent（通用信息提取代理）
│       │   ├── tools/            # 数据源工具
│       │   └── cli.py            # CLI 入口
│       ├── skills/               # 技能文件（领域知识）
│       │   ├── ai-intelligence.md
│       │   └── hk-stocks-alpha.md
│       └── output/               # One-Pager 输出
│
├── pyproject.toml                # Workspace 根配置
├── uv.lock                       # 锁定依赖
├── CLAUDE.md
├── lessons.md
└── progress.txt
```

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

**全局记忆**：
- 记忆文件存储在 `~/.harness/MEMORY.md`
- 通过 `MemoryController` 管理 CRUD 操作
- 自动注入到 Agent 上下文中

**会话管理数据流**：
```
SessionManager (单一数据源)
    ↓
MainWindow._refresh_session_list()
    ↓
SidebarPanel.update_sessions() (纯渲染)
```

### 数据流

```
用户输入 → AgentHarness.run() → AgentLoop.run()
    ↓
[构建上下文 → 调用 LLM → 解析响应 → 执行工具] (循环)
    ↓
返回 LoopResult
```

### Scraper 架构（技能驱动）

```
IntelAgent（通用代理）
    ↓ 加载 Skill 文件
    ↓ Skill 定义：工具清单、判断标准、输出模板
    ↓
AgentHarness.run(prompt)
    ↓
LLM 根据 Skill 自主决策工具调用
    ↓
One-Pager 输出 + MEMORY.md 自动更新
```

**核心设计**：
- Agent 不硬编码控制流，遵循 Bitter Lesson
- Skill 文件定义一切：工具选择、判断标准、工作流程
- 新领域只需创建 skill 文件（`skills/*.md`）

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

**双层认证**：
1. Gateway: JWT Token（用户认证，测试模式接受任意 token）
2. Agent: API Key（LLM Provider 认证）

**Vue 前端**：
- 位于 `packages/cloud/frontend/`
- 技术栈：Vue 3.4+ + TypeScript 5.0+ + Vite 5.0+ + Pinia + TailwindCSS
- 构建后挂载到 Gateway 容器提供静态文件服务

**Spring Cloud 集成**（可选依赖）：
- W3C TraceContext 追踪
- Prometheus 指标导出
- Redis 分布式会话存储
- Nacos/Eureka 服务发现
- 详见 `packages/sdk/docs/14-spring-cloud-integration.md`

---

## 关键开发原则

> 详细规范见 `packages/sdk/docs/programmer_skill.md`

- **🔴 Bitter Lesson 原则**：利用计算的通用方法击败手工编码的人类知识。提供健壮的原子工具，让模型自己规划和决策，避免过度工程化控制流
- **修改完即测试**：每次修改后立即验证，避免累积错误
- **简洁优先**：用最少的代码解决问题，不过度工程化
- **精准修改**：只碰必须碰的，不重构没坏的东西
- **需求分析优先**：编码前深入理解需求，不假设、不猜测；**API 和框架代码必须查阅官方文档**
- **API/框架文档必须查阅**：修改 API 调用、框架组件、库的使用方式前必须查阅官方文档，不能凭经验假设。**禁止凭经验猜测，必须先用 Context7 或官方文档查阅**
- **消息结构固定**：LLM API 消息有固定格式要求，Session 是单一数据源，用户消息必须持久化到 session
- **测试多轮迭代**：任何涉及消息处理的代码，都要测试第二轮迭代是否正常
- **QTextBrowser 限制**：只支持基础 CSS，复杂布局用 `<table>`，不支持 flexbox/grid

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

### MCP 工具包装器

MCP 工具通过 `MCPToolWrapper` 包装为 Harness Tool 接口：

```python
class MCPToolWrapper:
    @property
    def name(self) -> str:         # 格式: mcp_{server}_{tool}
    @property
    def input_schema(self) -> dict # JSON Schema
    def validate_arguments(self, args) -> tuple[bool, str | None]
    async def execute(self, args, ctx) -> ToolResult
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

# currentDate
Today's date is 2026-06-25.
