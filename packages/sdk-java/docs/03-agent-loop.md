# 03 - Agent Loop (Java 实现)

## 概述

Agent Loop 是 Harness SDK 的核心引擎，实现 ReAct（Reasoning and Acting）模式的自主执行循环。本文档详细说明 Java 版本的实现设计。

## ReAct 循环

```
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                        │
│                                                      │
│     ┌──────────┐                                    │
│     │  Start   │                                    │
│     └────┬─────┘                                    │
│          ↓                                          │
│     ┌──────────┐    ┌──────────┐                    │
│     │  Build   │───→│   LLM    │                    │
│     │ Context  │    │   Call   │                    │
│     └──────────┘    └────┬─────┘                    │
│                         ↓                           │
│                    ┌──────────┐                      │
│                    │  Tool    │                      │
│                    │  Calls?  │                      │
│                    └────┬─────┘                      │
│                    Yes  │  No                        │
│                    ↓    └──────────┐                 │
│               ┌──────────┐    ┌──────────┐          │
│               │ Execute  │    │  Return  │          │
│               │  Tools   │    │  Result  │          │
│               └────┬─────┘    └──────────┘          │
│                    │                                 │
│                    ↓                                 │
│              ┌──────────┐                            │
│              │ Max      │                            │
│              │ Iters?   │                            │
│              └────┬─────┘                            │
│           No  │  │  Yes                             │
│              ↓  └──────────┐                         │
│              │  Return     │                         │
│              │  Error      │                         │
│              └─────────────┘                         │
└─────────────────────────────────────────────────────┘
```

## Java 实现

### 核心类设计

```java
package com.harness.core;

import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Agent 循环引擎。
 * 实现 ReAct 模式的自主执行循环。
 */
public class AgentLoop {
    
    private final LlmClient llmClient;
    private final ToolExecutor toolExecutor;
    private final ContextBuilder contextBuilder;
    private final LoopConfig config;
    
    // 状态
    private volatile boolean interrupted = false;
    
    public AgentLoop(LlmClient llmClient, 
                      ToolExecutor toolExecutor,
                      ContextBuilder contextBuilder,
                      LoopConfig config) {
        this.llmClient = llmClient;
        this.toolExecutor = toolExecutor;
        this.contextBuilder = contextBuilder;
        this.config = config;
    }
    
    /**
     * 同步执行 Agent 循环。
     */
    public LoopResult run(String prompt, Session session) {
        return runAsync(prompt, session).join();
    }
    
    /**
     * 异步执行 Agent 循环。
     */
    public CompletableFuture<LoopResult> runAsync(String prompt, Session session) {
        return CompletableFuture.supplyAsync(() -> {
            int iteration = 0;
            TokenUsage totalUsage = new TokenUsage(0, 0);
            
            // 添加用户消息
            session.addMessage(new Message("user", prompt));
            
            while (iteration < config.maxIterations()) {
                // 检查中断
                if (interrupted) {
                    return LoopResult.interrupted(session, iteration);
                }
                
                // 构建上下文
                Context context = contextBuilder.build(session);
                
                // 调用 LLM
                LlmResponse response = llmClient.call(context);
                totalUsage = totalUsage.add(response.usage());
                
                // 添加助手消息
                session.addMessage(new Message("assistant", response.content()));
                
                // 检查是否需要工具调用
                if (!response.hasToolCalls()) {
                    return LoopResult.completed(session, response.content(), iteration, totalUsage);
                }
                
                // 执行工具
                List<ToolResult> results = toolExecutor.executeAll(response.toolCalls());
                
                // 添加工具结果
                for (ToolResult result : results) {
                    session.addMessage(Message.toolResult(result));
                }
                
                iteration++;
            }
            
            return LoopResult.maxIterationsReached(session, iteration);
        });
    }
    
    /**
     * 流式执行 Agent 循环。
     */
    public void stream(String prompt, Session session, Consumer<String> onChunk) {
        // 实现流式响应...
    }
    
    /**
     * 中断当前执行。
     */
    public void interrupt() {
        this.interrupted = true;
    }
}
```

### 配置类

```java
package com.harness.core;

/**
 * Agent 循环配置。
 */
public record LoopConfig(
    int maxIterations,           // 最大迭代次数，默认 10
    long timeoutPerTool,         // 工具超时（毫秒），默认 30000
    boolean enableCircuitBreaker, // 启用熔断器，默认 true
    boolean enableCostControl,   // 启用成本控制，默认 true
    String workingDirectory      // 工作目录
) {
    
    public static final int DEFAULT_MAX_ITERATIONS = 10;
    public static final long DEFAULT_TIMEOUT = 30000;
    
    public static LoopConfig defaults() {
        return new LoopConfig(
            DEFAULT_MAX_ITERATIONS,
            DEFAULT_TIMEOUT,
            true,
            true,
            System.getProperty("user.dir")
        );
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private int maxIterations = DEFAULT_MAX_ITERATIONS;
        private long timeoutPerTool = DEFAULT_TIMEOUT;
        private boolean enableCircuitBreaker = true;
        private boolean enableCostControl = true;
        private String workingDirectory = System.getProperty("user.dir");
        
        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }
        
        public Builder timeoutPerTool(long timeout) {
            this.timeoutPerTool = timeout;
            return this;
        }
        
        public Builder workingDirectory(String dir) {
            this.workingDirectory = dir;
            return this;
        }
        
        public LoopConfig build() {
            return new LoopConfig(maxIterations, timeoutPerTool, enableCircuitBreaker, enableCostControl, workingDirectory);
        }
    }
}
```

### 结果类型

```java
package com.harness.types;

/**
 * 循环执行结果。
 */
public record LoopResult(
    LoopState state,
    Session session,
    String content,             // 最终响应内容
    int iterations,             // 迭代次数
    TokenUsage tokenUsage,      // Token 使用统计
    String error                // 错误信息（如果有）
) {
    
    public boolean isCompleted() {
        return state == LoopState.COMPLETED;
    }
    
    public boolean isInterrupted() {
        return state == LoopState.INTERRUPTED;
    }
    
    public boolean hasError() {
        return state == LoopState.ERROR || error != null;
    }
    
    // 工厂方法
    public static LoopResult completed(Session session, String content, int iterations, TokenUsage usage) {
        return new LoopResult(LoopState.COMPLETED, session, content, iterations, usage, null);
    }
    
    public static LoopResult interrupted(Session session, int iterations) {
        return new LoopResult(LoopState.INTERRUPTED, session, null, iterations, null, null);
    }
    
    public static LoopResult error(Session session, int iterations, String error) {
        return new LoopResult(LoopState.ERROR, session, null, iterations, null, error);
    }
    
    public static LoopResult maxIterationsReached(Session session, int iterations) {
        return new LoopResult(LoopState.MAX_ITERATIONS, session, null, iterations, null, 
            "Max iterations reached: " + iterations);
    }
}

/**
 * 循环状态枚举。
 */
public enum LoopState {
    IDLE,           // 空闲
    BUILDING_CONTEXT, // 构建上下文
    CALLING_LLM,    // 调用 LLM
    EXECUTING_TOOLS, // 执行工具
    COMPLETED,      // 完成
    INTERRUPTED,    // 被中断
    ERROR,          // 错误
    MAX_ITERATIONS, // 达到最大迭代
    STUCK           // 卡住
}
```

## 异步模型

### Python vs Java 对比

| Python | Java |
|--------|------|
| `async def run()` | `CompletableFuture<LoopResult> runAsync()` |
| `await llm.call()` | `llm.callAsync().join()` |
| `async for chunk in stream` | `stream().subscribe(onNext, onError, onComplete)` |
| `asyncio.create_task()` | `CompletableFuture.supplyAsync()` |
| `asyncio.sleep()` | `Thread.sleep()` |

### 流式响应实现

```java
/**
 * 流式响应处理器。
 */
public class StreamingHandler {
    
    private final Consumer<String> onChunk;
    private final Consumer<Throwable> onError;
    private final Runnable onComplete;
    
    public StreamingHandler(Consumer<String> onChunk, 
                            Consumer<Throwable> onError, 
                            Runnable onComplete) {
        this.onChunk = onChunk;
        this.onError = onError;
        this.onComplete = onComplete;
    }
    
    public void handleChunk(String chunk) {
        onChunk.accept(chunk);
    }
    
    public void handleError(Throwable error) {
        onError.accept(error);
    }
    
    public void complete() {
        onComplete.run();
    }
}

// 使用示例
agent.streamAsync("分析代码")
    .thenAccept(chunk -> System.out.print(chunk))
    .exceptionally(error -> {
        error.printStackTrace();
        return null;
    });
```

## 生命周期钩子

### 钩子接口

```java
package com.harness.core.hooks;

/**
 * 生命周期钩子接口。
 */
public interface LifecycleHook {
    
    /**
     * 钩子触发点。
     */
    Set<HookPoint> hookPoints();
    
    /**
     * 执行钩子逻辑。
     */
    CompletableFuture<HookResult> execute(HookContext context);
}

/**
 * 钩子触发点。
 */
public enum HookPoint {
    ON_LOOP_START,         // 循环开始
    BEFORE_LLM_CALL,       // LLM 调用前
    AFTER_LLM_CALL,        // LLM 调用后
    BEFORE_TOOL_EXECUTE,   // 工具执行前
    AFTER_TOOL_EXECUTE,    // 工具执行后
    ON_ERROR,              // 错误发生
    ON_LOOP_END            // 循环结束
}

/**
 * 钩子上下文。
 */
public record HookContext(
    HookPoint hookPoint,
    String sessionId,
    int iteration,
    Message message,
    LlmResponse llmResponse,
    ToolCall toolCall,
    ToolResult toolResult,
    Throwable error
) {
    // Builder 模式...
}

/**
 * 钩子结果。
 */
public record HookResult(
    HookAction action,
    Message injectMessage,
    Map<String, Object> metadata
) {
    public static HookResult continue_() {
        return new HookResult(HookAction.CONTINUE, null, Map.of());
    }
    
    public static HookResult abort(String reason) {
        return new HookResult(HookAction.ABORT, null, Map.of("reason", reason));
    }
    
    public static HookResult inject(Message message) {
        return new HookResult(HookAction.INJECT_MESSAGE, message, Map.of());
    }
}

public enum HookAction {
    CONTINUE,        // 继续
    ABORT,           // 中止
    INJECT_MESSAGE,  // 注入消息
    MODIFY_ARGS,     // 修改参数
    MODIFY_RESULT    // 修改结果
}
```

### 自定义钩子示例

```java
/**
 * 日志钩子 - 记录所有工具调用。
 */
public class LoggingHook implements LifecycleHook {
    
    private final Logger logger = LoggerFactory.getLogger(LoggingHook.class);
    
    @Override
    public Set<HookPoint> hookPoints() {
        return Set.of(
            HookPoint.BEFORE_TOOL_EXECUTE,
            HookPoint.AFTER_TOOL_EXECUTE
        );
    }
    
    @Override
    public CompletableFuture<HookResult> execute(HookContext ctx) {
        if (ctx.hookPoint() == HookPoint.BEFORE_TOOL_EXECUTE) {
            logger.info("Executing tool: {} with args: {}", 
                ctx.toolCall().name(), 
                ctx.toolCall().arguments());
        } else {
            logger.info("Tool result: {}", 
                ctx.toolResult().success() ? "success" : "failed");
        }
        return CompletableFuture.completedFuture(HookResult.continue_());
    }
}

// 注册钩子
agent.addHook(new LoggingHook());
```

## 错误处理

### 智能错误处理器 (ErrorHandler)

Agent Loop 使用 `ErrorHandler` 进行智能错误决策：

```java
/**
 * Intelligent error handler with recovery strategies.
 */
public class ErrorHandler {

    public ErrorDecision handle(Exception error, ErrorContext context) {
        // 根据错误类型智能决策
    }
}
```

**支持的错误类型**：

| 错误类型 | 处理方式 |
|----------|----------|
| Rate Limit (429) | RETRY + 指数退避 |
| Context Overflow | COMPRESS_CONTEXT |
| Permission Denied | ABORT |
| Timeout | RETRY (最多 3 次) |
| Network Error | RETRY + 指数退避 |
| Tool Error | SKIP 或 RETRY |

### LLM 重试策略

Agent Loop 使用配置化的重试策略，支持 ErrorHandler 智能延迟和指数退避：

```java
/**
 * Call LLM with retry and intelligent error handling.
 *
 * Retry strategy:
 * - Max retries from config.retryOnError()
 * - Uses ErrorHandler for intelligent delay (e.g., Retry-After header)
 * - Fallback: exponential backoff with jitter
 */
private LLMResponse callLLMWithRetry(Context context, List<ToolDefinition> tools) {
    int maxRetries = config.retryOnError();

    for (int attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return llmClient.call(context.messages(), tools, context.systemPrompt());
        } catch (Exception e) {
            // Get intelligent decision from ErrorHandler
            ErrorContext errorContext = ErrorContext.builder()
                .error(e)
                .iteration(iteration.get())
                .attempt(attempt + 1)
                .build();

            ErrorDecision decision = errorHandler.handle(e, errorContext);

            if (decision.action() == ErrorAction.RETRY) {
                // Use ErrorHandler's delay or fallback to exponential backoff
                double delaySeconds;
                if (decision.delaySeconds() > 0) {
                    delaySeconds = decision.delaySeconds();
                } else {
                    // Exponential backoff with jitter (cap at 30s)
                    long baseBackoffMs = Math.min((long) Math.pow(2, attempt) * 1000, 30_000);
                    long jitterMs = random.nextLong(500);
                    delaySeconds = (baseBackoffMs + jitterMs) / 1000.0;
                }

                Thread.sleep((long) (delaySeconds * 1000));
            }
        }
    }

    return null;
}
```

**设计原则**：
- **智能延迟**：优先使用 ErrorHandler 返回的延迟（如 Retry-After header）
- **配置化**：重试次数可通过 `LoopConfig.retryOnError()` 调整
- **指数退避**：避免短时间大量重试，上限 30 秒
- **随机抖动**：防止多客户端同时重试（惊群效应）

### 工具执行超时

Agent Loop 使用 `CompletableFuture.orTimeout()` 强制执行工具超时：

```java
/**
 * Execute a single tool with timeout.
 */
private CompletableFuture<ToolResult> executeToolWithTimeout(ToolCall call, ToolContext context) {
    CompletableFuture<ToolResult> future = toolExecutor.execute(call, context);

    return future.orTimeout(config.timeoutPerTool(), TimeUnit.MILLISECONDS)
        .exceptionally(ex -> {
            if (ex.getCause() instanceof TimeoutException) {
                logger.warn("Tool {} timed out after {}ms", call.name(), config.timeoutPerTool());
                return ToolResult.error(
                    call.id(),
                    call.name(),
                    "Tool execution timed out after " + config.timeoutPerTool() + "ms"
                );
            }
            return ToolResult.error(call.id(), call.name(), ex.getMessage());
        });
}
```

**配置**：
- `LoopConfig.timeoutPerTool()`: 单个工具的超时时间（默认 30000 毫秒）

**注意**：超时后工具执行会被取消，Agent 会收到错误信息并可以决定下一步操作。

### 错误处理器

```java
package com.harness.core;

/**
 * 错误处理器。
 */
public class ErrorHandler {
    
    private final int maxRetries;
    private final Map<Class<? extends Throwable>, ErrorAction> actions;
    
    public ErrorHandler(int maxRetries) {
        this.maxRetries = maxRetries;
        this.actions = new HashMap<>();
        
        // 默认配置
        actions.put(RateLimitException.class, ErrorAction.retry(5.0));
        actions.put(TimeoutException.class, ErrorAction.retry(2.0));
        actions.put(AuthenticationException.class, ErrorAction.abort());
    }
    
    public ErrorDecision handle(Throwable error, ErrorContext context) {
        ErrorAction action = actions.getOrDefault(error.getClass(), ErrorAction.retry(1.0));
        
        if (action.type() == ErrorActionType.RETRY && context.attempt() < maxRetries) {
            return ErrorDecision.retry(action.delaySeconds());
        }
        
        return ErrorDecision.abort(error.getMessage());
    }
}

public record ErrorContext(
    Throwable error,
    int attempt,
    int contextTokens
) {}

public record ErrorDecision(
    ErrorActionType type,
    String message,
    double delaySeconds
) {
    public static ErrorDecision retry(double delay) {
        return new ErrorDecision(ErrorActionType.RETRY, null, delay);
    }
    
    public static ErrorDecision abort(String message) {
        return new ErrorDecision(ErrorActionType.ABORT, message, 0);
    }
}

public enum ErrorActionType {
    RETRY,
    ABORT,
    COMPRESS_CONTEXT,
    ESCALATE
}
```

## 性能优化

### 1. 连接池

```java
// OkHttp 连接池配置
OkHttpClient client = new OkHttpClient.Builder()
    .connectionPool(new ConnectionPool(10, 5, TimeUnit.MINUTES))
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(60, TimeUnit.SECONDS)
    .build();
```

### 2. Token 缓存

```java
public class TokenCounter {
    private final Cache<String, Integer> cache = Caffeine.newBuilder()
        .maximumSize(10000)
        .expireAfterAccess(Duration.ofMinutes(10))
        .build();
    
    public int count(String text) {
        return cache.get(text, this::countUncached);
    }
}
```

### 3. 并行工具执行

```java
public CompletableFuture<List<ToolResult>> executeAllAsync(List<ToolCall> calls) {
    List<CompletableFuture<ToolResult>> futures = calls.stream()
        .map(call -> CompletableFuture.supplyAsync(() -> execute(call)))
        .toList();
    
    return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
        .thenApply(v -> futures.stream()
            .map(CompletableFuture::join)
            .toList());
}
```

## 熔断器 (CircuitBreaker)

熔断器用于检测和防止无限循环，遵循 **Bitter Lesson** 原则：简单规则优于复杂启发式。

```java
CircuitBreaker cb = new CircuitBreaker();

// Before tool execution
if (cb.isOpen()) {
    throw new CircuitBreakerException(cb.getReason());
}

// Record call
cb.recordCall("read", Map.of("path", "/tmp/file.txt"));

// On error
cb.recordError(e);

// On success
cb.recordSuccess();
```

**检测机制**：
- 相同工具 + 相同参数重复调用（默认阈值 3 次）
- 短时间内过多错误（默认 60 秒内 5 次错误）

**配置**：

```java
CircuitBreakerConfig config = CircuitBreakerConfig.builder()
    .sameArgsThreshold(3)
    .errorThreshold(5)
    .errorWindowSeconds(60)
    .recoveryTimeoutSeconds(30)
    .build();

CircuitBreaker cb = new CircuitBreaker(config);
```

## 步骤预算控制 (StepBudgetController)

步骤预算控制器限制迭代次数和工具调用次数，防止失控的 Agent 循环。

```java
StepBudgetController budget = new StepBudgetController();
budget.startTask();

// Before each tool call
BudgetCheckResult check = budget.checkBeforeToolCall("read");
if (check.shouldStop()) {
    // Stop execution
}

// Record tool call
budget.recordToolCall("read");

// Advance iteration
budget.advanceIteration();

// End task
StepUsage usage = budget.endTask();
```

**配置**：

```java
StepBudgetConfig config = StepBudgetConfig.builder()
    .maxIterationsPerTask(50)
    .maxToolCallsPerStep(10)
    .maxToolCallsPerTask(200)
    .warningThreshold(0.8)
    .criticalThreshold(0.95)
    .actionOnExceed("stop")  // stop | warn | throttle
    .build();

StepBudgetController budget = new StepBudgetController(config);
```

**预算级别**：

| 级别 | 说明 |
|------|------|
| `NORMAL` | 在安全限制内 |
| `WARNING` | 接近限制（达到 warningThreshold） |
| `CRITICAL` | 接近限制（达到 criticalThreshold） |
| `EXCEEDED` | 预算超限，需要采取行动 |

## 生命周期钩子 (Lifecycle Hooks)

钩子系统允许在 Agent 循环的关键点注入自定义逻辑。

### 钩子触发点

```java
public enum HookPoint {
    BEFORE_LLM_CALL,        // LLM 调用前
    AFTER_LLM_CALL,         // LLM 调用后
    BEFORE_TOOL_EXECUTE,    // 工具执行前
    AFTER_TOOL_EXECUTE,     // 工具执行后
    ON_ERROR,               // 错误发生时
    ON_LOOP_START,          // 循环开始
    ON_LOOP_END,            // 循环结束
    ON_EXIT_ATTEMPT         // 尝试退出时（Ralph Loop）
}
```

### 钩子动作

```java
public enum HookAction {
    CONTINUE,           // 正常继续
    ABORT,              // 立即停止
    RETRY,              // 重试当前操作
    INJECT_MESSAGE,     // 向上下文添加消息
    MODIFY_ARGS,        // 修改工具参数
    MODIFY_RESULT,      // 修改工具结果
    REINJECT            // 清除上下文并重新注入提示（Ralph Loop）
}
```

### 使用示例

```java
// 在工具执行前检查参数
HookContext context = HookContext.builder()
    .hookPoint(HookPoint.BEFORE_TOOL_EXECUTE)
    .toolName("bash")
    .toolArgs(Map.of("command", "rm -rf /"))
    .build();

// 返回 ABORT 阻止危险操作
HookResult result = HookResult.abort("Dangerous command blocked");
```

## 进度事件 (ProgressEvent)

进度事件用于跟踪 Agent 执行过程，支持 UI 反馈和日志记录。

```java
// 创建进度事件
ProgressEvent event = ProgressEvent.of(
    ProgressEventType.TOOL_CALL,
    "Calling read tool"
);

// 带数据的事件
ProgressEvent event = ProgressEvent.of(
    ProgressEventType.LLM_RESPONSE,
    "LLM responded",
    Map.of("tokens", 150, "model", "claude-3")
);

// 带持续时间的事件
ProgressEvent event = ProgressEvent.of(
    ProgressEventType.TOOL_RESULT,
    "Tool completed",
    Map.of("tool", "read"),
    1234  // duration in ms
);
```

**事件类型**：

| 类型 | 说明 |
|------|------|
| `LOOP_START` | Agent 循环开始 |
| `LOOP_END` | Agent 循环结束 |
| `STATE_CHANGE` | 状态变化 |
| `TOOL_CALL` | 工具调用开始 |
| `TOOL_RESULT` | 工具调用结果 |
| `LLM_CALL` | LLM 调用开始 |
| `LLM_RESPONSE` | LLM 响应接收 |
| `TEXT_CHUNK` | 流式文本块 |
| `ITERATION` | 迭代计数 |
| `ERROR` | 错误发生 |

## 下一步

- [04-tool-system.md](./04-tool-system.md) - 了解工具系统的 Java 实现
- [07-sdk-api.md](./07-sdk-api.md) - 查看完整 API 参考
