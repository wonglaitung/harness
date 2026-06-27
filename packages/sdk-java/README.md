# Harness SDK Java

可内嵌的 AI Agent Harness 框架 - Java 实现

## 项目状态

✅ **Phase 4 完成** - 完整功能同步（Python SDK → Java SDK）

✅ **AgentLoop 完整集成** - 所有健壮性组件已集成到核心执行引擎

## 模块结构

```
harness-sdk-java/
├── harness-sdk-core/      # 核心模块（类型定义、AgentLoop、AgentHarness）
│   ├── guardrails/        # PII 检测和内容安全
│   ├── service/           # Spring Cloud 集成（服务发现、Redis 会话、错误处理）
│   └── testing/           # 测试工具（录制/回放）
├── harness-sdk-llm/       # LLM 客户端（Anthropic、OpenAI、Routing）
├── harness-sdk-mcp/       # MCP 协议集成（STDIO、SSE）
├── harness-sdk-tools/     # 内置工具（Read, Write, Edit, Bash, Glob, Grep）
├── harness-sdk-memory/    # 记忆系统（MEMORY.md 管理、向量存储）
├── harness-sdk-skills/    # 技能系统（Skill 加载、渐进式加载）
├── harness-sdk-security/  # 安全模块（沙箱、验证、审计）
└── harness-sdk-all/       # 聚合模块（Shadow JAR）
```

## 核心组件

### harness-sdk-core
- **类型定义**: Message, Session, ToolCall, ToolResult, LLMResponse, LoopResult
- **AgentHarness**: 统一 SDK 入口，整合所有组件
  - `run()`: 执行 Agent
  - `stream()`: 流式执行
  - `registerTool()`: 注册工具
  - `addHook()`: 添加生命周期钩子
  - `loadSkillsFromDir()`: 加载技能
- **HarnessConfig**: 统一配置管理，包含子配置：
  - `SecurityConfig`: 安全配置
  - `CostControlConfig`: 成本控制配置
  - `ObservabilityConfig`: 可观测性配置
  - `StorageConfig`: 存储配置
  - `OffloadConfig`: 输出卸载配置
  - `RoutingConfig`: LLM 路由配置
- **ToolRegistry**: 工具注册表，支持启用/禁用、分类管理
- **AgentLoop**: ReAct 执行引擎，支持：
  - LLM 重试：配置化重试次数 + 指数退避 + 随机抖动
  - 工具超时：`timeoutPerTool` 强制超时保护
  - 智能错误处理：`ErrorHandler` 根据错误类型智能决策
  - 熔断器：`CircuitBreaker` 检测相同工具+参数重复调用，自动注入停止消息
  - 步骤预算：`StepBudgetController` 限制迭代和工具调用次数
  - 成本控制：`CostController` 多级预算管理（Session/User/Global）
  - 停滞检测：`StuckDetector` 空结果/错误/语义相似度检测，自动注入反馈
  - 输出卸载：`OutputOffloader` 大工具输出自动卸载到临时文件
  - 进度事件：完整的 `ProgressEvent` 发射和格式化
  - 快照/恢复：`LoopSnapshot` 支持中断恢复
  - 输入验证：集成 `InputValidator`
  - 审计日志：集成 `AuditLogger`
  - 中断支持：可中断正在执行的循环
  - 剩余步骤提示：接近迭代上限时自动注入提示
- **生命周期钩子**:
  - `HookPoint`: 钩子触发点（LLM 调用前后、工具执行前后等）
  - `HookAction`: 钩子动作（CONTINUE、ABORT、RETRY、INJECT_MESSAGE 等）
  - `HookContext`: 钩子上下文
  - `HookResult`: 钩子返回结果
- **SelfVerificationHook**: 代码修改后自动运行测试，失败则注入错误消息
- **Guardrails 模块**: PII 检测和内容安全
  - `GuardrailConfig`: 配置（含 StreamInterceptConfig、JudgeConfig）
  - `GuardrailHook`: 生命周期钩子
  - `PIIDetector`: PII 检测器
  - `PIIEntity`: PII 实体
  - `ComplianceJudge`: Layer 2 LLM 合规裁判
  - `StreamInterceptor`: Token 级流式拦截器
  - `GuardrailExceptions`: 自定义异常（ContentRiskException, JudgeTimeoutException 等）
- **流式处理**:
  - `StreamingHandler`: 流式输出处理，支持背压控制
  - `Chunk`/`ChunkType`: 流式块类型定义
- **进度事件**: `ProgressEvent`, `ProgressEventType` 跟踪 Agent 执行进度
- **成本控制**: `CostConfig`, `BudgetStatus`, `UserBudgetStatus`, `GlobalBudgetStatus`
- **MetricsCollector**: Prometheus 指标收集器，支持迭代、工具调用、Token 使用追踪
- **TracingManager**: OpenTelemetry 追踪管理器，支持 W3C TraceContext 传播
- **TracingFilter**: HTTP 过滤器，支持 Spring Cloud Gateway 集成
- **RalphLoopHook**: 长任务循环续接，防止上下文焦虑导致的提前退出
- **LifecycleHook**: 生命周期钩子接口
- **OutputOffloader**: 大输出卸载到临时文件，保护上下文窗口
- **PermissionSet**: 细粒度权限控制（路径、命令、网络）
- **MockHarness**: 完整测试 Harness，支持预定义响应
- **SubAgentManager**: 子代理管理器，支持并行子任务执行
- **Tool 接口**: 工具抽象类，支持验证和异步执行
- **TokenCounter**: 基于 jtokkit 的 Token 计数
  - `count(String)`: 计算单个文本的 token 数量
  - `countAll(List<String>)`: 计算多个文本的总 token 数量
  - `countMessages(List<Message>)`: 计算消息列表的 token 数量
  - `clearCache()`: 清除缓存
- **LoopConfig**: 循环配置，支持 Builder 模式
- **ModelPresets**: 预定义模型配置（Claude, GPT, GLM, Qwen, DeepSeek 等）
- **ProgressFormatter**: 进度事件格式化（simple, detailed, colored, emoji）
- **LoopSnapshot**: 循环状态快照，支持中断/恢复
- **CostStorage**: 多级预算追踪接口（InMemoryCostStorage, SQLiteCostStorage）
- **ContextBudget**: Token 预算分配，支持优先级分配和压缩检测
- **SessionManager**: 会话管理，支持文件持久化

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
- **RecordingHarness**: 录制/回放测试工具
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
import com.harness.core.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;

// 方式 1：使用默认配置
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .apiKey("your-api-key")
    .build();

LoopResult result = agent.run("Hello, Claude!").join();
System.out.println(result.content());

// 方式 2：使用完整配置
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .maxIterations(10)
    .toolTimeout(30.0)
    .security(HarnessConfig.SecurityConfig.builder()
        .enableSandbox(true)
        .build())
    .build();

AgentHarness agent = new AgentHarness(config);

// 方式 3：从环境变量创建
AgentHarness agent = AgentHarness.fromEnv();
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
| `harness-sdk-core` | 核心模块（类型定义、AgentLoop、AgentHarness、Guardrails） |
| `harness-sdk-llm` | LLM 客户端（Anthropic、OpenAI、Routing） |
| `harness-sdk-mcp` | MCP 协议集成（STDIO、SSE） |
| `harness-sdk-tools` | 内置工具（Read, Write, Edit, Bash, Glob, Grep） |
| `harness-sdk-memory` | 记忆系统（MEMORY.md 管理、向量存储） |
| `harness-sdk-skills` | 技能系统（Skill 加载、渐进式加载） |
| `harness-sdk-security` | 安全模块（沙箱、验证、审计） |
| `harness-sdk-guardrails` | PII 检测和内容安全 |
| `harness-sdk-integration` | 集成测试 |

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

### Maven 依赖

```xml
<!-- 核心模块（必需） -->
<dependency>
    <groupId>com.harness</groupId>
    <artifactId>harness-sdk-core</artifactId>
    <version>1.0.0</version>
</dependency>

<!-- LLM 客户端（必需，二选一） -->
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
```

### Gradle 依赖

```groovy
// 核心模块（必需）
implementation 'com.harness:harness-sdk-core:1.0.0'

// LLM 客户端（必需）
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
import com.harness.core.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;
import com.harness.tools.ReadTool;
import com.harness.tools.GlobTool;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        // 方式 1：Builder 模式（推荐）
        AgentHarness agent = AgentHarness.builder()
            .model("claude-sonnet-4-6")
            .apiKey(System.getenv("ANTHROPIC_API_KEY"))
            .tools(List.of(new ReadTool(), new GlobTool()))
            .build();

        LoopResult result = agent.run("分析当前目录下的 Java 文件").join();
        System.out.println(result.content());

        // 方式 2：使用完整配置
        HarnessConfig config = HarnessConfig.builder()
            .model("claude-sonnet-4-6")
            .maxIterations(10)
            .toolTimeout(30.0)
            .systemPrompt("你是一个有帮助的 AI 助手")
            .build();

        AgentHarness agent2 = new AgentHarness(config);

        // 方式 3：从环境变量自动配置
        AgentHarness agent3 = AgentHarness.fromEnv();

        // 方式 4：使用第三方 OpenAI 兼容接口
        AgentHarness agent4 = AgentHarness.builder()
            .provider("openai")
            .baseUrl("https://api.your-provider.com/v1")
            .apiKey("your-api-key")
            .model("your-model-name")
            .build();
    }
}
```

### 流式执行

```java
import com.harness.core.Chunk;
import com.harness.core.ChunkType;

agent.stream("请解释什么是 ReAct 模式")
    .thenAccept(chunk -> {
        if (chunk.type() == ChunkType.TEXT) {
            System.out.print(chunk.content());
        } else if (chunk.type() == ChunkType.TOOL_CALL_START) {
            System.out.println("\n[调用工具: " + chunk.toolName() + "]");
        }
    })
    .join();
```

### 添加自定义工具

```java
import com.harness.tools.Tool;
import com.harness.types.ToolResult;

public class MyTool extends Tool {
    @Override
    public String name() {
        return "my_tool";
    }

    @Override
    public String description() {
        return "我的自定义工具";
    }

    @Override
    public Object inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "input", Map.of("type", "string", "description", "输入参数")
            ),
            "required", List.of("input")
        );
    }

    @Override
    public ToolResult execute(Map<String, Object> args, ToolContext ctx) {
        String input = (String) args.get("input");
        return ToolResult.success("处理结果: " + input);
    }
}

// 使用
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .tools(List.of(new MyTool()))
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