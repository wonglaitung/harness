# 03 - 工具系统详解

## 概述

工具系统让 LLM 能够"动手操作"——读取文件、执行命令、搜索代码、访问网络。工具系统是 Agent 能力的核心扩展机制。

## 架构

```
┌─────────────────────────────────────────────────┐
│                 Tool System                      │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐              │
│  │  Tool Base  │  │Tool Registry │              │
│  │  (抽象类)    │  │  (注册管理)   │              │
│  └──────┬──────┘  └──────┬───────┘              │
│         │                │                       │
│         ↓                ↓                       │
│  ┌─────────────────────────────────────────┐    │
│  │           Tool Executor                  │    │
│  │  ┌──────────┐  ┌───────────────────┐    │    │
│  │  │ Sequential│  │ Batch (Parallel)  │    │    │
│  │  │ Execute  │  │ Execute           │    │    │
│  │  └──────────┘  └───────────────────┘    │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │          Built-in Tools (9)              │    │
│  │  Read │ Write │ Edit │ Glob │ Grep      │    │
│  │  Bash │ WebSearch │ WebFetch            │    │
│  │  WebToMarkdown                           │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │        Custom + MCP Tools                │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Tool 基类

```java
import com.harness.core.Tool;
import com.harness.types.ToolResult;
import com.harness.core.ToolContext;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// Tool interface (all tools implement this)
public interface Tool {
    String name();                                        // 工具名称（LLM 可见）
    String description();                                 // 工具描述（LLM 可见）
    Map<String, Object> inputSchema();                    // 参数 JSON Schema
    CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx); // 执行工具并返回结果
    default ValidationResult validate(Map<String, Object> args) { return ValidationResult.valid(); }
    default boolean isDangerous() { return false; }       // 是否为危险工具
    default ToolCategory category() { return ToolCategory.GENERAL; }
}
```

### ToolResult

```java
import com.harness.types.ToolResult;
import java.util.Map;

// ToolResult record
public record ToolResult(
    String toolCallId,              // 工具调用ID（用于匹配LLM调用）
    boolean success,                // 是否成功执行
    String content,                 // 工具输出内容
    String error,                   // 错误信息（可为 null）
    String toolName,                // 工具名称
    Map<String, Object> metadata    // 附加元数据
) {
    // 工厂方法
    public static ToolResult success(String toolCallId, String content) { ... }
    public static ToolResult success(String toolCallId, String content, String toolName) { ... }
    public static ToolResult failure(String toolCallId, String error) { ... }
    public static ToolResult failure(String toolCallId, String error, String toolName) { ... }

    // 转换为API格式供LLM使用
    public Map<String, Object> toApiFormat() {
        return Map.of(
            "type", "tool_result",
            "tool_use_id", toolCallId,
            "content", success ? content : "Error: " + error,
            "is_error", !success
        );
    }
}
```

### ToolContext

```java
import com.harness.core.ToolContext;
import java.util.Map;

// ToolContext record
public record ToolContext(
    String sessionId,                       // 会话 ID
    String workingDirectory,                // 当前工作目录
    int iteration,                          // 当前迭代次数
    Map<String, Object> metadata            // 附加上下文
) {
    // 工厂方法
    public static ToolContext of(String workingDirectory, String sessionId) { ... }
    public static Builder builder() { ... }
}
```

### PermissionLevel

```java
// PermissionLevel is not a separate enum in Java SDK.
// Instead, tools declare danger level via isDangerous() and category() methods.
// ToolCategory enum: GENERAL, FILE_SYSTEM, SYSTEM, NETWORK
public enum ToolCategory {
    GENERAL,
    FILE_SYSTEM,
    SYSTEM,
    NETWORK
}
```

## 内置工具

### Read - 文件读取

```java
import com.harness.tools.ReadTool;

// ReadTool - 文件读取
// 参数:
//   file_path: String - 文件路径（必需）
//   offset: int - 起始行号（可选，默认 0）
//   limit: int - 读取行数（可选，默认 2000）
ReadTool tool = new ReadTool();
System.out.println(tool.name());        // "read"
System.out.println(tool.description()); // "Read file contents. Supports text files and image files."
```

### Write - 文件写入

```java
import com.harness.tools.WriteTool;

// WriteTool - 文件写入
// 参数:
//   file_path: String - 文件路径（必需）
//   content: String - 文件内容（必需）
WriteTool tool = new WriteTool();
System.out.println(tool.name());        // "write"
System.out.println(tool.isDangerous()); // true
```

### Edit - 文件编辑

```java
import com.harness.tools.EditTool;

// EditTool - 文件编辑
// 参数:
//   file_path: String - 文件路径（必需）
//   old_string: String - 要替换的字符串（必需）
//   new_string: String - 替换后的字符串（必需）
//   replace_all: boolean - 是否替换所有匹配（默认 false）
EditTool tool = new EditTool();
System.out.println(tool.name());        // "edit"
System.out.println(tool.isDangerous()); // true
```

### Glob - 文件搜索

```java
import com.harness.tools.GlobTool;

// GlobTool - 文件搜索
// 参数:
//   pattern: String - glob 模式（必需）
//   path: String - 搜索目录（可选）
GlobTool tool = new GlobTool();
System.out.println(tool.name()); // "glob"
```

### Grep - 内容搜索

```java
import com.harness.tools.GrepTool;

// GrepTool - 内容搜索
// 参数:
//   pattern: String - 正则表达式（必需）
//   path: String - 搜索路径（可选）
//   include: String - 文件名过滤，如 "*.java"（可选）
//   output_mode: String - "content" | "files_with_matches" | "count"
GrepTool tool = new GrepTool();
System.out.println(tool.name()); // "grep"
```

### Bash - 命令执行

```java
import com.harness.tools.BashTool;

// BashTool - 命令执行
// 参数:
//   command: String - 要执行的命令（必需）
//   timeout: long - 超时时间（毫秒，默认 120000）
BashTool tool = new BashTool(true); // sandboxMode = true
System.out.println(tool.name());        // "bash"
System.out.println(tool.isDangerous()); // true
```

### WebSearch - 网络搜索

```java
import com.harness.tools.WebSearchTool;

// WebSearchTool - 网络搜索
// 参数:
//   query: String - 搜索查询（必需）
//   max_results: int - 最大结果数（默认 5）
WebSearchTool tool = new WebSearchTool();
System.out.println(tool.name()); // "web_search"
```

### WebFetch - 网页获取

```java
import com.harness.tools.WebFetchTool;

// WebFetchTool - 网页获取
// 参数:
//   url: String - URL（必需）
//   format: String - "text" | "markdown" | "html"
WebFetchTool tool = new WebFetchTool();
System.out.println(tool.name()); // "web_fetch"
```

### WebToMarkdown - 网页转 Markdown

```java
import com.harness.tools.WebToMarkdownTool;

// WebToMarkdownTool - 网页转 Markdown
// 参数:
//   url: String - 网页 URL（必需）
//   selector: String - CSS 选择器提取特定内容（可选）
//   max_length: int - 最大内容长度（默认 50000）
//   include_links: boolean - 是否保留链接（默认 true）
//   include_images: boolean - 是否包含图片引用（默认 false）
WebToMarkdownTool tool = new WebToMarkdownTool();
System.out.println(tool.name()); // "web_to_markdown"
```

## Browser Automation Tools

浏览器自动化工具，使用 Playwright 提供确定性的浏览器操作能力。适用于金融/银行等需要精确控制的场景。

### Java SDK Browser Tools

```java
import com.harness.tools.browser.*;

// 创建浏览器工具
List<Tool> browserTools = List.of(
    new BrowserNavigateTool(),
    new BrowserClickTool(),
    new BrowserTypeTool(),
    new BrowserReadTool(),
    new BrowserScreenshotTool()
);

AgentHarness agent = AgentHarness.builder()
    .tools(browserTools)
    .build();
```

### 可用工具

| 工具 | 功能 | 参数 |
|-----|------|------|
| `BrowserNavigateTool` | 导航到 URL | `url` |
| `BrowserClickTool` | 点击元素 | `selector` |
| `BrowserTypeTool` | 输入文本 | `selector`, `text` |
| `BrowserReadTool` | 读取页面内容 | `selector` (可选) |
| `BrowserScreenshotTool` | 截图保存 | `filename` (可选) |
| `BrowserWaitTool` | 等待元素 | `selector`, `timeout` |

### System Browser 支持（内网环境）

Java SDK 支持使用系统已安装的浏览器，无需下载 Playwright 自带的浏览器。适合内网/离线环境。

```java
import com.harness.tools.browser.BrowserManager;

// 自动检测系统浏览器（Edge > Chrome > Chromium）
if (BrowserManager.useSystemBrowser()) {
    System.out.println("已配置系统浏览器");
}

// 或手动指定
BrowserManager.configure("msedge");  // Microsoft Edge
BrowserManager.configure("chrome");   // Google Chrome
```

### 配置选项

```java
BrowserManager.configure(builder -> builder
    .browserType("msedge")      // 浏览器类型
    .headless(false)            // 是否无头模式
    .defaultTimeout(30000)      // 默认超时（毫秒）
    .autoScreenshot(true)       // 自动截图
    .screenshotDir("./screenshots")  // 截图目录
);
```

### 使用示例

```java
// 1. 导航到页面
await agent.run("打开 https://example.com");

// 2. 登录银行网站
await agent.run("""
    1. 打开 https://bank.example.com
    2. 在用户名输入框输入 myuser
    3. 在密码输入框输入 mypass
    4. 点击登录按钮
    """);

// 3. 读取数据
await agent.run("读取账户余额表格");
```

### 安全考虑

浏览器工具具有 `PermissionLevel.DANGEROUS` 级别，需要用户确认或配置白名单：

```java
HarnessConfig config = HarnessConfig.builder()
    .allowDangerousTools(true)  // 允许危险工具
    .browserWhitelist(List.of(
        "https://internal.company.com",
        "https://bank.company.com"
    ))
    .build();
```

详见 [08-security.md](./08-security.md)。

## ToolExecutor

ToolExecutor 负责工具的调度和执行，支持串行和并行模式。

```java
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.types.ToolResult;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// ToolExecutor is managed internally by AgentHarness.
// Tools are registered and executed through AgentHarness.
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();

// Register tools
agent.registerTool(new ReadTool());
agent.registerTool(new BashTool());

// Tools are executed automatically during agent.run()
LoopResult result = agent.run("Read file src/Main.java").join();
```

### 执行流程

```
Tool Call(s)
    │
    ↓
┌─────────────┐
│ 权限检查     │ → 拒绝 → 返回 ToolResult(error="Permission denied")
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ 参数验证     │ → 失败 → 返回 ToolResult(error="Invalid arguments")
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│ 单个调用 → execute  │
│ 多个调用 → batch   │  （并行执行独立调用）
└──────┬──────────────┘
       │
       ↓
┌─────────────┐
│ 沙箱执行     │ → 超时 → 返回 ToolResult(error="Timeout")
└──────┬──────┘
       │
       ↓
   ToolResult
```

## 自定义工具

### 方式 1：继承 Tool 类

```java
import com.harness.core.Tool;
import com.harness.types.ToolResult;
import com.harness.core.ToolContext;
import com.harness.integration.AgentHarness;
import java.util.Map;
import java.util.List;
import java.util.concurrent.CompletableFuture;

// 自定义工具：DatabaseQueryTool
public class DatabaseQueryTool implements Tool {
    @Override
    public String name() { return "db_query"; }

    @Override
    public String description() { return "执行数据库查询"; }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "query", Map.of("type", "string", "description", "SQL 查询"),
                "database", Map.of("type", "string", "description", "数据库名")
            ),
            "required", List.of("query")
        );
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        String query = (String) args.get("query");
        String db = args.containsKey("database") ? (String) args.get("database") : "default";
        try {
            String result = executeSql(db, query);  // 自定义实现
            return CompletableFuture.completedFuture(
                ToolResult.success(ctx.sessionId(), String.valueOf(result), name())
            );
        } catch (Exception e) {
            return CompletableFuture.completedFuture(
                ToolResult.failure(ctx.sessionId(), e.getMessage(), name())
            );
        }
    }
}

// 注册
AgentHarness agent = AgentHarness.builder().build();
agent.registerTool(new DatabaseQueryTool());
```

### 方式 2：装饰器

```java
import com.harness.core.Tool;
import com.harness.types.ToolResult;
import com.harness.core.ToolContext;
import com.harness.integration.AgentHarness;
import java.util.Map;
import java.util.List;
import java.util.concurrent.CompletableFuture;

// Java SDK uses explicit Tool classes (no decorators).
// Create tools by implementing the Tool interface:

// 示例：自定义工具类
public class AddTool implements Tool {
    @Override public String name() { return "add"; }
    @Override public String description() { return "计算两个数的和"; }
    @Override public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "a", Map.of("type", "integer"),
                "b", Map.of("type", "integer")
            ),
            "required", List.of("a", "b")
        );
    }
    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        int a = ((Number) args.get("a")).intValue();
        int b = ((Number) args.get("b")).intValue();
        return CompletableFuture.completedFuture(
            ToolResult.success(ctx.sessionId(), String.valueOf(a + b), name())
        );
    }
}

AgentHarness agent = AgentHarness.builder().build();
agent.registerTool(new AddTool());
```

## 工具与 MCP 的关系

内置工具和 MCP 工具统一通过 ToolExecutor 调度：

| 工具来源 | 注册方式 | 权限控制 |
|----------|----------|----------|
| 内置工具 | 自动注册 | 按 PermissionLevel |
| 自定义工具 | `register_tool()` | 按 PermissionLevel |
| MCP 工具 | MCP 服务器自动注册 | 按 MCP 配置 |

```java
import com.harness.integration.AgentHarness;
import com.harness.mcp.McpServerConfig;

// MCP 工具和内置工具统一使用
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();

// 添加 MCP 服务器
agent.addMcpServer(McpServerConfig.builder()
    .name("github")
    .command("mcp-github")
    .build());

// LLM 可以同时调用内置工具和 MCP 工具
LoopResult result = agent.run("搜索代码中的 TODO 并在 GitHub 创建 issue").join();
```

## 下一步

- [05-memory-system.md](./05-memory-system.md) - 了解记忆系统
- [08-security.md](./08-security.md) - 了解安全设计和浏览器工具权限
- [16-skills-system.md](./16-skills-system.md) - 了解技能系统
- [06-mcp-integration.md](./06-mcp-integration.md) - MCP 协议集成
