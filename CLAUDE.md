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

---

## 常用命令

```bash
# 安装
pip install -e ".[dev]"              # 开发模式
pip install -e ".[dev,openai]"       # 包含 OpenAI 支持

# 测试
pytest                               # 运行所有测试
pytest tests/test_phase0.py          # 运行指定文件
pytest -v --cov=harness              # 详细输出 + 覆盖率

# 代码检查
ruff check src/                      # Lint
ruff format src/                     # 格式化
mypy src/                            # 类型检查
```

---

## 架构

### 核心组件

```
src/harness/
├── sdk/harness.py          # AgentHarness - 主入口
├── core/
│   ├── agent_loop.py       # ReAct 执行循环
│   ├── circuit_breaker.py  # 熔断器
│   └── error_handler.py    # 错误恢复
├── llm/
│   ├── base.py             # LLMClient 接口
│   ├── anthropic.py        # Claude
│   └── openai.py           # OpenAI/兼容接口
├── tools/
│   ├── base.py             # Tool 抽象类
│   ├── builtins.py         # 内置工具
│   └── executor.py         # 工具执行器
├── memory/
│   ├── session.py          # 会话管理
│   ├── store.py            # 存储
│   └── context_builder.py  # 上下文构建
├── progress.py             # 进度格式化
└── types.py                # 类型定义
```

### 数据流

```
用户输入 → AgentHarness.run() → AgentLoop.run()
    ↓
[构建上下文 → 调用 LLM → 解析响应 → 执行工具] (循环)
    ↓
返回 LoopResult
```

### 核心类型

| 类型 | 说明 |
|------|------|
| `Message` | 对话消息（role, content, metadata） |
| `Session` | 会话状态（消息 + token 使用量） |
| `ToolCall` | LLM 请求执行工具 |
| `ToolResult` | 工具执行结果 |
| `LoopResult` | Agent 循环最终结果 |
| `ProgressEvent` | 执行进度事件 |

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
    async def call(self, messages, tools=None, system=None) -> LLMResponse:
        ...
    async def stream(self, ...):
        ...

# 2. 在 AgentHarness._create_llm_client() 注册
```

### 添加工具

```python
# 1. 继承 Tool
class MyTool(Tool):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def input_schema(self) -> dict: ...
    async def execute(self, args, ctx) -> ToolResult: ...

# 2. 注册
agent = AgentHarness(tools=[MyTool()])
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

### 错误处理策略

| 错误类型 | 处理方式 |
|---------|---------|
| 速率限制 | 指数退避重试 |
| 上下文溢出 | 压缩上下文 |
| 超时 | 重试 |
| 权限拒绝 | 中止 |

---

## 配置示例

```python
from harness import AgentHarness, HarnessConfig

config = HarnessConfig(
    model="claude-sonnet-4-6",
    provider="anthropic",  # 或 "openai"
    base_url="...",        # 第三方 API
    api_key="...",
    max_tokens=4096,
    max_iterations=100,
)

agent = AgentHarness(config=config, tools=[...])
```

---

## 单元测试

```python
from harness.llm import MockLLMClient, MockResponse

mock = MockLLMClient(
    model="mock",
    responses=[MockResponse(content="测试响应")]
)
agent = AgentHarness(llm_client=mock, tools=[...])
```

---

## 📝 会话工作流

**会话开始时**：读取 `progress.txt` 了解项目进展，审查 `lessons.md` 检查错误

**功能更新后**：更新 `progress.txt` 记录进展，如有新学习心得更新 `lessons.md`
