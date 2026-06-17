# 04 - 工具系统 (Java 实现)

## 概述

工具系统是 Harness SDK 的核心组件，允许 Agent 与外部环境交互。本文档详细说明 Java 版本的工具系统设计。

## 工具接口

### 核心接口

```java
package com.harness.tools;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 工具接口 - 所有工具必须实现此接口。
 */
public interface Tool {

    /**
     * 工具名称（唯一标识）。
     */
    String name();

    /**
     * 工具描述（用于 LLM 理解工具用途）。
     */
    String description();

    /**
     * 输入参数 Schema (JSON Schema 格式)。
     */
    Map<String, Object> inputSchema();

    /**
     * 执行工具。
     *
     * @param args 输入参数
     * @param context 执行上下文
     * @return 执行结果
     */
    CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context);

    /**
     * 验证参数（可选实现）。
     *
     * @param args 输入参数
     * @return 验证结果
     */
    default ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }

    /**
     * 是否为危险工具。
     */
    default boolean isDangerous() {
        return false;
    }

    /**
     * 工具分类。
     */
    default ToolCategory category() {
        return ToolCategory.GENERAL;
    }
}
```

### 执行上下文

```java
package com.harness.tools;

/**
 * 工具执行上下文。
 */
public record ToolContext(
    String sessionId,           // 会话 ID
    String workingDirectory,    // 工作目录
    int iteration,              // 当前迭代次数
    TokenUsage tokenUsage,      // Token 使用统计
    SandboxExecutor sandbox,    // 沙箱执行器（可选）
    Map<String, Object> metadata // 额外元数据
) {

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String sessionId;
        private String workingDirectory = System.getProperty("user.dir");
        private int iteration = 0;
        private TokenUsage tokenUsage = new TokenUsage(0, 0);
        private SandboxExecutor sandbox;
        private Map<String, Object> metadata = Map.of();

        // Builder 方法...
    }
}
```

### 执行结果

```java
package com.harness.tools;

/**
 * 工具执行结果。
 */
public record ToolResult(
    boolean success,            // 是否成功
    String output,              // 输出内容
    String error,               // 错误信息（如果失败）
    Map<String, Object> metadata // 额外元数据
) {

    public static ToolResult success(String output) {
        return new ToolResult(true, output, null, Map.of());
    }

    public static ToolResult success(String output, Map<String, Object> metadata) {
        return new ToolResult(true, output, null, metadata);
    }

    public static ToolResult failure(String error) {
        return new ToolResult(false, null, error, Map.of());
    }

    public static ToolResult failure(String error, Map<String, Object> metadata) {
        return new ToolResult(false, null, error, metadata);
    }
}
```

## 内置工具

### ReadTool

```java
package com.harness.tools.builtin;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 文件读取工具。
 */
public class ReadTool implements Tool {

    public static final String NAME = "read";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "读取文件内容。支持文本文件和图像文件。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "要读取的文件绝对路径"
                ),
                "offset", Map.of(
                    "type", "integer",
                    "description", "起始行号（可选）",
                    "default", 0
                ),
                "limit", Map.of(
                    "type", "integer",
                    "description", "读取行数（可选）",
                    "default", 2000
                )
            ),
            "required", List.of("file_path")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String filePath = (String) args.get("file_path");
            int offset = args.containsKey("offset") ? ((Number) args.get("offset")).intValue() : 0;
            int limit = args.containsKey("limit") ? ((Number) args.get("limit")).intValue() : 2000;

            try {
                Path path = Path.of(filePath);

                // 安全检查
                if (!path.isAbsolute()) {
                    return ToolResult.failure("必须使用绝对路径");
                }

                if (!Files.exists(path)) {
                    return ToolResult.failure("文件不存在: " + filePath);
                }

                // 检测文件类型
                String contentType = Files.probeContentType(path);
                if (contentType != null && contentType.startsWith("image/")) {
                    return readImage(path);
                }

                // 读取文本文件
                List<String> lines = Files.readAllLines(path);
                int endLine = Math.min(offset + limit, lines.size());

                StringBuilder sb = new StringBuilder();
                for (int i = offset; i < endLine; i++) {
                    sb.append(String.format("%6d\t%s%n", i + 1, lines.get(i)));
                }

                if (endLine < lines.size()) {
                    sb.append(String.format("%n... 省略 %d 行 ...", lines.size() - endLine));
                }

                return ToolResult.success(sb.toString());

            } catch (IOException e) {
                return ToolResult.failure("读取文件失败: " + e.getMessage());
            }
        });
    }

    private ToolResult readImage(Path path) throws IOException {
        byte[] bytes = Files.readAllBytes(path);
        String base64 = Base64.getEncoder().encodeToString(bytes);
        String mediaType = Files.probeContentType(path);
        return ToolResult.success(
            "data:" + mediaType + ";base64," + base64,
            Map.of("is_image", true)
        );
    }
}
```

### WriteTool

```java
package com.harness.tools.builtin;

/**
 * 文件写入工具。
 */
public class WriteTool implements Tool {

    public static final String NAME = "write";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "写入文件内容。会覆盖已存在的文件。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "要写入的文件绝对路径"
                ),
                "content", Map.of(
                    "type", "string",
                    "description", "要写入的内容"
                )
            ),
            "required", List.of("file_path", "content")
        );
    }

    @Override
    public boolean isDangerous() {
        return true;  // 写入操作是危险的
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String filePath = (String) args.get("file_path");
            String content = (String) args.get("content");

            try {
                Path path = Path.of(filePath);

                // 安全检查
                if (!path.isAbsolute()) {
                    return ToolResult.failure("必须使用绝对路径");
                }

                // 创建父目录
                Files.createDirectories(path.getParent());

                // 写入文件
                Files.writeString(path, content);

                return ToolResult.success("文件已写入: " + filePath);

            } catch (IOException e) {
                return ToolResult.failure("写入文件失败: " + e.getMessage());
            }
        });
    }
}
```

### EditTool

```java
package com.harness.tools.builtin;

/**
 * 文件编辑工具。
 */
public class EditTool implements Tool {

    public static final String NAME = "edit";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "编辑文件，替换指定的文本内容。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "要编辑的文件绝对路径"
                ),
                "old_string", Map.of(
                    "type", "string",
                    "description", "要替换的文本（必须唯一匹配）"
                ),
                "new_string", Map.of(
                    "type", "string",
                    "description", "替换后的文本"
                ),
                "replace_all", Map.of(
                    "type", "boolean",
                    "description", "是否替换所有匹配",
                    "default", false
                )
            ),
            "required", List.of("file_path", "old_string", "new_string")
        );
    }

    @Override
    public boolean isDangerous() {
        return true;
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String filePath = (String) args.get("file_path");
            String oldString = (String) args.get("old_string");
            String newString = (String) args.get("new_string");
            boolean replaceAll = args.containsKey("replace_all") && (boolean) args.get("replace_all");

            try {
                Path path = Path.of(filePath);
                String content = Files.readString(path);

                // 检查匹配
                int count = countMatches(content, oldString);
                if (count == 0) {
                    return ToolResult.failure("未找到匹配的文本");
                }
                if (count > 1 && !replaceAll) {
                    return ToolResult.failure("找到 " + count + " 处匹配，请使用更具体的文本或设置 replace_all=true");
                }

                // 执行替换
                String newContent = replaceAll
                    ? content.replace(oldString, newString)
                    : content.replaceFirst(Pattern.quote(oldString), Matcher.quoteReplacement(newString));

                Files.writeString(path, newContent);

                return ToolResult.success(String.format("已替换 %d 处匹配", replaceAll ? count : 1));

            } catch (IOException e) {
                return ToolResult.failure("编辑文件失败: " + e.getMessage());
            }
        });
    }

    private int countMatches(String text, String pattern) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(pattern, index)) != -1) {
            count++;
            index += pattern.length();
        }
        return count;
    }
}
```

### BashTool

```java
package com.harness.tools.builtin;

/**
 * Shell 命令执行工具。
 */
public class BashTool implements Tool {

    public static final String NAME = "bash";

    private final boolean sandboxMode;
    private final SandboxExecutor sandbox;

    public BashTool(boolean sandboxMode) {
        this.sandboxMode = sandboxMode;
        this.sandbox = sandboxMode ? new SandboxExecutor() : null;
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "执行 Shell 命令。" + (sandboxMode ? "（沙箱模式）" : "");
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "command", Map.of(
                    "type", "string",
                    "description", "要执行的命令"
                ),
                "timeout", Map.of(
                    "type", "integer",
                    "description", "超时时间（毫秒）",
                    "default", 120000
                )
            ),
            "required", List.of("command")
        );
    }

    @Override
    public boolean isDangerous() {
        return true;
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.SYSTEM;
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String command = (String) args.get("command");
        long timeout = args.containsKey("timeout")
            ? ((Number) args.get("timeout")).longValue()
            : 120000;

        if (sandboxMode) {
            return sandbox.execute(command, timeout);
        } else {
            return executeDirectly(command, timeout, context.workingDirectory());
        }
    }

    private CompletableFuture<ToolResult> executeDirectly(String command, long timeout, String workDir) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                ProcessBuilder pb = new ProcessBuilder("bash", "-c", command);
                pb.directory(new File(workDir));
                pb.redirectErrorStream(true);

                Process process = pb.start();

                boolean finished = process.waitFor(timeout, TimeUnit.MILLISECONDS);
                if (!finished) {
                    process.destroyForcibly();
                    return ToolResult.failure("命令执行超时");
                }

                String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);

                if (process.exitValue() == 0) {
                    return ToolResult.success(output);
                } else {
                    return ToolResult.failure("命令执行失败 (exit code: " + process.exitValue() + ")\n" + output);
                }

            } catch (Exception e) {
                return ToolResult.failure("命令执行异常: " + e.getMessage());
            }
        });
    }
}
```

### GlobTool

```java
package com.harness.tools.builtin;

/**
 * 文件模式匹配工具。
 */
public class GlobTool implements Tool {

    public static final String NAME = "glob";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "使用 glob 模式搜索文件。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "pattern", Map.of(
                    "type", "string",
                    "description", "Glob 模式，如 **/*.java"
                ),
                "path", Map.of(
                    "type", "string",
                    "description", "搜索目录（可选，默认当前目录）"
                )
            ),
            "required", List.of("pattern")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String pattern = (String) args.get("pattern");
            String basePath = args.containsKey("path")
                ? (String) args.get("path")
                : context.workingDirectory();

            try {
                PathMatcher matcher = FileSystems.getDefault().getPathMatcher("glob:" + pattern);
                List<String> matches = new ArrayList<>();

                Files.walkFileTree(Path.of(basePath), new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        if (matcher.matches(file.getFileName())) {
                            matches.add(file.toString());
                        }
                        return FileVisitResult.CONTINUE;
                    }
                });

                // 按修改时间排序
                matches.sort((a, b) -> {
                    try {
                        return -Files.getLastModifiedTime(Path.of(a))
                            .compareTo(Files.getLastModifiedTime(Path.of(b)));
                    } catch (IOException e) {
                        return 0;
                    }
                });

                return ToolResult.success(String.join("\n", matches));

            } catch (IOException e) {
                return ToolResult.failure("搜索失败: " + e.getMessage());
            }
        });
    }
}
```

### GrepTool

```java
package com.harness.tools.builtin;

/**
 * 内容搜索工具。
 */
public class GrepTool implements Tool {

    public static final String NAME = "grep";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "使用正则表达式搜索文件内容。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "pattern", Map.of(
                    "type", "string",
                    "description", "正则表达式模式"
                ),
                "path", Map.of(
                    "type", "string",
                    "description", "搜索目录或文件"
                ),
                "glob", Map.of(
                    "type", "string",
                    "description", "文件过滤模式（如 *.java）"
                ),
                "ignore_case", Map.of(
                    "type", "boolean",
                    "description", "忽略大小写",
                    "default", false
                )
            ),
            "required", List.of("pattern")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String pattern = (String) args.get("pattern");
            String basePath = args.containsKey("path")
                ? (String) args.get("path")
                : context.workingDirectory();
            String glob = args.containsKey("glob") ? (String) args.get("glob") : null;
            boolean ignoreCase = args.containsKey("ignore_case") && (boolean) args.get("ignore_case");

            try {
                Pattern regex = ignoreCase
                    ? Pattern.compile(pattern, Pattern.CASE_INSENSITIVE)
                    : Pattern.compile(pattern);

                List<String> results = new ArrayList<>();
                Path rootPath = Path.of(basePath);

                Files.walkFileTree(rootPath, new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        // 检查 glob 过滤
                        if (glob != null) {
                            PathMatcher matcher = FileSystems.getDefault().getPathMatcher("glob:" + glob);
                            if (!matcher.matches(file.getFileName())) {
                                return FileVisitResult.CONTINUE;
                            }
                        }

                        try {
                            List<String> lines = Files.readAllLines(file);
                            for (int i = 0; i < lines.size(); i++) {
                                if (regex.matcher(lines.get(i)).find()) {
                                    results.add(String.format("%s:%d:%s",
                                        file, i + 1, lines.get(i)));
                                }
                            }
                        } catch (IOException e) {
                            // 忽略无法读取的文件
                        }

                        return FileVisitResult.CONTINUE;
                    }
                });

                return ToolResult.success(String.join("\n", results));

            } catch (Exception e) {
                return ToolResult.failure("搜索失败: " + e.getMessage());
            }
        });
    }
}
```

## 工具执行器

```java
package com.harness.tools;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * 工具执行器 - 负责调度和执行工具。
 */
public class ToolExecutor {

    private final Map<String, Tool> tools;
    private final ExecutorService executor;
    private final long defaultTimeout;

    public ToolExecutor(List<Tool> tools, long defaultTimeout) {
        this.tools = new HashMap<>();
        for (Tool tool : tools) {
            this.tools.put(tool.name(), tool);
        }
        this.executor = Executors.newCachedThreadPool();
        this.defaultTimeout = defaultTimeout;
    }

    /**
     * 执行单个工具。
     */
    public CompletableFuture<ToolResult> execute(ToolCall call, ToolContext context) {
        Tool tool = tools.get(call.name());
        if (tool == null) {
            return CompletableFuture.completedFuture(
                ToolResult.failure("未知工具: " + call.name())
            );
        }

        // 验证参数
        ValidationResult validation = tool.validate(call.arguments());
        if (!validation.valid()) {
            return CompletableFuture.completedFuture(
                ToolResult.failure("参数验证失败: " + validation.error())
            );
        }

        // 执行（带超时）
        return tool.execute(call.arguments(), context)
            .orTimeout(defaultTimeout, TimeUnit.MILLISECONDS)
            .exceptionally(e -> ToolResult.failure("执行超时或异常: " + e.getMessage()));
    }

    /**
     * 并行执行多个工具。
     */
    public CompletableFuture<List<ToolResult>> executeAll(List<ToolCall> calls, ToolContext context) {
        List<CompletableFuture<ToolResult>> futures = calls.stream()
            .map(call -> execute(call, context))
            .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
            .thenApply(v -> futures.stream()
                .map(CompletableFuture::join)
                .toList());
    }

    /**
     * 获取所有工具。
     */
    public List<Tool> listTools() {
        return new ArrayList<>(tools.values());
    }

    /**
     * 注册新工具。
     */
    public void registerTool(Tool tool) {
        tools.put(tool.name(), tool);
    }
}
```

## 自定义工具

### 实现自定义工具

```java
/**
 * 自定义工具示例：数据库查询工具。
 */
public class DatabaseQueryTool implements Tool {

    private final DataSource dataSource;

    public DatabaseQueryTool(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public String name() {
        return "db_query";
    }

    @Override
    public String description() {
        return "执行只读 SQL 查询。";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "sql", Map.of(
                    "type", "string",
                    "description", "SELECT 语句"
                )
            ),
            "required", List.of("sql")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.DATABASE;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        String sql = (String) args.get("sql");
        if (sql == null || sql.isBlank()) {
            return ValidationResult.invalid("SQL 不能为空");
        }

        // 安全检查：只允许 SELECT
        String upperSql = sql.trim().toUpperCase();
        if (!upperSql.startsWith("SELECT")) {
            return ValidationResult.invalid("只允许 SELECT 查询");
        }

        // 检查危险操作
        String[] dangerousKeywords = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"};
        for (String keyword : dangerousKeywords) {
            if (upperSql.contains(keyword)) {
                return ValidationResult.invalid("SQL 包含禁止的操作: " + keyword);
            }
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String sql = (String) args.get("sql");

            try (Connection conn = dataSource.getConnection();
                 Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(sql)) {

                // 转换为 JSON
                List<Map<String, Object>> rows = new ArrayList<>();
                ResultSetMetaData meta = rs.getMetaData();
                int columnCount = meta.getColumnCount();

                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= columnCount; i++) {
                        row.put(meta.getColumnLabel(i), rs.getObject(i));
                    }
                    rows.add(row);
                }

                ObjectMapper mapper = new ObjectMapper();
                return ToolResult.success(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(rows));

            } catch (Exception e) {
                return ToolResult.failure("查询失败: " + e.getMessage());
            }
        });
    }
}
```

### 使用装饰器模式

```java
/**
 * 工具装饰器 - 添加日志功能。
 */
public class LoggingToolDecorator implements Tool {

    private final Tool delegate;
    private final Logger logger;

    public LoggingToolDecorator(Tool delegate, Logger logger) {
        this.delegate = delegate;
        this.logger = logger;
    }

    @Override
    public String name() {
        return delegate.name();
    }

    @Override
    public String description() {
        return delegate.description();
    }

    @Override
    public Map<String, Object> inputSchema() {
        return delegate.inputSchema();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        logger.info("执行工具: {} 参数: {}", name(), args);

        long startTime = System.currentTimeMillis();

        return delegate.execute(args, context)
            .thenApply(result -> {
                long duration = System.currentTimeMillis() - startTime;
                logger.info("工具执行完成: {} 耗时: {}ms 结果: {}",
                    name(), duration, result.success() ? "成功" : "失败");
                return result;
            })
            .exceptionally(e -> {
                logger.error("工具执行异常: {}", name(), e);
                return ToolResult.failure(e.getMessage());
            });
    }
}

// 使用
Tool tool = new LoggingToolDecorator(new ReadTool(), logger);
```

## 工具分类

```java
package com.harness.tools;

/**
 * 工具分类。
 */
public enum ToolCategory {
    FILE_SYSTEM,    // 文件系统操作
    SYSTEM,         // 系统命令
    DATABASE,       // 数据库操作
    NETWORK,        // 网络请求
    MCP,            // MCP 工具
    GENERAL,        // 通用工具
    CUSTOM          // 自定义工具
}
```

## 下一步

- [05-memory-system.md](./05-memory-system.md) - 了解记忆系统
- [06-mcp-integration.md](./06-mcp-integration.md) - 了解 MCP 工具集成
