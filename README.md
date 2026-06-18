# Harness

**可内嵌的 Python AI Agent SDK**

```
Agent = Model + Harness
```

让 LLM 从"回答问题"变成能自主操作的智能体。

---

## 特性

- **多 LLM 支持** — Anthropic Claude、OpenAI 及兼容 API
- **工具系统** — 内置文件操作、Web 搜索，支持自定义工具
- **MCP 协议** — 连接外部 MCP 工具服务器扩展能力
- **技能注入** — 根据上下文自动注入专业技能
- **安全沙箱** — 命令验证、注入检测、审计日志
- **成本控制** — Token 预算管理、熔断机制
- **中断恢复** — 保存快照、断点续传
- **可观测性** — OpenTelemetry 集成

---

## 安装

```bash
pip install harness-sdk
```

需要 Python 3.10+。

---

## 快速开始

```python
from harness import AgentHarness
from harness.tools import ReadTool, WriteTool

# 创建 Agent
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), WriteTool()],
)

# 运行
import asyncio
result = asyncio.run(agent.run("读取 README.md 并总结"))
print(result.content)
```

---

## 使用 OpenAI

```python
from harness import AgentHarness
from harness.tools import ReadTool

agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    tools=[ReadTool()],
)

result = asyncio.run(agent.run("分析当前目录结构"))
```

---

## 使用第三方 API

```python
agent = AgentHarness(
    model="deepseek-chat",
    provider="openai",
    base_url="https://api.deepseek.com/v1",
    api_key="your-api-key",
    tools=[ReadTool()],
)
```

---

## 自定义工具

```python
from harness import Tool, ToolResult

class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "搜索网络信息"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }

    async def execute(self, args: dict, ctx) -> ToolResult:
        query = args["query"]
        # 实现搜索逻辑
        return ToolResult(content=f"搜索结果: {query}")

# 使用
agent = AgentHarness(model="claude-sonnet-4-6", tools=[SearchTool()])
```

---

## MCP 集成

```python
from harness import AgentHarness, MCPServerConfig

# 连接 MCP 服务器
agent = AgentHarness(
    model="claude-sonnet-4-6",
    mcp_servers=[
        MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="mcp-server-filesystem",
            args=["--root", "/workspace"],
        )
    ],
)

# MCP 工具自动可用
result = asyncio.run(agent.run("列出 /workspace 目录内容"))
```

---

## 项目结构

| 包 | 说明 |
|---|------|
| [packages/sdk/](packages/sdk/) | harness-sdk — 核心 Python SDK |
| [packages/client/](packages/client/) | harness-client — Windows 桌面客户端 |
| [packages/cloud/](packages/cloud/) | harness-cloud — Docker 沙箱云服务 |
| [packages/scraper/](packages/scraper/) | harness-scraper — 智能文档爬取工具 |

---

## 开发

```bash
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness

# 安装依赖
uv sync --all-packages

# 运行测试
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/ -v

# 代码检查
uv run ruff check packages/sdk/src/
uv run ruff format packages/sdk/src/
```

---

## 文档

- [SDK 详细文档](packages/sdk/docs/)
- [编程规范](packages/sdk/docs/programmer_skill.md)
- [经验教训](lessons.md)

---

## 许可证

MIT License
