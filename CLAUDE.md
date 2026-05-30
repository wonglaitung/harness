# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 快速参考

> **📚 详细文档**：完整指南请查看 [docs/](docs/) 目录
> **⚠️ 经验教训**：关键警告和最佳实践请参阅 [lessons.md](lessons.md)
> **🔧 编程规范**：开发流程、系统设计决策请遵守 [docs/programmer_skill.md](docs/programmer_skill.md)
> **📅 进度跟踪**：[progress.txt](progress.txt) - 项目当前进展

---

## 项目概述

Harness 是一个可内嵌的 Python AI Agent SDK。它让 LLM 从"回答问题"变成能自主操作的智能体。

```
Agent = Model + Harness
```

**核心能力**：多 LLM 支持、工具系统、技能注入、安全沙箱、MCP 协议、成本控制、中断恢复、可观测性集成。

---

## 常用命令

```bash
# 安装
pip install -e ".[dev]"                    # 开发模式
pip install -e ".[dev,openai,observability,sqlite,web]"  # 开发 + 所有扩展

# 测试
pytest                                     # 运行所有测试
pytest tests/test_phase0.py                # 运行指定文件
pytest -v --cov=harness                    # 详细输出 + 覆盖率
pytest -k "test_name"                      # 按名称筛选测试

# 代码检查
ruff check src/                            # Lint
ruff format src/                           # 格式化
mypy src/                                  # 类型检查
python -m py_compile src/harness/file.py   # 单文件语法检查
```

---

## 架构

### 核心组件

```
src/harness/
├── sdk/
│   ├── harness.py          # AgentHarness - 主入口
│   └── config.py           # HarnessConfig - 配置类
├── core/
│   ├── agent_loop.py       # ReAct 执行循环
│   ├── circuit_breaker.py  # 熔断器
│   ├── error_handler.py    # 错误恢复
│   ├── cost_controller.py  # 成本控制
│   ├── streaming.py        # 流式背压控制
│   └── observability.py    # OpenTelemetry 集成
├── llm/
│   ├── base.py             # LLMClient 接口
│   ├── anthropic.py        # Claude
│   ├── openai.py           # OpenAI/兼容接口
│   └── mock.py             # Mock 客户端
├── tools/
│   ├── base.py             # Tool 抽象类
│   ├── builtins.py         # 内置工具 (Read, Write, Bash, Web, etc.)
│   ├── executor.py         # 工具执行器
│   └── registry.py         # 工具注册表
├── memory/
│   ├── session.py          # 会话管理
│   ├── store.py            # SQLite/File 存储
│   ├── context_builder.py  # 上下文构建
│   ├── compressor.py       # 上下文压缩
│   └── token_counter.py    # Token 计数
├── skills/
│   ├── base.py             # Skill 基类
│   ├── registry.py         # 技能注册
│   ├── injector.py         # System prompt 注入
│   └── loader.py           # 文件加载
├── security/
│   ├── sandbox.py          # 沙箱执行
│   ├── validation.py       # 输入验证
│   ├── audit.py            # 审计日志
│   └── sanitizer.py        # 输出脱敏
├── mcp/
│   ├── transport.py        # Stdio/HTTP 传输
│   ├── client.py           # JSON-RPC 2.0 客户端
│   ├── manager.py          # MCP 服务器管理
│   └── tool_wrapper.py     # MCP 工具包装
├── testing/
│   ├── mock_harness.py     # MockHarness 测试工具
│   ├── recording.py        # RecordingHarness 录制/回放
│   └── pytest_plugin.py    # pytest 插件
├── progress.py             # 进度格式化
├── types.py                # 类型定义
└── model_presets.py        # 模型预设配置
```

### 数据流

```
用户输入 → AgentHarness.run() → AgentLoop.run()
    ↓
[构建上下文 → 调用 LLM → 解析响应 → 执行工具] (循环)
    ↓
返回 LoopResult

中断/恢复：
save_snapshot() → LoopSnapshot (可序列化)
resume_from_snapshot(snapshot) → 恢复执行
```

### 核心类型

| 类型 | 说明 |
|------|------|
| `Message` | 对话消息（role, content, metadata） |
| `Session` | 会话状态（消息 + token 使用量） |
| `ToolCall` | LLM 请求执行工具 |
| `ToolResult` | 工具执行结果 |
| `LoopResult` | Agent 循环最终结果 |
| `LoopSnapshot` | 循环快照（用于中断恢复） |
| `ProgressEvent` | 执行进度事件 |
| `CostConfig` | 成本控制配置 |
| `BudgetExceededError` | 预算超限异常 |

---

## 关键开发原则

> 详细规范见 [docs/programmer_skill.md](docs/programmer_skill.md)

- **修改完即测试**：每次修改后立即验证，避免累积错误
- **简洁优先**：用最少的代码解决问题，不过度工程化
- **精准修改**：只碰必须碰的，不重构没坏的东西
- **需求分析优先**：编码前深入理解需求，不假设、不猜测

---

## 开发指南

### 添加 LLM Provider

```python
# 1. 继承 LLMClient
class MyLLM(LLMClient):
    @property
    def model_name(self) -> str: ...

    async def call(self, messages, tools=None, system=None) -> LLMResponse:
        ...

    async def stream(self, messages, ...):
        ...

# 2. 直接传入 AgentHarness
agent = AgentHarness(llm_client=MyLLM(LLMConfig(model="my-model")))
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

# 方式 2：装饰器（推荐简单工具）
@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b
```

### 第三方 OpenAI 格式 API 配置

```python
# 方式 1：直接传参
agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",
    api_key="your-api-key",
    model="your-model-name",
    provider="openai",
)

# 方式 2：环境变量
# export OPENAI_API_KEY=xxx
# export OPENAI_BASE_URL=https://api.xxx.com/v1
agent = AgentHarness(model="model-name", provider="openai")

# 方式 3：配置文件 (config.yaml)
agent = AgentHarness.from_config("config.yaml")
```

### 进度显示

```python
# 简单用法
result = await agent.run("任务", verbose=True)

# 自定义格式
from harness import create_progress_handler
handler = create_progress_handler("emoji")  # simple/detailed/colored/emoji
result = await agent.run("任务", on_progress=handler)
```

### 中断恢复

```python
# 保存快照
snapshot = await agent.save_snapshot()

# 恢复执行
result = await agent.resume_from_snapshot(snapshot)

# 序列化
data = snapshot.to_dict()
snapshot = LoopSnapshot.from_dict(data)
```

### 错误处理策略

| 错误类型 | 处理方式 |
|---------|---------|
| 速率限制 | 指数退避重试 |
| 上下文溢出 | 压缩上下文 |
| 超时 | 重试 |
| 权限拒绝 | 中止 |
| 预算超限 | 抛出 BudgetExceededError |

---

## 测试

### MockHarness（推荐）

```python
from harness.testing import MockHarness, MockResponse
from harness.types import StopReason, ToolCall

# 简单测试
mock = MockHarness(responses=[
    MockResponse(content="模拟响应"),
])

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
```

### RecordingHarness（录制/回放）

```python
from harness.testing import RecordingHarness

# 录制真实交互
recorder = RecordingHarness(agent)
result = await recorder.run("复杂任务")
recorder.save_recording("fixture")

# 回放测试
mock = MockHarness()
mock.load_recording("fixture.json")
```

---

## 配置示例

```python
from harness import AgentHarness, HarnessConfig, CostConfig

config = HarnessConfig(
    # LLM 配置
    model="claude-sonnet-4-6",
    provider="anthropic",  # 或 "openai"
    base_url="...",        # 第三方 API
    api_key="...",
    context_window="auto", # 自动检测或 "32k"/"64k"/"128k"/"200k"
    max_tokens="auto",     # 自动或具体数值

    # Agent 配置
    max_iterations=100,
    tool_timeout=30.0,
    system_prompt="...",

    # 成本控制
    cost_config=CostConfig(
        session_token_limit=100000,
        daily_token_limit=1000000,
    ),

    # 存储
    memory_dir=".harness/memory",
)

agent = AgentHarness(config=config, tools=[...])
```

---

## 📝 会话工作流

**会话开始时**：读取 `progress.txt` 了解项目进展，审查 `lessons.md` 检查错误

**功能更新后**：更新 `progress.txt` 记录进展，如有新学习心得更新 `lessons.md`
