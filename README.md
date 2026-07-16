# Harness

**可内嵌的 AI Agent SDK — Python & Java**

```
Agent = Model + Harness
```

让 LLM 从"回答问题"变成能自主操作的智能体。

---

## 特性

- **多语言支持** — Python SDK 和 Java SDK，99.5% API 一致
- **多 LLM 支持** — Anthropic Claude、OpenAI 及兼容 API
- **工具系统** — 内置文件操作、Web 搜索、浏览器自动化，支持自定义工具
- **MCP 协议** — 连接外部 MCP 工具服务器扩展能力
- **技能注入** — 根据上下文自动注入专业技能
- **记忆系统** — 跨会话持久化记忆，支持去重和内容提炼
- **Loop Engineering** — 目标驱动执行，Agent 自主运行直到目标达成
- **触发器系统** — Cron/Interval 定时触发，自动化任务调度
- **工作流编排** — 多步骤工作流，依赖解析，并行执行
- **外部集成** — GitHub、Slack、Webhook 连接器
- **安全沙箱** — 命令验证、注入检测、审计日志
- **成本控制** — Token 预算管理、熔断机制
- **中断恢复** — 保存快照、断点续传
- **可观测性** — OpenTelemetry 集成
- **知识图谱** — 内置 code-review-graph 支持，提供代码结构分析和智能代码审查

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

### 排程与自动化

支持 Cron 表达式和固定间隔的定时任务：

```python
from harness import AgentHarness
from harness.triggers import CronTrigger, IntervalTrigger, TriggerManager, TriggerAction
from harness.loop import Automation

agent = AgentHarness(model="claude-sonnet-4-6")

# 方式 1：使用 Automation 简化 API
daily_report = Automation(
    name="daily-report",
    schedule="0 9 * * *",  # 每天 9:00
    goal="生成每日报告并发送到 Slack",
)

health_check = Automation(
    name="health-check",
    interval_seconds=300,  # 每 5 分钟
    goal="检查系统健康状态",
)

# 启动
import asyncio
async def run_automations():
    await daily_report.start(agent)
    await health_check.start(agent)

    # 保持运行
    await asyncio.sleep(3600)

    # 停止
    await daily_report.stop()
    await health_check.stop()

asyncio.run(run_automations())

# 方式 2：使用 TriggerManager 精细控制
manager = TriggerManager(agent)

cron_trigger = CronTrigger(
    schedule="0 9 * * 1-5",  # 工作日 9:00
    action=TriggerAction(goal="生成工作日报"),
)

interval_trigger = IntervalTrigger(
    interval_seconds=600,  # 每 10 分钟
    action=TriggerAction(goal="检查服务状态"),
)

manager.register(cron_trigger)
manager.register(interval_trigger)

await manager.start()
# ... 运行中 ...
await manager.stop()
```

**Cron 表达式格式**：
```
┌──────── 分钟 (0-59)
│ ┌────── 小时 (0-23)
│ │ ┌──── 日 (1-31)
│ │ │ ┌── 月 (1-12)
│ │ │ │ ┌ 星期 (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

常用模式：
| 表达式 | 说明 |
|--------|------|
| `*/5 * * * *` | 每 5 分钟 |
| `0 * * * *` | 每小时整点 |
| `0 9 * * *` | 每天 9:00 |
| `0 9 * * 1-5` | 工作日 9:00 |
| `0 0 1 * *` | 每月 1 日 |

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

```groovy
// Gradle
implementation 'com.harness:harness-sdk-all:1.0.0'
```

或直接使用 Shadow JAR：

```bash
# 下载 harness-sdk-all.jar 并放入项目
```

需要 Java 17+。

### 快速开始

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;
import com.harness.tools.ReadTool;
import com.harness.tools.GlobTool;

import java.util.List;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .maxIterations(10)
    .build();

AgentHarness agent = AgentHarness.builder()
    .config(config)
    .addTool(new ReadTool())
    .addTool(new GlobTool())
    .build();

LoopResult result = agent.run("分析当前项目的代码结构").join();

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
    .build();

AgentHarness agent = AgentHarness.builder()
    .config(config)
    .addTool(new ReadTool())
    .build();

LoopResult result = agent.run("读取配置文件").join();
```

### 自定义工具

```java
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

import java.util.List;
import java.util.Map;
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
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("query")) {
            return ValidationResult.invalid("query is required");
        }
        return ValidationResult.valid();
    }
    
    @Override
    public CompletableFuture<ToolResult> execute(
        Map<String, Object> args, 
        ToolContext context
    ) {
        String query = (String) args.get("query");
        ToolResult result = ToolResult.builder()
            .toolCallId(context.toolCallId())
            .content("搜索结果: " + query)
            .toolName(name())
            .build();
        return CompletableFuture.completedFuture(result);
    }
}

// 使用
AgentHarness agent = AgentHarness.builder()
    .config(HarnessConfig.builder()
        .provider("openai")
        .apiKey(System.getenv("OPENAI_API_KEY"))
        .model("gpt-4o")
        .build())
    .addTool(new SearchTool())
    .build();
```

### MCP 集成

```java
import com.harness.mcp.*;

McpManager mcpManager = new McpManager();
mcpManager.addServer("filesystem", McpServerConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build());

AgentHarness agent = AgentHarness.builder()
    .config(HarnessConfig.builder()
        .model("claude-sonnet-4-6")
        .apiKey(System.getenv("ANTHROPIC_API_KEY"))
        .build())
    .mcpManager(mcpManager)
    .build();

LoopResult result = agent.run("列出 /workspace 目录内容").join();
```

### 记忆系统

```java
import com.harness.tools.UpdateCoreMemoryTool;

AgentHarness agent = AgentHarness.builder()
    .config(HarnessConfig.builder()
        .model("claude-sonnet-4-6")
        .apiKey(System.getenv("ANTHROPIC_API_KEY"))
        .build())
    .addTool(new UpdateCoreMemoryTool())  // 允许 Agent 自主更新记忆
    .build();

// 用户说"我使用 Windows"，Agent 会提炼为"操作系统：Windows"存入 MEMORY.md
LoopResult result = agent.run("我使用 Windows，偏好深色主题").join();
```

### 排程与自动化

```java
import com.harness.triggers.*;
import com.harness.loop.Automation;
import com.harness.loop.AutomationStatus;

// 方式 1：使用 Automation 简化 API
Automation dailyReport = new Automation(
    "daily-report",
    "0 9 * * *",  // 每天 9:00
    "生成每日报告并发送到 Slack"
);

Automation healthCheck = new Automation(
    "health-check",
    300,  // 每 300 秒（5 分钟）
    "检查系统健康状态"
);

// 启动
dailyReport.start(agent).join();
healthCheck.start(agent).join();

// 查看状态
System.out.println(dailyReport.status());  // RUNNING

// 停止
dailyReport.stop().join();
healthCheck.stop().join();

// 方式 2：使用 TriggerManager 精细控制
TriggerManager manager = new TriggerManager(agent);

CronTrigger cronTrigger = new CronTrigger(
    "workday-report",
    "0 9 * * 1-5",  // 工作日 9:00
    new TriggerAction.Builder()
        .goal("生成工作日报")
        .maxIterations(50)
        .build()
);

IntervalTrigger intervalTrigger = new IntervalTrigger(
    "service-check",
    600,  // 每 600 秒（10 分钟）
    new TriggerAction.Builder()
        .goal("检查服务状态")
        .build()
);

manager.register(cronTrigger);
manager.register(intervalTrigger);

// 启动所有触发器
manager.start().join();

// 查看触发器状态
for (Map<String, Object> info : manager.listTriggers()) {
    System.out.println(info.get("id") + ": " + info.get("state"));
}

// 停止所有触发器
manager.stop().join();
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
| Loop Engineering | 目标驱动执行、并行 Worktree、工作流编排 |
| 触发器系统 | Cron/Interval 触发、自动化任务调度 |

---

## 项目结构

| 包 | 说明 |
|---|------|
| [packages/sdk/](packages/sdk/) | harness-sdk — Python SDK |
| [packages/sdk-java/](packages/sdk-java/) | harness-sdk-java — Java SDK (99.5% 功能同步) |
| [packages/client/](packages/client/) | harness-client — Windows 桌面客户端 |
| [packages/cloud/](packages/cloud/) | harness-cloud — Docker 沙箱云服务 |
| [packages/scraper/](packages/scraper/) | harness-scraper — 智能文档爬取工具 |

### 代码库统计（Graph 分析）

| 指标 | 数值 |
|------|------|
| 总节点数 | 8,407 |
| 总边数 | 47,566 |
| 文件数 | 588 |
| 测试节点 | 1,263 |
| 类 | 1,089 |
| 函数 | 5,428 |

**主要社区**：
- `core-config` (1,582 节点) — SDK 核心配置
- `core-builder` (1,414 节点) — 构建器模式
- `ui-theme` (650 节点) — PyQt6 客户端 UI
- `memory-memory` (327 节点) — 记忆系统
- `mcp-tool` (120 节点) — MCP 集成

**关键执行流**：
- `session_websocket` — WebSocket 会话管理
- `run` / `stream` / `run_goal` — Agent 执行入口

---

## 开发

```bash
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness

# Python SDK 开发
uv sync --all-packages
PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/ -v

# Java SDK 构建（使用 snap gradle）
cd packages/sdk-java
snap run gradle build
snap run gradle :harness-sdk-all:shadowJar

# 发布到 Maven Local
snap run gradle publishToMavenLocal
```

---

## 文档

- [Python SDK 详细文档](packages/sdk/docs/)
- [Java SDK 详细文档](packages/sdk-java/docs/)
- [客户端用户指南](packages/client/README.md)
- [编程规范](packages/sdk/docs/programmer_skill.md)
- [经验教训](lessons.md)

---

## 知识图谱工具

本项目集成了 **code-review-graph** MCP 服务器，提供：

- **结构化代码搜索** — 基于图谱的语义搜索，比 Grep 更高效
- **影响分析** — 理解代码变更的影响范围
- **架构洞察** — 自动检测代码社区和关键节点
- **智能审查** — 风险评分和优先级建议

详见 [CLAUDE.md](CLAUDE.md) 中的 "MCP Tools: code-review-graph" 章节。

---

## 许可证

MIT License