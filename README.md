# Harness

可内嵌的 Python AI Agent SDK + Windows 桌面客户端。

```
Agent = Model + Harness
```

让 LLM 从"回答问题"变成能自主操作的智能体。

## 项目结构

这是一个 **Monorepo** 项目，包含两个包：

| 包 | 说明 |
|---|------|
| [packages/sdk/](packages/sdk/) | **harness-sdk** - 可内嵌的 Python AI Agent SDK（跨平台） |
| [packages/client/](packages/client/) | **harness-client** - Windows 桌面客户端（PyQt6） |

## 快速开始

### 安装

```bash
# 需要 Python 3.10+
git clone https://github.com/wonglaitung/harness.git
cd harness

# 安装所有包
uv sync --all-packages
```

### SDK 使用

```python
from harness import AgentHarness, ReadTool

# 创建 Agent
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool()],
)

# 运行（异步）
import asyncio
result = asyncio.run(agent.run("读取 pyproject.toml 文件"))
print(result.content)
```

### 运行客户端

```powershell
cd packages\client
uv run python -m harness_client
```

## SDK 功能

- **多 LLM 支持** - Anthropic、OpenAI 及兼容 API
- **工具系统** - 内置文件操作、Web 搜索等工具，支持自定义
- **技能注入** - 根据用户输入自动注入专业技能
- **MCP 协议** - 连接外部 MCP 工具服务器
- **Guardrails** - PII 检测和内容安全（简/繁/英文）
- **安全沙箱** - 命令验证、注入检测、审计日志
- **成本控制** - Token 预算管理、熔断机制
- **中断恢复** - 保存快照、断点续传
- **可观测性** - OpenTelemetry 集成

## 客户端功能

- 对话界面（支持流式输出）
- 三栏布局（可折叠侧边栏 + 右侧面板）
- MCP 服务器管理
- 技能系统（支持 `/` 自动补全）
- 多会话管理
- 多模型支持
- 统一配置目录（`~/.harness/`）

## 开发

```bash
# 运行测试
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/ -v

# 代码检查
uv run ruff check packages/sdk/src/
uv run ruff format packages/sdk/src/
```

## 文档

- [SDK 详细文档](packages/sdk/docs/)
- [客户端使用指南](packages/client/README.md)
- [编程规范](packages/sdk/docs/programmer_skill.md)

## 许可证

MIT License
