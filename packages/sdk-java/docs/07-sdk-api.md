# 07 - SDK API 参考

## 概述

本文档提供 Harness SDK 的完整 API 参考。SDK 以 `harness` 包名发布，所有公共 API 通过 `harness/__init__.py` 导出。

> **注意**：本文档基于 Python SDK API。Java SDK 有对应的实现，详见各章节的 Java 示例代码。

## Java SDK 特有 API

### AgentHarness.fromEnv()

从环境变量创建 AgentHarness 实例。

```java
import com.harness.integration.AgentHarness;

// 方式 1：使用 HarnessConfig.fromEnv()
HarnessConfig config = HarnessConfig.fromEnv();
AgentHarness agent = AgentHarness.builder()
    .config(config)
    .build();

// 方式 2：使用静态方法（推荐）
AgentHarness agent = AgentHarness.fromEnv();

// 方式 3：带工具
AgentHarness agent = AgentHarness.fromEnv(List.of(new ReadTool()));
```

**支持的环境变量**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `HARNESS_MODEL` | 模型名称 | `claude-sonnet-4-6` |
| `HARNESS_PROVIDER` | 提供商 | `auto` |
| `HARNESS_BASE_URL` | 自定义 API 端点 | - |
| `HARNESS_MAX_ITERATIONS` | 最大迭代次数 | `10` |
| `HARNESS_SYSTEM_PROMPT` | 系统提示词 | - |
| `HARNESS_MEMORY_DIR` | 记忆目录 | `.harness/memory` |
| `HARNESS_SANDBOX_WORKSPACE` | 沙箱工作区 | 当前目录 |

### ToolVerificationConfig

工具验证配置，用于目标驱动执行中的客观验证。

```java
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.ToolVerificationConfig;

// Python 项目验证
ToolVerificationConfig config = ToolVerificationConfig.builder()
    .addCommand("pytest", "pytest", "tests/", "-v")
    .addCommand("mypy", "mypy", "src/")
    .addCommand("ruff", "ruff", "check", "src/")
    .build();

// 预设配置
ToolVerificationConfig.pythonDefaults();   // pytest + mypy + ruff
ToolVerificationConfig.gradleDefaults();   // gradle test + check
ToolVerificationConfig.mavenDefaults();    // mvn test
ToolVerificationConfig.npmDefaults();      // npm test + lint

// 结合 GoalConfig 使用
GoalConfig goalConfig = GoalConfig.builder()
    .description("修复所有类型错误")
    .verificationMethod(VerificationMethod.TOOL)
    .toolVerificationConfig(config)
    .build();
```

详见 [18-loop-engineering.md](./18-loop-engineering.md) 的工具验证章节。

---

## 公共 API 导出

```java
// Java SDK 公共 API 导出
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.core.Tool;
import com.harness.core.LifecycleHook;
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.Session;
import com.harness.types.ToolCall;
import com.harness.types.ToolResult;
import com.harness.types.TokenUsage;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.automation.Automation;
import com.harness.loop.automation.AutomationConfig;
import com.harness.memory.MemoryFileManager;
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import com.harness.memory.VectorMemoryStore;
import com.harness.memory.VectorMemoryConfig;
import com.harness.memory.VectorSearchResult;
import com.harness.memory.SystemPromptBuilder;
import com.harness.memory.SystemPromptConfig;
import com.harness.memory.SystemPromptSource;
import com.harness.memory.ContextConfig;
import com.harness.memory.ContextBudget;
import com.harness.memory.ContextCompressor;
import com.harness.memory.CompressionConfig;
import com.harness.memory.BuiltContext;
import com.harness.memory.SessionStore;
import com.harness.memory.FileSessionStore;
import com.harness.memory.SQLiteSessionStore;
import com.harness.skills.Skill;
import com.harness.skills.SkillLoader;
import com.harness.skills.SkillRegistry;
import com.harness.skills.SkillInjector;
import com.harness.security.InputValidator;
import com.harness.security.PromptInjectionDetector;
import com.harness.security.AuditLogger;
import com.harness.security.ResultSanitizer;
import com.harness.mcp.McpManager;
import com.harness.mcp.McpServerConfig;
import com.harness.mcp.McpToolInfo;
import com.harness.core.MockHarness;
```

## AgentHarness

AgentHarness 是 SDK 的主入口，提供完整的 Agent 运行时。

### 构造函数

```java
// AgentHarness 构造 - 使用 Builder 模式
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.core.Tool;
import com.harness.core.LLMClient;
import java.util.List;

AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")           // 模型名称
    .apiKey("sk-ant-...")                 // API 密钥（或设置环境变量）
    .config(HarnessConfig.builder()
        .provider("anthropic")             // LLM 提供商 - "anthropic", "openai", 或 "auto"
        .baseUrl(null)                     // 自定义 API 端点
        .build())
    .llmClient(null)                       // 自定义 LLM 客户端实例
    .addTool(new ReadTool())               // 可用的工具
    .build();
```

### Provider 自动检测

如果不指定 `provider`，SDK 根据 `model` 名称自动检测：

| model 前缀 | provider |
|------------|----------|
| `claude-*` | `anthropic` |
| `gpt-*`, `o1-*`, `o3-*` | `openai` |
| 其他 | `openai`（通过 `base_url` 使用兼容 API） |

### 核心方法

#### run() - 执行任务

```java
// run() - 执行任务
import com.harness.types.LoopResult;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

CompletableFuture<LoopResult> run(String prompt);
CompletableFuture<LoopResult> run(String prompt, String sessionId);
CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress);
```

#### run_sync() - 同步执行

```java
// run() 在 Java 中天然同步（通过 .join() 阻塞）
LoopResult result = agent.run("prompt").join();          // 同步执行
// 或异步
agent.run("prompt").thenAccept(result -> { ... });       // 异步回调
```

**事件循环检测**：使用语义化 API 检测运行中的事件循环：

```java
// Java 中不需要事件循环检测 - 使用 CompletableFuture 自然支持同步/异步
// 同步调用（阻塞当前线程）
LoopResult result = agent.run("prompt").join();

// 异步调用（非阻塞）
agent.run("prompt").thenAccept(result -> {
    // 处理结果
});
```

**注意**：不要依赖字符串匹配检测事件循环（如检查异常消息），这在不同 Python 版本中可能不稳定。

#### stream() - 流式执行

```java
// stream() - 流式执行（Java 中通过 run() + result 获取完整响应）
// Java SDK 的 run() 返回 CompletableFuture<LoopResult>
// 工具调用在内部处理，最终结果包含完整响应
CompletableFuture<LoopResult> future = agent.run("prompt");
LoopResult result = future.join();
System.out.println(result.content()); // 获取完整响应
```

#### run_goal() - 目标驱动执行

```java
// run_goal() - 目标驱动执行
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import java.util.function.Function;
import java.util.concurrent.CompletableFuture;

CompletableFuture<GoalResult> runGoal(String goal);
CompletableFuture<GoalResult> runGoal(String goal, String sessionId);
CompletableFuture<GoalResult> runGoal(String goal, String sessionId,
    Consumer<Object> onProgress, Function<GoalResult, Boolean> customVerifier);
CompletableFuture<GoalResult> runGoal(GoalConfig goalConfig, Consumer<Object> onProgress);

// 示例：
GoalResult result = agent.runGoal("修复所有类型错误", null).join();
if (result.status() == GoalStatus.ACHIEVED) {
    System.out.println("目标达成，共 " + result.totalIterations() + " 轮迭代");
}
```

详见 [18-loop-engineering.md](./18-loop-engineering.md)。

#### tool() - 注册工具装饰器

```java
// Java 中没有装饰器语法 - 使用实现 Tool 接口注册工具
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.types.ToolResult;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class HelloTool implements Tool {
    @Override public String getName() { return "hello"; }
    @Override public String getDescription() { return "Say hello"; }
    @Override
    public Map<String, Object> inputSchema() {
        return Map.of("type", "object", "properties",
            Map.of("name", Map.of("type", "string")));
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        String name = (String) args.getOrDefault("name", "world");
        return CompletableFuture.completedFuture(
            ToolResult.success(ctx.sessionId(), "Hello, " + name + "!", getName()));
    }
}

agent.registerTool(new HelloTool());
```

#### 钩子注册说明

钩子通过继承 `LifecycleHook` 类并使用 `add_hook()` 方法注册：

```java
// 钩子通过实现 LifecycleHook 接口并使用 addHook() 方法注册：
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import java.util.List;

public class MyHook implements LifecycleHook {
    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext ctx) {
        // 钩子逻辑
        return HookResult.continue_();
    }
}

// 注册钩子
agent.addHook(new MyHook());
```

#### add_hook() - 注册生命周期钩子

```java
// addHook() - 注册生命周期钩子
import com.harness.core.LifecycleHook;
import java.util.List;

void addHook(LifecycleHook hook);
void addHook(LifecycleHook hook, List<HookPoint> points);

// 注册钩子允许在关键执行点注入自定义逻辑：
// - LLM 调用前后
// - 工具执行前后
// - 错误发生时
// - 循环开始/结束时
```

#### remove_hook() - 移除生命周期钩子

```java
// removeHook() - 移除生命周期钩子
void removeHook(LifecycleHook hook);
```

#### create_snapshot() - 创建执行快照

```java
// createSnapshot() - 创建执行快照
import com.harness.types.LoopSnapshot;

LoopSnapshot createSnapshot(String sessionId, int iteration);

// 快照可用于保存进度并稍后恢复执行。
LoopSnapshot snapshot = agent.createSnapshot("my-session", 0);
// LoopSnapshot 可序列化保存
```

#### restore_from_snapshot() - 从快照恢复执行

```java
// restoreFromSnapshot() - 从快照恢复执行
import com.harness.types.LoopSnapshot;
import com.harness.types.LoopResult;
import java.util.concurrent.CompletableFuture;

CompletableFuture<LoopResult> restoreFromSnapshot(LoopSnapshot snapshot);

// 从保存的快照恢复
LoopResult result = agent.restoreFromSnapshot(snapshot).join();
```

#### registerTool() - 注册工具

```java
public void registerTool(Tool tool)
```

### MCP 方法

```java
// MCP 方法
import com.harness.mcp.McpServerConfig;

boolean addMcpServer(McpServerConfig config);
void registerMcpServer(McpServerConfig config);
boolean connectMcpServer(String serverName);
Map<String, Boolean> connectAllMcpServers();
void disconnectMcpServer(String serverName);
```

### 技能方法

```java
// 技能方法
import com.harness.skills.Skill;
import java.nio.file.Path;
import java.util.List;

int loadSkillsFromDir(Path directory);
boolean activateSkill(String skillName);
boolean deactivateSkill(String skillName);
List<Skill> getMatchingSkills(String userInput);
```

#### 技能自动注入

`AgentHarness.run()` 会自动将匹配的技能注入到 system prompt：

```java
// 技能自动匹配和注入
// 如果用户输入匹配某个技能的 triggers，该技能内容会被注入到 system prompt
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;

AgentHarness agent = AgentHarness.builder().build();

LoopResult result = agent.run("将 README.md 转换为 Word 文档").join();

// 手动激活技能（即使不匹配 triggers 也会注入）
agent.activateSkill("code-review");
result = agent.run("检查这段代码").join();
```

#### 完整示例

```java
// 完整示例
import com.harness.integration.AgentHarness;
import com.harness.skills.Skill;
import com.harness.types.LoopResult;
import java.nio.file.Path;
import java.util.List;

AgentHarness agent = AgentHarness.builder().build();

// 加载自定义技能目录
agent.loadSkillsFromDir(Path.of(".harness/skills"));

// 查看匹配的技能
List<Skill> matching = agent.getMatchingSkills("review this code");
System.out.println("匹配的技能: " + matching);

// 手动激活技能
agent.activateSkill("security-audit");

// 运行（技能会自动注入）
LoopResult result = agent.run("检查安全问题").join();

// 停用技能
agent.deactivateSkill("security-audit");
```

### 配置方法

```java
// 配置方法
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;

// 从环境变量创建
AgentHarness agent = AgentHarness.fromEnv();
// 或
HarnessConfig config = HarnessConfig.fromEnv();
AgentHarness agent2 = AgentHarness.builder().config(config).build();
```

## HarnessConfig

```java
import com.harness.core.HarnessConfig;

// Java HarnessConfig uses Builder pattern:
HarnessConfig config = HarnessConfig.builder()
    // LLM 配置
    .model("claude-sonnet-4-6")
    .apiKey("sk-ant-...")
    .provider("auto")            // "auto", "anthropic", "openai"
    .baseUrl(null)               // 自定义 API 端点
    .contextWindow(200000)       // 模型上下文窗口大小（默认 200000）
    .maxTokens(4096)             // 最大输出 token（默认 4096）
    .temperature(1.0)            // 生成温度

    // Agent Loop 配置
    .maxIterations(10)           // 最大迭代次数
    .toolTimeout(30.0)           // 工具超时（秒）

    // 兼容性配置
    .toolResultRole("tool")      // "tool" (原生) 或 "user" (兼容模式)

    // 记忆配置
    .memoryDir(".harness/memory")
    .memoryMdPath(null)          // 全局 MEMORY.md 文件路径
    .sessionWindow(100)          // 会话滑动窗口大小

    // 工具配置
    .sandboxWorkspace(null)      // 沙箱工作区
    .enableNetwork(false)        // 是否启用网络

    // 系统提示
    .systemPrompt("")            // 基础系统提示

    // 文档大小检查
    .maxDocumentSize(10 * 1024 * 1024)          // 10MB
    .maxTotalDocumentsSize(20 * 1024 * 1024)    // 20MB
    .documentSizeAction(HarnessConfig.DocumentSizeAction.WARN)
    .documentTokenWarningRatio(0.5)

    // 子配置
    .security(HarnessConfig.SecurityConfig.builder().build())
    .costControl(HarnessConfig.CostControlConfig.builder().build())
    .observability(HarnessConfig.ObservabilityConfig.builder().build())
    .storage(HarnessConfig.StorageConfig.builder().build())
    .routing(HarnessConfig.RoutingConfig.builder().build())
    .build();
```

### 默认值

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | String | `claude-sonnet-4-6` | 模型名称 |
| `provider` | String | `auto` | 提供商 |
| `apiKey` | String | `null` | API 密钥 |
| `baseUrl` | String | `null` | 自定义 API 端点 |
| `contextWindow` | int | `200000` | 模型上下文窗口大小 |
| `maxTokens` | int | `4096` | 最大输出 token |
| `temperature` | double | `1.0` | 生成温度 |
| `maxIterations` | int | `10` | 最大迭代次数 |
| `toolTimeout` | double | `30.0` | 工具超时（秒） |
| `toolResultRole` | String | `tool` | 工具结果角色 |
| `memoryDir` | String | `.harness/memory` | 记忆目录 |
| `sessionWindow` | int | `100` | 会话滑动窗口大小 |
| `enableNetwork` | boolean | `false` | 是否启用网络 |
| `systemPrompt` | String | `""` | 基础系统提示 |

### step_budget 步骤预算控制

使用 `StepBudgetConfig` 限制单次任务的迭代次数和工具调用次数，防止模型过度探索。

```java
// 使用 StepBudgetConfig 限制单次任务的迭代次数和工具调用次数
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .maxIterations(3)
    // step_budget 在 Java SDK 中通过 HarnessConfig 配置
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `max_iterations_per_task` | int | 50 | 任务最大迭代次数 |
| `max_tool_calls_per_step` | int | 10 | 单次 LLM 响应最大工具调用数 |
| `max_tool_calls_per_task` | int | 200 | 任务最大工具调用总数 |
| `warning_threshold` | float | 0.8 | 触发警告的阈值比例 |
| `critical_threshold` | float | 0.95 | 触发严重警告的阈值比例 |
| `action_on_exceed` | str | "stop" | 超限时的动作："stop", "warn", "throttle" |

#### 推荐值

| 任务类型 | max_iterations | max_tool_calls_per_step | max_tool_calls_per_task |
|---------|----------------|------------------------|------------------------|
| 简单任务（读文件、回答问题） | 2-3 | 2-3 | 5 |
| 中等任务（代码分析、多步推理） | 5-7 | 5 | 10-15 |
| 复杂任务（代码生成、研究） | 10-15 | 10 | 50-100 |

### tool_result_role 兼容模式

Anthropic API 要求工具结果以特定格式发送：`role: "user"` + `tool_result` blocks。SDK 内部使用 `role: "tool"` 作为抽象，在发送到 API 前自动转换。

某些代理 API（如 OpenAI 格式的 proxy）不支持 `tool_result` blocks。使用 `tool_result_role="user"` 可将工具结果转换为普通用户消息。

#### 配置示例

```java
// 原生 Anthropic API（默认）- 使用 tool_result blocks
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .toolResultRole("tool")
    .build();

// 兼容模式 - 适用于不支持 tool_result blocks 的 proxy API
HarnessConfig configCompat = HarnessConfig.builder()
    .toolResultRole("user")
    .baseUrl("https://your-proxy-api.com/v1")
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();
```

#### 消息格式对比

**原生模式 (`tool_result_role="tool"`)**：
```json
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_123",
            "content": "文件内容..."
        }
    ]
}
```

**兼容模式 (`tool_result_role="user"`)**：
```json
{
    "role": "user",
    "content": "[TOOL RESULT - read_file]\nTool call ID: toolu_123...\nStatus: SUCCESS\n\n文件内容..."
}
```

兼容模式会包含工具名称和调用 ID，帮助模型识别这是哪个工具的返回结果。

#### 注意事项

- OpenAI provider 不需要此设置（直接使用 `role: "tool"`）
- 仅 Anthropic provider 需要配置此项
- 如果代理 API 支持 `tool_result` blocks，优先使用原生模式 (`tool_result_role="tool"`)

### 模型预设

Java SDK 不包含内置模型预设。请在 `HarnessConfig.Builder` 中显式指定模型参数：

```java
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .contextWindow(200000)
    .maxTokens(4096)
    .build();
```

### max_tokens 配置

Java SDK 使用固定的默认值 `maxTokens = 4096`，不支持自动模式。可根据模型需要手动调整：

```java
HarnessConfig config = HarnessConfig.builder()
    .model("claude-opus-4-6")
    .maxTokens(8192)  // Opus 支持更大的输出
    .build();
```

### 从环境变量加载

```java
// Java SDK 支持从环境变量创建配置
HarnessConfig config = HarnessConfig.fromEnv();
AgentHarness agent = AgentHarness.builder()
    .config(config)
    .build();

// 支持的环境变量:
// ANTHROPIC_API_KEY / OPENAI_API_KEY
// HARNESS_MODEL, HARNESS_PROVIDER, HARNESS_BASE_URL
// HARNESS_MAX_ITERATIONS, HARNESS_SYSTEM_PROMPT, HARNESS_MEMORY_DIR
```

## Java SDK 配置类

Java SDK 提供与 Python SDK 功能对等的配置类，采用 Builder 模式构建。

### LoopConfig

Java SDK 的核心 Loop 配置类，对应 Python 的 `HarnessConfig`：

```java
import com.harness.core.LoopConfig;

LoopConfig config = LoopConfig.builder()
    .maxIterations(10)              // 最大迭代次数
    .timeoutPerTool(30000)          // 工具超时（毫秒）
    .enableParallelTools(true)      // 并行工具执行
    .retryOnError(3)                // LLM 错误重试次数
    .enableProgress(true)           // 进度事件
    .enableCircuitBreaker(true)     // 断路器
    .enableCostControl(true)        // 成本控制
    .workingDirectory(".")          // 工作目录
    .toolResultRole("tool")         // 工具结果角色："tool" (原生) 或 "user" (兼容)
    .contextWindow(200000)          // 上下文窗口大小
    .sessionWindow(100)             // 会话滑动窗口大小
    .enableCompression(true)        // 自动上下文压缩
    .systemPrompt("")               // 基础系统提示
    .build();
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `maxIterations` | int | 10 | 最大迭代次数（LLM 调用） |
| `timeoutPerTool` | long | 30000 | 工具超时（毫秒） |
| `enableParallelTools` | boolean | true | 并行工具执行 |
| `retryOnError` | int | 3 | LLM 错误重试次数 |
| `enableProgress` | boolean | true | 进度事件 |
| `enableCircuitBreaker` | boolean | true | 断路器（工具故障保护） |
| `enableCostControl` | boolean | true | 成本控制 |
| `workingDirectory` | String | user.dir | 工作目录 |
| `memoryMdPath` | String | null | MEMORY.md 文件路径 |
| `toolResultRole` | String | "tool" | 工具结果角色 |
| `contextWindow` | int | 200000 | 上下文窗口大小（token） |
| `sessionWindow` | int | 100 | 会话滑动窗口大小（消息数） |
| `enableCompression` | boolean | true | 自动上下文压缩 |
| `systemPrompt` | String | "" | 基础系统提示 |

#### 上下文压缩配置

`contextWindow`, `sessionWindow`, `enableCompression` 配置项用于控制上下文管理：

- **contextWindow**: 模型上下文窗口大小（默认 200000 token）
- **sessionWindow**: 会话滑动窗口大小（默认 100 条消息）
- **enableCompression**: 当上下文超过预算时自动压缩

```java
// 启用自动压缩
LoopConfig config = LoopConfig.builder()
    .contextWindow(200000)      // Claude 默认窗口
    .sessionWindow(50)          // 保守的会话窗口
    .enableCompression(true)    // 启用压缩
    .build();

// 禁用压缩（适合短任务）
LoopConfig config = LoopConfig.builder()
    .enableCompression(false)
    .maxIterations(3)
    .build();
```

详见 [05-memory-system.md](./05-memory-system.md)。

### 文档大小检查

Java SDK 支持对上传的文档进行大小检查，与 Python SDK 功能完全同步。

#### HarnessConfig 配置

```java
import com.harness.core.HarnessConfig;
import com.harness.core.HarnessConfig.DocumentSizeAction;

HarnessConfig config = HarnessConfig.builder()
    .maxDocumentSize(5 * 1024 * 1024)           // 5MB
    .maxTotalDocumentsSize(10 * 1024 * 1024)    // 10MB
    .documentSizeAction(DocumentSizeAction.ERROR)  // WARN/ERROR/TRUNCATE
    .documentTokenWarningRatio(0.5)             // 50% 上下文窗口阈值
    .build();
```

#### DocumentSizeAction 枚举

| 行为 | 说明 |
|------|------|
| `WARN` | 记录警告日志，继续处理 |
| `ERROR` | 抛出 `DocumentTooLargeException` 异常 |
| `TRUNCATE` | 截断文档到限制大小 |

#### DocumentTooLargeException

```java
import com.harness.types.DocumentTooLargeException;

try {
    LLMResponse response = client.call(messages, null, systemPrompt);
} catch (DocumentTooLargeException e) {
    System.out.println("文档过大: " + e.getFilename() +
                       " (" + e.getSize() / 1024 / 1024 + "MB)");
}
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `maxDocumentSize` | int | 10MB | 单个文档解码后大小限制 |
| `maxTotalDocumentsSize` | int | 20MB | 所有文档总大小限制 |
| `documentSizeAction` | DocumentSizeAction | WARN | 超限时的行为 |
| `documentTokenWarningRatio` | double | 0.5 | 文档占用上下文窗口比例警告阈值 |

### RalphLoopConfig

Ralph Loop 的配置类，支持自定义任务完成检查：

```java
import com.harness.core.RalphLoopConfig;
import java.util.function.Predicate;

// 使用默认任务完成检查（检查 "TASK_COMPLETE" 标记）
RalphLoopConfig config = RalphLoopConfig.builder()
    .goal("修复所有类型错误")
    .maxIterations(50)
    .build();

// 使用自定义 Predicate 检查任务完成
Predicate<String> customCheck = response ->
    response.contains("SUCCESS") && response.contains("0 errors");

RalphLoopConfig config = RalphLoopConfig.builder()
    .goal("测试覆盖率达标")
    .taskCompleteCheck(customCheck)  // 自定义检查
    .progressDir(Path.of("./progress"))  // 进度记录目录
    .build();
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `goal` | String | 必填 | 目标描述 |
| `maxIterations` | int | 50 | 最大迭代次数 |
| `taskCompleteCheck` | Predicate<String> | null | 自定义任务完成检查 |
| `progressDir` | Path | null | 进度记录目录 |

#### 自定义 Predicate 示例

```java
// 检查编译成功
Predicate<String> compileCheck = response ->
    response.contains("BUILD SUCCESS") && !response.contains("error:");

// 检查测试通过
Predicate<String> testCheck = response ->
    response.contains("Tests run:") && response.contains("Failures: 0");

// 检查覆盖率达标
Predicate<String> coverageCheck = response -> {
    // 解析覆盖率报告
    if (response.contains("Line Coverage:")) {
        String[] parts = response.split("Line Coverage:");
        if (parts.length > 1) {
            String coverageStr = parts[1].trim().split("%")[0];
            double coverage = Double.parseDouble(coverageStr);
            return coverage >= 80.0;
        }
    }
    return false;
};

RalphLoopConfig config = RalphLoopConfig.builder()
    .goal("测试覆盖率达到 80%")
    .taskCompleteCheck(coverageCheck)
    .build();
```

详见 [03-agent-loop.md](./03-agent-loop.md)。

### ContextConfig

上下文构建配置类：

```java
import com.harness.memory.ContextConfig;

// 使用默认配置
ContextConfig config = ContextConfig.defaults();

// 自定义配置（使用 setter）
ContextConfig config = new ContextConfig();
config.setMaxTokens(200000);
config.setSystemPrompt("你是一个代码助手");
config.setWindowSize(100);           // 会话窗口大小
config.setEnableCompression(true);   // 启用压缩
config.setCompressionThreshold(0.8); // 压缩阈值（80% 上下文占用）
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `maxTokens` | int | 200000 | 最大上下文 token |
| `systemPrompt` | String | "" | 系统提示 |
| `windowSize` | int | 100 | 会话窗口大小 |
| `enableCompression` | boolean | true | 启用压缩 |
| `compressionThreshold` | double | 0.9 | 压缩阈值 |

### ContextBudget

Token 预算分配类：

```java
import com.harness.memory.ContextBudget;

// 使用默认分配（200000 tokens，4096 response reserve）
ContextBudget budget = new ContextBudget();

// 使用自动分配方法（推荐）
// messages 占 70%，skills 占 20%，memory 占 10%
ContextBudget budget = ContextBudget.allocate(
    200000,  // maxTokens
    5000,    // systemPromptTokens
    3000     // toolTokens
);

// 自定义比例分配
ContextBudget budget = ContextBudget.allocate(
    200000,  // maxTokens
    5000,    // systemPromptTokens
    3000,    // toolTokens
    0.6,     // messageRatio (60%)
    0.25,    // skillsRatio (25%)
    0.15     // memoryRatio (15%)
);

// 查看预算使用情况
int available = budget.availableForInput();  // 可用于输入的 token
int used = budget.used();                    // 已分配的 token
int remaining = budget.remaining();          // 剩余未分配的 token
boolean needsCompress = budget.needsCompression(); // 是否需要压缩
```

### SubAgentConfig

子代理配置类：

```java
import com.harness.core.SubAgentConfig;

SubAgentConfig config = SubAgentConfig.builder()
    .name("code_analyzer")
    .task("分析 src/core 目录的代码质量")
    .tools(List.of("read", "glob", "grep"))  // 允许的工具
    .maxIterations(5)
    .reportFormat("summary")   // "summary" | "full" | "structured"
    .systemPrompt("你是一个代码分析专家")
    .build();
```

#### reportFormat 说明

| 格式 | 说明 |
|-----|------|
| `summary` | 返回摘要（最多 500 字符） |
| `full` | 返回完整响应 |
| `structured` | 返回结构化数据（包含 messages） |

### SubAgentManager.Factory Pattern

SubAgentManager 使用工厂模式避免模块循环依赖：

```java
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.integration.HarnessAgentFactory;

// 创建真实 AgentHarness 的工厂
HarnessAgentFactory factory = new HarnessAgentFactory();

// 创建 SubAgentManager
SubAgentManager manager = new SubAgentManager(parentAgent, factory);

// 或使用 mock 工厂（测试用）
SubAgentManager manager = new SubAgentManager();  // 默认 MockAgentFactory

// 启动子代理
manager.spawn(SubAgentConfig.builder()
    .name("analyzer")
    .task("分析代码")
    .build());

// 并行运行所有子代理
Map<String, SubAgentResult> results = manager.runAll().join();
```

详见 [03-agent-loop.md](./03-agent-loop.md)。

## LLM 客户端

### LLMClient 接口

```java
// LLMClient 接口
import com.harness.types.LLMResponse;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public interface LLMClient {
    String modelName();
    CompletableFuture<LLMResponse> call(
        List<Map<String, Object>> messages,
        List<Map<String, Object>> tools,
        String system);
}
```

### LLMResponse

```java
// LLMResponse record
import com.harness.types.LLMResponse;
import com.harness.types.TokenUsage;
import java.util.List;
import java.util.Map;

// Java LLMResponse record fields:
// - String content              // 文本内容
// - List<ToolCall> toolCalls    // 工具调用列表
// - TokenUsage usage            // token 使用统计
// - String stopReason           // 停止原因
// - Map<String, Object> raw     // 原始响应
```

### TokenUsage

```java
// TokenUsage record
import com.harness.types.TokenUsage;

// Java TokenUsage record fields:
// - int inputTokens
// - int outputTokens
// - int cacheCreationInputTokens
// - int cacheReadInputTokens
TokenUsage usage = new TokenUsage(100, 50);
```

### AnthropicClient

```java
// AnthropicClient（通过 HarnessConfig 自动选择）
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;

AgentHarness agent = AgentHarness.builder()
    .config(HarnessConfig.builder()
        .apiKey("sk-ant-...")
        .model("claude-sonnet-4-6")
        .build())
    .build();
```

### OpenAIClient

支持所有 OpenAI 兼容 API（DeepSeek、硅基流动、本地 vLLM 等）。

```java
// OpenAIClient（Java SDK 原生支持）
import com.harness.llm.OpenAIClient;

// 创建客户端
OpenAIClient client = new OpenAIClient("sk-...", "gpt-4o");

// 自定义 base URL（用于第三方 API）
OpenAIClient client = new OpenAIClient("sk-...", "https://api.deepseek.com/v1", "deepseek-chat");
```

#### Java SDK OpenAIClient

```java
import com.harness.llm.OpenAIClient;

// 创建客户端
OpenAIClient client = new OpenAIClient("sk-...", "gpt-4o");

// 自定义 base URL（用于第三方 API）
OpenAIClient client = new OpenAIClient("sk-...", "https://api.deepseek.com/v1", "deepseek-chat");
```

#### 多模态内容支持

Java SDK 的 OpenAIClient 支持多模态消息（文本 + 图片 + 文档）：

```java
import com.harness.types.Message;
import java.util.List;
import java.util.Map;

// 构建多模态消息
Message message = new Message("user", List.of(
    Map.of("type", "text", "text", "请分析这份文档"),
    Map.of(
        "type", "document",
        "source", Map.of(
            "type", "base64",
            "media_type", "application/pdf",
            "data", pdfBase64Data
        ),
        "filename", "report.pdf"
    )
));

// 调用 API
LLMResponse response = client.call(List.of(message), null, "你是一个助手");
```

**文档转换策略**：

Java SDK 采用兼容性优先策略，将多模态内容转换为文本表示：

| 内容类型 | 转换方式 | 说明 |
|---------|---------|------|
| `text` | 直接传递 | 文本内容 |
| `image` | 占位符 | `[Image attached: image/png]` |
| `document` | 解码嵌入 | 文档内容解码后嵌入消息 |

**转换示例**：

```
原始消息:
  [text] "请分析这份报告"
  [document] report.pdf (base64)

转换后:
  请分析这份报告

  --- Attached File: report.pdf ---
  [文档完整内容]
  --- End of File ---
```

**不修改原始数据**：`convertMultimodalToText()` 方法只读取原始内容，创建新的字符串，不会修改传入的 Message 对象。

这种策略确保与所有 OpenAI 兼容 API 的兼容性（GLM、Qwen、DeepSeek、本地模型），无需担心 API 是否支持 `file` 类型。

#### 第三方 API 兼容性

OpenAIClient 已处理部分第三方 API 的非标准响应：

```java
// 自动处理非标准错误响应
// 某些 API 在错误时返回字符串而非标准响应对象
if (response instanceof String) {
    throw new IllegalArgumentException("API returned non-standard response: "
        + ((String) response).substring(0, Math.min(200, ((String) response).length())));
}
```

**常见第三方 API**：

| 提供者 | base_url | 说明 |
|-------|----------|------|
| DeepSeek | `https://api.deepseek.com/v1` | ~0.01元/千token |
| 硅基流动 | `https://api.siliconflow.cn/v1` | 多模型支持 |
| 本地 vLLM | `http://localhost:8000/v1` | 本地推理 |
| 本地 Ollama | `http://localhost:11434/v1` | 本地推理 |

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `api_key` | str | 必填 | API Key |
| `model` | str | 必填 | 模型名称 |
| `base_url` | str | OpenAI URL | API 基础 URL |
| `max_tokens` | int | 8192 | 最大输出 token |
| `temperature` | float | 1.0 | 生成温度 |
| `timeout` | float | 120.0 | 请求超时（秒） |

### 自定义 LLM 客户端

```java
// 自定义 LLM 客户端
import com.harness.core.LLMClient;
import com.harness.integration.AgentHarness;
import com.harness.types.LLMResponse;
import com.harness.types.TokenUsage;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class MyLLM implements LLMClient {
    @Override public String modelName() { return "my-model"; }

    @Override
    public CompletableFuture<LLMResponse> call(
            List<Map<String, Object>> messages,
            List<Map<String, Object>> tools,
            String system) {
        // 实现自定义 LLM 调用逻辑
        return CompletableFuture.completedFuture(
            new LLMResponse("response", null,
                new TokenUsage(0, 0), "end_turn"));
    }
}

// 直接传入
AgentHarness agent = AgentHarness.builder()
    .llmClient(new MyLLM())
    .build();
```

## CPU Router（成本优化的 LLM 路由）

CPU Router 使用轻量级 CPU 模型（如 Qwen2.5-1.5B）作为路由器，根据请求复杂度路由到不同的下游模型，实现成本优化。

### 架构

```
User Request → Router (CPU) → high/low label → Downstream LLM
```

### RoutingConfig

```java
// RoutingConfig - 使用 HarnessConfig.RoutingConfig
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .routing(HarnessConfig.RoutingConfig.builder()
        .highModel("gpt-4o")
        .highProvider("auto")
        .lowModel("gpt-4o-mini")
        .lowProvider("auto")
        .routerModelPath("models/qwen2.5-1.5b.gguf")
        .defaultRoute("high")
        .routerTimeout(0.2)
        .historyWindow(5)
        .build())
    .build();
```

### 使用示例

#### 基础配置

```java
// 基础配置
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .routing(HarnessConfig.RoutingConfig.builder()
        .highModel("gpt-4o")
        .lowModel("gpt-4o-mini")
        .routerModelPath("models/qwen2.5-1.5b.gguf")
        .build())
    .build();

AgentHarness agent = AgentHarness.builder()
    .config(config)
    .addTool(new ReadTool())
    .build();
```

#### 自动检测 provider

```java
// provider 自动检测
import com.harness.core.HarnessConfig;

HarnessConfig.RoutingConfig routing = HarnessConfig.RoutingConfig.builder()
    .highModel("claude-sonnet-4-6")   // 自动检测 → anthropic
    .lowModel("qwen-plus")            // 自动检测 → openai
    .routerModelPath("models/qwen3.5-0.8b.gguf")
    .build();
```

#### 不同服务商

```java
// 不同服务商
import com.harness.core.HarnessConfig;

HarnessConfig.RoutingConfig routing = HarnessConfig.RoutingConfig.builder()
    .highModel("gpt-4o")
    .highApiKey("sk-openai-xxx")
    .lowModel("deepseek-chat")
    .lowApiKey("sk-deepseek-xxx")
    .lowBaseUrl("https://api.deepseek.com/v1")
    .routerModelPath("models/qwen3.5-0.8b.gguf")
    .build();
```

### EmbeddedLlamaClient

嵌入式 Llama 客户端，使用 llama-cpp-python 加载 GGUF 模型。

```java
// EmbeddedLlamaClient（Java SDK 中通过 RoutingConfig.routerModelPath 配置）
// 嵌入式 Llama 客户端在 Java SDK 中通过 GGUF 模型路径配置
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .routing(HarnessConfig.RoutingConfig.builder()
        .routerModelPath("models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
        .build())
    .build();
```

#### context_window 自动推断

从 GGUF 文件名推断模型名称并设置上下文大小：

| 文件名 | 推断模型名 | 默认 context_window |
|--------|-----------|-------------------|
| `qwen3.5-0.8b-instruct-q4_k_m.gguf` | `qwen3.5-0.8b` | 2048（路由任务足够） |
| `qwen2.5-1.5b-chat-q5_k_m.gguf` | `qwen2.5-1.5b` | 2048 |

未知模型默认使用 2048，足够路由任务使用。

### RoutingLLMClient

路由 LLM 客户端，实现请求路由逻辑。

```java
// RoutingLLMClient（Java SDK 中通过 HarnessConfig.RoutingConfig 自动配置）
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .routing(HarnessConfig.RoutingConfig.builder()
        .highModel("gpt-4o")
        .lowModel("gpt-4o-mini")
        .routerModelPath("models/qwen2.5-1.5b.gguf")
        .build())
    .build();

// RoutingLLMClient 会在 AgentHarness 内部自动创建
AgentHarness agent = AgentHarness.builder().config(config).build();
```

### 路由判断逻辑

默认路由判断标准：

| 判断条件 | 路由目标 |
|---------|---------|
| 需要多步推理 | high |
| 需要调用多个工具 | high |
| 需要代码生成或修改 | high |
| 需要深度分析或报告 | high |
| 简单问答、查询、翻译 | low |

**重要**：当不确定时，选择 high。宁可浪费也不要牺牲质量。

### 进度事件

路由决策会触发 `ProgressEventType.ROUTER_DECISION` 事件：

```java
// 进度事件
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;
import java.util.function.Consumer;

AgentHarness agent = AgentHarness.builder().build();

Consumer<Object> onProgress = event -> {
    // 路由决策会触发路由决策事件
    if (event instanceof Map) {
        Map<?, ?> data = (Map<?, ?>) event;
        System.out.println("路由到: " + data.get("route"));
        System.out.println("目标模型: " + data.get("target_model"));
        System.out.println("路由延迟: " + data.get("router_latency_ms") + "ms");
    }
};

LoopResult result = agent.run("帮我分析这段代码", null, onProgress).join();
```

### 依赖安装

```bash
# 安装 llama-cpp-python（嵌入式模式）
pip install llama-cpp-python

# 或安装预编译版本（推荐）
# macOS (Apple Silicon)
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

# Linux (CUDA)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

## 类型定义

### MessageRole

```java
// MessageRole（Java SDK 中通过 Message 类的方法表示）
import com.harness.types.Message;

// Java 中没有 MessageRole 枚举，而是使用 Message 工厂方法：
Message user = Message.user("Hello");
Message assistant = Message.assistant("Hi there");
Message tool = Message.tool("result", "call_123", "tool_name");
Message system = Message.system("You are helpful");
```

### LoopState

```java
import com.harness.types.LoopState;

public enum LoopState {
    IDLE("idle"),
    BUILDING_CONTEXT("building"),
    CALLING_LLM("calling"),
    PARSING_RESPONSE("parsing"),
    EXECUTING_TOOLS("executing"),
    COMPLETED("completed"),
    ERROR("error"),
    INTERRUPTED("interrupted"),
    STUCK("stuck"),
    MAX_ITERATIONS("max_iterations");
}
```

### LoopResult

```java
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.TokenUsage;

// Java LoopResult record fields:
// - LoopState status            // 循环状态
// - Session session             // 当前会话
// - List<Message> messages      // 消息列表
// - String finalResponse        // 最终响应内容
// - int iterations              // 实际循环次数
// - String error                // 错误信息（如果有）
// - TokenUsage tokenUsage       // token 使用统计

LoopResult result = harness.run("分析代码").join();
if (result.isSuccess()) {
    System.out.println(result.content());
    System.out.println("Iterations: " + result.iterations());
}
```

### ToolCall

```java
import com.harness.types.ToolCall;
import java.util.Map;

// Java ToolCall record fields:
// - String id                    // 工具调用 ID
// - String name                  // 工具名称
// - Map<String, Object> arguments // 调用参数

ToolCall call = new ToolCall("call_123", "read", Map.of("path", "test.txt"));
```

### GoalStatus

```java
// GoalStatus（Java SDK 已在 GoalStatus.java 中定义）
import com.harness.loop.types.GoalStatus;

// Java GoalStatus 枚举值：
// ACHIEVED("achieved")          - 目标达成
// TIMEOUT("timeout")            - 超时
// MAX_ITERATIONS("max_iterations") - 达到最大迭代
// MAX_RESETS("max_resets")      - 达到最大重置次数
// ERROR("error")                - Agent 执行错误
// VERIFIER_FAULT("verifier_fault") - 验证器故障
// CANCELLED("cancelled")        - 用户取消
```

### GoalConfig

```java
// GoalConfig（Java SDK 已在 GoalConfig.java 中定义）
import com.harness.loop.types.GoalConfig;
import java.util.function.Function;

// Java GoalConfig 使用 Builder 模式：
GoalConfig config = GoalConfig.builder()
    .description("目标描述")                    // 目标描述
    .sessionId(null)                           // 会话 ID
    .successCriteria("成功标准")                // 成功标准
    .workspaceDir(".")                         // 工作目录
    .maxIterations(50)                         // 最大迭代次数
    .maxContextResets(5)                       // 最大上下文重置次数
    .timeoutSeconds(3600)                      // 超时时间（秒）
    .customVerifier(null)                      // 自定义验证函数
    .maxTokens(null)                           // 最大 token 数
    .maxCostUsd(null)                          // 最大成本（美元）
    .build();
```

### GoalResult

```java
// GoalResult（Java SDK 已在 GoalResult.java 中定义）
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationRecord;
import java.util.Map;
import java.util.List;

// Java GoalResult record fields：
// - String goal                      // 目标描述
// - GoalStatus status                // 执行状态
// - int totalIterations              // 总迭代次数
// - int contextResets                // 上下文重置次数
// - Map<String, Integer> totalTokens // Token 使用量
// - double durationSeconds           // 执行时长
// - String finalResponse             // 最终响应
// - List<VerificationRecord> verificationLog // 验证日志
// - String error                     // 错误详情
```

详见 [18-loop-engineering.md](./18-loop-engineering.md)。

## Automation API

Automation 是 Loop Engineering Phase 2 的核心 API，整合 Trigger + GoalConfig 实现自动化执行。

### Automation

```java
// Automation
import com.harness.loop.automation.Automation;

// 创建定时任务
Automation automation = Automation.builder()
    .name("daily-report")
    .schedule("0 9 * * *")           // cron 表达式：每天 9:00
    .goal("生成每日报告并发送到 Slack")
    .addSkill("report-generation")
    .build();

// 创建间隔任务
Automation healthCheck = Automation.builder()
    .name("health-check")
    .intervalSeconds(300)           // 每 5 分钟
    .goal("检查系统健康状态")
    .build();

// 启动
automation.start(null).join();

// 查看状态
System.out.println("状态: " + automation.getStatus());  // RUNNING

// 停止
automation.stop().join();
```

### AutomationConfig

```java
// AutomationConfig（Java SDK 已在 AutomationConfig.java 中定义）
import com.harness.loop.automation.AutomationConfig;
import java.util.function.Function;

// Java AutomationConfig 使用 Builder 模式：
AutomationConfig config = AutomationConfig.builder()
    .name("daily-report")                         // 自动化名称
    .goal("生成每日报告")                          // 目标描述
    .schedule("0 9 * * *")                       // cron 表达式（三选一）
    // .intervalSeconds(300)                      // 间隔秒数
    // .trigger(null)                             // 自定义 Trigger
    .workspaceDir(".")                           // 工作目录
    .maxIterations(50)                           // 最大迭代
    .timeoutSeconds(3600)                        // 超时时间
    .addSkill("report-generation")               // 技能
    .build();
```

### AutomationStatus

```java
// AutomationStatus（Java SDK 已在 AutomationStatus.java 中定义）
import com.harness.loop.automation.AutomationStatus;

// Java AutomationStatus 枚举值：
// PENDING    - 等待启动
// RUNNING    - 运行中
// PAUSED     - 已暂停
// STOPPED    - 已停止
// ERROR      - 错误状态
```

### AutomationResult

```java
// AutomationResult（Java SDK 已在 AutomationResult.java 中定义）
import com.harness.loop.automation.AutomationResult;
import com.harness.loop.automation.AutomationStatus;
import com.harness.loop.types.GoalResult;

// Java AutomationResult 包含字段：
// - String automationName
// - AutomationStatus status
// - GoalResult goalResult
// - int runCount
// - int errorCount
// - String errorMessage
```

详见 [17-trigger-system.md](./17-trigger-system.md)。

## Trigger System API

Trigger System 提供触发器基础设施，支持时间、事件驱动的自动化执行。

### CronTrigger

```java
// CronTrigger
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerAction;
import com.harness.triggers.TriggerManager;

TriggerAction action = TriggerAction.builder()
    .goal("生成每日报告")
    .addSkill("report-generation")
    .build();

CronTrigger trigger = CronTrigger.builder()
    .schedule("0 9 * * *")          // 每天 9:00
    .action(action)
    .build();

// 查看下次运行时间
var nextRuns = trigger.getNextRuns(5);
for (var runTime : nextRuns) {
    System.out.println("下次运行: " + runTime);
}

// 启动
trigger.start(callback).join();

// 停止
trigger.stop().join();
```

### IntervalTrigger

```java
// IntervalTrigger
import com.harness.triggers.IntervalTrigger;
import com.harness.triggers.TriggerAction;

TriggerAction action = TriggerAction.builder()
    .goal("检查系统健康状态")
    .build();

IntervalTrigger trigger = IntervalTrigger.builder()
    .intervalSeconds(300)          // 每 5 分钟
    .action(action)
    .build();
```

### TriggerAction

```java
// TriggerAction
import com.harness.triggers.TriggerAction;
import com.harness.triggers.TriggerEvent;

TriggerAction action = TriggerAction.builder()
    .goal("修复所有类型错误")               // 目标描述
    .workspaceDir(".")                     // 工作目录
    .maxIterations(50)                     // 最大迭代
    .timeoutSeconds(3600)                  // 超时时间
    .customVerifier(null)                  // 自定义验证器
    .addSkill("typescript")                // 激活的技能
    .build();

// 转换为 GoalConfig
TriggerEvent event = TriggerEvent.builder()
    .triggerType("CRON")
    .triggerId("trigger-1")
    .build();
var goalConfig = action.toGoalConfig(event);
```

### TriggerManager

```java
// TriggerManager
import com.harness.triggers.TriggerManager;
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerAction;
import com.harness.integration.AgentHarness;

AgentHarness agent = AgentHarness.builder().build();
TriggerManager manager = new TriggerManager();

// 注册触发器
TriggerAction action = TriggerAction.builder()
    .goal("生成每日报告")
    .build();
String triggerId = manager.register(
    CronTrigger.builder().schedule("0 9 * * *").action(action).build(),
    true);

// 列出所有触发器
var triggers = manager.listTriggers();
for (var t : triggers) {
    System.out.println("ID: " + t.id() + ", Type: " + t.type() + ", Enabled: " + t.enabled());
}

// 启动所有触发器
manager.start().join();

// 停止所有触发器
manager.stop().join();

// 注销触发器
manager.unregister(triggerId);
```

### TriggerType & TriggerState

```java
// TriggerType（Java SDK 已在 TriggerType.java 中定义）
import com.harness.triggers.TriggerType;
import com.harness.triggers.TriggerState;

// Java TriggerType 枚举值：
// CRON        - 定时触发
// INTERVAL    - 间隔触发
// WEBHOOK     - HTTP webhook
// HEARTBEAT   - 心跳
// FILE_WATCH  - 文件变化
// EVENT       - 事件总线

// Java TriggerState 枚举值：
// IDLE        - 空闲
// RUNNING     - 运行中
// PAUSED      - 已暂停
// STOPPED     - 已停止
// ERROR       - 错误
```

详见 [17-trigger-system.md](./17-trigger-system.md)。

## Service 模块 (Spring Cloud 集成)

`harness.service` 模块提供 FastAPI 服务包装，用于 Spring Cloud 微服务集成。

### 安装

```bash
# 基础服务
pip install harness-sdk[service]

# Prometheus 指标
pip install harness-sdk[prometheus]

# Redis 分布式存储
pip install harness-sdk[redis]

# Nacos 服务发现
pip install harness-sdk[nacos]
```

### 快速启动

```java
// 使用 Spring Boot 启动服务
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class HarnessServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(HarnessServiceApplication.class, args);
    }
}
// 端点：
// GET  /health              - 健康检查
// POST /api/run             - 同步执行 Agent
// WebSocket /ws/run         - 流式执行
```

### FastAPI 应用

```java
// Spring Boot 端点
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

@RestController
public class HarnessController {

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "healthy"));
    }

    @PostMapping("/api/run")
    public ResponseEntity<Map<String, Object>> run(@RequestBody Map<String, String> body) {
        // 同步执行 Agent
        return ResponseEntity.ok(Map.of("status", "completed", "content", "..."));
    }
}
```

### TracingMiddleware

从 Spring Cloud Gateway 提取 W3C TraceContext：

```java
// TracingMiddleware（Java Spring Boot 中使用 Filter）
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

@Component
public class TracingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String traceId = request.getHeader("traceparent");
        if (traceId == null) {
            traceId = request.getHeader("X-B3-TraceId");
        }
        if (traceId == null) {
            traceId = request.getHeader("X-Trace-Id");
        }
        // 将 traceId 传递给下游处理
        chain.doFilter(request, response);
    }
}
```

**支持的 Header 格式**：
- `traceparent` (W3C TraceContext)
- `X-B3-TraceId` (Zipkin/Sleuth)
- `X-Trace-Id` (自定义)

### MetricsCollector

Prometheus 指标收集器：

```java
// MetricsCollector（Java 中使用 Micrometer）
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.stereotype.Component;

@Component
public class MetricsCollector {
    private final Counter iterationCounter;
    private final Counter toolCallCounter;
    private final Counter tokenCounter;
    private final Timer llmCallTimer;

    public MetricsCollector(MeterRegistry registry) {
        this.iterationCounter = Counter.builder("harness_loop_iterations_total")
            .description("总循环迭代次数").register(registry);
        this.toolCallCounter = Counter.builder("harness_tool_calls_total")
            .description("工具调用次数").register(registry);
        this.tokenCounter = Counter.builder("harness_llm_tokens_total")
            .description("Token 使用量").register(registry);
        this.llmCallTimer = Timer.builder("harness_llm_call_duration_seconds")
            .description("LLM 调用耗时").register(registry);
    }

    public void recordIteration() { iterationCounter.increment(); }
    public void recordToolCall(String tool, boolean success, double duration) {
        toolCallCounter.increment();
    }
}
```

**导出的指标**：

| 指标名 | 类型 | 说明 |
|-------|------|------|
| `harness_loop_iterations_total` | Counter | 总循环迭代次数 |
| `harness_tool_calls_total` | Counter | 工具调用次数 |
| `harness_llm_tokens_total` | Counter | Token 使用量 |
| `harness_session_duration_seconds` | Histogram | 会话持续时间 |
| `harness_active_sessions` | Gauge | 当前活跃会话数 |

### RedisSessionStore

分布式会话存储：

```java
// RedisSessionStore（Java 中使用 Spring Session）
import org.springframework.session.MapSession;
import org.springframework.session.SessionRepository;
import org.springframework.data.redis.core.RedisTemplate;

// 使用 Spring Session Redis 配置
// Spring Boot 自动配置 Redis Session Store
// application.yml:
// spring.session.store-type: redis
// spring.redis.host: localhost
// spring.redis.port: 6379
```

**特点**：
- JSON 序列化（非 pickle），跨语言兼容
- Schema 版本管理
- TTL 自动清理

### RedisDistributedLock

分布式锁：

```java
// RedisDistributedLock（Java 中使用 Redisson）
import org.redisson.Redisson;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;

Config config = new Config();
config.useSingleServer().setAddress("redis://localhost:6379");
RedissonClient redisson = Redisson.create(config);

RLock lock = redisson.getLock("my-resource");
try {
    lock.lock(30, TimeUnit.SECONDS);
    // 执行需要锁保护的操作
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

### 服务发现

```java
// 服务发现（Java 中使用 Spring Cloud Discovery）
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.cloud.client.ServiceInstance;

// Spring Cloud 自动配置服务发现
// application.yml:
// spring.cloud.nacos.discovery.server-addr: nacos:8848
// 或
// eureka.client.service-url.defaultZone: http://eureka:8761/eureka/

// 注册服务实例（Spring Cloud 自动处理）
// 获取服务实例
DiscoveryClient discoveryClient = ...;
List<ServiceInstance> instances = discoveryClient.getInstances("harness-agent");
```

### 错误处理

统一错误响应格式：

```java
// 错误处理（Java 中使用 Spring ControllerAdvice）
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import java.time.Instant;
import java.util.Map;

@RestControllerAdvice
public class ErrorHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleInvalidInput(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(Map.of(
            "errorCode", "AGENT_400_001",
            "errorMessage", e.getMessage(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleInternalError(RuntimeException e) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
            "errorCode", "AGENT_500_001",
            "errorMessage", "Internal error",
            "timestamp", Instant.now().toString()
        ));
    }
}
```

**错误码定义**：

| 错误码 | HTTP 状态 | 说明 |
|-------|----------|------|
| `AGENT_400_001` | 400 | 输入参数无效 |
| `AGENT_401_001` | 401 | 未授权 |
| `AGENT_403_001` | 403 | 禁止访问 |
| `AGENT_404_001` | 404 | 资源不存在 |
| `AGENT_500_001` | 500 | 内部错误 |
| `AGENT_502_001` | 502 | LLM 服务错误 |
| `AGENT_502_002` | 502 | 工具执行错误 |
| `AGENT_400_002` | 400 | 预算超限 |
| `AGENT_400_003` | 400 | 迭代次数超限 |
| `AGENT_400_004` | 400 | 检测到死循环 |

### 可选依赖状态

运行时检测可选依赖是否可用：

```java
// 可选依赖状态（Java 中通过 Maven/Gradle 依赖检查）
// Java SDK 的可选依赖通过 Maven scope: provided 或 optional 管理
// 运行时检查依赖是否可用：
boolean prometheusAvailable = false;
try {
    Class.forName("io.micrometer.core.instrument.Metrics");
    prometheusAvailable = true;
} catch (ClassNotFoundException e) {
    // prometheus-client 未添加
}

boolean redisAvailable = false;
try {
    Class.forName("org.springframework.data.redis.core.RedisTemplate");
    redisAvailable = true;
} catch (ClassNotFoundException e) {
    // spring-data-redis 未添加
}
```

## 下一步

- [03-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop
- [04-tool-system.md](./04-tool-system.md) - 了解工具系统和 Browser Automation
- [05-memory-system.md](./05-memory-system.md) - 了解上下文压缩和记忆管理
- [08-security.md](./08-security.md) - 了解安全设计
- [06-mcp-integration.md](./06-mcp-integration.md) - MCP 协议集成
- [18-loop-engineering.md](./18-loop-engineering.md) - Loop Engineering 完整指南
