# Harness SDK Java 版本设计文档

> 可内嵌的 AI Agent Harness 框架 - Java 实现

## 目录

- [01-overview.md](./01-overview.md) - 项目概述与架构总览
- [02-java-ecosystem.md](./02-java-ecosystem.md) - Java 生态系统依赖分析
- [03-agent-loop.md](./03-agent-loop.md) - Agent Loop 代理循环引擎 (Java 实现)
- [04-tool-system.md](./04-tool-system.md) - Tool System 工具系统
- [05-memory-system.md](./05-memory-system.md) - Memory System 记忆系统
- [06-mcp-integration.md](./06-mcp-integration.md) - MCP 协议集成
- [07-sdk-api.md](./07-sdk-api.md) - SDK API 设计
- [08-security.md](./08-security.md) - 安全设计
- [09-implementation.md](./09-implementation.md) - 实施路线图
- [10-comparison.md](./10-comparison.md) - 与 Python SDK 对比
- [11-testing.md](./11-testing.md) - 测试策略
- [12-deployment.md](./12-deployment.md) - JAR 包部署指南
- [13-production-readiness.md](./13-production-readiness.md) - 生产就绪检查
- [14-bank-integration.md](./14-bank-integration.md) - 银行系统集成指南
- [15-spring-cloud-integration.md](./15-spring-cloud-integration.md) - Spring Cloud 集成指南
- [16-skills-system.md](./16-skills-system.md) - Skills System 技能系统
- [17-trigger-system.md](./17-trigger-system.md) - Trigger System 触发器系统
- [18-loop-engineering.md](./18-loop-engineering.md) - Loop Engineering 循环工程
- [19-worktrees.md](./19-worktrees.md) - Worktrees 并行隔离执行
- [20-connectors.md](./20-connectors.md) - Connectors 外部系统集成
- [21-orchestrator.md](./21-orchestrator.md) - Orchestrator 工作流编排
- [22-examples.md](./22-examples.md) - 示例代码
- [programmer_skill.md](./programmer_skill.md) - 编程规范

## 项目定位

将 Python 版本的 harness-sdk 改写为 Java 版本，为银行客户提供：

- **可内嵌到 Java 系统**的 AI Agent SDK
- **JAR 包形式交付**，方便项目整合
- **Java 17+ 兼容**，适配银行标准技术栈

### 核心理念

```
Agent = Model + Harness
```

- **Model**: 大语言模型（Claude/GPT/本地模型），提供推理能力
- **Harness**: 围绕模型的框架层，提供记忆、工具、触发器、技能

### 与 Python 版本的对应关系

| Python SDK | Java SDK | 说明 |
|------------|----------|------|
| `anthropic` | `anthropic-java` | Anthropic 官方 SDK |
| `openai` | `openai-java` | OpenAI 官方 SDK，支持第三方 API |
| `asyncio` | `CompletableFuture` / `Reactor` | 异步模型差异 |
| `pydantic` | `Jackson` / `Java Record` | 数据模型 |
| `tiktoken` | `jtokkit` | Token 计数 |
| `mcp` Python | `mcp-java-sdk` | MCP 官方 Java SDK |

## 快速预览

### 最简使用示例

```java
// 创建 Harness 实例
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .tools(List.of(
        new ReadTool(),
        new BashTool(true)  // sandbox mode
    ))
    .memoryDir(Path.of("~/.harness/memory"))
    .build();

Harness agent = new Harness(config);

// 同步调用
LoopResult result = agent.run("分析当前目录的代码结构");
System.out.println(result.getContent());

// 流式调用
agent.stream("帮我重构这个函数")
    .subscribe(chunk -> System.out.print(chunk),
               error -> error.printStackTrace(),
               () -> System.out.println("\nDone"));
```

### 内嵌到现有系统

```java
// 集成到 Spring Boot
@RestController
public class AgentController {
    
    private final Harness agent;
    
    public AgentController() {
        this.agent = Harness.fromConfig("harness.yaml");
    }
    
    @PostMapping("/chat")
    public ResponseEntity<ChatResponse> chat(
            @RequestBody ChatRequest request,
            @RequestParam String sessionId) {
        
        LoopResult result = agent.run(request.getMessage(), sessionId);
        return ResponseEntity.ok(new ChatResponse(result.getContent()));
    }
}
```

### JAR 包引入方式

```kotlin
// Gradle - 使用本地 JAR
implementation(files("libs/harness-sdk-all-1.0.0.jar"))

// 或使用文件目录
implementation(fileTree("libs") { include("*.jar") })
```

```xml
<!-- Maven -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk</artifactId>
    <version>1.0.0</version>
    <scope>system</scope>
    <systemPath>${project.basedir}/libs/harness-sdk-all-1.0.0.jar</systemPath>
</dependency>
```

## 设计原则

1. **JAR 包交付**: 构建为独立 JAR 包，可直接复制到银行环境
2. **Java 17 兼容**: 使用 Record、Pattern Matching 等现代 Java 特性
3. **安全默认**: 默认沙箱模式，显式开启危险权限
4. **可观测性**: 内置日志、追踪、指标（支持银行审计要求）
5. **离线友好**: 所有依赖打包，无需网络访问

## 功能特性

### 核心功能

- **Agent Loop**: ReAct 循环、Circuit Breaker、Stuck Detection、Step Budget
- **工具系统**: ReadTool, WriteTool, EditTool, BashTool, GrepTool, GlobTool
- **记忆系统**: MemoryFileManager, Memory Scoring, Archive, ContextBuilder
- **技能系统**: SkillRegistry, SkillLoader, SkillInjector
- **MCP 协议**: McpManager, StdioTransport, HTTPTransport
- **安全系统**: InputValidator, ResultSanitizer, SandboxExecutor, AuditLogger
- **Guardrails**: PIIDetector, ChinesePIIRecognizers

### 新增功能 (v1.0.0)

| 功能 | 说明 |
|------|------|
| ModelPresets | 根据模型名称自动检测 provider、context_window |
| toolResultRole | 兼容不支持 "tool" role 的代理 API |
| Memory Scoring | 基于 Bjork's Theory 的检索强度计算 |
| Memory Archive | 自动归档低重要性记忆 |
| Tracing 集成 | OpenTelemetry tracing 集成到 AgentLoop |
| Error Handler | 完整错误处理策略 (RETRY/COMPRESS_CONTEXT/ABORT) |

### 测试覆盖

- **27 个功能演示示例**: `examples/SdkFeatureDemo.java`
- **7 个单元测试文件**: ModelPreset, MemoryEntry, MemoryScoringConfig 等
- **覆盖率目标**: 80%+

## 技术选型

| 类别 | 选择 | 说明 |
|------|------|------|
| 构建工具 | Gradle (Kotlin DSL) | 灵活的依赖管理 |
| Java 版本 | Java 17 | 银行标准版本 |
| 异步模型 | CompletableFuture | 简单可靠，无需响应式框架 |
| JSON 处理 | Jackson | Java 标准 JSON 库 |
| HTTP 客户端 | OkHttp | 高性能，成熟稳定 |
| Token 计数 | jtokkit | OpenAI 兼容，支持 cl100k_base |

## 依赖清单

```
harness-sdk-all-1.0.0.jar 包含:
├── anthropic-java-2.40.1         # Anthropic 官方 SDK（Claude API）
├── openai-java-4.39.1            # OpenAI 官方 SDK（第三方兼容 API）
├── mcp-java-sdk-0.5.0            # MCP 官方 Java SDK
├── jtokkit-1.0.0                 # Token 计数
├── jackson-databind-2.17.0       # JSON 处理
└── slf4j-api-2.0.0               # 日志接口
```

**银行第三方 API 配置**:

```java
// 使用 Anthropic Claude API（银行内部 API Gateway）
AnthropicClient client = AnthropicOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/anthropic")  // 银行 API Gateway
    .apiKey(getApiKeyFromVault())                     // 从密钥管理系统获取
    .build();

// 或使用 OpenAI 兼容 API（银行内部 API Gateway）
OpenAIClient client = OpenAIOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/v1")  // 银行 API Gateway
    .apiKey(getApiKeyFromVault())              // 从密钥管理系统获取
    .build();
```

## 模块结构

```
harness-sdk-java/
├── harness-sdk-core/           # 核心模块（必须）
├── harness-sdk-llm/            # LLM 客户端（openai-java 适配）
├── harness-sdk-mcp/            # MCP 集成
├── harness-sdk-tools/          # 内置工具
├── harness-sdk-memory/         # 记忆系统
├── harness-sdk-skills/         # 技能系统
└── harness-sdk-all/            # 聚合模块（包含所有依赖）
```

## 与 Python 版本的同步策略

### 核心原则

- **核心逻辑直接翻译 Python SDK**
- **底层组件使用成熟库**（openai-java, mcp-java-sdk, jtokkit）
- **保持 API 完全一致**
- **模块结构对应 Python**

**不使用**：AgentScope Java、LangChain4j、Google ADK 等 Agent Framework

### 目录结构映射

```
Python SDK                              Java SDK
packages/sdk/src/harness/               packages/sdk-java/src/main/java/com/harness/
├── sdk/harness.py                      ├── sdk/Harness.java
├── core/agent_loop.py                  ├── core/AgentLoop.java
├── tools/                              ├── tools/
├── mcp/                                ├── mcp/
├── memory/                             ├── memory/
├── skills/                             ├── skills/
└── security/                           └── security/
```

### 同步工作流

1. **识别变更**: `git diff --name-only packages/sdk/src/harness/`
2. **映射到 Java**: `.py` 文件对应 `.java` 文件
3. **翻译更新**: 保持 API 名称一致，翻译 Python 代码
4. **测试验证**: 运行对应测试确保行为一致

Python 版本作为主导版本，Java 版本跟进：

1. **功能同步**: Python 版本新功能稳定后，迁移到 Java
2. **API 一致**: 保持 API 设计理念一致，但适配 Java 最佳实践
3. **独立发布**: Java 版本有独立的版本号和发布周期