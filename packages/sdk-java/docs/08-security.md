# 08 - 安全设计 (Java 实现)

## 概述

安全是 Harness SDK 的核心设计原则，特别是在银行等敏感环境中。本文档详细说明 Java 版本的安全设计。

## 安全架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Architecture                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Input Validation                      │ │
│  │  - 长度限制                                            │ │
│  │  - 内容检测 (注入攻击、敏感数据)                        │ │
│  │  - 格式验证                                            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Sandbox Execution                     │ │
│  │  - 文件系统隔离                                        │ │
│  │  - 命令限制                                            │ │
│  │  - 网络隔离                                            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Output Sanitization                   │ │
│  │  - 敏感数据脱敏                                        │ │
│  │  - 日志清理                                            │ │
│  │  - 错误信息过滤                                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Audit Logging                         │ │
│  │  - 操作记录                                            │ │
│  │  - Token 使用统计                                      │ │
│  │  - 安全事件追踪                                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## SecurityConfig

```java
package com.harness.security;

/**
 * 安全配置。
 */
public record SecurityConfig(
    boolean enableInputValidation,      // 启用输入验证
    boolean enableOutputSanitization,   // 启用输出清理
    boolean enableAuditLog,            // 启用审计日志
    boolean enableSandbox,             // 启用沙箱
    int maxInputLength,                // 最大输入长度
    int maxOutputLength,               // 最大输出长度
    String auditLogDir,               // 审计日志目录
    int auditRetentionDays,           // 审计日志保留天数
    List<String> forbiddenKeywords,   // 禁止关键词
    List<SanitizationRule> sanitizationRules // 脱敏规则
) {

    public static Builder builder() {
        return new Builder();
    }

    public static SecurityConfig defaults() {
        return builder().build();
    }

    public static SecurityConfig banking() {
        return builder()
            .enableInputValidation(true)
            .enableOutputSanitization(true)
            .enableAuditLog(true)
            .enableSandbox(true)
            .maxInputLength(10000)
            .maxOutputLength(50000)
            .auditRetentionDays(90)
            .forbiddenKeywords(List.of(
                "DROP TABLE", "DELETE FROM", "TRUNCATE",
                "EXEC(", "EVAL(", "<SCRIPT>"
            ))
            .build();
    }

    public static class Builder {
        private boolean enableInputValidation = true;
        private boolean enableOutputSanitization = true;
        private boolean enableAuditLog = false;
        private boolean enableSandbox = true;
        private int maxInputLength = 50000;
        private int maxOutputLength = 100000;
        private String auditLogDir = "/var/log/harness/audit";
        private int auditRetentionDays = 30;
        private List<String> forbiddenKeywords = List.of();
        private List<SanitizationRule> sanitizationRules = List.of();

        // Builder 方法...
    }
}
```

## 输入验证

### InputValidator 接口

```java
package com.harness.security;

import java.util.List;
import java.util.regex.Pattern;

/**
 * 输入验证器。
 */
public interface InputValidator {

    /**
     * 验证输入。
     */
    ValidationResult validate(String input);
}

/**
 * 默认输入验证器。
 */
public class DefaultInputValidator implements InputValidator {

    private final SecurityConfig config;
    private final List<Pattern> dangerousPatterns;

    public DefaultInputValidator(SecurityConfig config) {
        this.config = config;

        // 预编译危险模式
        this.dangerousPatterns = List.of(
            // SQL 注入
            Pattern.compile("(?i)(DROP|DELETE|TRUNCATE|ALTER|CREATE)\\s+(TABLE|DATABASE)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("(?i)UNION\\s+SELECT", Pattern.CASE_INSENSITIVE),

            // 命令注入
            Pattern.compile(";\\s*(rm|del|format|shutdown)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\|\\s*(rm|del|cat)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\$\\({[^}]*}", Pattern.CASE_INSENSITIVE),

            // XSS
            Pattern.compile("<script[^>]*>", Pattern.CASE_INSENSITIVE),
            Pattern.compile("javascript:", Pattern.CASE_INSENSITIVE),
            Pattern.compile("onerror\\s*=", Pattern.CASE_INSENSITIVE),

            // 路径遍历
            Pattern.compile("\\.\\.(/|\\\\)"),
            Pattern.compile("/etc/passwd", Pattern.CASE_INSENSITIVE),
            Pattern.compile("/proc/self", Pattern.CASE_INSENSITIVE)
        );
    }

    @Override
    public ValidationResult validate(String input) {
        // 检查长度
        if (input == null) {
            return ValidationResult.invalid("输入不能为空");
        }

        if (input.length() > config.maxInputLength()) {
            return ValidationResult.invalid("输入过长，最大 " + config.maxInputLength() + " 字符");
        }

        // 检查禁止关键词
        String upperInput = input.toUpperCase();
        for (String keyword : config.forbiddenKeywords()) {
            if (upperInput.contains(keyword.toUpperCase())) {
                return ValidationResult.invalid("输入包含禁止的内容: " + keyword);
            }
        }

        // 检查危险模式
        for (Pattern pattern : dangerousPatterns) {
            if (pattern.matcher(input).find()) {
                return ValidationResult.invalid("输入包含潜在的攻击模式");
            }
        }

        return ValidationResult.valid();
    }
}
```

### 验证结果

```java
package com.harness.security;

/**
 * 验证结果。
 */
public record ValidationResult(
    boolean valid,
    String error
) {

    public static ValidationResult valid() {
        return new ValidationResult(true, null);
    }

    public static ValidationResult invalid(String error) {
        return new ValidationResult(false, error);
    }

    public boolean isValid() {
        return valid;
    }

    public String getError() {
        return error;
    }
}
```

## 沙箱执行

### SandboxExecutor

```java
package com.harness.security;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * 沙箱执行器 - 安全地执行命令。
 */
public class SandboxExecutor {

    private final String workingDirectory;
    private final List<String> readOnlyPaths;
    private final List<String> readWritePaths;
    private final List<String> deniedPaths;
    private final Set<String> allowedCommands;
    private final Set<String> deniedCommands;
    private final long defaultTimeout;

    public SandboxExecutor(String workingDirectory,
                           List<String> readOnlyPaths,
                           List<String> readWritePaths,
                           List<String> deniedPaths,
                           long defaultTimeout) {
        this.workingDirectory = workingDirectory;
        this.readOnlyPaths = readOnlyPaths;
        this.readWritePaths = readWritePaths;
        this.deniedPaths = deniedPaths;
        this.allowedCommands = Set.of(
            "ls", "cat", "head", "tail", "grep", "find",
            "pwd", "echo", "mkdir", "touch", "rm", "cp", "mv",
            "git", "python", "java", "javac", "gradle", "mvn"
        );
        this.deniedCommands = Set.of(
            "sudo", "su", "chmod", "chown", "passwd",
            "shutdown", "reboot", "halt", "init",
            "dd", "fdisk", "mkfs", "mount", "umount"
        );
        this.defaultTimeout = defaultTimeout;
    }

    /**
     * 在沙箱中执行命令。
     */
    public CompletableFuture<CommandResult> execute(String command) {
        return execute(command, defaultTimeout);
    }

    /**
     * 在沙箱中执行命令（带超时）。
     */
    public CompletableFuture<CommandResult> execute(String command, long timeout) {
        return CompletableFuture.supplyAsync(() -> {
            // 解析命令
            String[] parts = command.split("\\s+");
            String baseCommand = parts[0];

            // 检查禁止命令
            if (deniedCommands.contains(baseCommand)) {
                return CommandResult.denied("禁止执行命令: " + baseCommand);
            }

            // 检查允许命令（如果配置了白名单）
            if (!allowedCommands.isEmpty() && !allowedCommands.contains(baseCommand)) {
                return CommandResult.denied("不允许执行命令: " + baseCommand);
            }

            // 检查路径访问
            ValidationResult pathValidation = validatePaths(command);
            if (!pathValidation.isValid()) {
                return CommandResult.denied(pathValidation.getError());
            }

            // 执行命令
            try {
                ProcessBuilder pb = new ProcessBuilder("bash", "-c", command);
                pb.directory(new File(workingDirectory));
                pb.redirectErrorStream(true);

                // 设置环境变量（可选）
                pb.environment().put("PATH", "/usr/bin:/bin");

                Process process = pb.start();

                boolean finished = process.waitFor(timeout, TimeUnit.MILLISECONDS);
                if (!finished) {
                    process.destroyForcibly();
                    return CommandResult.timeout("命令执行超时");
                }

                String output = readOutput(process);

                if (process.exitValue() == 0) {
                    return CommandResult.success(output);
                } else {
                    return CommandResult.failure("命令执行失败 (exit code: " + process.exitValue() + ")", output);
                }

            } catch (Exception e) {
                return CommandResult.error("执行异常: " + e.getMessage());
            }
        });
    }

    /**
     * 检查文件路径访问权限。
     */
    public boolean canAccessPath(String path) {
        Path targetPath = Path.of(path).toAbsolutePath();

        // 检查禁止路径
        for (String denied : deniedPaths) {
            if (targetPath.startsWith(Path.of(denied).toAbsolutePath())) {
                return false;
            }
        }

        // 检查读写路径
        for (String allowed : readWritePaths) {
            if (targetPath.startsWith(Path.of(allowed).toAbsolutePath())) {
                return true;
            }
        }

        // 检查只读路径
        for (String allowed : readOnlyPaths) {
            if (targetPath.startsWith(Path.of(allowed).toAbsolutePath())) {
                return true;  // 只读，需要额外检查
            }
        }

        return false;
    }

    // 私有方法
    private ValidationResult validatePaths(String command) {
        // 提取命令中的路径
        List<String> paths = extractPaths(command);

        for (String path : paths) {
            if (!canAccessPath(path)) {
                return ValidationResult.invalid("禁止访问路径: " + path);
            }
        }

        return ValidationResult.valid();
    }

    private List<String> extractPaths(String command) {
        // 简化的路径提取逻辑
        return List.of();  // 实际实现需要更复杂的解析
    }

    private String readOutput(Process process) throws IOException {
        InputStream is = process.getInputStream();
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int len;
        while ((len = is.read(buffer)) != -1) {
            baos.write(buffer, 0, len);
        }
        return baos.toString(StandardCharsets.UTF_8);
    }
}

/**
 * 命令执行结果。
 */
public record CommandResult(
    CommandStatus status,
    String output,
    String error
) {

    public static CommandResult success(String output) {
        return new CommandResult(CommandStatus.SUCCESS, output, null);
    }

    public static CommandResult failure(String error, String output) {
        return new CommandResult(CommandStatus.FAILURE, output, error);
    }

    public static CommandResult denied(String reason) {
        return new CommandResult(CommandStatus.DENIED, null, reason);
    }

    public static CommandResult timeout(String reason) {
        return new CommandResult(CommandStatus.TIMEOUT, null, reason);
    }

    public static CommandResult error(String reason) {
        return new CommandResult(CommandStatus.ERROR, null, reason);
    }

    public boolean isSuccess() {
        return status == CommandStatus.SUCCESS;
    }
}

public enum CommandStatus {
    SUCCESS,
    FAILURE,
    DENIED,
    TIMEOUT,
    ERROR
}
```

## 输出清理

### ResultSanitizer

```java
package com.harness.security;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 输出清理器。
 */
public interface ResultSanitizer {

    /**
     * 清理输出内容。
     */
    String sanitize(String content);
}

/**
 * 默认输出清理器。
 */
public class DefaultResultSanitizer implements ResultSanitizer {

    private final List<SanitizationRule> rules;

    public DefaultResultSanitizer(List<SanitizationRule> rules) {
        this.rules = rules;
    }

    public static DefaultResultSanitizer banking() {
        return new DefaultResultSanitizer(List.of(
            // 银行卡号
            SanitizationRule.regex(
                "\\d{16,19}",
                match -> match.substring(0, 4) + "****" + match.substring(match.length() - 4)
            ),
            // 身份证号
            SanitizationRule.regex(
                "\\d{17}[0-9Xx]",
                match -> match.substring(0, 6) + "********" + match.substring(14)
            ),
            // 手机号
            SanitizationRule.regex(
                "1[3-9]\\d{9}",
                match -> match.substring(0, 3) + "****" + match.substring(7)
            ),
            // 邮箱
            SanitizationRule.regex(
                "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
                match -> "***@***.***"
            ),
            // API Key
            SanitizationRule.regex(
                "(sk-|api[_-]?key[_-]?)[a-zA-Z0-9]{20,}",
                match -> "***API_KEY***"
            ),
            // 密码
            SanitizationRule.regex(
                "(password|passwd|pwd)[\"']?[:=][\"']?[^\"',\\s]{8,}",
                match -> "password=***REDACTED***"
            )
        ));
    }

    @Override
    public String sanitize(String content) {
        if (content == null) {
            return null;
        }

        String result = content;
        for (SanitizationRule rule : rules) {
            result = rule.apply(result);
        }
        return result;
    }
}
```

### SanitizationRule

```java
package com.harness.security;

import java.util.regex.Pattern;
import java.util.function.Function;

/**
 * 脱敏规则。
 */
public interface SanitizationRule {

    /**
     * 应用规则。
     */
    String apply(String content);

    /**
     * 正则表达式规则。
     */
    static SanitizationRule regex(String pattern, Function<String, String> replacer) {
        return new RegexSanitizationRule(Pattern.compile(pattern), replacer);
    }

    /**
     * 固定替换规则。
     */
    static SanitizationRule fixed(String pattern, String replacement) {
        return regex(pattern, match -> replacement);
    }
}

/**
 * 正则表达式脱敏规则。
 */
class RegexSanitizationRule implements SanitizationRule {

    private final Pattern pattern;
    private final Function<String, String> replacer;

    RegexSanitizationRule(Pattern pattern, Function<String, String> replacer) {
        this.pattern = pattern;
        this.replacer = replacer;
    }

    @Override
    public String apply(String content) {
        Matcher matcher = pattern.matcher(content);
        StringBuffer sb = new StringBuffer();

        while (matcher.find()) {
            String match = matcher.group();
            String replacement = replacer.apply(match);
            matcher.appendReplacement(sb, replacement);
        }
        matcher.appendTail(sb);

        return sb.toString();
    }
}
```

## 审计日志

### AuditLogger

```java
package com.harness.security;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 审计日志记录器。
 */
public class AuditLogger {

    private final Path logDir;
    private final int retentionDays;
    private final ExecutorService executor;
    private final ObjectMapper mapper;

    public AuditLogger(Path logDir, int retentionDays) {
        this.logDir = logDir;
        this.retentionDays = retentionDays;
        this.executor = Executors.newSingleThreadExecutor();
        this.mapper = new ObjectMapper();

        try {
            Files.createDirectories(logDir);
        } catch (IOException e) {
            throw new RuntimeException("无法创建审计日志目录", e);
        }
    }

    /**
     * 记录审计日志。
     */
    public void log(AuditLogEntry entry) {
        executor.submit(() -> writeLog(entry));
    }

    /**
     * 批量记录。
     */
    public void logAll(List<AuditLogEntry> entries) {
        executor.submit(() -> {
            for (AuditLogEntry entry : entries) {
                writeLog(entry);
            }
        });
    }

    /**
     * 清理过期日志。
     */
    public void cleanup() {
        executor.submit(() -> {
            LocalDate cutoff = LocalDate.now().minusDays(retentionDays);

            try {
                Files.list(logDir)
                    .filter(path -> {
                        String filename = path.getFileName().toString();
                        if (!filename.startsWith("audit-") || !filename.endsWith(".jsonl")) {
                            return false;
                        }

                        String dateStr = filename.substring(6, 16);  // audit-YYYY-MM-DD.jsonl
                        LocalDate fileDate = LocalDate.parse(dateStr);
                        return fileDate.isBefore(cutoff);
                    })
                    .forEach(path -> {
                        try {
                            Files.delete(path);
                        } catch (IOException e) {
                            // 忽略删除失败
                        }
                    });
            } catch (IOException e) {
                // 忽略清理失败
            }
        });
    }

    /**
     * 关闭日志记录器。
     */
    public void close() {
        executor.shutdown();
    }

    // 私有方法
    private void writeLog(AuditLogEntry entry) {
        String filename = "audit-" + LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE) + ".jsonl";
        Path filePath = logDir.resolve(filename);

        try {
            String json = mapper.writeValueAsString(entry) + "\n";
            Files.write(filePath, json.getBytes(StandardCharsets.UTF_8),
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            // 记录失败不应该影响主流程
            System.err.println("写入审计日志失败: " + e.getMessage());
        }
    }
}
```

### AuditLogEntry

```java
package com.harness.security;

import java.time.Instant;
import java.util.Map;

/**
 * 审计日志条目。
 */
public record AuditLogEntry(
    Instant timestamp,
    String sessionId,
    String userId,
    String action,
    String hookPoint,
    int iteration,
    String toolName,
    Map<String, Object> toolArgs,
    boolean toolSuccess,
    String error,
    int inputTokens,
    int outputTokens,
    Map<String, Object> metadata
) {

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Instant timestamp = Instant.now();
        private String sessionId;
        private String userId;
        private String action;
        private String hookPoint;
        private int iteration = 0;
        private String toolName;
        private Map<String, Object> toolArgs = Map.of();
        private boolean toolSuccess = true;
        private String error;
        private int inputTokens = 0;
        private int outputTokens = 0;
        private Map<String, Object> metadata = Map.of();

        public Builder timestamp(Instant timestamp) { this.timestamp = timestamp; return this; }
        public Builder sessionId(String sessionId) { this.sessionId = sessionId; return this; }
        public Builder userId(String userId) { this.userId = userId; return this; }
        public Builder action(String action) { this.action = action; return this; }
        public Builder hookPoint(String hookPoint) { this.hookPoint = hookPoint; return this; }
        public Builder iteration(int iteration) { this.iteration = iteration; return this; }
        public Builder toolName(String toolName) { this.toolName = toolName; return this; }
        public Builder toolArgs(Map<String, Object> toolArgs) { this.toolArgs = toolArgs; return this; }
        public Builder toolSuccess(boolean toolSuccess) { this.toolSuccess = toolSuccess; return this; }
        public Builder error(String error) { this.error = error; return this; }
        public Builder inputTokens(int inputTokens) { this.inputTokens = inputTokens; return this; }
        public Builder outputTokens(int outputTokens) { this.outputTokens = outputTokens; return this; }
        public Builder metadata(Map<String, Object> metadata) { this.metadata = metadata; return this; }

        public AuditLogEntry build() {
            return new AuditLogEntry(timestamp, sessionId, userId, action, hookPoint, iteration,
                toolName, toolArgs, toolSuccess, error, inputTokens, outputTokens, metadata);
        }
    }
}
```

### 审计钩子

```java
package com.harness.security;

import com.harness.core.hooks.*;

import java.util.Set;
import java.util.concurrent.CompletableFuture;

/**
 * 审计日志钩子。
 */
public class AuditLoggingHook implements LifecycleHook {

    private final AuditLogger auditLogger;
    private final String userId;

    public AuditLoggingHook(AuditLogger auditLogger, String userId) {
        this.auditLogger = auditLogger;
        this.userId = userId;
    }

    @Override
    public Set<HookPoint> hookPoints() {
        return Set.of(
            HookPoint.ON_LOOP_START,
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.AFTER_LLM_CALL,
            HookPoint.BEFORE_TOOL_EXECUTE,
            HookPoint.AFTER_TOOL_EXECUTE,
            HookPoint.ON_ERROR,
            HookPoint.ON_LOOP_END
        );
    }

    @Override
    public CompletableFuture<HookResult> execute(HookContext ctx) {
        AuditLogEntry entry = AuditLogEntry.builder()
            .sessionId(ctx.sessionId())
            .userId(userId)
            .hookPoint(ctx.hookPoint().name())
            .iteration(ctx.iteration())
            .action(describeAction(ctx))
            .build();

        // 添加详细信息
        if (ctx.hookPoint() == HookPoint.BEFORE_TOOL_EXECUTE) {
            entry = AuditLogEntry.builder()
                .sessionId(ctx.sessionId())
                .userId(userId)
                .hookPoint(ctx.hookPoint().name())
                .iteration(ctx.iteration())
                .action("Tool call")
                .toolName(ctx.toolCall().name())
                .toolArgs(ctx.toolCall().arguments())
                .build();
        }

        if (ctx.hookPoint() == HookPoint.AFTER_TOOL_EXECUTE) {
            entry = AuditLogEntry.builder()
                .sessionId(ctx.sessionId())
                .userId(userId)
                .hookPoint(ctx.hookPoint().name())
                .iteration(ctx.iteration())
                .action("Tool result")
                .toolName(ctx.toolCall().name())
                .toolSuccess(ctx.toolResult().success())
                .build();
        }

        if (ctx.hookPoint() == HookPoint.AFTER_LLM_CALL) {
            entry = AuditLogEntry.builder()
                .sessionId(ctx.sessionId())
                .userId(userId)
                .hookPoint(ctx.hookPoint().name())
                .iteration(ctx.iteration())
                .action("LLM response")
                .inputTokens(ctx.llmResponse().usage().inputTokens())
                .outputTokens(ctx.llmResponse().usage().outputTokens())
                .build();
        }

        if (ctx.hookPoint() == HookPoint.ON_ERROR) {
            entry = AuditLogEntry.builder()
                .sessionId(ctx.sessionId())
                .userId(userId)
                .hookPoint(ctx.hookPoint().name())
                .iteration(ctx.iteration())
                .action("Error")
                .error(ctx.error() != null ? ctx.error().getMessage() : "Unknown error")
                .build();
        }

        auditLogger.log(entry);

        return CompletableFuture.completedFuture(HookResult.continue_());
    }

    private String describeAction(HookContext ctx) {
        return switch (ctx.hookPoint()) {
            case ON_LOOP_START -> "Loop started";
            case ON_LOOP_END -> "Loop ended";
            case BEFORE_LLM_CALL -> "Calling LLM";
            case AFTER_LLM_CALL -> "LLM response received";
            case BEFORE_TOOL_EXECUTE -> "Executing tool: " + ctx.toolCall().name();
            case AFTER_TOOL_EXECUTE -> "Tool result: " + (ctx.toolResult().success() ? "success" : "failed");
            case ON_ERROR -> "Error: " + ctx.error().getMessage();
            default -> ctx.hookPoint().name();
        };
    }
}
```

## 安全最佳实践

### 1. 最小权限原则

```java
// 只授予必要的权限
SandboxExecutor sandbox = new SandboxExecutor(
    workDir,
    List.of("/app/config"),           // 只读
    List.of(workDir),                  // 只写
    List.of("/etc", "/root", "/var"),  // 禁止
    30000                              // 超时
);
```

### 2. 输入验证优先

```java
// 所有用户输入都必须验证
InputValidator validator = new DefaultInputValidator(config);
ValidationResult result = validator.validate(userInput);

if (!result.isValid()) {
    return LoopResult.error(session, 0, result.getError());
}
```

### 3. 输出清理

```java
// 所有输出都必须清理
ResultSanitizer sanitizer = DefaultResultSanitizer.banking();
String safeOutput = sanitizer.sanitize(rawOutput);
```

### 4. 审计全覆盖

```java
// 所有操作都必须审计
agent.addHook(new AuditLoggingHook(auditLogger, userId));
```

### 5. 错误信息不暴露敏感信息

```java
// 错误信息应该通用，不暴露内部细节
public String getSafeErrorMessage(Exception e) {
    // 不暴露文件路径、API Key 等
    if (e instanceof FileNotFoundException) {
        return "文件操作失败";
    }
    if (e instanceof AuthenticationException) {
        return "认证失败";
    }
    return "操作失败，请稍后重试";
}
```

## 下一步

- [09-implementation.md](./09-implementation.md) - 了解实施路线图
- [14-bank-integration.md](./14-bank-integration.md) - 银行系统集成指南