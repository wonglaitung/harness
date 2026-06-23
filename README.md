# Harness

**可内嵌的 AI Agent SDK — Python & Java**

```
Agent = Model + Harness
```

让 LLM 从"回答问题"变成能自主操作的智能体。

---

## 特性

- **多语言支持** — Python SDK 和 Java SDK，API 设计一致
- **多 LLM 支持** — Anthropic Claude、OpenAI 及兼容 API
- **工具系统** — 内置文件操作、Web 搜索，支持自定义工具
- **MCP 协议** — 连接外部 MCP 工具服务器扩展能力
- **技能注入** — 根据上下文自动注入专业技能
- **记忆系统** — 跨会话持久化记忆，支持去重和内容提炼
- **安全沙箱** — 命令验证、注入检测、审计日志
- **成本控制** — Token 预算管理、熔断机制
- **中断恢复** — 保存快照、断点续传
- **可观测性** — OpenTelemetry 集成

---

## Python SDK

### 安装

```bash
pip install harness-sdk
```

需要 Python 3.10+。

### 快速开始

```python
from harness import AgentHarness
from harness.tools import ReadTool, WriteTool

agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), WriteTool()],
)

import asyncio
result = asyncio.run(agent.run("读取 README.md 并总结"))
print(result.content)
```

### 使用 OpenAI

```python
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    tools=[ReadTool()],
)

result = asyncio.run(agent.run("分析当前目录结构"))
```

### 自定义工具

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
        return ToolResult(content=f"搜索结果: {args['query']}")

agent = AgentHarness(model="claude-sonnet-4-6", tools=[SearchTool()])
```

### MCP 集成

```python
from harness import AgentHarness, MCPServerConfig

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
```

### 记忆系统

Agent 可以跨会话保持记忆，自动提炼用户偏好：

```python
from harness.tools.builtins import UpdateCoreMemoryTool

agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[UpdateCoreMemoryTool()],  # 允许 Agent 自主更新记忆
)

# 用户说"我使用 Windows"，Agent 会提炼为"操作系统：Windows"存入 MEMORY.md
result = asyncio.run(agent.run("我使用 Windows，偏好深色主题"))
```

记忆特性：
- **内容提炼**：自动将用户原话提炼为简洁陈述
- **去重检测**：相似内容自动跳过，避免重复记忆
- **分类存储**：按 User Profile、Key Decisions、Learned Patterns、Project Context 分类

---

## Java SDK

专为银行环境设计：以 JAR 包形式交付，支持离线部署。

### 安装

```xml
<!-- Maven -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-all</artifactId>
    <version>1.0.0</version>
</dependency>
```

或直接使用 Shadow JAR：

```bash
# 下载 harness-sdk-all.jar 并放入项目
```

需要 Java 17+。

### 快速开始

```java
import com.harness.*;
import com.harness.tools.*;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .tools(List.of(new ReadTool(), new GlobTool()))
    .maxIterations(10)
    .build();

Harness agent = new Harness(config);
LoopResult result = agent.run("分析当前项目的代码结构");

if (result.isCompleted()) {
    System.out.println(result.content());
}
```

### 使用 OpenAI 兼容 API

```java
HarnessConfig config = HarnessConfig.builder()
    .provider("openai")
    .model("gpt-4o")
    .apiKey(System.getenv("OPENAI_API_KEY"))
    .baseUrl("https://api.your-company.com/v1")  // 可选：自定义端点
    .tools(List.of(new ReadTool()))
    .build();

Harness agent = new Harness(config);
LoopResult result = agent.run("读取配置文件");
```

### 自定义工具

```java
import com.harness.tools.*;
import java.util.concurrent.CompletableFuture;

public class SearchTool implements Tool {
    
    @Override
    public String name() {
        return "search";
    }
    
    @Override
    public String description() {
        return "搜索网络信息";
    }
    
    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "query", Map.of("type", "string", "description", "搜索关键词")
            ),
            "required", List.of("query")
        );
    }
    
    @Override
    public CompletableFuture<ToolResult> execute(
        Map<String, Object> args, 
        ToolContext context
    ) {
        String query = (String) args.get("query");
        return CompletableFuture.completedFuture(
            new ToolResult("搜索结果: " + query, true)
        );
    }
}
```

### MCP 集成

```java
import com.harness.mcp.*;

McpConfig mcpConfig = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build();

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .mcpServers(Map.of("filesystem", mcpConfig))
    .build();

Harness agent = new Harness(config);
LoopResult result = agent.run("列出 /workspace 目录内容");
```

### 记忆系统

```java
import com.harness.tools.UpdateCoreMemoryTool;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .tools(List.of(new UpdateCoreMemoryTool()))  // 允许 Agent 自主更新记忆
    .build();

Harness agent = new Harness(config);
// 用户说"我使用 Windows"，Agent 会提炼为"操作系统：Windows"存入 MEMORY.md
LoopResult result = agent.run("我使用 Windows，偏好深色主题");
```

### Java SDK 特性

| 特性 | 说明 |
|---|---|
| JAR 包交付 | 单一 JAR 包含所有依赖，可直接复制到银行环境 |
| 离线部署 | 无需网络访问，支持银行合规要求 |
| 记忆系统 | 跨会话持久化，支持去重和内容提炼 |
| 审计日志 | 内置审计系统，支持 SIEM 集成 |
| 安全沙箱 | 工具默认沙箱模式，显式开启危险权限 |
| Shadow JAR | 使用 Gradle Shadow 插件打包，解决依赖冲突 |

---

## 项目结构

| 包 | 说明 |
|---|------|
| [packages/sdk/](packages/sdk/) | harness-sdk — Python SDK |
| [packages/sdk-java/](packages/sdk-java/) | harness-sdk-java — Java SDK |
| [packages/client/](packages/client/) | harness-client — Windows 桌面客户端 |
| [packages/cloud/](packages/cloud/) | harness-cloud — Docker 沙箱云服务 |
| [packages/scraper/](packages/scraper/) | harness-scraper — 智能文档爬取工具 |

---

## 开发

```bash
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness

# Python SDK 开发
uv sync --all-packages
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/ -v

# Java SDK 构建
cd packages/sdk-java
./gradlew build
./gradlew :harness-sdk-all:shadowJar
```

---

## 文档

- [Python SDK 详细文档](packages/sdk/docs/)
- [Java SDK 详细文档](packages/sdk-java/docs/)
- [编程规范](packages/sdk/docs/programmer_skill.md)
- [经验教训](lessons.md)

---

## 许可证

MIT License