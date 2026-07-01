# Harness SDK Java

可内嵌的 AI Agent Harness 框架 - Java 实现

## 项目状态

✅ **99.5% 功能同步** - Python SDK → Java SDK

**已完成模块**：
- ✅ Core（AgentLoop, HarnessConfig, Tool 接口, Guardrails）
- ✅ LLM（Anthropic, OpenAI, Routing, Mock）
- ✅ MCP（STDIO, SSE 传输）
- ✅ Tools（Read, Write, Edit, Bash, Glob, Grep）
- ✅ Memory（MEMORY.md 管理, 向量存储）
- ✅ Skills（Skill 加载, 渐进式加载）
- ✅ Security（沙箱, 验证, 审计）
- ✅ Triggers（CronTrigger, IntervalTrigger, TriggerManager）
- ✅ Connectors（GitHub, Slack, Webhook）
- ✅ Loop Engineering（GoalLoop, ParallelGoalExecutor, Automation）
- ✅ Orchestrator（WorkflowEngine, TeamOrchestrator, DependencyGraph）

**未实现（设计差异）**：
- Python `pytest_plugin`（Python 测试框架特有）
- Python `AsyncSQLiteSessionStore`（Java 使用同步 JDBC）

## 模块结构

```
harness-sdk-java/
├── harness-sdk-core/          # 核心模块（类型定义、Tool 接口、Guardrails）
│   ├── core/                  # HarnessConfig, AgentLoop, 生命周期钩子
│   ├── guardrails/            # PII 检测和内容安全
│   ├── recording/             # 录制工具（RecordingHarness 简单版）
│   ├── service/               # Spring Cloud 集成（服务发现、Redis 会话、错误处理）
│   ├── testing/               # 测试工具（MockHarness）
│   └── types/                 # 类型定义（LoopResult, ToolResult 等）
├── harness-sdk-llm/           # LLM 客户端（Anthropic、OpenAI、Routing）
├── harness-sdk-mcp/           # MCP 协议集成（STDIO、SSE）
├── harness-sdk-tools/         # 内置工具（Read, Write, Edit, Bash, Glob, Grep）
├── harness-sdk-memory/        # 记忆系统（MEMORY.md 管理、向量存储）
├── harness-sdk-skills/        # 技能系统（Skill 加载、渐进式加载）
├── harness-sdk-security/      # 安全模块（沙箱、验证、审计）
├── harness-sdk-guardrails/    # PII 检测和内容安全（独立模块）
├── harness-sdk-triggers/      # 触发器系统（CronTrigger, IntervalTrigger, TriggerManager）
├── harness-sdk-connectors/    # 外部系统集成（GitHub, Slack, Webhook）
├── harness-sdk-loop/          # Loop Engineering（GoalLoop, ParallelGoalExecutor, Automation）
├── harness-sdk-orchestrator/  # 工作流编排（WorkflowEngine, TeamOrchestrator）
├── harness-sdk-integration/   # AgentHarness 入口类 + 测试工具（RecordingHarness 回放版）
├── harness-sdk-all/           # 聚合模块（单 JAR 包含所有依赖）
└── examples/                  # 示例代码
```

## 核心组件

### harness-sdk-core
- **类型定义**: Message, Session, ToolCall, ToolResult, LLMResponse, LoopResult, Chunk, ChunkType
- **HarnessConfig**: 统一配置管理，支持 Builder 模式
  - `provider()`: LLM 提供商（"anthropic", "openai", "auto"）
  - `baseUrl()`: 自定义 API 地址
  - `model()`: 模型名称
  - `maxIterations()`: 最大迭代次数
  - `toolTimeout()`: 工具超时时间
  - 子配置：SecurityConfig, CostControlConfig, ObservabilityConfig, StorageConfig, OffloadConfig, RoutingConfig
- **Tool 接口**: 工具抽象接口
  - `name()`: 工具名称
  - `description()`: 工具描述
  - `inputSchema()`: 参数 Schema
  - `execute()`: 异步执行
  - `validate()`: 参数验证
- **ToolRegistry**: 工具注册表，支持启用/禁用、分类管理
- **AgentLoop**: ReAct 执行引擎（位于 harness-sdk-integration）
- **生命周期钩子**: HookPoint, HookAction, HookContext, HookResult
- **Guardrails 模块**: PII 检测和内容安全
- **进度事件**: ProgressEvent, ProgressEventType
- **TokenCounter**: 基于 jtokkit 的 Token 计数
- **MockHarness**: 测试 Harness，支持预定义响应

### harness-sdk-integration
- **AgentHarness**: 统一 SDK 入口
  - `run(prompt)`: 执行 Agent
  - `run(prompt, sessionId)`: 指定会话 ID
  - `run(prompt, sessionId, onProgress)`: 带进度回调
  - `continueSession(sessionId, prompt)`: 继续会话
  - `runGoal(goal)`: 目标驱动执行
  - `runGoal(goal, sessionId)`: 带会话 ID 的目标驱动执行
  - `runGoal(goal, sessionId, onProgress, customVerifier)`: 完整参数的目标驱动执行
  - `runGoal(goalConfig, onProgress)`: 使用 GoalConfig 的目标驱动执行
  - `registerTool(tool)`: 注册工具
  - `addHook(hook)`: 添加生命周期钩子
- **Builder 模式**: `AgentHarness.builder().config(config).addTool(tool).build()`

### harness-sdk-llm
- **AnthropicClient**: Claude API 客户端，支持自定义 baseUrl
- **OpenAIClient**: OpenAI/兼容 API 客户端
- **MockLLMClient**: 测试用 Mock 客户端，支持预定义响应
- **RoutingLLMClient**: 智能路由客户端，基于请求复杂度选择模型（高/低成本模型）
- **LlamaCppClient**: 嵌入式 GGUF 模型客户端（用于路由决策，需 llama.cpp JNI）

### harness-sdk-mcp
- **McpManager**: MCP 服务器管理器，支持多服务器连接
- **McpServerConfig**: 服务器配置（STDIO/SSE 传输）
- **McpToolWrapper**: MCP 工具包装器，适配 Harness Tool 接口
- **McpToolInfo**: MCP 工具元数据

### harness-sdk-tools
- **ReadTool**: 文件读取，支持行号、图片
- **WriteTool**: 文件写入
- **EditTool**: 文本替换
- **BashTool**: Shell 命令执行
- **GlobTool**: 文件模式匹配
- **GrepTool**: 内容搜索
- **UpdateCoreMemoryTool**: Agent 自主更新 Core Memory，支持内容提炼和去重

### harness-sdk-memory
- **MemoryFileManager**: MEMORY.md 文件管理，支持字符级去重检测
- **MemoryCategory**: 记忆类别枚举，支持 `getValue()` / `fromValue()` 方法
- **MemoryEntry**: 记忆条目
- **SessionManager**: 会话持久化
- **ContextCompressor**: 上下文压缩器，支持消息摘要和保留最近消息
- **CompressionConfig**: 压缩配置
- **CompressionResult**: 压缩结果
- **SystemPromptBuilder**: 动态系统提示组装，支持 AGENTS.md/MEMORY.md
- **SystemPromptConfig**: 系统提示配置
- **SystemPromptSource**: 系统提示源
- **VectorMemoryStore**: 语义搜索记忆存储，支持 Retrieval Strength 加权

### harness-sdk-skills
- **SkillRegistry**: 技能文件加载和管理
- **Skill**: 技能定义
- **SkillMetadata**: 技能元数据（描述、版本、工具、触发器）
- **SkillLoader**: 技能文件加载器，支持多路径搜索和自动发现
- **SkillInjector**: 技能注入器，将匹配的技能注入系统提示
- **InjectionConfig**: 注入配置
- **ProgressiveSkillLoader**: 渐进式技能加载器，三级加载（Frontmatter/Full/References）节省上下文

### harness-sdk-core/service
- **ServiceDiscovery**: 服务发现，支持 Nacos/Eureka/静态配置
- **RedisSessionStore**: Redis 分布式会话存储，支持 TTL 和分布式锁
- **RedisDistributedLock**: 分布式锁，支持 AutoCloseable
- **ServiceErrorHandler**: 统一错误处理，标准化 REST API 错误响应

### harness-sdk-core/testing
- **MockHarness**: 测试 Harness，支持预定义响应

### harness-sdk-core/recording
- **RecordingHarness**: 简单录制工具（录制 LLM 交互）
- **RecordingConfig**: 录制配置
- **RecordedInteraction**: 单条交互记录

### harness-sdk-integration/testing
- **RecordingHarness**: 完整录制/回放工具（支持从 JSON 文件回放）
- **RecordingConfig**: 录制配置

### harness-sdk-security
- **InputValidator**: 输入验证，检测注入模式
- **PromptInjectionDetector**: Prompt 注入检测
- **FileInputValidator**: 文件路径验证
- **SandboxExecutor**: 沙箱执行器
- **LightweightSandbox**: 轻量级沙箱
- **AuditLogger**: 审计日志
- **ResultSanitizer**: 输出脱敏

## 快速开始

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.llm.OpenAIClient;
import com.harness.types.LoopResult;
import com.harness.tools.ReadTool;
import com.harness.tools.GlobTool;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        // 方式 1：使用 HarnessConfig 创建（推荐）
        HarnessConfig config = HarnessConfig.builder()
            .provider("openai")
            .baseUrl("https://api.openai.com/v1")
            .apiKey("your-api-key")
            .model("gpt-4o")
            .maxIterations(10)
            .build();

        AgentHarness agent = AgentHarness.builder()
            .config(config)
            .tools(List.of(new ReadTool(), new GlobTool()))
            .build();

        LoopResult result = agent.run("分析当前目录").join();
        System.out.println(result.content());

        // 方式 2：直接传入 LLMClient
        OpenAIClient llmClient = new OpenAIClient(
            "your-api-key",
            "https://api.openai.com/v1",
            "gpt-4o"
        );

        AgentHarness agent2 = AgentHarness.builder()
            .llmClient(llmClient)
            .addTool(new ReadTool())
            .build();

        // 方式 3：从环境变量自动配置
        HarnessConfig configFromEnv = HarnessConfig.fromEnv();
        AgentHarness agent3 = AgentHarness.builder()
            .config(configFromEnv)
            .build();
    }
}
```

## 构建

### 使用 Snap Gradle（推荐）

```bash
# 构建所有模块
snap run gradle build

# 跳过测试构建
snap run gradle build -x test

# 只构建核心模块
snap run gradle :harness-sdk-core:build

# 查看所有可用模块
snap run gradle projects
```

### 可用模块

| 模块 | 说明 |
|------|------|
| `harness-sdk-core` | 核心模块（类型定义、HarnessConfig、Tool 接口、Guardrails） |
| `harness-sdk-llm` | LLM 客户端（Anthropic、OpenAI、Routing） |
| `harness-sdk-mcp` | MCP 协议集成（STDIO、SSE） |
| `harness-sdk-tools` | 内置工具（Read, Write, Edit, Bash, Glob, Grep） |
| `harness-sdk-memory` | 记忆系统（MEMORY.md 管理、向量存储） |
| `harness-sdk-skills` | 技能系统（Skill 加载、渐进式加载） |
| `harness-sdk-security` | 安全模块（沙箱、验证、审计） |
| `harness-sdk-guardrails` | PII 检测和内容安全 |
| `harness-sdk-triggers` | 触发器系统（CronTrigger, IntervalTrigger, TriggerManager） |
| `harness-sdk-connectors` | 外部系统集成（GitHub, Slack, Webhook） |
| `harness-sdk-loop` | Loop Engineering（GoalLoop, ParallelGoalExecutor, Automation, Worktree） |
| `harness-sdk-orchestrator` | 工作流编排（WorkflowEngine, TeamOrchestrator, DependencyGraph） |
| `harness-sdk-integration` | AgentHarness 入口类 + 完整测试工具 |
| `harness-sdk-all` | **聚合模块**（单 JAR 包含所有依赖，推荐使用） |

### 发布到 Maven Local

```bash
# 发布所有模块到本地 Maven 仓库
snap run gradle publishToMavenLocal

# 发布后可在 ~/.m2/repository/com/harness/ 找到
```

### 构建 JAR 包

每个模块构建后会生成 JAR 包：

```bash
# 构建所有模块的 JAR
snap run gradle build

# JAR 输出位置
# harness-sdk-core/build/libs/harness-sdk-core-*.jar
# harness-sdk-llm/build/libs/harness-sdk-llm-*.jar
# ...
```

## 使用 SDK-Java

### 快速开始（推荐：使用聚合模块）

```xml
<!-- Maven：单依赖包含所有模块 -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-all</artifactId>
    <version>1.0.0</version>
</dependency>
```

```groovy
// Gradle：单依赖包含所有模块
implementation 'com.harness:harness-sdk-all:1.0.0'
```

### Maven 依赖

```xml
<!-- 核心模块（必需） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-core</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- LLM 客户端（必需，包含 Anthropic、OpenAI、Mock、Routing） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-llm</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 内置工具（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-tools</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- MCP 协议支持（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-mcp</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 记忆系统（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-memory</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 技能系统（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-skills</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 安全模块（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-security</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- PII 检测和内容安全（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-guardrails</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 触发器系统（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-triggers</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 外部系统集成（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-connectors</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- Loop Engineering（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-loop</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 工作流编排（可选） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-orchestrator</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- 聚合模块（推荐：单依赖包含所有模块） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-all</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Gradle 依赖

```groovy
// 核心模块（必需）
implementation 'com.harness:harness-sdk-core:1.0.0'

// LLM 客户端（必需，包含 Anthropic、OpenAI、Mock、Routing）
implementation 'com.harness:harness-sdk-llm:1.0.0'

// 内置工具（可选）
implementation 'com.harness:harness-sdk-tools:1.0.0'

// MCP 协议支持（可选）
implementation 'com.harness:harness-sdk-mcp:1.0.0'

// 记忆系统（可选）
implementation 'com.harness:harness-sdk-memory:1.0.0'

// 技能系统（可选）
implementation 'com.harness:harness-sdk-skills:1.0.0'

// 安全模块（可选）
implementation 'com.harness:harness-sdk-security:1.0.0'

// PII 检测和内容安全（可选）
implementation 'com.harness:harness-sdk-guardrails:1.0.0'

// 触发器系统（可选）
implementation 'com.harness:harness-sdk-triggers:1.0.0'

// 外部系统集成（可选）
implementation 'com.harness:harness-sdk-connectors:1.0.0'

// Loop Engineering（可选）
implementation 'com.harness:harness-sdk-loop:1.0.0'

// 工作流编排（可选）
implementation 'com.harness:harness-sdk-orchestrator:1.0.0'

// 聚合模块（推荐：单依赖包含所有模块）
implementation 'com.harness:harness-sdk-all:1.0.0'
```

### 环境变量配置

```bash
# Anthropic Claude
export ANTHROPIC_API_KEY=your-api-key

# OpenAI / 兼容接口
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，默认 OpenAI
```

### 基本用法

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;
import com.harness.tools.ReadTool;
import com.harness.tools.GlobTool;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        // 方式 1：使用 HarnessConfig（推荐）
        HarnessConfig config = HarnessConfig.builder()
            .provider("openai")
            .baseUrl("https://api.openai.com/v1")
            .apiKey("your-api-key")
            .model("gpt-4o")
            .maxIterations(10)
            .toolTimeout(30.0)
            .systemPrompt("你是一个有帮助的 AI 助手")
            .build();

        AgentHarness agent = AgentHarness.builder()
            .config(config)
            .tools(List.of(new ReadTool(), new GlobTool()))
            .build();

        LoopResult result = agent.run("分析当前目录下的 Java 文件").join();
        System.out.println(result.content());

        // 方式 2：使用第三方 OpenAI 兼容接口
        HarnessConfig customConfig = HarnessConfig.builder()
            .provider("openai")
            .baseUrl("https://api.your-provider.com/v1")
            .apiKey("your-api-key")
            .model("your-model-name")
            .build();

        AgentHarness agent2 = AgentHarness.builder()
            .config(customConfig)
            .build();

        // 方式 3：从环境变量自动配置
        // 需要设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY
        HarnessConfig configFromEnv = HarnessConfig.fromEnv();
        AgentHarness agent3 = AgentHarness.builder()
            .config(configFromEnv)
            .build();
    }
}
```

### 进度回调

AgentHarness 支持通过进度回调监控执行过程：

```java
import com.harness.types.ProgressEvent;

agent.run("分析项目结构", null, progress -> {
    if (progress instanceof ProgressEvent event) {
        System.out.println("[" + event.type() + "] " + event.message());
    }
}).join();
```

### 添加自定义工具

```java
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.core.ToolCategory;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class MyTool implements Tool {

    @Override
    public String name() {
        return "my_tool";
    }

    @Override
    public String description() {
        return "我的自定义工具";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "input", Map.of("type", "string", "description", "输入参数")
            ),
            "required", List.of("input")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.GENERAL;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("input")) {
            return ValidationResult.invalid("input is required");
        }
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String input = (String) args.get("input");
        String toolCallId = context != null ? context.toolCallId() : "";

        // 使用 Builder 创建结果
        ToolResult result = ToolResult.builder()
            .toolCallId(toolCallId)
            .content("处理结果: " + input)
            .toolName(name())
            .build();

        return CompletableFuture.completedFuture(result);
    }
}

// 使用
AgentHarness agent = AgentHarness.builder()
    .config(HarnessConfig.builder()
        .provider("openai")
        .apiKey("your-api-key")
        .model("gpt-4o")
        .build())
    .addTool(new MyTool())
    .build();
```

### 更多示例

完整示例代码见：
- `examples/SimpleTest.java` - 基础用法
- `harness-sdk-integration/src/test/java/com/harness/integration/SdkFeatureDemoRealApi.java` - 27 个功能演示

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| anthropic-java | 2.40.1 | Anthropic Claude API |
| openai-java | 4.39.1 | OpenAI 兼容 API |
| mcp-java-sdk | 0.5.0 | MCP 协议 |
| jtokkit | 1.0.0 | Token 计数 |
| jackson | 2.17.0 | JSON 处理 |
| slf4j | 2.0.0 | 日志接口 |

## 文档

详细设计文档请见 [docs/](docs/) 目录。