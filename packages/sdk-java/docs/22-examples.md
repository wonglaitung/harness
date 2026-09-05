# 12 - 示例代码

## 概述

本文档提供 Harness SDK 的完整使用示例，涵盖从基础用法到高级功能的各种场景。

## 基础用法

### 最简 Agent

```java
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;

public class BasicAgentExample {
    public static void main(String[] args) throws Exception {
        AgentHarness agent = AgentHarness.builder().build();
        LoopResult result = agent.run("你好，请介绍一下你自己").join();
        System.out.println(result.content());
    }
}
```

### 使用 OpenAI 模型

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;

HarnessConfig config = HarnessConfig.builder()
    .apiKey("sk-...")
    .model("gpt-4o")
    .provider("openai")
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();
LoopResult result = agent.run("分析这段代码的性能问题").join();
```

### 使用第三方 OpenAI 兼容 API

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;

HarnessConfig config = HarnessConfig.builder()
    .baseUrl("https://api.your-provider.com/v1")
    .apiKey("your-api-key")
    .model("your-model-name")
    // provider auto-detected as openai (since not claude-* prefix)
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();
LoopResult result = agent.run("翻译以下文本为英文").join();
```

### 流式输出

```java
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;

AgentHarness agent = AgentHarness.builder().build();

LoopResult result = agent.run("写一篇关于 AI 的短文").join();
System.out.println(result.content());
```

### 从配置文件创建

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;

HarnessConfig config = HarnessConfig.fromEnv();
AgentHarness agent = AgentHarness.builder().config(config).build();
LoopResult result = agent.run("检查项目状态").join();
```

## 自定义工具

### 装饰器注册

```java
import com.harness.integration.AgentHarness;
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.types.ToolResult;
import com.harness.types.LoopResult;
import java.util.Map;

public class WeatherTool implements Tool {
    private final String city;

    public WeatherTool(String city) { this.city = city; }

    @Override public String getName() { return "get_weather"; }
    @Override public String getDescription() { return "获取指定城市的天气"; }
    @Override
    public Map<String, Object> inputSchema() {
        return Map.of("type", "object", "properties",
            Map.of("city", Map.of("type", "string", "description", "城市名")));
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        String city = (String) args.getOrDefault("city", "default");
        return CompletableFuture.completedFuture(
            ToolResult.success(ctx.sessionId(), city + ": 晴天, 25°C", getName()));
    }
}

AgentHarness agent = AgentHarness.builder()
    .addTool(new WeatherTool("北京"))
    .build();

LoopResult result = agent.run("查一下北京天气").join();
```

### 继承 Tool 类

```java
import com.harness.integration.AgentHarness;
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.types.ToolResult;
import com.harness.types.LoopResult;
import java.util.Map;

public class DatabaseTool implements Tool {

    @Override public String getName() { return "db_query"; }

    @Override public String getDescription() { return "执行数据库查询"; }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "query", Map.of("type", "string", "description", "SQL 查询"),
                "database", Map.of("type", "string", "description", "数据库名")),
            "required", java.util.List.of("query"));
    }

    @Override public boolean isDangerous() { return true; }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        try {
            String database = (String) args.getOrDefault("database", "default");
            String query = (String) args.get("query");
            String result = executeSql(database, query);
            return CompletableFuture.completedFuture(
                ToolResult.success(ctx.sessionId(), String.valueOf(result), getName()));
        } catch (Exception e) {
            return CompletableFuture.completedFuture(
                ToolResult.failure(ctx.sessionId(), e.getMessage(), getName()));
        }
    }

    private String executeSql(String database, String query) {
        // 实际实现调用数据库
        return "query result";
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.registerTool(new DatabaseTool());
```

## Lifecycle Hooks

### 请求审批

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import java.util.List;
import java.util.Scanner;

public class ApprovalHook implements LifecycleHook {

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext ctx) {
        // 危险操作需要用户确认
        if ("bash".equals(ctx.toolName()) || "write".equals(ctx.toolName())) {
            String command = "bash".equals(ctx.toolName())
                ? (String) ctx.toolArgs().getOrDefault("command", "")
                : String.valueOf(ctx.toolArgs());
            System.out.println("Agent 想要执行 " + ctx.toolName() + ": " + command);
            Scanner scanner = new Scanner(System.in);
            System.out.print("允许？(y/n): ");
            String confirm = scanner.nextLine();
            if (!"y".equalsIgnoreCase(confirm)) {
                return HookResult.abort("用户拒绝了操作");
            }
        }
        return HookResult.continue_();
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new ApprovalHook());
LoopResult result = agent.run("删除临时文件").join();
```

### 日志记录

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.List;

public class LoggingHook implements LifecycleHook {
    private static final Logger logger = LoggerFactory.getLogger(LoggingHook.class);

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.AFTER_LLM_CALL, HookPoint.AFTER_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext ctx) {
        if (ctx.hookPoint() == HookPoint.AFTER_LLM_CALL && ctx.llmResponse() != null) {
            logger.info("LLM 调用: {} 输入 tokens, {} 输出 tokens",
                ctx.llmResponse().usage().inputTokens(),
                ctx.llmResponse().usage().outputTokens());
        } else if (ctx.hookPoint() == HookPoint.AFTER_TOOL_EXECUTE && ctx.toolResult() != null) {
            logger.info("工具 {}: {} 字符", ctx.toolName(),
                ctx.toolResult().content() != null ? ctx.toolResult().content().length() : 0);
        }
        return HookResult.continue_();
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new LoggingHook());
```

### 阻止过早退出

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LifecycleHook;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.types.Message;
import java.util.List;

public class PreventEarlyExitHook implements LifecycleHook {

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.ON_EXIT_ATTEMPT);
    }

    @Override
    public HookResult execute(HookContext ctx) {
        // 如果任务未完成，阻止 Agent 草率退出
        if (ctx.messages() != null && !ctx.messages().isEmpty()) {
            Message lastMsg = ctx.messages().get(ctx.messages().size() - 1);
            if (lastMsg.contentAsString() != null && !lastMsg.contentAsString().contains("完成")) {
                // 注入消息让 Agent 继续工作
                return HookResult.injectMessage(
                    Message.user("请继续完成任务，不要提前结束。"));
            }
        }
        return HookResult.continue_();
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new PreventEarlyExitHook());
```

## 自验证

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HookPoint;
import com.harness.core.LifecycleHook;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.types.LoopResult;
import java.util.List;

public class AutoVerifyHook implements LifecycleHook {
    private final AgentHarness agent;
    private final String verifyCommand;
    private final int maxRetries;

    public AutoVerifyHook(AgentHarness agent, String verifyCommand, int maxRetries) {
        this.agent = agent;
        this.verifyCommand = verifyCommand;
        this.maxRetries = maxRetries;
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.AFTER_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext ctx) {
        // 写文件后自动运行测试
        if ("write".equals(ctx.toolName())) {
            // 执行验证命令
            for (int i = 0; i < maxRetries; i++) {
                try {
                    Process process = Runtime.getRuntime().exec(verifyCommand);
                    int exitCode = process.waitFor();
                    if (exitCode == 0) {
                        return HookResult.continue_();
                    }
                } catch (Exception e) {
                    // 继续重试
                }
            }
            return HookResult.injectMessage(
                Message.user("测试失败，请修复并重试。"));
        }
        return HookResult.continue_();
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.addHook(new AutoVerifyHook(agent, "pytest -x", 3));
LoopResult result = agent.run("实现一个计算器类并确保测试通过").join();
```

## Ralph Loop（长任务）

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import java.util.concurrent.CompletableFuture;

AgentHarness agent = AgentHarness.builder().build();

// 使用 GoalConfig 执行长任务
GoalConfig config = GoalConfig.builder()
    .description("重构整个认证模块，添加 OAuth2 支持，确保所有测试通过")
    .maxIterations(100)
    .timeoutSeconds(3600)
    .build();

GoalResult result = agent.runGoal(config, null).join();
System.out.println("完成步数: " + result.totalIterations());
System.out.println("总成本: $" + String.format("%.4f",
    result.totalTokens().getOrDefault("input", 0) * 0.00001));
```

## Sub-Agent

```java
import com.harness.integration.AgentHarness;
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.loop.types.GoalResult;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

AgentHarness agent = AgentHarness.builder().build();
SubAgentManager subAgentManager = new SubAgentManager();

// 并行执行多个子任务
CompletableFuture<Map<String, GoalResult>> future1 = CompletableFuture.supplyAsync(() -> {
    GoalConfig config = GoalConfig.builder()
        .description("分析代码质量")
        .maxIterations(5)
        .build();
    GoalResult result = agent.runGoal(config, null).join();
    return Map.of("analysis", result);
});

CompletableFuture<Map<String, GoalResult>> future2 = CompletableFuture.supplyAsync(() -> {
    GoalConfig config = GoalConfig.builder()
        .description("检查安全漏洞")
        .maxIterations(5)
        .build();
    GoalResult result = agent.runGoal(config, null).join();
    return Map.of("security", result);
});

CompletableFuture.allOf(future1, future2).join();

Map<String, GoalResult> results1 = future1.join();
Map<String, GoalResult> results2 = future2.join();

for (Map.Entry<String, GoalResult> entry : results1.entrySet()) {
    System.out.println("任务: " + entry.getKey());
    System.out.println("成功: " + entry.getValue().achieved());
    System.out.println("结果: " + entry.getValue().finalResponse());
}
```

## 技能系统

### 使用技能

```java
import com.harness.skills.SkillLoader;
import com.harness.skills.SkillRegistry;
import java.nio.file.Path;

// 加载技能目录
SkillLoader loader = new SkillLoader();
SkillRegistry registry = new SkillRegistry();
registry.addSkillDir(Path.of(".harness/skills"));

// 列出可用技能
registry.listSkills().forEach(skill ->
    System.out.println(skill.name() + ": " + skill.description())
);
```

### 创建技能文件

```markdown
---
name: code-review
description: Review code for issues and improvements
tools: [read, grep, glob]
priority: 10
---

# Code Review Skill

You are an expert code reviewer. Your task is to:
1. Read the code files carefully
2. Identify bugs, security issues, and performance problems
3. Provide actionable suggestions with specific fixes

## Guidelines
- Focus on correctness first, then performance
- Always check for security vulnerabilities
- Provide concrete fix suggestions, not just complaints
- Rate severity: Critical / Warning / Info
```

## MCP 集成

### 使用 MCP 服务器

```java
import com.harness.integration.AgentHarness;
import com.harness.mcp.McpServerConfig;
import com.harness.types.LoopResult;
import java.util.Map;

AgentHarness agent = AgentHarness.builder().build();

// 创建 MCP 服务器配置
McpServerConfig githubConfig = McpServerConfig.builder()
    .name("github")
    .transport("stdio")
    .command("mcp-github")
    .env(Map.of("GITHUB_TOKEN", "your-token-here"))
    .build();
agent.addMcpServer(githubConfig);

McpServerConfig slackConfig = McpServerConfig.builder()
    .name("slack")
    .transport("stdio")
    .command("mcp-slack")
    .args(java.util.List.of("--token", "$SLACK_TOKEN"))
    .env(Map.of("SLACK_TOKEN", "your-slack-token"))
    .build();
agent.addMcpServer(slackConfig);

// 连接所有服务器
agent.connectAllMcpServers();

LoopResult result = agent.run("查看最近的 GitHub issue 并在 Slack 通知团队").join();
```

### 自定义 LLM 客户端

```java
import com.harness.integration.AgentHarness;
import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.TokenUsage;
import com.harness.types.LoopResult;
import java.util.List;
import java.util.Map;

public class MyCustomLLM implements LLMClient {

    @Override public String modelName() { return "my-custom-model"; }

    @Override
    public CompletableFuture<LLMResponse> call(
            List<Map<String, Object>> messages,
            List<Map<String, Object>> tools,
            String system) {
        // 实现自定义 LLM 调用逻辑
        String responseText = callMyApi(messages, tools, system);
        return CompletableFuture.completedFuture(
            new LLMResponse(responseText, null,
                new TokenUsage(0, 0), "end_turn"));
    }

    private String callMyApi(List<Map<String, Object>> messages,
                             List<Map<String, Object>> tools,
                             String system) {
        // 自定义 API 调用实现
        return "custom response";
    }
}

AgentHarness agent = AgentHarness.builder()
    .llmClient(new MyCustomLLM())
    .build();
LoopResult result = agent.run("你好").join();
```

## 触发器

### Cron 触发

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.automation.Automation;
import com.harness.loop.automation.AutomationConfig;

AgentHarness agent = AgentHarness.builder().build();

// 每天 9:00 生成日报
Automation dailyReport = Automation.builder()
    .name("daily-report")
    .schedule("0 9 * * *")
    .goal("生成昨日工作日报，包括完成的任务和待处理的事项")
    .build();

dailyReport.start(new com.harness.loop.GoalLoop.AgentRunner() {
    @Override
    public CompletableFuture<com.harness.types.LoopResult> run(String prompt, String sessionId) {
        return agent.run(prompt, sessionId);
    }
    @Override
    public CompletableFuture<com.harness.types.LoopResult> run(String prompt, String sessionId,
            java.util.function.Consumer<Object> progress) {
        return agent.run(prompt, sessionId, progress);
    }
    @Override
    public com.harness.types.Session getSession(String sessionId) {
        return agent.getOrCreateSession(sessionId);
    }
    @Override
    public int getContextWindow() {
        return agent.getConfig().getContextWindow();
    }
}).join();
```

### Webhook 触发

```java
import com.harness.integration.AgentHarness;
import com.harness.triggers.TriggerAction;
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerManager;

AgentHarness agent = AgentHarness.builder().build();
TriggerManager triggerManager = new TriggerManager();

// Webhook 触发器配置（通过 HTTP 端点接收事件）
TriggerAction action = TriggerAction.builder()
    .goal("审查 PR #{event.pull_request.number}")
    .skills(java.util.List.of("code-review"))
    .build();

CronTrigger githubTrigger = CronTrigger.builder()
    .name("github-pr")
    .action(action)
    .build();

triggerManager.register(githubTrigger, true);
```

## 安全配置

### 最小权限

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .maxIterations(10)
    .enableNetwork(false)
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();
```

### 成本控制

```java
import com.harness.core.HarnessConfig;
import com.harness.core.HarnessConfig.CostControlConfig;

// 使用 CostControlConfig 进行成本控制
HarnessConfig config = HarnessConfig.builder()
    .maxIterations(30)
    .costControl(CostControlConfig.builder()
        .maxTokensPerSession(500000)
        .globalDailyBudgetUsd(5.0)
        .build())
    .build();

AgentHarness agent = AgentHarness.builder()
    .config(config)
    .build();
```

## FastAPI 集成

```java
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

@RestController
public class AiController {

    private final AgentHarness agent = AgentHarness.builder().build();

    @PostMapping("/ai")
    public ResponseEntity<Map<String, String>> aiEndpoint(@RequestParam String message) {
        LoopResult result = agent.run(message).join();
        return ResponseEntity.ok(Map.of("response", result.content()));
    }

    @PostMapping("/ai/stream")
    public ResponseEntity<Map<String, String>> aiStreamEndpoint(@RequestParam String message) {
        LoopResult result = agent.run(message).join();
        return ResponseEntity.ok(Map.of("response", result.content()));
    }
}
```

## 测试

```java
import com.harness.core.MockHarness;
import com.harness.core.MockResponse;
import java.util.Map;

// 简单 mock
MockHarness mock = new MockHarness();
mock.addResponse(MockResponse.text("分析完成"));
MockHarness.MockLoopResult result = mock.run("分析代码").join();
assert result.finalResponse().equals("分析完成");

// 多步工具调用
mock.reset();
mock.addResponse(MockResponse.toolUse("call_1", "read", Map.of("path", "src/Main.java")));
mock.addResponse(MockResponse.text("代码质量良好"));
result = mock.run("分析代码").join();
assert result.finalResponse().equals("代码质量良好");
```

## 全局记忆

### 配置全局记忆文件

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.types.LoopResult;
import java.nio.file.Path;

// 配置全局 MEMORY.md 文件路径
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .memoryMdPath(Path.of(System.getProperty("user.home"), ".harness", "MEMORY.md").toString())
    .build();

AgentHarness agent = AgentHarness.builder().config(config).build();

// Agent 会自动加载全局记忆到 system prompt
LoopResult result = agent.run("帮我重构这段代码").join();
```

### 全局记忆文件格式

```markdown
# MEMORY.md

## User Profile
- 使用 Windows 操作系统
- 偏好 Python 语言
- 使用 VS Code 编辑器

## Key Decisions
- 2024-01-15: 选择 SQLite 作为会话存储

## Learned Patterns
- 用户喜欢详细的代码示例
- 用户偏好中文回复

## Project Context
- 项目使用 Python 3.11+
- 代码风格遵循 Black 格式化
```

### 即时更新特性

全局记忆文件在每次 `run()` 调用时重新读取，修改后立即生效：

```java
import com.harness.integration.AgentHarness;
import com.harness.memory.MemoryFileManager;
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import com.harness.types.LoopResult;
import java.nio.file.Path;

AgentHarness agent = AgentHarness.builder().build();

// 第一次调用 - 加载当前记忆
LoopResult result1 = agent.run("分析项目结构").join();

// 更新记忆文件
MemoryFileManager manager = new MemoryFileManager(
    Path.of(System.getProperty("user.home"), ".harness"));
manager.addEntry(new MemoryEntry(
    MemoryCategory.USER_PROFILE,
    "偏好简洁的代码注释",
    MemorySource.USER_INPUT));

// 第二次调用 - 自动加载更新后的记忆
LoopResult result2 = agent.run("添加函数注释").join();
```

## Loop Engineering

Loop Engineering 是目标驱动执行范式：用户描述目标，Agent 自主运行直到完成。

### 基础用法：目标驱动执行

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;

AgentHarness agent = AgentHarness.builder().build();

// 用户描述目标，Agent 自主运行直到完成
GoalResult result = agent.runGoal(
    "修复 src/ 目录下所有类型错误",
    null).join();

if (result.status() == GoalStatus.ACHIEVED) {
    System.out.println("目标达成！共 " + result.totalIterations() + " 轮迭代");
} else if (result.status() == GoalStatus.MAX_ITERATIONS) {
    System.out.println("达到最大迭代次数 " + result.totalIterations());
} else {
    System.out.println("目标未达成: " + result.status().getValue());
}
```

### 自定义验证器

使用自定义函数验证目标是否达成：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import java.util.function.Function;

// 自定义验证器：检查测试覆盖率是否达到 80%
Function<GoalResult, Boolean> checkCoverage = result -> {
    try {
        Process process = Runtime.getRuntime().exec(
            new String[]{"pytest", "--cov", "--cov-report=term"});
        int exitCode = process.waitFor();
        // 解析覆盖率报告
        return exitCode == 0;
    } catch (Exception e) {
        return false;
    }
};

AgentHarness agent = AgentHarness.builder().build();

GoalResult result = agent.runGoal(
    goal -> "将测试覆盖率提升到 80%",
    null).join();

// 使用 GoalConfig 的完整配置
GoalConfig config = GoalConfig.builder()
    .description("将测试覆盖率提升到 80%")
    .customVerifier(checkCoverage)
    .maxIterations(50)
    .build();

GoalResult result2 = agent.runGoal(config, null).join();
System.out.println("状态: " + result2.status().getValue());
System.out.println("迭代次数: " + result2.totalIterations());
```

### GoalConfig 完整配置

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;

AgentHarness agent = AgentHarness.builder().build();

GoalConfig config = GoalConfig.builder()
    .description("实现用户认证模块")
    .successCriteria("所有测试通过，覆盖率 >= 80%")
    .workspaceDir("./src/auth")

    // 迭代控制
    .maxIterations(50)
    .maxContextResets(5)
    .timeoutSeconds(3600)

    // 成本控制
    .maxTokens(500000)
    .maxCostUsd(10.0)
    .build();

GoalResult result = agent.runGoal(config, null).join();
```

### 定时自动化 (Phase 2)

使用 Automation 创建定时任务：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.automation.Automation;
import com.harness.loop.types.GoalResult;
import java.util.concurrent.CompletableFuture;

AgentHarness agent = AgentHarness.builder().build();

// Cron 定时任务：每天 9:00 生成日报
Automation dailyReport = Automation.builder()
    .name("daily-report")
    .schedule("0 9 * * *")
    .goal("分析昨日 Git 提交，生成工作日报")
    .build();

// 间隔任务：每 5 分钟健康检查
Automation healthCheck = Automation.builder()
    .name("health-check")
    .intervalSeconds(300)
    .goal("检查系统健康状态，如有异常发送告警")
    .build();

// 启动自动化
dailyReport.start(null).join();
healthCheck.start(null).join();

System.out.println("自动化任务已启动，按 Ctrl+C 停止");
try {
    Thread.sleep(3600000); // 运行 1 小时
} finally {
    dailyReport.stop().join();
    healthCheck.stop().join();
}
```

### 并行 Worktree 执行 (Phase 3)

在隔离的 worktree 中并行执行多个目标：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.worktree.WorktreeOrchestrator;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeResult;
import com.harness.loop.types.GoalResult;
import java.util.Map;
import java.util.List;

AgentHarness agent = AgentHarness.builder().build();

// 创建 AgentRunner 适配器
GoalLoop.AgentRunner agentRunner = new GoalLoop.AgentRunner() {
    @Override
    public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
        return agent.run(prompt, sessionId);
    }
    @Override
    public CompletableFuture<LoopResult> run(String prompt, String sessionId,
            Consumer<Object> progress) {
        return agent.run(prompt, sessionId, progress);
    }
    @Override
    public Session getSession(String sessionId) {
        return agent.getOrCreateSession(sessionId);
    }
    @Override
    public int getContextWindow() {
        return agent.getConfig().getContextWindow();
    }
};

WorktreeOrchestrator orchestrator = new WorktreeOrchestrator(agentRunner, ".");

// 定义并行任务
List<WorktreeConfig> tasks = List.of(
    WorktreeConfig.builder()
        .name("feature-auth")
        .goal("实现用户认证功能")
        .baseBranch("main")
        .build(),
    WorktreeConfig.builder()
        .name("feature-api")
        .goal("实现 REST API 端点")
        .baseBranch("main")
        .build(),
    WorktreeConfig.builder()
        .name("feature-tests")
        .goal("编写集成测试")
        .baseBranch("main")
        .build());

// 并行执行
Map<String, WorktreeResult> results = orchestrator.runParallel(tasks).join();

// 查看结果
for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
    System.out.println(entry.getKey() + ": " + entry.getValue().getStatus());
}

// 合并成功的分支
for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
    if ("completed".equals(entry.getValue().getStatus())) {
        orchestrator.merge(entry.getKey());
        System.out.println("已合并: " + entry.getKey());
    }
}
```

### 指标监控

监控 Goal 执行的详细指标：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;

AgentHarness agent = AgentHarness.builder().build();

GoalResult result = agent.runGoal(
    "重构数据库访问层",
    null).join();

// 详细指标
System.out.println("状态: " + result.status().getValue());
System.out.println("迭代次数: " + result.totalIterations());
System.out.println("上下文重置: " + result.contextResets());
System.out.println("Token 使用: " + result.totalTokens());
System.out.println("执行时长: " + String.format("%.1f", result.durationSeconds()) + "秒");

// 验证日志
for (com.harness.loop.types.VerificationRecord record : result.verificationLog()) {
    System.out.println("  第" + record.iteration() + "轮: " + record.result().getValue());
    if (record.reason() != null) {
        System.out.println("    原因: " + record.reason());
    }
}
```

### 错误处理

处理各种执行状态：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;

AgentHarness agent = AgentHarness.builder().build();
GoalResult result = agent.runGoal("复杂任务", null).join();

switch (result.status()) {
    case ACHIEVED:
        System.out.println("目标达成");
        break;
    case TIMEOUT:
        System.out.println("超时，已运行 " + result.durationSeconds() + "秒");
        break;
    case MAX_ITERATIONS:
        System.out.println("达到最大迭代次数，建议增加 maxIterations");
        break;
    case MAX_RESETS:
        System.out.println("上下文重置次数过多，任务可能过于复杂");
        break;
    case ERROR:
        System.out.println("执行错误: " + result.error());
        break;
    case VERIFIER_FAULT:
        System.out.println("验证器故障，请检查 customVerifier 实现");
        break;
    case CANCELLED:
        System.out.println("用户取消");
        break;
}
```

### 工作流编排

组合多个目标形成工作流：

```java
import com.harness.integration.AgentHarness;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;

public class CodeReviewWorkflow {

    public static GoalResult codeReviewWorkflow(AgentHarness agent) {
        // Step 1: 静态分析
        GoalResult result1 = agent.runGoal(
            "运行静态分析，找出代码问题", null).join();
        if (result1.status() != GoalStatus.ACHIEVED) {
            return result1;
        }

        // Step 2: 修复问题
        GoalResult result2 = agent.runGoal(
            "修复所有发现的代码问题", null).join();
        if (result2.status() != GoalStatus.ACHIEVED) {
            return result2;
        }

        // Step 3: 运行测试
        GoalResult result3 = agent.runGoal(
            "确保所有测试通过", null).join();

        return result3;
    }

    public static void main(String[] args) {
        AgentHarness agent = AgentHarness.builder().build();
        GoalResult result = codeReviewWorkflow(agent);
        System.out.println("工作流完成: " + result.status().getValue());
    }
}
```
