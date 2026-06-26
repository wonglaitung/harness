# 07 - SDK API 参考

## 概述

本文档提供 Harness SDK Java 版本的完整 API 参考。

## 公共 API 导出

```java
// 导入核心类
import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.core.*;
import com.harness.types.*;
import com.harness.tools.*;
import com.harness.mcp.*;
import com.harness.memory.*;
import com.harness.skills.*;
import com.harness.security.*;
```

## 核心 SDK

### Harness（主入口）

```java
package com.harness;

/**
 * Harness SDK 主入口类。
 * 
 * 使用示例：
 * <pre>
 * HarnessConfig config = HarnessConfig.builder()
 *     .model("claude-sonnet-4-6")
 *     .apiKey(System.getenv("ANTHROPIC_API_KEY"))
 *     .tools(List.of(new ReadTool(), new BashTool(true)))
 *     .build();
 * 
 * Harness agent = new Harness(config);
 * LoopResult result = agent.run("分析代码");
 * </pre>
 */
public class Harness {
    
    /**
     * 使用配置创建 Harness 实例。
     */
    public Harness(HarnessConfig config);
    
    /**
     * 从配置文件创建实例。
     */
    public static Harness fromConfig(String configPath);
    
    /**
     * 同步执行 Agent。
     * 
     * @param prompt 用户输入
     * @return 执行结果
     */
    public LoopResult run(String prompt);
    
    /**
     * 带会话 ID 的同步执行。
     */
    public LoopResult run(String prompt, String sessionId);
    
    /**
     * 异步执行 Agent。
     */
    public CompletableFuture<LoopResult> runAsync(String prompt);
    
    /**
     * 流式执行。
     */
    public void stream(String prompt, Consumer<String> onChunk);
    
    /**
     * 注册工具。
     */
    public void registerTool(Tool tool);
    
    /**
     * 添加生命周期钩子。
     */
    public void addHook(LifecycleHook hook);
    
    /**
     * 中断当前执行。
     */
    public void interrupt();
    
    /**
     * 获取会话。
     */
    public Session getSession(String sessionId);
    
    /**
     * 清除会话。
     */
    public void clearSession(String sessionId);
}
```

### HarnessConfig

```java
package com.harness;

/**
 * Harness 配置类。
 */
public record HarnessConfig(
    String model,                    // 模型名称
    String apiKey,                   // API 密钥
    String baseUrl,                  // 自定义 API 端点
    String provider,                 // LLM 提供商: "anthropic" 或 "openai"
    List<Tool> tools,               // 工具列表
    String memoryDir,               // 记忆目录
    String memoryMdPath,            // MEMORY.md 路径
    int maxIterations,              // 最大迭代次数
    int contextWindow,              // 上下文窗口
    int maxTokens,                  // 最大输出 token
    double temperature,             // 温度参数
    String systemPrompt,            // 系统提示词
    boolean auditEnabled,          // 是否启用审计
    SecurityConfig security,       // 安全配置
    CostConfig costControl         // 成本控制配置
) {

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        // Builder 实现...
    }
}
```

### LLM 客户端配置

SDK 支持两种 LLM 客户端：

#### Anthropic Claude API（推荐）

```java
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.Model;

// 使用 Anthropic 官方 SDK
AnthropicClient anthropicClient = AnthropicOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/anthropic")  // 银行 API Gateway（可选）
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .build();

// 通过 HarnessConfig 配置
HarnessConfig config = HarnessConfig.builder()
    .provider("anthropic")
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .baseUrl("https://api.your-bank.com/anthropic")  // 可选
    .tools(List.of(new ReadTool(), new BashTool(true)))
    .build();
```

#### OpenAI 兼容 API（第三方）

```java
import com.openai.client.okhttp.OpenAIOkHttpClient;

// 使用 OpenAI 官方 SDK（支持第三方 API）
OpenAIClient openaiClient = OpenAIOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/v1")  // 银行 API Gateway
    .apiKey(System.getenv("BANK_API_KEY"))
    .build();

// 通过 HarnessConfig 配置
HarnessConfig config = HarnessConfig.builder()
    .provider("openai")
    .model("your-model-name")
    .apiKey(System.getenv("BANK_API_KEY"))
    .baseUrl("https://api.your-bank.com/v1")
    .tools(List.of(new ReadTool(), new BashTool(true)))
    .build();
```

## 类型定义

### Message

```java
package com.harness.types;

/**
 * 消息类型。
 */
public record Message(
    String role,                              // user, assistant, tool
    String content,
    Map<String, Object> metadata
) {
    /**
     * 创建用户消息。
     */
    public static Message user(String content);
    
    /**
     * 创建助手消息。
     */
    public static Message assistant(String content);
    
    /**
     * 创建工具结果消息。
     */
    public static Message toolResult(ToolResult result);
}
```

### Session

```java
package com.harness.types;

/**
 * 会话类型。
 */
public record Session(
    String id,
    List<Message> messages,
    TokenUsage tokenUsage,
    Instant createdAt,
    Instant updatedAt
) {
    /**
     * 添加消息到会话。
     */
    public Session addMessage(Message message);
    
    /**
     * 清除消息。
     */
    public Session clear();
    
    /**
     * 创建新会话。
     */
    public static Session create();
    
    /**
     * 创建带 ID 的会话。
     */
    public static Session create(String id);
}
```

### LoopResult

```java
package com.harness.types;

/**
 * 循环执行结果。
 */
public record LoopResult(
    LoopState state,
    Session session,
    String content,
    int iterations,
    TokenUsage tokenUsage,
    String error
) {
    public boolean isCompleted();
    public boolean isInterrupted();
    public boolean hasError();
    
    public static LoopResult completed(Session session, String content, int iterations, TokenUsage usage);
    public static LoopResult interrupted(Session session, int iterations);
    public static LoopResult error(Session session, int iterations, String error);
}
```

### TokenUsage

```java
package com.harness.types;

/**
 * Token 使用统计。
 */
public record TokenUsage(
    int inputTokens,
    int outputTokens
) {
    public int total() {
        return inputTokens + outputTokens;
    }
    
    public TokenUsage add(TokenUsage other) {
        return new TokenUsage(
            this.inputTokens + other.inputTokens,
            this.outputTokens + other.outputTokens
        );
    }
}
```

### ValidationResult

```java
package com.harness.core;

/**
 * 工具参数验证结果。
 */
public record ValidationResult(
    boolean isValid,    // 验证是否通过
    String error        // 错误信息（验证失败时）
) {
    /**
     * 创建验证通过结果。
     */
    public static ValidationResult valid() {
        return new ValidationResult(true, null);
    }
    
    /**
     * 创建验证失败结果。
     */
    public static ValidationResult invalid(String error) {
        return new ValidationResult(false, error);
    }
    
    /**
     * 便捷方法：检查验证是否通过。
     */
    public boolean passed() {
        return isValid;
    }
}
```

### TokenCounter

```java
package com.harness.core;

/**
 * 基于 jtokkit 的 Token 计数器。
 * 使用 Caffeine 缓存提升性能。
 */
public class TokenCounter {
    
    /**
     * 计算单个文本的 token 数量。
     * @param text 输入文本，null 返回 0
     */
    public int count(String text);
    
    /**
     * 计算多个文本的总 token 数量。
     */
    public int countAll(List<String> texts);
    
    /**
     * 计算消息列表的 token 数量。
     */
    public int countMessages(List<Message> messages);
    
    /**
     * 清除缓存。
     */
    public void clearCache();
}
```

**使用示例**:
```java
TokenCounter counter = new TokenCounter();

// 计算单个文本
int tokens = counter.count("Hello, world!");

// 计算多个文本
int total = counter.countAll(List.of("Hello", "World"));

// 计算消息列表
List<Message> messages = List.of(
    Message.system("You are a helpful assistant."),
    Message.user("Hello!")
);
int msgTokens = counter.countMessages(messages);

// 清除缓存（可选）
counter.clearCache();
```

## 工具系统

### Tool 接口

```java
package com.harness.tools;

/**
 * 工具接口。
 */
public interface Tool {
    
    /**
     * 工具名称。
     */
    String name();
    
    /**
     * 工具描述。
     */
    String description();
    
    /**
     * 输入 Schema (JSON Schema 格式)。
     */
    Map<String, Object> inputSchema();
    
    /**
     * 执行工具。
     */
    CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context);
    
    /**
     * 验证参数。
     */
    default ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }
}
```

### 内置工具

```java
// 文件读取工具
public class ReadTool implements Tool {
    public static final String NAME = "read";
}

// 文件写入工具
public class WriteTool implements Tool {
    public static final String NAME = "write";
}

// 文件编辑工具
public class EditTool implements Tool {
    public static final String NAME = "edit";
}

// 文件搜索工具
public class GlobTool implements Tool {
    public static final String NAME = "glob";
}

// 内容搜索工具
public class GrepTool implements Tool {
    public static final String NAME = "grep";
}

// Shell 命令工具
public class BashTool implements Tool {
    public static final String NAME = "bash";
    
    /**
     * @param sandbox 是否启用沙箱模式
     */
    public BashTool(boolean sandbox);
}
```

## MCP 集成

### McpClient

```java
package com.harness.mcp;

/**
 * MCP 客户端。
 */
public class McpClient {
    
    /**
     * 创建 MCP 客户端。
     */
    public static McpClient create(String serverName, McpConfig config);
    
    /**
     * 连接服务器。
     */
    public CompletableFuture<Void> connect();
    
    /**
     * 断开连接。
     */
    public CompletableFuture<Void> disconnect();
    
    /**
     * 获取工具列表。
     */
    public CompletableFuture<List<McpTool>> listTools();
    
    /**
     * 调用工具。
     */
    public CompletableFuture<McpToolResult> callTool(String name, Map<String, Object> args);
}
```

## 安全

### SecurityConfig

```java
package com.harness.security;

/**
 * 安全配置。
 */
public record SecurityConfig(
    boolean enableInputValidation,      // 启用输入验证
    boolean enableOutputSanitization,   // 启用输出清理
    boolean enableAuditLog,            // 启用审计日志
    int maxInputLength,                // 最大输入长度
    int maxOutputLength,               // 最大输出长度
    String auditLogDir,               // 审计日志目录
    int auditRetentionDays            // 审计日志保留天数
) {
    public static Builder builder() { ... }
}
```

### SandboxExecutor

```java
package com.harness.security;

/**
 * 沙箱执行器。
 */
public class SandboxExecutor {
    
    /**
     * 创建沙箱执行器。
     * 
     * @param workingDirectory 工作目录
     * @param readOnlyPaths 只读路径
     * @param readWritePaths 读写路径
     */
    public SandboxExecutor(String workingDirectory, 
                            List<String> readOnlyPaths,
                            List<String> readWritePaths);
    
    /**
     * 在沙箱中执行命令。
     */
    public CompletableFuture<CommandResult> execute(String command);
}
```

## 完整使用示例

### 基础使用

```java
import com.harness.*;
import com.harness.tools.*;

public class BasicExample {
    public static void main(String[] args) {
        HarnessConfig config = HarnessConfig.builder()
            .model("claude-sonnet-4-6")
            .apiKey(System.getenv("ANTHROPIC_API_KEY"))
            .tools(List.of(
                new ReadTool(),
                new GlobTool()
            ))
            .maxIterations(10)
            .build();
        
        Harness agent = new Harness(config);
        LoopResult result = agent.run("分析当前项目的代码结构");
        
        if (result.isCompleted()) {
            System.out.println(result.content());
        } else {
            System.err.println("Error: " + result.error());
        }
    }
}
```

### 流式响应

```java
import java.util.concurrent.CountDownLatch;

public class StreamingExample {
    public static void main(String[] args) throws Exception {
        Harness agent = Harness.fromConfig("harness.yaml");
        
        CountDownLatch latch = new CountDownLatch(1);
        
        agent.stream("帮我重构这个函数", chunk -> {
            System.out.print(chunk);
        });
        
        // 等待完成
        latch.await();
    }
}
```

### MCP 集成

```java
import com.harness.mcp.*;

public class McpExample {
    public static void main(String[] args) {
        // 配置 MCP 服务器
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
        
        // 使用 MCP 工具
        LoopResult result = agent.run("读取 README.md 文件的内容");
        System.out.println(result.content());
    }
}
```

## 下一步

- [08-security.md](./08-security.md) - 详细了解安全设计
- [03-agent-loop.md](./03-agent-loop.md) - 了解 Agent 循环实现
