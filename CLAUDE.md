# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### 安装可选依赖

```bash
uv sync --all-packages --extra openai --extra observability --extra sqlite
```

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
│   └── client/                   # harness-client 包
│       ├── src/harness_client/
│       │   ├── ui/               # PyQt6 UI 组件
│       │   └── controllers/      # 控制器（连接 SDK）
│       ├── resources/            # 样式、模板
│       └── harness-client.spec   # PyInstaller 配置
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
├── skills/
│   ├── base.py             # Skill 基类
│   ├── registry.py         # 技能注册
│   └── injector.py         # System prompt 注入
├── mcp/
│   ├── manager.py          # MCP 服务器管理
│   └── transport.py        # Stdio/HTTP 传输
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
│   ├── right_panel.py        # 右侧面板（技能/MCP/文件树）
│   ├── settings_dialog.py    # 设置对话框
│   └── mcp_panel.py          # MCP 配置面板
└── controllers/              # 控制器（数据层）
    ├── chat_controller.py    # 管理 AgentHarness
    ├── session_manager.py    # 会话状态管理（单一数据源）
    ├── mcp_controller.py     # 管理 MCP 服务器
    └── skill_controller.py   # 管理技能
```

**界面布局**：三栏结构
- **左侧栏**：可折叠导航（COLLAPSED_WIDTH=56px, EXPANDED_WIDTH=220px）
- **中央区**：对话面板（Markdown 渲染 + 流式输出）
- **右侧面板**：可折叠区块（技能/MCP 服务器/文件树）

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

---

## 关键开发原则

> 详细规范见 `packages/sdk/docs/programmer_skill.md`

- **🔴 Bitter Lesson 原则**：利用计算的通用方法击败手工编码的人类知识。提供健壮的原子工具，让模型自己规划和决策，避免过度工程化控制流
- **修改完即测试**：每次修改后立即验证，避免累积错误
- **简洁优先**：用最少的代码解决问题，不过度工程化
- **精准修改**：只碰必须碰的，不重构没坏的东西
- **需求分析优先**：编码前深入理解需求，不假设、不猜测；**API 和框架代码必须查阅官方文档**
- **API/框架文档必须查阅**：修改 API 调用、框架组件、库的使用方式前必须查阅官方文档，不能凭经验假设

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
    def input_schema(self) -> dict: ...
    async def execute(self, args, ctx) -> ToolResult: ...

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
Today's date is 2026-05-31.
