# 02 - Agent Loop 详解

## 概述

Agent Loop 是 Harness 的核心执行引擎，实现了 ReAct（Reasoning + Acting）模式。它负责管理 LLM 交互循环、工具调用、上下文构建、安全检查和错误处理。

## 核心流程

### ReAct 循环

```
while not finished:
    1. 构建上下文（ContextBuilder 组装系统提示 + 记忆 + 技能）
    2. 调用 LLM
    3. 解析响应
    4. 如果有工具调用 → 执行工具 → 结果追加到消息 → 继续
    5. 如果完成 → 返回 LoopResult
```

### 循环保护机制

| 机制 | 配置字段 | 说明 |
|------|----------|------|
| **最大步数** | `max_iterations` (默认 10) | 限制循环次数（业界标准：OpenAI Agents SDK: 10, LangChain: 10-15） |
| **迭代提醒** | 内置 | 接近迭代上限时注入提示让模型优雅收尾 |
| **工具超时** | `timeout_per_tool` (默认 30.0s) | 每个工具调用的超时时间 |
| **熔断器** | `enable_circuit_breaker` (默认 True) | 相同工具+参数重复 3 次时中断 |
| **卡住检测** | `max_stuck_feedbacks` (默认 2) | 检测重复输出或无进展状态 |
| **成本控制** | `enable_cost_control` (默认 True) | 累计成本超限时中断 |
| **步骤预算** | `step_budget_config` | 限制单次 LLM 响应的工具调用数和任务总调用数 |
| **并行工具** | `enable_parallel_tools` (默认 True) | 启用并行工具调用 |
| **错误重试** | `retry_on_error` (默认 3) | API 错误自动重试次数 |

#### 迭代提醒机制

当接近迭代上限（剩余 2 步）时，Agent Loop 会自动注入提醒消息：

```java
// AgentLoop 核心逻辑
int remainingSteps = config.maxIterations() - iteration;
if (remainingSteps <= 2 && iteration > 0) {
    session = session.addMessage(Message.user(
        "[系统提示] 还有 " + remainingSteps + " 步达到迭代上限。请立即总结当前进展并给出最终回答。"
    ));
}
```

这使模型有机会在达到硬性限制前优雅地完成任务或给出当前进展摘要。

#### 达到迭代上限时的响应恢复

如果达到 `max_iterations`，Agent Loop 会尝试从 session 中提取最后的助手消息作为回复：

```java
// 从 session 中提取有意义的回复
String finalResponse = null;
List<Message> messages = session.messages();
for (int i = messages.size() - 1; i >= 0; i--) {
    Message msg = messages.get(i);
    if ("assistant".equals(msg.role()) && msg.content() != null) {
        finalResponse = msg.content();
        break;
    }
}

return LoopResult.builder()
    .status(LoopState.ERROR)
    .finalResponse(finalResponse)  // 尽可能提供回复
    .error("Max iterations reached")
    .session(session)
    .build();
```

这确保即使模型没有主动给出最终回复，用户也能看到之前的助手消息。

## AgentLoop 类

```java
import com.harness.core.LLMClient;
import com.harness.core.Tool;
import com.harness.core.LoopConfig;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import java.util.List;

// AgentLoop is managed internally by AgentHarness.
// Use AgentHarness to run agent loops:
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();

// Simple run
LoopResult result = agent.run("Your prompt here").join();

// Run with session
LoopResult result2 = agent.run("Continue work", "session-id").join();

// Run in goal-driven mode
GoalResult goalResult = agent.runGoal("Refactor the auth module").join();
```

### LoopConfig

Agent Loop 的配置通过 `LoopConfig` 类管理：

```java
import com.harness.core.LoopConfig;

// LoopConfig is a record with a builder pattern:
LoopConfig config = LoopConfig.builder()
    .maxIterations(10)              // 业界标准（OpenAI Agents SDK: 10, LangChain: 10-15）
    .timeoutPerTool(30000L)         // 每个工具调用的超时时间（毫秒）
    .enableParallelTools(true)      // 是否启用并行工具调用
    .retryOnError(3)                // 错误重试次数
    .enableProgress(true)           // 是否启用进度事件
    .enableCircuitBreaker(true)     // 是否启用熔断器
    .enableCostControl(true)        // 是否启用成本控制
    .workingDirectory("/workspace") // 工具执行的工作目录
    .maxStuckFeedbacks(2)           // 最大反馈注入尝试次数
    .stuckMinIterations(3)          // 卡住检测前的最小迭代次数
    .stuckConsecutiveFailures(3)    // 触发卡住检测的连续失败次数
    .contextWindow(200000)          // 上下文窗口大小
    .sessionWindow(100)             // 会话滑动窗口
    .enableCompression(true)        // 启用压缩
    .build();

// 或使用默认配置
LoopConfig defaults = LoopConfig.defaults();
```

### LoopState

```java
import com.harness.types.LoopState;

// Agent 循环状态机状态
public enum LoopState {
    IDLE("idle"),                    // 空闲，等待输入
    BUILDING_CONTEXT("building"),    // 构建上下文
    CALLING_LLM("calling"),          // 调用 LLM
    PARSING_RESPONSE("parsing"),     // 解析响应
    EXECUTING_TOOLS("executing"),    // 执行工具
    COMPLETED("completed"),          // 完成
    ERROR("error"),                  // 错误状态
    INTERRUPTED("interrupted"),      // 被中断
    STUCK("stuck"),                  // 陷入停滞
    MAX_ITERATIONS("max_iterations"); // 达到最大迭代次数
}
```

### LoopResult

```java
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.TokenUsage;
import com.harness.types.Session;
import com.harness.types.Message;

// LoopResult is a record with factory methods:
public record LoopResult(
    LoopState status,              // 循环状态
    Session session,               // 当前会话
    List<Message> messages,        // 消息列表
    String finalResponse,          // 最终响应内容
    int iterations,                // 实际循环次数
    String error,                  // 错误信息（如果有）
    TokenUsage tokenUsage          // token 使用统计
) {
    // 获取最终文本内容
    public String content() {
        return finalResponse != null ? finalResponse : "";
    }

    // 检查循环是否成功完成
    public boolean isSuccess() {
        return status == LoopState.COMPLETED;
    }

    // 工厂方法
    public static LoopResult completed(Session session, String response, int iterations, TokenUsage usage) { ... }
    public static LoopResult error(Session session, int iterations, String error) { ... }
    public static LoopResult maxIterations(Session session, int iterations) { ... }
}
```

## 消息处理流程

Agent Loop 在处理用户消息时遵循"Session 作为单一数据源"原则，确保消息在多轮迭代中不丢失。

### 核心原则

1. **Session 是单一数据源**：所有消息都存储在 `session.messages` 中
2. **消息持久化**：用户消息在第一次迭代时被持久化到 session
3. **ContextBuilder 只读取**：上下文构建器从 session 读取消息，不修改 session

### 消息流

```
┌──────────────────────────────────────────────────────────────────┐
│                        First Iteration                            │
│                                                                   │
│  用户输入 → session.add_message(Message(role="user", content))   │
│                          ↓                                        │
│           ContextBuilder.build(session) ← 从 session 读取         │
│                          ↓                                        │
│                    LLM 调用                                       │
│                          ↓                                        │
│           session.add_message(Message(role="assistant"))         │
│           session.add_message(Message(role="tool"))              │
├──────────────────────────────────────────────────────────────────┤
│                      Second Iteration                             │
│                                                                   │
│           ContextBuilder.build(session)                           │
│                          ↓                                        │
│           messages = [user, assistant, tool, tool]  ← 完整上下文  │
│                          ↓                                        │
│                    LLM 调用                                       │
└──────────────────────────────────────────────────────────────────┘
```

### 代码实现

```java
// AgentLoop 核心逻辑（在 AgentHarness 内部管理）
// AgentHarness.run() 方法内部执行以下循环：

// 1. 第一次迭代时持久化用户消息
if (iteration == 0 && prompt != null) {
    session = session.addMessage(Message.user(prompt));
}

// 2. 从 session 构建上下文（包含所有历史消息）
// 内部通过 ContextBuilder 完成

// 3. 调用 LLM
// 内部通过 LLMClient 完成

// 4. 添加 assistant 消息
if (response.content() != null) {
    session = session.addMessage(Message.assistant(response.content()));
}

// 5. 执行工具并添加 tool 消息
if (response.isToolUse()) {
    List<ToolResult> toolResults = executeTools(response.toolCalls(), session);
    for (ToolResult result : toolResults) {
        session = session.addMessage(Message.tool(
            result.content(), result.toolCallId(), result.toolName()
        ));
    }
}

// 使用 AgentHarness 运行时，所有这些步骤自动完成：
AgentHarness agent = AgentHarness.builder().build();
LoopResult result = agent.run("Read and analyze src/Main.java").join();
```

### 注意事项

- **不要临时添加消息**：所有消息都应该通过 `session.add_message()` 持久化
- **ContextBuilder 不修改 session**：上下文构建器只负责读取和窗口裁剪
- **工具结果也持久化**：tool message 同样存储在 session 中

## Lifecycle Hooks

Agent Loop 在关键执行点触发生命周期钩子，允许外部代码拦截、修改或注入行为。

### HookPoint 枚举

```java
import com.harness.core.HookPoint;

// HookPoint 枚举
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

### HookContext

**Python SDK**:

```java
import com.harness.core.HookContext;
import com.harness.core.HookPoint;

// HookContext record fields:
// - HookPoint hookPoint         当前钩子点
// - String sessionId            当前会话 ID
// - int iteration               当前迭代次数
// - String toolName             工具名称（用于工具钩子）
// - Map<String, Object> toolArgs  工具参数（用于 BEFORE_TOOL_EXECUTE）
// - ToolResult toolResult       工具结果（用于 AFTER_TOOL_EXECUTE）
// - LLMResponse llmResponse     LLM 响应（用于 AFTER_LLM_CALL）
// - Exception error             错误（用于 ON_ERROR）
// - List<Message> messages      当前消息（可选）
// - Map<String, Object> metadata  附加元数据

HookContext context = HookContext.builder()
    .hookPoint(HookPoint.BEFORE_TOOL_EXECUTE)
    .sessionId("my-session")
    .iteration(1)
    .toolName("read")
    .toolArgs(Map.of("path", "src/Main.java"))
    .build();
```

**Java SDK**:

```java
import com.harness.core.HookContext;
import com.harness.core.HookPoint;

// Java HookContext record fields:
// - HookPoint hookPoint
// - String sessionId
// - int iteration
// - String toolName
// - Map<String, Object> toolArgs
// - ToolResult toolResult
// - LLMResponse llmResponse
// - Exception error
// - List<Message> messages
// - Map<String, Object> metadata

HookContext context = HookContext.builder()
    .hookPoint(HookPoint.BEFORE_TOOL_EXECUTE)
    .sessionId("my-session")
    .iteration(1)
    .toolName("read")
    .toolArgs(Map.of("path", "src/Main.java"))
    .build();
```

### 注册钩子

钩子通过继承 `LifecycleHook` 类并实现 `hook_points` 和 `execute` 方法来创建，然后通过 `agent.add_hook()` 注册。

**Python SDK**:

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import java.util.List;
import java.util.Map;

// 创建自定义钩子
public class MyPermissionHook implements LifecycleHook {
    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        if ("bash".equals(context.toolName())) {
            Map<String, Object> args = context.toolArgs();
            if (args != null) {
                String command = (String) args.get("command");
                if (command != null && (command.contains("rm -rf") || command.contains("sudo"))) {
                    return HookResult.abort("Dangerous command blocked");
                }
            }
        }
        return HookResult.continue_();
    }
}

// 注册钩子到 Agent
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();
agent.addHook(new MyPermissionHook());

// 使用内置钩子
agent.addHook(new com.harness.hooks.LoggingHook());
agent.addHook(new com.harness.hooks.AbortOnDangerousToolHook());
agent.addHook(new com.harness.hooks.MaxToolCallsHook("bash", 10));
```

**Java SDK**:

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import java.util.List;
import java.util.Map;

// 创建自定义钩子
public class MyPermissionHook implements LifecycleHook {
    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        if ("bash".equals(context.toolName())) {
            Map<String, Object> args = context.toolArgs();
            if (args != null) {
                String command = (String) args.get("command");
                if (command != null && (command.contains("rm -rf") || command.contains("sudo"))) {
                    return HookResult.abort("Dangerous command blocked");
                }
            }
        }
        return HookResult.continue_();
    }
}

// 注册钩子
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();
agent.addHook(new MyPermissionHook());

// 使用内置钩子
agent.addHook(new com.harness.hooks.LoggingHook());
agent.addHook(new com.harness.hooks.AbortOnDangerousToolHook());
agent.addHook(new com.harness.hooks.MaxToolCallsHook("bash", 10));
```

### 钩子执行顺序

同一钩子点的多个处理器按注册顺序依次执行。每个处理器通过返回 `HookResult` 来控制后续行为：

| 动作 | 说明 |
|------|------|
| **CONTINUE** | 正常继续执行 |
| **ABORT** | 立即停止执行 |
| **RETRY** | 重试当前操作 |
| **INJECT_MESSAGE** | 向上下文注入消息 |
| **MODIFY_ARGS** | 修改工具参数（BEFORE_TOOL_EXECUTE 钩子） |
| **MODIFY_RESULT** | 修改工具结果（AFTER_TOOL_EXECUTE 钩子） |
| **REINJECT** | 清除上下文并重新注入提示（Ralph Loop 使用） |

### ON_EXIT_ATTEMPT 钩子

`ON_EXIT_ATTEMPT` 是特殊钩子，在循环准备退出时触发。可以用于：
- 阻止过早退出（要求 Agent 继续工作）
- 添加最终检查或验证
- 注入总结指令

```java
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.types.Message;
import java.util.List;

// 防止过早退出的钩子
public class PreventEarlyExitHook implements LifecycleHook {
    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.ON_EXIT_ATTEMPT);
    }

    @Override
    public HookResult execute(HookContext context) {
        if (!isTaskComplete(context)) {
            // 注入消息让 Agent 继续工作
            Message message = Message.user("任务尚未完成，请继续工作。");
            return HookResult.injectMessage(message);
        }
        return HookResult.continue_();
    }

    private boolean isTaskComplete(HookContext context) {
        if (context.messages() != null && !context.messages().isEmpty()) {
            Message lastMessage = context.messages().get(context.messages().size() - 1);
            if (lastMessage.content() != null &&
                lastMessage.content().toLowerCase().contains("task complete")) {
                return true;
            }
        }
        return false;
    }
}

// 注册钩子
AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new PreventEarlyExitHook());
```

## Stuck Detection（卡住检测）

Agent Loop 内置卡住检测机制，采用两级检测策略：

### 检测策略

| 策略 | 说明 | 成本 |
|------|------|------|
| **空/错误检测** | 连续 N 次空结果或错误响应 | 零成本 |
| **语义检测** | 基于 embedding 的相似度检测，捕捉重复输出模式 | 需要模型 |

### 检测模式

| 模式 | 检测方法 |
|------|----------|
| **空结果** | 连续 N 次工具返回空内容 |
| **错误循环** | 连续 N 次工具返回错误 |
| **语义重复** | 连续 N 轮输出高度相似（相似度 ≥ 阈值） |

### 配置选项

```java
import com.harness.core.LoopConfig;

// 基础配置（空/错误检测，零依赖）
LoopConfig config = LoopConfig.builder()
    .maxStuckFeedbacks(2)           // 最大反馈注入次数
    .stuckMinIterations(3)          // 最小迭代次数后开始检测
    .stuckConsecutiveFailures(3)    // 连续失败次数阈值
    .build();

// 语义检测通过 StuckDetectorConfig 配置
// StuckDetectorConfig 在 Java SDK 中通过 LoopConfig 的字段控制
```

### 安装依赖

语义检测需要安装可选依赖：

```bash
pip install harness-sdk[stuck]
```

默认使用 `bge-small-zh-v1.5` 模型（中文优化，约 100MB）。

### 检测后行为

检测到卡住状态后，Agent Loop 会：

1. **注入反馈消息**：提醒 Agent 尝试不同方法
2. **清除检测状态**：避免误判
3. **最终中断**：反馈次数耗尽后终止循环

### 反馈消息示例

```java
// 第一次检测到语义重复
"[循环检测] 检测到重复的输出模式（相似度 95%）。\n" +
"你的方法似乎在原地打转，请尝试完全不同的策略。"

// 第二次检测（最后机会）
"[循环检测 - 最后机会] 重复模式仍在继续（相似度 93%）。\n" +
"请立即承认无法继续或采用根本性不同的方法。"
```

### 自动降级

如果 `sentence-transformers` 未安装，语义检测自动禁用，退回空/错误检测。不会影响 Agent 正常运行。

## Ralph Loop（长任务循环）

Ralph Loop 是专为长时间运行任务设计的循环模式，解决"上下文焦虑"问题——当任务步骤过多时，LLM 倾向于草率完成。它通过 `RalphLoopHook` 实现，该钩子拦截退出尝试并在任务未真正完成时触发继续执行。

### RalphLoopHook

```java
import com.harness.integration.AgentHarness;
import com.harness.core.RalphLoopHook;
import com.harness.core.RalphLoopConfig;
import java.util.function.Predicate;

// 创建 Ralph Loop 钩子
RalphLoopConfig config = RalphLoopConfig.builder()
    .maxLoops(5)
    .taskCompleteCheck(response ->
        response.toLowerCase().contains("done") ||
        response.contains("TASK_COMPLETE")
    )
    .build();
RalphLoopHook ralphHook = new RalphLoopHook(config);

// 注册到 Agent
AgentHarness agent = AgentHarness.builder().build();
agent.addHook(ralphHook);

// 执行长任务 - Ralph Loop 会自动处理继续执行
LoopResult result = agent.run("重构整个认证模块，添加 OAuth2 支持").join();
```

### RalphLoopConfig

```java
import com.harness.core.RalphLoopConfig;
import java.util.function.Predicate;

// RalphLoopConfig 使用 Builder 模式
RalphLoopConfig config = RalphLoopConfig.builder()
    .maxLoops(5)                    // 最大继续循环次数
    .contextThreshold(0.6)          // 上下文阈值（触发 Ralph Loop 的最低使用率）
    .taskCompleteCheck(response ->  // 自定义任务完成检测函数
        response.contains("TASK_COMPLETE") ||
        response.contains("所有任务已完成")
    )
    .progressDir(Path.of("./progress"))  // 进度保存目录
    .build();
```

**Java SDK 配置**：

```java
import com.harness.core.RalphLoopConfig;
import java.util.function.Predicate;

// 使用 Builder 创建配置
RalphLoopConfig config = RalphLoopConfig.builder()
    .maxLoops(5)
    .contextThreshold(0.6)
    // 自定义任务完成检测（Java 使用 Predicate）
    .taskCompleteCheck(response ->
        response.contains("TASK_COMPLETE") ||
        response.contains("所有任务已完成")
    )
    .progressDir(Path.of("./progress"))
    .build();
```
    continuation_prompt_template: str = (  # 继续提示模板
        "[任务继续] 之前的上下文已达到限制，但任务尚未完成。\n\n"
        "请继续之前的工作。以下是最后一步的输出摘要：\n\n"
        "{previous_response}\n\n"
        "请继续执行，直到任务完全完成。"
    )
    context_threshold: float = 0.6        # 触发上下文阈值（最大 token 的比例）
```

### 工作原理

1. **拦截退出尝试**：当 Agent 准备退出时，`ON_EXIT_ATTEMPT` 钩子被触发
2. **任务完成检测**：检查 LLM 响应是否表明任务真正完成
   - 默认检测完成关键词：`task complete`, `all done`, `finished successfully` 等
   - 可自定义检测函数
3. **触发继续执行**：如果任务未完成：
   - 增加循环计数
   - 构建继续提示
   - 返回 `REINJECT` 动作，清除上下文并注入继续指令
4. **循环限制**：防止无限循环（默认最多 5 次继续）

### Ralph Loop vs 标准 Agent Loop

| 特性 | 标准 Agent Loop | Ralph Loop |
|------|----------------|------------|
| **适用场景** | 短任务（< 10 步） | 长任务（可能 50+ 步） |
| **退出策略** | 完成/出错即退出 | 防止草率完成，检测真正完成状态 |
| **上下文管理** | 简单追加 | 自动上下文重置（REINJECT 动作） |
| **继续机制** | 无 | 自动检测未完成任务并继续 |
| **配置方式** | 无 | 通过 `RalphLoopHook` 钩子配置 |

### 使用方式

```java
import com.harness.integration.AgentHarness;
import com.harness.core.RalphLoopHook;
import com.harness.core.RalphLoopConfig;

// 简单使用：添加默认 Ralph Loop 钩子
AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new RalphLoopHook());

// 自定义配置：设置最大循环次数和完成检测
RalphLoopConfig config = RalphLoopConfig.builder()
    .maxLoops(3)
    .taskCompleteCheck(response -> {
        String lower = response.toLowerCase();
        return lower.contains("task complete") ||
               lower.contains("all done") ||
               lower.contains("finished");
    })
    .build();
agent.addHook(new RalphLoopHook(config));

// 执行长任务
LoopResult result = agent.run("重构整个代码库，添加类型注解和测试").join();
```

## Sub-Agent 管理

Sub-Agent 允许主 Agent 创建子代理来处理子任务，实现任务分解和并行执行。`SubAgentManager` 管理子代理的生命周期。

### SubAgentConfig

```java
import com.harness.core.SubAgentConfig;

// SubAgentConfig 使用 Builder 模式
SubAgentConfig config = SubAgentConfig.builder()
    .name("core_analyzer")             // 子代理唯一名称
    .task("Analyze src/core directory") // 任务描述
    .tools(List.of("read", "grep"))    // 可用工具列表（null = 继承父代理所有工具）
    .maxIterations(20)                  // 最大迭代次数
    .build();
```

**工具过滤说明**：

当指定 `tools` 参数时，子代理只会继承父代理中名称匹配的工具。支持常用别名：

| 别名 | 实际工具名 |
|------|-----------|
| `read` | `read` |
| `write` | `write_file` |
| `edit` | `edit_file` |
| `glob` | `glob` |
| `grep` | `grep` |
| `bash` | `bash` |

```java
import com.harness.core.SubAgentConfig;
import java.util.List;

// 子代理只继承读取类工具
SubAgentConfig readerConfig = SubAgentConfig.builder()
    .name("reader")
    .task("只读分析")
    .tools(List.of("read", "glob", "grep"))  // 只允许读取操作
    .build();

// 子代理继承所有父代理工具
SubAgentConfig fullAccessConfig = SubAgentConfig.builder()
    .name("full-access")
    .task("完整访问")
    .tools(null)  // null = 继承所有
    .build();
```

### SubAgentResult

```java
import com.harness.core.SubAgentResult;
import com.harness.core.SubAgentStatus;

// SubAgentResult record
public record SubAgentResult(
    String name,                        // 子代理名称
    boolean success,                    // 是否成功完成
    SubAgentStatus status,              // 状态
    String summary,                     // 结果摘要
    String fullResponse,                // 完整响应
    Map<String, Object> structuredResult, // 结构化结果
    int iterations,                     // 使用的迭代次数
    Map<String, Integer> tokenUsage,    // token 使用统计
    String error                        // 错误信息
) {}
```

### SubAgentManager

SubAgentManager 使用 **工厂模式** 创建子代理，支持不同实现（真实 AgentHarness、Mock 等）。

**Python SDK**：

```java
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.integration.AgentHarness;
import com.harness.integration.AgentHarnessParentAdapter;
import com.harness.integration.HarnessAgentFactory;

// 创建父代理
AgentHarness parent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();

// 使用工厂创建管理器
SubAgentManager manager = new SubAgentManager(
    new AgentHarnessParentAdapter(parent),
    new HarnessAgentFactory()
);

// 创建子代理配置
SubAgentConfig config1 = SubAgentConfig.builder()
    .name("core_analyzer")
    .task("Analyze src/core directory for code quality issues")
    .tools(List.of("read", "grep"))
    .maxIterations(15)
    .build();

SubAgentConfig config2 = SubAgentConfig.builder()
    .name("security_analyzer")
    .task("Check for security vulnerabilities in src/ directory")
    .tools(List.of("read", "grep", "bash"))
    .maxIterations(20)
    .build();

// 创建并运行子代理
manager.spawn(config1);
manager.spawn(config2);
Map<String, SubAgentResult> results = manager.runAll().join();

// 处理结果
for (Map.Entry<String, SubAgentResult> entry : results.entrySet()) {
    SubAgentResult result = entry.getValue();
    if (result.success()) {
        System.out.println(entry.getKey() + ": " + result.summary());
    } else {
        System.out.println(entry.getKey() + " failed with status: " + result.status());
    }
}
```

**Java SDK**（工厂模式）：

```java
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.integration.HarnessAgentFactory;
import com.harness.integration.AgentHarnessParentAdapter;

// 创建父代理
AgentHarness parent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();

// 使用工厂创建管理器（真实 AgentHarness）
SubAgentManager manager = new SubAgentManager(
    new AgentHarnessParentAdapter(parent),
    new HarnessAgentFactory()
);

// 创建子代理配置
SubAgentConfig config1 = SubAgentConfig.builder()
    .name("core_analyzer")
    .task("Analyze src/core directory")
    .tools(List.of("read", "grep"))
    .maxIterations(15)
    .build();

// 创建子代理
manager.spawn(config1);

// 并行运行所有子代理
Map<String, SubAgentResult> results = manager.runAll().join();
```

### 工厂模式架构

SubAgentManager 使用 `AgentFactory` 接口创建子代理运行器：

```
SubAgentManager
    ├── AgentFactory (接口)
    │   ├── HarnessAgentFactory (真实 AgentHarness)
    │   └── MockAgentFactory (默认模拟实现)
    │
    └── AgentHarnessParent (接口)
        └── AgentHarnessParentAdapter (适配器)
```

**设计优势**：
- **解耦**：SubAgentManager 在 `harness-sdk-core` 模块，不直接依赖 `AgentHarness`
- **可测试**：使用 MockAgentFactory 进行单元测试
- **可扩展**：支持其他 Agent 实现（如 MockHarness）

### 子代理状态

```java
import com.harness.core.SubAgentStatus;

// SubAgentStatus 枚举
public enum SubAgentStatus {
    PENDING,      // 等待运行
    RUNNING,      // 运行中
    COMPLETED,    // 成功完成
    FAILED,       // 执行失败
    CANCELLED     // 被取消
}
```

### 使用场景

```java
import com.harness.integration.AgentHarness;
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.integration.AgentHarnessParentAdapter;
import com.harness.integration.HarnessAgentFactory;

// 复杂任务分解为多个子任务并行执行
AgentHarness agent = AgentHarness.builder().build();
SubAgentManager manager = new SubAgentManager(
    new AgentHarnessParentAdapter(agent),
    new HarnessAgentFactory()
);

// 创建多个子代理分析不同模块
List<SubAgentConfig> configs = new ArrayList<>();
for (int i = 0; i < 5; i++) {
    configs.add(SubAgentConfig.builder()
        .name("module_" + i)
        .task("Analyze module " + i + " for performance issues")
        .tools(List.of("read", "grep"))
        .build());
}

// 创建并运行所有子代理
for (SubAgentConfig config : configs) {
    manager.spawn(config);
}
Map<String, SubAgentResult> results = manager.runAll().join();

// 聚合结果
StringBuilder aggregatedSummary = new StringBuilder();
for (Map.Entry<String, SubAgentResult> entry : results.entrySet()) {
    if (entry.getValue().success()) {
        aggregatedSummary.append(entry.getKey())
            .append(": ")
            .append(entry.getValue().summary())
            .append("\n");
    }
}
```

## Self-Verification（自验证）

自验证钩子实现了 `write-code → run-tests → fix-errors` 的自动验证循环。`SelfVerificationHook` 在代码修改后自动运行测试，并将失败结果注入回上下文供 LLM 修复。

### SelfVerificationConfig

```java
import com.harness.core.SelfVerificationConfig;
import java.util.List;
import java.nio.file.Path;

// SelfVerificationConfig 使用 Builder 模式
SelfVerificationConfig config = SelfVerificationConfig.builder()
    .testCommand("pytest")                           // 测试命令
    .testArgs(List.of("-x", "--tb=short"))           // 测试参数
    .triggerTools(List.of("write", "edit"))          // 触发验证的工具
    .workingDirectory(Path.of("/workspace"))          // 工作目录
    .timeout(60.0)                                    // 超时时间（秒）
    .maxRetries(3)                                    // 最大重试次数
    .verifyOnChange(true)                             // 是否每次代码修改都验证
    .skipIfNoTests(true)                             // 无测试文件时是否跳过
    .testPattern("test_*.java")                      // 测试文件模式
    .build();
```

### SelfVerificationHook

```java
import com.harness.integration.AgentHarness;
import com.harness.core.SelfVerificationHook;
import com.harness.core.SelfVerificationConfig;
import java.util.List;

// 创建自验证钩子
SelfVerificationConfig config = SelfVerificationConfig.builder()
    .testCommand("pytest")
    .testArgs(List.of("-x", "-v", "--tb=short"))
    .maxRetries(3)
    .verifyOnChange(true)
    .build();
SelfVerificationHook verificationHook = new SelfVerificationHook(config);

// 注册到 Agent
AgentHarness agent = AgentHarness.builder().build();
agent.addHook(verificationHook);

// 现在代码修改后会自动运行测试
LoopResult result = agent.run("Fix the bug in src/main.py").join();
```

### 工作原理

1. **触发条件**：当 `AFTER_TOOL_EXECUTE` 钩子触发且工具名在 `trigger_tools` 列表中时
2. **测试检测**：检查当前目录是否存在测试文件（匹配 `test_pattern`）
3. **测试执行**：运行配置的测试命令
4. **结果处理**：
   - 测试通过：继续正常执行
   - 测试失败：注入错误消息到上下文，要求 LLM 修复
   - 超时/错误：记录日志并继续
5. **重试限制**：防止无限重试（默认最多 3 次）

### 使用示例

```java
import com.harness.integration.AgentHarness;
import com.harness.core.SelfVerificationHook;
import com.harness.core.SelfVerificationConfig;
import java.util.List;

// 创建带自验证的 Agent
AgentHarness agent = AgentHarness.builder().build();

// 配置自验证（使用 pytest 测试）
SelfVerificationConfig config = SelfVerificationConfig.builder()
    .testCommand("pytest")
    .testArgs(List.of("-x", "--tb=short", "--disable-warnings"))
    .maxRetries(2)
    .verifyOnChange(true)
    .skipIfNoTests(true)
    .build();
SelfVerificationHook verification = new SelfVerificationHook(config);

// 添加钩子
agent.addHook(verification);

// 执行任务 - 代码修改后会自动运行测试
LoopResult result = agent.run(
    "Refactor the authentication module to use JWT tokens. " +
    "Update tests accordingly."
).join();

// 如果测试失败，Agent 会自动收到错误信息并修复
```

### 高级配置

```java
import com.harness.core.SelfVerificationConfig;
import java.util.List;

// 自定义触发工具
SelfVerificationConfig config = SelfVerificationConfig.builder()
    .triggerTools(List.of("write", "edit"))  // 只对 write 和 edit 工具触发
    .testCommand("python -m unittest")       // 使用 unittest
    .testArgs(List.of("discover", "-s", "tests", "-p", "test_*.py"))
    .verifyOnChange(false)                   // 只在任务完成时验证
    .build();

// 多个测试命令
SelfVerificationConfig multiConfig = SelfVerificationConfig.builder()
    .testCommand("bash")                     // 使用 bash 执行复杂测试脚本
    .testArgs(List.of("-c", "pytest && mypy . && black --check ."))
    .timeout(120.0)                          // 更长超时时间
    .build();
```

## Tool Output Offload（工具输出卸载）

当工具输出过大时（如读取大型文件、目录列表等），会导致上下文膨胀，增加成本并可能超出模型限制。Output Offload 机制自动检测大型输出并将其卸载到临时文件，上下文中只保留引用。

### OffloadConfig

```java
import com.harness.core.OffloadConfig;
import java.nio.file.Path;

// OffloadConfig 使用 Builder 模式
OffloadConfig config = OffloadConfig.builder()
    .enabled(true)                     // 是否启用卸载（默认 true）
    .sizeThresholdChars(50000)         // 触发卸载的最小输出大小（字符数，默认 50000）
    .maxOutputsPerSession(50)          // 每会话最大卸载数量
    .cleanupOnSessionEnd(false)        // 会话结束时是否清理文件
    .previewLength(500)                // 上下文中保留的预览长度（默认 500）
    .tempDir(Path.of(".harness/offload")) // 卸载文件存储目录
    .build();
```

### OffloadedOutput

```java
import com.harness.core.OffloadedOutput;
import java.nio.file.Path;
import java.time.LocalDateTime;

// OffloadedOutput record
public record OffloadedOutput(
    Path filePath,                // 卸载文件路径
    String toolName,              // 产生此输出的工具名
    String toolCallId,            // 工具调用 ID
    int originalSize,             // 原始输出大小（字符）
    String preview,               // 预览内容（保留在上下文中）
    String summary,               // 可选摘要
    LocalDateTime createdAt,      // 创建时间
    String sessionId              // 所属会话 ID
) {}
```

### 使用示例

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.core.OffloadConfig;

// 配置卸载
OffloadConfig offloadConfig = OffloadConfig.builder()
    .sizeThresholdChars(10000)    // 超过 10KB 的输出将被卸载
    .maxOutputsPerSession(20)     // 每会话最多 20 个卸载文件
    .previewLength(300)           // 保留 300 字符预览
    .build();

HarnessConfig config = HarnessConfig.builder()
    .offload(offloadConfig)
    .build();
AgentHarness agent = new AgentHarness(config);

// 正常使用 - 大型输出会自动卸载
LoopResult result = agent.run("读取并分析所有源代码文件").join();
```

### 卸载后的上下文引用

当输出被卸载后，上下文中会包含类似以下的引用：

```
[Output from read_file (15000 chars)]
Preview: #!/usr/bin/env python3
"""Main module..."""
Full output saved to: .harness/offload/session_abc123_read_file_call_456.txt
```

**注意**：卸载文件默认存储在当前工作目录的 `.harness/offload/` 下，确保 sandbox 可以访问。LLM 可以根据需要使用 Read 工具加载完整内容。

## Step Budget（步骤预算）

步骤预算控制每个任务的迭代次数和工具调用次数，防止无限循环或过度消耗资源。与 CostController（基于 Token）不同，StepBudget 基于"步骤"计数。

### StepBudgetConfig

```java
import com.harness.core.StepBudgetConfig;

// StepBudgetConfig 使用 Builder 模式
StepBudgetConfig config = StepBudgetConfig.builder()
    .maxIterationsPerTask(50)        // 每任务最大迭代次数
    .maxToolCallsPerStep(10)         // 每步（单次 LLM 响应）最大工具调用数
    .maxToolCallsPerTask(200)        // 每任务最大工具调用总数
    .warningThreshold(0.8)           // 警告阈值（使用率）
    .criticalThreshold(0.95)         // 临界阈值（使用率）
    .actionOnExceed("stop")          // 超限动作：stop | warn | throttle
    .throttleRatio(0.5)              // 节流时使用的剩余预算比例
    .build();
```

### BudgetLevel

```java
import com.harness.core.BudgetLevel;

// BudgetLevel 枚举
public enum BudgetLevel {
    NORMAL,       // 正常范围内
    WARNING,      // 接近限制（>= warning_threshold）
    CRITICAL,     // 临近限制（>= critical_threshold）
    EXCEEDED      // 超出限制（>= 1.0）
}
```

### 使用示例

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.core.StepBudgetConfig;

// 配置步骤预算
StepBudgetConfig budgetConfig = StepBudgetConfig.builder()
    .maxIterationsPerTask(30)        // 最多 30 次迭代
    .maxToolCallsPerStep(5)          // 每次 LLM 响应最多 5 个工具调用
    .maxToolCallsPerTask(100)        // 总共最多 100 次工具调用
    .actionOnExceed("stop")          // 超限时停止
    .build();

// 通过 HarnessConfig 配置
// 注意：StepBudget 配置在 HarnessConfig 中通过 LoopConfig 字段控制
LoopConfig loopConfig = LoopConfig.builder()
    .maxIterations(30)
    .build();

AgentHarness agent = AgentHarness.builder().build();

// 执行任务 - 预算会在每次迭代和工具调用前检查
LoopResult result = agent.run("分析代码库并生成报告").join();
```

### 预算检查时机

1. **每次迭代前**：检查迭代次数是否超限
2. **每次工具调用前**：检查工具调用次数是否超限
3. **每步工具调用限制**：防止单次 LLM 响应触发过多工具调用

### 超限动作

| 动作 | 行为 |
|------|------|
| `stop` | 立即停止执行，返回错误 |
| `warn` | 记录警告但继续执行 |
| `throttle` | 启用节流模式，限制后续工具调用数量 |

## Cost Controller（成本控制）

Agent Loop 内置成本控制机制，防止意外的高额 API 费用。

```java
import com.harness.core.HarnessConfig;
import com.harness.core.HarnessConfig.CostControlConfig;

// 成本控制通过 HarnessConfig.CostControlConfig 配置
CostControlConfig costConfig = CostControlConfig.builder()
    .maxTokensPerSession(1_000_000)      // 每会话最大 token 数
    .maxToolCallsPerSession(500)          // 每会话最大工具调用数
    .maxIterationsPerRequest(20)          // 每请求最大迭代数
    .dailyTokenLimit(10_000_000)          // 每日 token 限额
    .globalDailyBudgetUsd(100.0)          // 全局每日预算（美元）
    .autoThrottle(true)                   // 自动节流
    .build();

HarnessConfig config = HarnessConfig.builder()
    .costControl(costConfig)
    .build();

AgentHarness agent = new AgentHarness(config);
```

### BudgetStatus

```java
import com.harness.core.BudgetStatus;
import com.harness.types.TokenUsage;

// BudgetStatus record
public record BudgetStatus(
    boolean isWithinBudget,          // 是否在预算内
    TokenUsage usage,                // token 使用统计
    String warningMessage,           // 警告信息
    boolean shouldCompress,          // 是否应该压缩上下文
    boolean shouldDowngrade,         // 是否应该降级模型
    double usageRatio                // 使用率（0.0-1.0）
) {
    // 检查是否处于警告状态
    public boolean isWarning() {
        return warningMessage != null && isWithinBudget;
    }

    // 预算内剩余 token 数
    public int remainingTokens(int maxTokensPerSession) {
        return Math.max(0, maxTokensPerSession - usage.totalTokens());
    }

    // 预算内剩余工具调用次数
    public int remainingToolCalls(int maxToolCallsPerSession) {
        return Math.max(0, maxToolCallsPerSession - usage.toolCalls());
    }
}
```

## 流式输出

Agent Loop 支持流式输出，允许逐步接收 LLM 的响应。

```java
// Java SDK 使用 CompletableFuture 进行异步操作
// 流式输出通过 progress callback 实现
AgentHarness agent = AgentHarness.builder().build();

// 使用 progress callback 接收流式输出
agent.run("分析这段代码", null, chunk -> {
    System.out.print(chunk);  // 逐步输出
}).join();
```

流式输出遵循背压控制：如果消费者处理速度慢于生产速度，LLM 读取会被自动暂停。

## 错误处理

### 重试策略

| 错误类型 | 处理方式 |
|----------|----------|
| API 限流 (429) | 指数退避重试 |
| API 错误 (5xx) | 重试最多 `retry_on_error` 次（默认 3） |
| 工具执行错误 | 返回错误信息给 LLM |
| 上下文超长 | 触发压缩或截断 |
| 成本超限 | 中断并返回结果 |

### LLM 重试策略

Agent Loop 使用配置化的重试策略，支持指数退避和随机抖动：

```java
// 重试次数从配置读取
int maxLlmRetries = config.retryOnError();  // 默认 3

// 重试延迟策略（内部实现）
long delay;
if (decision.delaySeconds() > 0) {
    // 优先使用 ErrorHandler 返回的延迟（如 rate limit 的 Retry-After）
    delay = decision.delaySeconds();
} else {
    // 指数退避 + 随机抖动（防止重试风暴）
    long baseBackoff = Math.min((long) Math.pow(2, llmAttempt), 30);  // 上限 30s
    double jitter = Math.random() * 0.5;                              // 随机抖动
    delay = baseBackoff + (long) jitter;
}
```

**设计原则**：
- 配置化：重试次数可通过 `LoopConfig.retry_on_error` 调整
- ErrorHandler 优先：尊重 API 返回的重试建议（如 Retry-After header）
- 指数退避：避免短时间大量重试
- 随机抖动：防止多客户端同时重试（惊群效应）

### 熔断器

熔断器用于检测和防止无限循环，遵循 **Bitter Lesson** 原则：简单规则优于复杂启发式。

**检测机制**：
- 只检测"相同工具 + 相同参数"重复调用
- 默认阈值：`same_args_threshold = 3`（调用 3 次触发熔断）
- 不检测复杂的序列模式（避免误报）

```java
import com.harness.core.CircuitBreaker;
import com.harness.core.CircuitBreakerConfig;

// 默认配置
CircuitBreaker cb = new CircuitBreaker();

// 自定义阈值
CircuitBreakerConfig cbConfig = CircuitBreakerConfig.builder()
    .sameArgsThreshold(3)           // 相同工具+参数重复次数
    .errorThreshold(5)              // 错误次数阈值
    .errorWindowSeconds(60)         // 错误统计窗口
    .recoveryTimeoutSeconds(30)     // 恢复超时
    .build();
CircuitBreaker customCb = new CircuitBreaker(cbConfig);

// 记录调用
Map<String, Object> args = Map.of("path", "test.txt");
customCb.recordCall("read", args);

// 检查状态
if (customCb.isOpen()) {
    System.out.println("熔断器已打开: " + customCb.getReason());
}
```

**设计原则**：
1. **简单规则**：只检测明显的重复行为
2. **信任模型**：通过 system prompt 指导模型何时停止
3. **避免误报**：不干预并行工具调用等正常行为

### 工具执行超时

Agent Loop 使用 `asyncio.wait_for` 强制执行工具超时，防止病态工具阻塞整个执行：

```java
import com.harness.types.ToolResult;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

// 工具执行超时保护（Java SDK 内部使用 CompletableFuture）
// AgentHarness 配置中通过 LoopConfig.timeoutPerTool 控制
LoopConfig config = LoopConfig.builder()
    .timeoutPerTool(30000L)  // 默认 30000ms (30s)
    .build();

// 内部实现类似：
try {
    ToolResult result = tool.execute(args, context)
        .get(30, TimeUnit.SECONDS);  // 超时等待
} catch (TimeoutException e) {
    // 超时后返回错误结果
    ToolResult result = ToolResult.failure(
        toolCallId,
        "Tool execution timed out after 30s",
        toolName
    );
}
```

**配置**：
- `LoopConfig.timeout_per_tool`: 单个工具的超时时间（默认 30.0 秒）

**注意**：超时后工具执行会被取消，Agent 会收到错误信息并可以决定下一步操作。

### Step Budget 资源清理

Agent Loop 使用 `finally` 块确保 `StepBudgetController.end_task()` 总是被调用，防止资源泄漏：

```java
// 确保 step_budget 在任何情况下都被清理（Java SDK 内部实现）
// AgentHarness 使用 try-finally 确保资源清理
try {
    // 主循环...
    while (iteration < config.maxIterations()) {
        // ... 执行循环
    }
} finally {
    // 无论成功、失败、中断，都确保清理
    if (stepBudget != null) {
        try {
            stepBudget.endTask();
        } catch (Exception e) {
            logger.error("Error while ending step budget task", e);
        }
    }
}
```

**设计原则**：
- 资源清理必须放在 `finally` 块中
- 清理操作本身需要捕获异常，避免掩盖原始错误

---

## 上下文压缩（Context Compression）

当对话历史超过 token 预算时，Harness 自动压缩上下文以保持响应能力。

### 压缩触发条件

```
estimated_tokens > budget.available_for_input * compression_threshold
```

默认阈值：`compression_threshold = 0.9`（90% 容量时触发）

### 压缩流程

```
1. 检测：ContextBuilder 估算当前 token 数
2. 触发：超过阈值时启动压缩
3. 压缩：ContextCompressor 保留最近消息，生成旧消息摘要
4. 合并：摘要合并到 system prompt（确保 chat template 正确）
5. 返回：[system(prompt + summary), user, assistant, ...]
```

### 关键设计：避免 system 消息冲突

**问题**：vLLM 等推理引擎的 chat template 要求 system 消息必须在开头。错误做法：

```
[system(real_prompt), system(compression_summary), user, assistant, ...]  ❌
```

**解决方案**：压缩器只返回摘要字符串，由 ContextBuilder 合并到真正的 system prompt：

```
[system(real_prompt + summary), user, assistant, ...]  ✅
```

### ContextBuilder 压缩集成

**Python SDK**：

```java
import com.harness.memory.ContextBuilder;

// 创建带压缩功能的 ContextBuilder
ContextBuilder builder = new ContextBuilder()
    .withMaxTokens(200000)
    .withCompressionEnabled(true);

// 构建上下文（自动压缩）
BuiltContext context = builder.build(session);
// context.systemPrompt() - 系统提示（含压缩摘要）
// context.messages() - 压缩后的消息列表
// context.compressionResult() - 压缩详情（如有）
```

**Java SDK**：

```java
import com.harness.memory.ContextBuilder;

// 创建带压缩功能的 ContextBuilder（使用链式调用）
ContextBuilder builder = new ContextBuilder()
    .withMaxTokens(200000)
    .withCompressionEnabled(true);
// 注意：compressionThreshold 需要通过 ContextConfig 设置

// 构建上下文
BuiltContext context = builder.build(session);
// context.systemPrompt() - 系统提示（含压缩摘要）
// context.messages() - 压缩后的消息列表
// context.compressionResult() - 压缩详情
```

### AgentLoop 配置

通过 `LoopConfig` 配置上下文窗口和压缩：

**Python SDK**：

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LoopConfig;

// Java SDK 通过 LoopConfig 配置上下文窗口和压缩
LoopConfig config = LoopConfig.builder()
    .contextWindow(200000)       // 上下文窗口大小
    .sessionWindow(100)          // 会话滑动窗口
    .enableCompression(true)     // 启用压缩（默认 true）
    .build();

AgentHarness agent = AgentHarness.builder()
    .loopConfig(config)
    .build();
```

**Java SDK**：

```java
import com.harness.core.LoopConfig;

LoopConfig config = LoopConfig.builder()
    .contextWindow(200000)       // 上下文窗口
    .sessionWindow(100)          // 滑动窗口
    .enableCompression(true)     // 启用压缩
    .build();
```

### LoopConfig 新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `contextWindow` | `int` | `200000` | 上下文窗口 token 数 |
| `sessionWindow` | `int` | `100` | 会话滑动窗口消息数 |
| `enableCompression` | `boolean` | `true` | 启用自动压缩 |
| `systemPrompt` | `String` | `""` | 基础系统提示 |

### 压缩摘要格式

压缩生成的摘要包含：

```text
[Previous conversation summary]

### User Requests
- User asked: What is the project structure?
- User asked: Analyze the authentication flow

### Key Actions
- Assistant: Read file src/auth/login.py
- Assistant: Identified OAuth2 implementation

### Tools Used
- Tool: read
- Tool: grep
```

摘要合并到 system prompt 后，Agent 可以理解之前的对话内容，同时释放大量 token 空间。

---

## 完整流程图

```
用户输入
    │
    ↓
┌─────────────────────────────────────────────────┐
│ ON_LOOP_START Hook                               │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Context Builder                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ 1. 加载系统提示（SystemPromptBuilder）       │ │
│ │ 2. 加载技能（ProgressiveSkillLoader）        │ │
│ │ 3. 加载记忆（MemoryManager）                 │ │
│ │ 4. 组装 AGENTS.md（如有）                    │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Agent Loop                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │              Loop Body                       │ │
│ │                                              │ │
│ │  ┌─────────────┐                            │ │
│ │  │BEFORE_LLM_ │                            │ │
│ │  │CALL Hook    │                            │ │
│ │  │Hook         │                            │ │
│ │  └──────┬──────┘                            │ │
│ │         ↓                                   │ │
│ │  ┌───────────┐    ┌───────────┐            │ │
│ │  │   LLM     │───→│AFTER_LLM_ │            │ │
│ │  │   Call    │    │CALL Hook  │            │ │
│ │  └───────────┘    │           │            │ │
│ │                    └─────┬─────┘            │ │
│ │                          ↓                  │ │
│ │              ┌───────────────────┐          │ │
│ │              ↓                   ↓          │ │
│ │        ┌──────────┐      ┌──────────┐      │ │
│ │        │Tool Call │      │  Finish  │      │ │
│ │        │          │      │          │      │ │
│ │        └────┬─────┘      └────┬─────┘      │ │
│ │             ↓                 │            │ │
│ │  ┌──────────────┐             │            │ │
│ │  │BEFORE_TOOL_ │             │            │ │
│ │  │EXECUTE Hook │             │            │ │
│ │  └──────┬───────┘             │            │ │
│ │         ↓                     │            │ │
│ │  ┌──────────┐                 │            │ │
│ │  │ Execute  │                 │            │ │
│ │  │  Tool    │                 │            │ │
│ │  └────┬─────┘                 │            │ │
│ │       ↓                       │            │ │
│ │  ┌───────────────┐            │            │ │
│ │  │AFTER_TOOL_   │            │            │ │
│ │  │EXECUTE Hook  │            │            │ │
│ │  └───────┬───────┘            │            │ │
│ │          │                    │            │ │
│ │          ↓                    ↓            │ │
│ │     Back to LLM          ┌──────────┐      │ │
│ │                          │ON_EXIT_  │      │ │
│ │                          │ATTEMPT   │      │ │
│ │                          │Hook      │      │ │
│ │                          └──────────┘      │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│  熔断器 | 卡住检测 | 成本控制                     │
└─────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────────────┐
│ Memory Update                                    │
└─────────────────────────────────────────────────┘
    │
    ↓
LoopResult
```

## 下一步

- [04-tool-system.md](./04-tool-system.md) - 了解工具系统
- [05-memory-system.md](./05-memory-system.md) - 了解记忆系统
- [18-loop-engineering.md](./18-loop-engineering.md) - 了解 Loop Engineering 目标驱动执行
- [07-sdk-api.md](./07-sdk-api.md) - 查看 SDK API
