# 14 - 银行系统集成指南

## 概述

本文档详细说明如何将 Harness SDK Java 版本集成到银行系统中，包括安全配置、审计要求、合规检查等。

## 银行环境特点

### 安全要求

- **离线部署**: 无法访问外部网络
- **密钥管理**: 使用银行内部密钥管理系统
- **审计日志**: 所有操作必须记录
- **数据隔离**: 敏感数据不能流出系统
- **合规检查**: 需要通过安全扫描

### 技术栈

- Java 17 (LTS 版本)
- Spring Boot 3.x
- 内部 Maven 仓库 (Nexus/Artifactory)
- 内部监控系统

## 部署架构

### 典型架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        银行内部网络                               │
│                                                                  │
│  ┌─────────────────┐      ┌─────────────────┐                  │
│  │   前端应用       │─────→│  API Gateway    │                  │
│  │   (React/Vue)   │      │  (Spring Cloud) │                  │
│  └─────────────────┘      └────────┬────────┘                  │
│                                    │                            │
│                           ┌────────↓────────┐                  │
│                           │  Agent Service  │                  │
│                           │  ┌───────────┐  │                  │
│                           │  │ Harness   │  │                  │
│                           │  │ SDK (JAR) │  │                  │
│                           │  └───────────┘  │                  │
│                           └────────┬────────┘                  │
│                                    │                            │
│         ┌──────────────────────────┼──────────────────────────┐ │
│         │                          │                          │ │
│  ┌──────↓──────┐    ┌─────────────↓─────────┐    ┌─────────↓──┐│
│  │   密钥管理   │    │      审计日志          │    │  监控系统   ││
│  │   (Vault)   │    │   (SIEM/ELK)          │    │ (Prometheus)││
│  └─────────────┘    └───────────────────────┘    └─────────────┘│
│                                                                  │
│                         ┌────────────────┐                       │
│                         │   内部 API     │                       │
│                         │ (核心银行系统)  │                       │
│                         └────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## 集成步骤

### 1. 引入 JAR 包

```kotlin
// build.gradle.kts

dependencies {
    // Harness SDK
    implementation(files("libs/harness-sdk-all-1.0.0.jar"))
    
    // Spring Boot (如果使用)
    implementation("org.springframework.boot:spring-boot-starter-web:3.2.0")
    
    // 日志 (选择银行标准日志框架)
    implementation("org.slf4j:slf4j-api:2.0.0")
    implementation("ch.qos.logback:logback-classic:1.4.0")
}
```

### 2. 配置密钥管理

```java
import com.harness.HarnessConfig;
import com.harness.security.VaultApiKeyProvider;

@Configuration
public class HarnessConfiguration {
    
    @Bean
    public Harness harness(VaultService vaultService) {
        // 从银行密钥管理系统获取 API Key
        String apiKey = vaultService.getSecret("anthropic/api-key");
        
        HarnessConfig config = HarnessConfig.builder()
            .model("claude-sonnet-4-6")
            .apiKey(apiKey)
            .tools(List.of(
                new ReadTool(),
                new BashTool(true)  // 沙箱模式
            ))
            .workingDirectory("/secure/workspace")
            .auditEnabled(true)
            .auditLogDir("/var/log/harness/audit")
            .security(SecurityConfig.builder()
                .enableInputValidation(true)
                .enableOutputSanitization(true)
                .enableAuditLog(true)
                .maxInputLength(10000)
                .build())
            .build();
        
        return new Harness(config);
    }
}
```

### 3. 审计日志配置

```java
import com.harness.core.hooks.LifecycleHook;
import com.harness.core.hooks.HookPoint;
import com.harness.core.hooks.HookContext;
import com.harness.core.hooks.HookResult;

/**
 * 审计日志钩子 - 记录所有操作到银行 SIEM 系统。
 */
public class AuditLoggingHook implements LifecycleHook {
    
    private final AuditLogger auditLogger;
    
    public AuditLoggingHook(AuditLogger auditLogger) {
        this.auditLogger = auditLogger;
    }
    
    @Override
    public Set<HookPoint> hookPoints() {
        return Set.of(
            HookPoint.ON_LOOP_START,
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.BEFORE_TOOL_EXECUTE,
            HookPoint.AFTER_TOOL_EXECUTE,
            HookPoint.ON_ERROR,
            HookPoint.ON_LOOP_END
        );
    }
    
    @Override
    public CompletableFuture<HookResult> execute(HookContext context) {
        AuditLogEntry entry = AuditLogEntry.builder()
            .timestamp(Instant.now())
            .sessionId(context.sessionId())
            .hookPoint(context.hookPoint().name())
            .iteration(context.iteration())
            .userId(getCurrentUserId())  // 从安全上下文获取
            .action(describeAction(context))
            .build();
        
        auditLogger.log(entry);
        
        return CompletableFuture.completedFuture(HookResult.continue_());
    }
    
    private String describeAction(HookContext ctx) {
        return switch (ctx.hookPoint()) {
            case BEFORE_TOOL_EXECUTE -> 
                "Tool call: " + ctx.toolCall().name();
            case AFTER_TOOL_EXECUTE -> 
                "Tool result: " + (ctx.toolResult().success() ? "success" : "failed");
            case ON_ERROR -> 
                "Error: " + ctx.error().getMessage();
            default -> 
                ctx.hookPoint().name();
        };
    }
}

// 注册钩子
agent.addHook(new AuditLoggingHook(siemAuditLogger));
```

### 4. 数据脱敏

```java
import com.harness.security.ResultSanitizer;
import com.harness.security.SanitizationRule;

/**
 * 银行数据脱敏规则。
 */
public class BankDataSanitizer implements ResultSanitizer {
    
    private final List<SanitizationRule> rules = List.of(
        // 脱敏银行卡号
        SanitizationRule.regex(
            "\\d{16,19}", 
            match -> match.substring(0, 4) + "****" + match.substring(match.length() - 4)
        ),
        // 脱敏身份证号
        SanitizationRule.regex(
            "\\d{17}[0-9Xx]", 
            match -> match.substring(0, 6) + "********" + match.substring(14)
        ),
        // 脱敏手机号
        SanitizationRule.regex(
            "1[3-9]\\d{9}", 
            match -> match.substring(0, 3) + "****" + match.substring(7)
        )
    );
    
    @Override
    public String sanitize(String content) {
        String result = content;
        for (SanitizationRule rule : rules) {
            result = rule.apply(result);
        }
        return result;
    }
}
```

## 安全配置

### 沙箱模式

```java
import com.harness.security.SandboxExecutor;

/**
 * 配置安全的沙箱环境。
 */
public class SecureSandboxConfig {
    
    public SandboxExecutor createSandbox(String userId) {
        // 用户工作目录
        String workDir = "/secure/workspace/" + userId;
        
        // 只读路径 (系统配置、公共资源)
        List<String> readOnlyPaths = List.of(
            "/app/config",
            "/app/resources"
        );
        
        // 读写路径 (用户数据)
        List<String> readWritePaths = List.of(
            workDir,
            "/shared/" + userId
        );
        
        // 禁止访问的路径
        List<String> deniedPaths = List.of(
            "/etc",
            "/root",
            "/var/log"
        );
        
        return new SandboxExecutor(workDir, readOnlyPaths, readWritePaths, deniedPaths);
    }
}
```

### 输入验证

```java
import com.harness.security.InputValidator;
import com.harness.security.ValidationResult;

/**
 * 银行输入验证器。
 */
public class BankInputValidator implements InputValidator {
    
    // 禁止的关键词
    private static final List<String> FORBIDDEN_KEYWORDS = List.of(
        "DROP TABLE",
        "DELETE FROM",
        "TRUNCATE",
        "EXEC(",
        "EVAL(",
        "<SCRIPT>"
    );
    
    @Override
    public ValidationResult validate(String input) {
        // 检查长度
        if (input.length() > 50000) {
            return ValidationResult.invalid("输入过长，最大 50000 字符");
        }
        
        // 检查禁止关键词
        String upperInput = input.toUpperCase();
        for (String keyword : FORBIDDEN_KEYWORDS) {
            if (upperInput.contains(keyword)) {
                return ValidationResult.invalid("输入包含禁止的内容: " + keyword);
            }
        }
        
        // 检查敏感数据模式
        if (containsSensitiveData(input)) {
            // 记录审计日志
            auditLogger.warn("输入包含敏感数据，已标记处理");
        }
        
        return ValidationResult.valid();
    }
}
```

## 监控集成

### Prometheus 指标

```java
import io.prometheus.client.Counter;
import io.prometheus.client.Histogram;

/**
 * Harness 监控指标。
 */
public class HarnessMetrics {
    
    // 请求计数
    private static final Counter requests = Counter.build()
        .name("harness_requests_total")
        .help("Total Harness requests")
        .labelNames("model", "status")
        .register();
    
    // Token 使用量
    private static final Counter tokens = Counter.build()
        .name("harness_tokens_total")
        .help("Total tokens used")
        .labelNames("model", "type")
        .register();
    
    // 请求延迟
    private static final Histogram latency = Histogram.build()
        .name("harness_request_duration_seconds")
        .help("Request duration in seconds")
        .labelNames("model")
        .register();
    
    // 工具调用计数
    private static final Counter toolCalls = Counter.build()
        .name("harness_tool_calls_total")
        .help("Total tool calls")
        .labelNames("tool", "status")
        .register();
    
    public static void recordRequest(String model, String status) {
        requests.labels(model, status).inc();
    }
    
    public static void recordTokens(String model, int input, int output) {
        tokens.labels(model, "input").inc(input);
        tokens.labels(model, "output").inc(output);
    }
    
    public static Histogram.Timer startTimer(String model) {
        return latency.labels(model).startTimer();
    }
    
    public static void recordToolCall(String tool, boolean success) {
        toolCalls.labels(tool, success ? "success" : "failed").inc();
    }
}
```

### 健康检查

```java
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;

/**
 * Harness 健康检查。
 */
@Component
public class HarnessHealthIndicator implements HealthIndicator {
    
    private final Harness agent;
    
    @Override
    public Health health() {
        try {
            // 检查 Agent 是否正常
            LoopResult result = agent.run("ping", "health-check-session");
            
            if (result.isCompleted()) {
                return Health.up()
                    .withDetail("model", agent.getConfig().model())
                    .withDetail("status", "healthy")
                    .build();
            } else {
                return Health.down()
                    .withDetail("error", result.error())
                    .build();
            }
        } catch (Exception e) {
            return Health.down(e).build();
        }
    }
}
```

## 合规检查清单

### 部署前检查

- [ ] **依赖扫描**: OWASP 依赖检查无高危漏洞
- [ ] **SBOM**: 已提供软件物料清单
- [ ] **许可证**: 所有依赖使用 MIT/Apache 2.0 许可证
- [ ] **密钥管理**: API Key 存储在银行密钥管理系统
- [ ] **审计日志**: 所有操作记录到 SIEM 系统
- [ ] **数据脱敏**: 敏感数据已配置脱敏规则
- [ ] **沙箱模式**: Shell 工具使用沙箱模式
- [ ] **输入验证**: 启用输入验证和注入检测

### 运行时检查

- [ ] **访问控制**: 通过 API Gateway 限制访问
- [ ] **会话隔离**: 每个用户独立会话
- [ ] **资源限制**: 配置合理的 Token 和迭代限制
- [ ] **错误处理**: 错误信息不暴露敏感信息
- [ ] **日志脱敏**: 日志中不包含敏感数据

## 示例：交易分析服务

```java
package com.bank.service;

import com.harness.*;
import com.harness.core.LoopResult;
import com.harness.tools.*;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 交易分析服务 - 使用 Harness SDK 分析交易异常。
 */
@Service
public class TransactionAnalysisService {
    
    private static final Logger logger = LoggerFactory.getLogger(TransactionAnalysisService.class);
    
    private final Harness agent;
    private final AuditLogger auditLogger;
    
    public TransactionAnalysisService(Harness agent, AuditLogger auditLogger) {
        this.agent = agent;
        this.auditLogger = auditLogger;
    }
    
    /**
     * 分析交易是否存在异常。
     * 
     * @param transactionData 交易数据
     * @param userId 用户 ID (用于审计)
     * @return 分析结果
     */
    public AnalysisResult analyzeTransaction(String transactionData, String userId) {
        // 记录审计日志
        auditLogger.log(AuditLogEntry.builder()
            .action("TRANSACTION_ANALYSIS_START")
            .userId(userId)
            .dataHash(hashData(transactionData))
            .timestamp(Instant.now())
            .build());
        
        try {
            // 构建提示词
            String prompt = """
                分析以下交易数据，识别是否存在异常模式：
                
                1. 检查交易金额是否异常
                2. 检查交易时间是否异常
                3. 检查交易地点是否异常
                4. 检查交易频率是否异常
                
                交易数据：
                %s
                
                请提供分析结论和建议。
                """.formatted(maskSensitiveData(transactionData));
            
            // 执行分析
            LoopResult result = agent.run(prompt, "txn-" + userId + "-" + System.currentTimeMillis());
            
            if (result.isCompleted()) {
                // 记录成功日志
                auditLogger.log(AuditLogEntry.builder()
                    .action("TRANSACTION_ANALYSIS_SUCCESS")
                    .userId(userId)
                    .timestamp(Instant.now())
                    .build());
                
                return AnalysisResult.success(result.content(), result.tokenUsage());
            } else {
                // 记录失败日志
                auditLogger.log(AuditLogEntry.builder()
                    .action("TRANSACTION_ANALYSIS_FAILED")
                    .userId(userId)
                    .error(result.error())
                    .timestamp(Instant.now())
                    .build());
                
                return AnalysisResult.failure(result.error());
            }
            
        } catch (Exception e) {
            logger.error("Transaction analysis failed", e);
            
            auditLogger.log(AuditLogEntry.builder()
                .action("TRANSACTION_ANALYSIS_ERROR")
                .userId(userId)
                .error(e.getMessage())
                .timestamp(Instant.now())
                .build());
            
            return AnalysisResult.failure(e.getMessage());
        }
    }
    
    private String maskSensitiveData(String data) {
        // 脱敏银行卡号、身份证号等
        return data
            .replaceAll("\\d{16,19}", "****CARD****")
            .replaceAll("\\d{17}[0-9Xx]", "****ID****");
    }
    
    private String hashData(String data) {
        // 用于审计日志的数据哈希
        return Integer.toHexString(data.hashCode());
    }
}
```

## 下一步

- [08-security.md](./08-security.md) - 详细了解安全设计
- [12-deployment.md](./12-deployment.md) - 了解 JAR 包部署详情
