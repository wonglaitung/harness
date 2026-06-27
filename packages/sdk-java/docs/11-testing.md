# 11 - 测试策略

## 概述

本文档说明 Harness SDK Java 版本的测试策略，包括单元测试、集成测试和性能测试。

## 测试架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Architecture                      │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Unit Tests                            │ │
│  │  - 核心类型测试                                        │ │
│  │  - 工具系统测试                                        │ │
│  │  - 记忆系统测试                                        │ │
│  │  - 安全模块测试                                        │ │
│  │  覆盖率目标: 80%+                                      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Integration Tests                     │ │
│  │  - LLM API 集成测试                                    │ │
│  │  - MCP 服务器集成测试                                  │ │
│  │  - 端到端流程测试                                      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  Performance Tests                     │ │
│  │  - Token 计数性能                                      │ │
│  │  - 并发执行测试                                        │ │
│  │  - 内存使用测试                                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 测试框架

### JUnit 5 配置

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testImplementation("org.mockito:mockito-core:5.10.0")
    testImplementation("org.assertj:assertj-core:3.25.0")
}

tasks.test {
    useJUnitPlatform()
}
```

### 测试基类

```java
package com.harness.testing;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.TestInfo;
import org.junit.jupiter.api.TestReporter;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 测试基类。
 */
public abstract class BaseTest {

    protected Path tempDir;
    protected TestInfo testInfo;

    @BeforeEach
    void setUp(TestInfo testInfo) throws Exception {
        this.testInfo = testInfo;
        this.tempDir = Files.createTempDirectory("harness-test-" + testInfo.getTestMethod().get().getName());

        doSetUp();
    }

    @AfterEach
    void tearDown() throws Exception {
        doTearDown();

        // 清理临时目录
        if (tempDir != null) {
            Files.walk(tempDir)
                .sorted((a, b) -> -a.compareTo(b))
                .forEach(path -> {
                    try {
                        Files.deleteIfExists(path);
                    } catch (Exception e) {
                        // 忽略
                    }
                });
        }
    }

    protected void doSetUp() throws Exception {
        // 子类重写
    }

    protected void doTearDown() throws Exception {
        // 子类重写
    }
}
```

## 单元测试

### 核心类型测试

```java
package com.harness.types;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;

class MessageTest {

    @Test
    @DisplayName("创建用户消息")
    void createUserMessage() {
        Message message = Message.user("Hello");

        assertThat(message.role()).isEqualTo("user");
        assertThat(message.content()).isEqualTo("Hello");
        assertThat(message.metadata()).isEmpty();
    }

    @Test
    @DisplayName("创建助手消息")
    void createAssistantMessage() {
        Message message = Message.assistant("Hi there!");

        assertThat(message.role()).isEqualTo("assistant");
        assertThat(message.content()).isEqualTo("Hi there!");
    }

    @Test
    @DisplayName("创建带元数据的消息")
    void createMessageWithMetadata() {
        Map<String, Object> metadata = Map.of("source", "test");
        Message message = new Message("user", "Hello", metadata);

        assertThat(message.metadata()).containsEntry("source", "test");
    }
}
```

```java
package com.harness.types;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class TokenUsageTest {

    @Test
    void testTotal() {
        TokenUsage usage = new TokenUsage(100, 50);

        assertThat(usage.total()).isEqualTo(150);
    }

    @Test
    void testAdd() {
        TokenUsage usage1 = new TokenUsage(100, 50);
        TokenUsage usage2 = new TokenUsage(200, 100);

        TokenUsage result = usage1.add(usage2);

        assertThat(result.inputTokens()).isEqualTo(300);
        assertThat(result.outputTokens()).isEqualTo(150);
    }
}
```

### 工具系统测试

```java
package com.harness.tools;

import com.harness.testing.BaseTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;

class ReadToolTest extends BaseTest {

    private ReadTool tool;
    private ToolContext context;

    @Override
    protected void doSetUp() {
        tool = new ReadTool();
        context = ToolContext.builder()
            .workingDirectory(tempDir.toString())
            .build();
    }

    @Test
    @DisplayName("读取存在的文件")
    void readExistingFile() throws Exception {
        // 准备测试文件
        Path testFile = tempDir.resolve("test.txt");
        Files.writeString(testFile, "Hello, World!");

        // 执行
        Map<String, Object> args = Map.of("file_path", testFile.toString());
        ToolResult result = tool.execute(args, context).join();

        // 验证
        assertThat(result.success()).isTrue();
        assertThat(result.output()).contains("Hello, World!");
    }

    @Test
    @DisplayName("读取不存在的文件")
    void readNonExistingFile() {
        Map<String, Object> args = Map.of("file_path", "/non/existing/file.txt");
        ToolResult result = tool.execute(args, context).join();

        assertThat(result.success()).isFalse();
        assertThat(result.error()).contains("文件不存在");
    }

    @Test
    @DisplayName("使用相对路径应失败")
    void readWithRelativePath() {
        Map<String, Object> args = Map.of("file_path", "relative/path.txt");
        ToolResult result = tool.execute(args, context).join();

        assertThat(result.success()).isFalse();
        assertThat(result.error()).contains("绝对路径");
    }

    @Test
    @DisplayName("读取文件部分内容")
    void readFileWithOffsetAndLimit() throws Exception {
        Path testFile = tempDir.resolve("test.txt");
        Files.write(testFile, List.of("Line 1", "Line 2", "Line 3", "Line 4", "Line 5"));

        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "offset", 1,
            "limit", 2
        );
        ToolResult result = tool.execute(args, context).join();

        assertThat(result.success()).isTrue();
        assertThat(result.output()).contains("Line 2", "Line 3");
        assertThat(result.output()).doesNotContain("Line 1", "Line 4");
    }
}
```

```java
package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class ToolExecutorTest {

    @Test
    @DisplayName("并行执行多个工具")
    void executeMultipleToolsInParallel() {
        Tool tool1 = mock(Tool.class);
        when(tool1.name()).thenReturn("tool1");
        when(tool1.execute(any(), any()))
            .thenReturn(CompletableFuture.completedFuture(ToolResult.success("result1")));

        Tool tool2 = mock(Tool.class);
        when(tool2.name()).thenReturn("tool2");
        when(tool2.execute(any(), any()))
            .thenReturn(CompletableFuture.completedFuture(ToolResult.success("result2")));

        ToolExecutor executor = new ToolExecutor(List.of(tool1, tool2), 30000);

        List<ToolCall> calls = List.of(
            new ToolCall("tool1", Map.of()),
            new ToolCall("tool2", Map.of())
        );

        List<ToolResult> results = executor.executeAll(calls, mock(ToolContext.class)).join();

        assertThat(results).hasSize(2);
        assertThat(results.get(0).output()).isEqualTo("result1");
        assertThat(results.get(1).output()).isEqualTo("result2");
    }

    @Test
    @DisplayName("工具执行超时")
    void toolExecutionTimeout() {
        Tool slowTool = mock(Tool.class);
        when(slowTool.name()).thenReturn("slow_tool");
        when(slowTool.execute(any(), any()))
            .thenReturn(CompletableFuture.supplyAsync(() -> {
                try {
                    Thread.sleep(5000);
                    return ToolResult.success("done");
                } catch (InterruptedException e) {
                    return ToolResult.failure("interrupted");
                }
            }));

        ToolExecutor executor = new ToolExecutor(List.of(slowTool), 100);  // 100ms 超时

        ToolCall call = new ToolCall("slow_tool", Map.of());
        ToolResult result = executor.execute(call, mock(ToolContext.class)).join();

        assertThat(result.success()).isFalse();
        assertThat(result.error()).contains("超时");
    }
}
```

### Token 计数测试

```java
package com.harness.memory;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;

class TokenCounterTest {

    private final TokenCounter counter = new TokenCounter();

    @Test
    @DisplayName("计算英文 Token")
    void countEnglishTokens() {
        String text = "Hello, world!";
        int count = counter.count(text);

        // "Hello, world!" 通常约 4 个 token
        assertThat(count).isGreaterThan(0).isLessThan(10);
    }

    @Test
    @DisplayName("计算中文 Token")
    void countChineseTokens() {
        String text = "你好，世界！";
        int count = counter.count(text);

        // 中文字符通常每个 1-2 个 token
        assertThat(count).isGreaterThan(0);
    }

    @Test
    @DisplayName("空字符串返回 0")
    void countEmptyString() {
        assertThat(counter.count("")).isEqualTo(0);
        assertThat(counter.count(null)).isEqualTo(0);
    }

    @Test
    @DisplayName("缓存功能")
    void cachingWorks() {
        String text = "This is a test string for caching";

        int count1 = counter.count(text);
        int count2 = counter.count(text);

        assertThat(count1).isEqualTo(count2);
    }
}
```

### 安全模块测试

```java
package com.harness.security;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.assertj.core.api.Assertions.*;

class InputValidatorTest {

    private final InputValidator validator = new DefaultInputValidator(SecurityConfig.defaults());

    @Test
    @DisplayName("验证正常输入")
    void validateNormalInput() {
        ValidationResult result = validator.validate("请帮我分析代码");
        assertThat(result.isValid()).isTrue();
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "DROP TABLE users",
        "DELETE FROM accounts",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
        "$(rm -rf /)"
    })
    @DisplayName("检测危险输入")
    void detectDangerousInput(String input) {
        ValidationResult result = validator.validate(input);
        assertThat(result.isValid()).isFalse();
    }

    @Test
    @DisplayName("输入过长应拒绝")
    void rejectLongInput() {
        SecurityConfig config = SecurityConfig.builder()
            .maxInputLength(100)
            .build();

        InputValidator validator = new DefaultInputValidator(config);

        String longInput = "a".repeat(200);
        ValidationResult result = validator.validate(longInput);

        assertThat(result.isValid()).isFalse();
        assertThat(result.getError()).contains("过长");
    }
}
```

```java
package com.harness.security;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.assertj.core.api.Assertions.*;

class ResultSanitizerTest {

    private final ResultSanitizer sanitizer = DefaultResultSanitizer.banking();

    @Test
    @DisplayName("脱敏银行卡号")
    void sanitizeBankCardNumber() {
        String input = "您的银行卡号 6222021234567890123 已绑定";
        String result = sanitizer.sanitize(input);

        assertThat(result).contains("6222****0123");
        assertThat(result).doesNotContain("6222021234567890123");
    }

    @Test
    @DisplayName("脱敏身份证号")
    void sanitizeIdNumber() {
        String input = "身份证号：110101199001011234";
        String result = sanitizer.sanitize(input);

        assertThat(result).contains("110101********1234");
        assertThat(result).doesNotContain("110101199001011234");
    }

    @Test
    @DisplayName("脱敏手机号")
    void sanitizePhoneNumber() {
        String input = "联系电话：13812345678";
        String result = sanitizer.sanitize(input);

        assertThat(result).contains("138****5678");
        assertThat(result).doesNotContain("13812345678");
    }

    @Test
    @DisplayName("脱敏 API Key")
    void sanitizeApiKey() {
        String input = "API Key: sk-ant-api03-abcdefghijklmnop1234567890";
        String result = sanitizer.sanitize(input);

        assertThat(result).contains("***API_KEY***");
        assertThat(result).doesNotContain("sk-ant-api03-abcdefghijklmnop1234567890");
    }
}
```

## 集成测试

### Mock Harness

```java
package com.harness.testing;

import com.harness.*;
import com.harness.types.*;
import java.util.List;
import java.util.ArrayList;
import java.util.function.Consumer;

/**
 * Mock Harness - 用于测试。
 */
public class MockHarness {

    private final List<MockResponse> responses;
    private int responseIndex = 0;
    private final List<String> prompts = new ArrayList<>();

    public MockHarness(List<MockResponse> responses) {
        this.responses = responses;
    }

    public LoopResult run(String prompt) {
        prompts.add(prompt);

        if (responseIndex >= responses.size()) {
            return LoopResult.error(null, 0, "No more mock responses");
        }

        MockResponse response = responses.get(responseIndex++);
        return LoopResult.completed(null, response.content(), 1, new TokenUsage(100, 50));
    }

    public void stream(String prompt, Consumer<String> onChunk) {
        MockResponse response = responses.get(responseIndex++);
        for (char c : response.content().toCharArray()) {
            onChunk.accept(String.valueOf(c));
        }
    }

    public List<String> getPrompts() {
        return prompts;
    }

    public static MockHarness withResponses(MockResponse... responses) {
        return new MockHarness(List.of(responses));
    }
}

/**
 * Mock 响应。
 */
public record MockResponse(
    String content,
    List<ToolCall> toolCalls
) {
    public static MockResponse content(String content) {
        return new MockResponse(content, List.of());
    }

    public static MockResponse toolCall(String name, Map<String, Object> args) {
        return new MockResponse(null, List.of(new ToolCall(name, args)));
    }
}
```

### 使用 Mock 测试

```java
package com.harness;

import com.harness.testing.*;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class MockHarnessTest {

    @Test
    void testMockResponse() {
        MockHarness mock = MockHarness.withResponses(
            MockResponse.content("Hello, I'm Claude!"),
            MockResponse.content("How can I help you?")
        );

        LoopResult result1 = mock.run("Hi");
        assertThat(result1.content()).isEqualTo("Hello, I'm Claude!");

        LoopResult result2 = mock.run("What can you do?");
        assertThat(result2.content()).isEqualTo("How can I help you?");
    }

    @Test
    void testStreamResponse() {
        MockHarness mock = MockHarness.withResponses(
            MockResponse.content("Hello")
        );

        StringBuilder received = new StringBuilder();
        mock.stream("Hi", chunk -> received.append(chunk));

        assertThat(received.toString()).isEqualTo("Hello");
    }
}
```

### LLM API 集成测试

```java
package com.harness.llm;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import static org.assertj.core.api.Assertions.*;

class AnthropicClientIntegrationTest {

    @Test
    @Tag("integration")
    @EnabledIfEnvironmentVariable(named = "ANTHROPIC_API_KEY", matches = ".+")
    @DisplayName("调用 Anthropic API")
    void callAnthropicApi() {
        AnthropicClient client = new AnthropicClient(
            System.getenv("ANTHROPIC_API_KEY"),
            "claude-sonnet-4-6"
        );

        List<Message> messages = List.of(Message.user("Say 'Hello' in Chinese"));

        LLMResponse response = client.call(messages);

        assertThat(response.content()).isNotEmpty();
        assertThat(response.content()).containsIgnoringCase("你好");
    }

    @Test
    @Tag("integration")
    @EnabledIfEnvironmentVariable(named = "ANTHROPIC_API_KEY", matches = ".+")
    @DisplayName("流式响应")
    void streamingResponse() {
        AnthropicClient client = new AnthropicClient(
            System.getenv("ANTHROPIC_API_KEY"),
            "claude-sonnet-4-6"
        );

        List<Message> messages = List.of(Message.user("Count from 1 to 5"));

        StringBuilder received = new StringBuilder();
        client.stream(messages, chunk -> received.append(chunk));

        assertThat(received.toString()).contains("1", "2", "3", "4", "5");
    }
}
```

### MCP 集成测试

```java
package com.harness.mcp;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.condition.EnabledIf;
import static org.assertj.core.api.Assertions.*;

class McpClientIntegrationTest {

    private boolean mcpServerAvailable() {
        // 检查 MCP 服务器是否可用
        return System.getenv("MCP_SERVER_PATH") != null;
    }

    @Test
    @Tag("integration")
    @EnabledIf("mcpServerAvailable")
    void testMcpConnection() {
        McpConfig config = McpConfig.builder()
            .transport(McpTransport.STDIO)
            .command(System.getenv("MCP_SERVER_PATH"))
            .build();

        HarnessMcpClient client = new HarnessMcpClient("test", config);

        client.connect().join();
        assertThat(client.isConnected()).isTrue();

        List<McpToolInfo> tools = client.listTools().join();
        assertThat(tools).isNotEmpty();

        client.disconnect().join();
        assertThat(client.isConnected()).isFalse();
    }
}
```

## 性能测试

### Token 计数性能

```java
package com.harness.memory;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import java.util.concurrent.TimeUnit;
import static org.assertj.core.api.Assertions.*;

class TokenCounterPerformanceTest {

    private final TokenCounter counter = new TokenCounter();

    @Test
    @DisplayName("Token 计数性能测试")
    void tokenCountingPerformance() {
        // 生成大量文本
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 10000; i++) {
            sb.append("This is a test sentence for token counting. ");
        }
        String text = sb.toString();

        // 测试计数时间
        long start = System.nanoTime();
        int count = counter.count(text);
        long duration = System.nanoTime() - start;

        System.out.println("Token count: " + count);
        System.out.println("Time: " + TimeUnit.NANOSECONDS.toMillis(duration) + "ms");

        // 应该在合理时间内完成
        assertThat(duration).isLessThan(TimeUnit.SECONDS.toNanos(1));
    }

    @Test
    @DisplayName("缓存命中测试")
    void cacheHitTest() {
        String text = "This text will be cached after first count";

        // 第一次计数
        counter.count(text);

        // 第二次应该更快（缓存命中）
        long start = System.nanoTime();
        counter.count(text);
        long cachedDuration = System.nanoTime() - start;

        assertThat(cachedDuration).isLessThan(1000000);  // < 1ms
    }
}
```

### 并发测试

```java
package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import java.util.concurrent.*;
import java.util.List;
import java.util.ArrayList;
import static org.assertj.core.api.Assertions.*;

class ToolExecutorConcurrencyTest {

    @Test
    @DisplayName("并发执行工具")
    void concurrentToolExecution() throws Exception {
        // 模拟延迟工具
        Tool delayedTool = new Tool() {
            @Override
            public String name() { return "delayed"; }

            @Override
            public String description() { return "Delayed tool"; }

            @Override
            public Map<String, Object> inputSchema() { return Map.of(); }

            @Override
            public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
                return CompletableFuture.supplyAsync(() -> {
                    try {
                        Thread.sleep(100);
                        return ToolResult.success("done");
                    } catch (InterruptedException e) {
                        return ToolResult.failure("interrupted");
                    }
                });
            }
        };

        ToolExecutor executor = new ToolExecutor(List.of(delayedTool), 5000);

        // 并发执行 10 次
        int count = 10;
        ExecutorService pool = Executors.newFixedThreadPool(count);
        List<Future<ToolResult>> futures = new ArrayList<>();

        long start = System.currentTimeMillis();

        for (int i = 0; i < count; i++) {
            futures.add(pool.submit(() ->
                executor.execute(new ToolCall("delayed", Map.of()), mock(ToolContext.class)).join()
            ));
        }

        // 等待所有完成
        for (Future<ToolResult> future : futures) {
            assertThat(future.get().success()).isTrue();
        }

        long duration = System.currentTimeMillis() - start;

        // 并发执行应该比顺序执行快
        // 顺序执行: 10 * 100ms = 1000ms
        // 并发执行: 约 100ms
        assertThat(duration).isLessThan(500);

        pool.shutdown();
    }
}
```

## 测试覆盖率

### JaCoCo 配置

```kotlin
// build.gradle.kts
plugins {
    jacoco
}

tasks.test {
    finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
    dependsOn(tasks.test)

    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}

tasks.jacocoTestCoverageVerification {
    violationRules {
        rule {
            limit {
                minimum = "0.80".toBigDecimal()
            }
        }
    }
}
```

### 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| harness-sdk-core | 85% |
| harness-sdk-tools | 80% |
| harness-sdk-mcp | 75% |
| harness-sdk-memory | 80% |
| harness-sdk-security | 90% |

## 下一步

- [12-deployment.md](./12-deployment.md) - 部署指南
- [13-production-readiness.md](./13-production-readiness.md) - 生产就绪检查

## 功能演示测试套件

### SdkFeatureDemo.java

位于 `examples/SdkFeatureDemo.java`，包含 27 个功能演示示例：

| 序号 | 测试方法 | 功能 |
|------|---------|------|
| 1 | `demo01_basicConversation` | 基础对话功能 |
| 2 | `demo02_fileTools` | 文件操作工具 |
| 3 | `demo03_multiTurnConversation` | 多轮对话会话管理 |
| 4 | `demo04_costControl` | 成本控制 |
| 5 | `demo05_progressTracking` | 进度追踪 |
| 6 | `demo06_customTool` | 自定义工具 |
| 7 | `demo07_mockTesting` | Mock 测试 |
| 8 | `demo08_skillsSystem` | 技能系统 |
| 9 | `demo09_skillInjection` | 技能注入 |
| 10 | `demo10_mcpIntegration` | MCP 服务器 |
| 11 | `demo11_securitySystem` | 安全系统 |
| 12 | `demo12_observability` | 可观测性 |
| 13 | `demo13_advancedCostControl` | 多级成本控制 |
| 14 | `demo14_interruptAndResume` | 中断与恢复 |
| 15 | `demo15_configuration` | 配置管理 |
| 16 | `demo16_completeWorkflow` | 完整工作流 |
| 17 | `demo17_lifecycleHooks` | 生命周期钩子 |
| 18 | `demo18_dynamicSystemPrompt` | 动态系统提示 |
| 19 | `demo19_ralphLoop` | Ralph Loop |
| 20 | `demo20_subAgent` | Sub-Agent 管理 |
| 21 | `demo21_selfVerification` | 自验证钩子 |
| 22 | `demo22_progressiveSkills` | 渐进式技能加载 |
| 23 | `demo23_memoryMd` | MEMORY.md 标准 |
| 24 | `demo24_vectorSearch` | 向量检索 |
| 25 | `demo25_semanticStuckDetection` | 语义卡住检测 |
| 26 | `demo26_guardrails` | Guardrails PII 检测 |
| 27 | `demo27_cpuRouter` | CPU Router |

### 运行示例

```bash
cd packages/sdk-java

# 编译 SDK
gradle build

# 运行示例（需要配置 API Key）
java -cp harness-sdk-all/build/libs/*:examples/ com.harness.examples.SdkFeatureDemo
```

### MockLLMClient

测试使用内置的 MockLLMClient 模拟 LLM 响应：

```java
static class MockLLMClient implements LLMClient {
    private final String response;
    
    @Override
    public String modelName() { return "mock-model"; }
    
    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return new LLMResponse(response);
    }
    
    @Override
    public CompletableFuture<LLMResponse> callAsync(...) { ... }
    
    @Override
    public void stream(..., StreamCallback onChunk) { ... }
}
```

### 单元测试清单

| 模块 | 测试文件 | 覆盖内容 |
|------|---------|---------|
| Core | `ModelPresetTest.java` | ModelPreset, ModelPresets |
| Integration | `AgentHarnessTest.java` | AgentHarness 生命周期 |
| LLM | `MockResponseTest.java` | Mock 响应处理 |
| Memory | `MemoryEntryTest.java` | MemoryEntry, retrieval strength |
| Memory | `MemoryScoringConfigTest.java` | 评分配置 |
| Skills | `SkillLoaderTest.java` | 技能加载 |
| Skills | `SkillRegistryTest.java` | 技能注册与匹配 |