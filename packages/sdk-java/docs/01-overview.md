# 01 - 项目概述与架构总览

## 项目背景

### 问题陈述

银行环境主要使用 Java 作为开发语言，而现有的 AI Agent SDK 多为 Python 实现。银行客户需要：

- 在自己的 Java 应用中嵌入 AI Agent 能力
- 以 JAR 包形式交付，方便项目整合
- 符合银行安全合规要求（离线部署、审计日志等）
- 与现有 Java 技术栈无缝集成

### 解决方案

构建 **Harness SDK Java 版本**：

- 以 JAR 包形式交付，可直接复制到银行环境
- 基于 Java 17，使用现代 Java 特性
- 完整实现 Python SDK 的核心功能
- 支持离线部署，无需网络访问

## ✅ 架构决策：直接翻译 Python SDK

### 核心原则

- **核心逻辑直接翻译 Python SDK**
- **底层组件使用成熟库**（openai-java, mcp-java-sdk, jtokkit）
- **保持 API 完全一致**
- **模块结构对应 Python**

**不使用**：AgentScope Java、LangChain4j、Google ADK 等 Agent Framework

### 同步策略

Python SDK 更新时，Java 版本同步跟进：

| Python SDK | Java SDK | 同步方式 |
|------------|----------|---------|
| `harness/sdk/harness.py` | `Harness.java` | 直接翻译 |
| `harness/core/agent_loop.py` | `AgentLoop.java` | 直接翻译 |
| `harness/tools/*.py` | `tools/*.java` | 直接翻译 |
| `harness/mcp/*.py` | `mcp/*.java` | 直接翻译 |

## 架构总览

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER JAVA APPLICATION                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   HARNESS SDK (JAR)                         │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                    Agent Loop                         │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │ Input   │→ │ Context │→ │   LLM   │→ │ Output  │  │  │ │
│  │  │  │ Handler │  │ Builder │  │  Call   │  │ Parser  │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  │       ↓            ↓            ↓            ↓       │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │Trigger  │  │ Memory  │  │  Tool   │  │ Action  │  │  │ │
│  │  │  │ Manager │  │ System  │  │ System  │  │ Handler │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                   Skills System                       │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │ │
│  │  │  │  Skill  │  │  Skill  │  │  Skill  │               │  │ │
│  │  │  │ Loader  │  │Registry │  │Injector │               │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                 Infrastructure                        │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │ Config  │  │Logging &│  │  Error  │  │ Metrics │  │  │ │
│  │  │  │ Manager │  │ Tracing │  │ Handler │  │& Stats  │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│         ↓                              ↓                         │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │  LLM PROVIDERS  │          │  MCP SERVERS    │               │
│  │  ┌───────────┐  │          │  ┌───────────┐  │               │
│  │  │ Anthropic │  │          │  │ Filesystem│  │               │
│  │  │   OpenAI  │  │          │  │  GitHub   │  │               │
│  │  │   Bedrock │  │          │  │  Custom   │  │               │
│  │  └───────────┘  │          │  └───────────┘  │               │
│  └─────────────────┘          └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件关系

```
                    ┌─────────────────┐
                    │   Trigger       │
                    │   Manager       │
                    └────────┬────────┘
                             │ 触发执行
                             ↓
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Context │←→→ │   LLM   │←→→ │  Tool   │         │
│  │ Builder │    │  Client │    │Executor │         │
│  └────┬────┘    └────┬────┘    └────┬────┘         │
│       │              │              │               │
│       ↓              ↓              ↓               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Memory  │    │ Skills  │    │ Actions │         │
│  │ System  │    │ System  │    │/Outputs │         │
│  └─────────┘    └─────────┘    └─────────┘         │
└─────────────────────────────────────────────────────┘
```

## Java 版本技术选型

### 语言与运行时

| 项目 | 选择 | 说明 |
|------|------|------|
| Java 版本 | Java 17 | 银行标准版本，支持 Record、Pattern Matching |
| 构建工具 | Gradle 8.x (Kotlin DSL) | 灵活的依赖管理和构建脚本 |
| 测试框架 | JUnit 5 + Mockito | Java 标准测试框架 |

### 核心依赖

| 类别 | Python 依赖 | Java 依赖 | 说明 |
|------|------------|-----------|------|
| LLM API (Claude) | `anthropic` | `anthropic-java` | Anthropic 官方 SDK，支持自定义 base URL |
| LLM API (OpenAI 兼容) | `openai` | `openai-java` | OpenAI 官方 SDK，支持自定义 base URL |
| MCP | `mcp` | `mcp-java-sdk` | MCP 官方 Java SDK |
| Token 计数 | `tiktoken` | `jtokkit` | OpenAI 兼容 |
| JSON | `pydantic` | `Jackson` | Java 标准 JSON 库 |
| HTTP | `aiohttp` | (SDK 内置) | OkHttp 内置于 anthropic-java 和 openai-java |
| 异步 | `asyncio` | `CompletableFuture` | Java 17 原生支持 |

**重要说明**:
- 银行环境可使用 Anthropic Claude API 或第三方 OpenAI 格式 API
- 两个官方 SDK 都支持 `baseUrl` 配置，可连接银行内部 API Gateway

### 模块结构

```
harness-sdk-java/
├── build.gradle.kts              # 根项目配置
├── settings.gradle.kts           # 模块定义
├── harness-sdk-core/             # 核心模块
│   ├── src/main/java/com/harness/
│   │   ├── Harness.java          # 主入口
│   │   ├── HarnessConfig.java    # 配置类
│   │   ├── core/
│   │   │   ├── AgentLoop.java    # ReAct 循环
│   │   │   ├── LoopConfig.java
│   │   │   └── hooks/            # 生命周期钩子
│   │   ├── types/
│   │   │   ├── Message.java      # 消息类型
│   │   │   ├── Session.java      # 会话类型
│   │   │   └── LoopResult.java   # 结果类型
│   │   └── security/             # 安全组件
│   └── src/test/java/
├── harness-sdk-llm/              # LLM 客户端
│   └── src/main/java/com/harness/llm/
│       ├── LLMClientAdapter.java  # openai-java 适配器
│       └── StreamingHandler.java  # 流式处理
├── harness-sdk-mcp/              # MCP 集成
│   └── src/main/java/com/harness/mcp/
│       ├── McpClient.java
│       └── McpToolAdapter.java
├── harness-sdk-tools/            # 内置工具
│   └── src/main/java/com/harness/tools/
│       ├── Tool.java
│       ├── ReadTool.java
│       ├── WriteTool.java
│       └── BashTool.java
├── harness-sdk-memory/           # 记忆系统
│   └── src/main/java/com/harness/memory/
│       ├── ContextBuilder.java
│       └── TokenCounter.java
├── harness-sdk-skills/           # 技能系统
│   └── src/main/java/com/harness/skills/
│       └── SkillRegistry.java
└── harness-sdk-all/              # 聚合模块（Shadow JAR）
    └── build.gradle.kts          # Shadow 插件配置
```

## Python vs Java 实现对比

### 异步模型对比

| Python (asyncio) | Java (CompletableFuture) |
|------------------|--------------------------|
| `async def run()` | `CompletableFuture<LoopResult> runAsync()` |
| `await llm.call()` | `llm.callAsync().join()` |
| `async for chunk in stream` | `stream().subscribe(...)` |
| `async with context:` | `try (var ctx = context) { }` |

### 数据模型对比

```python
# Python - Pydantic
@dataclass
class Message:
    role: str
    content: str
    metadata: dict = field(default_factory=dict)
```

```java
// Java - Record
public record Message(
    String role,
    String content,
    Map<String, Object> metadata
) {
    public Message(String role, String content) {
        this(role, content, Map.of());
    }
}
```

### API 设计对比

```python
# Python SDK
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), BashTool(sandbox=True)]
)
result = await agent.run("分析代码")
```

```java
// Java SDK
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .tools(List.of(new ReadTool(), new BashTool(true)))
    .build();

Harness agent = new Harness(config);
LoopResult result = agent.run("分析代码");
```

## 设计原则

### 1. JAR 包优先

- 所有依赖打包为单一 JAR
- 支持离线部署
- 提供 SHA256 校验和

### 2. Java 最佳实践

- 使用 Builder 模式构建复杂对象
- 使用 Record 定义不可变数据
- 使用 Optional 避免 null
- 使用 CompletableFuture 处理异步

### 3. 安全默认

- 工具默认沙箱模式
- 显式开启危险权限
- 内置审计日志

### 4. 银行合规

- 支持离线环境
- 提供 OWASP 依赖扫描报告
- 提供 SBOM (Software Bill of Materials)
- 审计日志支持 SIEM 集成

## 下一步

- [02-java-ecosystem.md](./02-java-ecosystem.md) - 详细了解 Java 生态系统依赖
- [03-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop 的 Java 实现
- [07-sdk-api.md](./07-sdk-api.md) - 查看 SDK API 设计
