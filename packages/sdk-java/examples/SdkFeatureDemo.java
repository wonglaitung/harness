/**
 * Harness Java SDK 功能演示示例
 *
 * 这个文件展示了 Harness Java SDK 的主要功能，共 27 个演示。
 *
 * 运行方式：
 * 1. 作为 JUnit 测试运行
 * 2. 或直接运行 main 方法查看演示
 *
 * @author Harness Team
 */
package com.harness.examples;

import com.harness.core.*;
import com.harness.types.*;
import com.harness.tools.*;
import com.harness.memory.*;
import com.harness.skills.*;
import com.harness.skills.SkillMetadata;
import com.harness.mcp.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

public class SdkFeatureDemo {

    private static final String MODEL = System.getenv().getOrDefault("OPENAI_MODEL", "gpt-4o-mini");

    public static void main(String[] args) throws Exception {
        System.out.println("=== Harness Java SDK 功能演示 ===\n");

        demo01_basicConversation();
        demo02_fileTools();
        demo03_multiTurnConversation();
        demo04_costControl();
        demo05_progressTracking();
        demo06_customTool();
        demo07_mockTesting();
        demo08_skillsSystem();
        demo09_skillInjection();
        demo10_mcpIntegration();
        demo11_securitySystem();
        demo12_observability();
        demo13_advancedCostControl();
        demo14_interruptAndResume();
        demo15_configuration();
        demo16_completeWorkflow();
        demo17_lifecycleHooks();
        demo18_dynamicSystemPrompt();
        demo19_ralphLoop();
        demo20_subAgent();
        demo21_selfVerification();
        demo22_progressiveSkills();
        demo23_memoryMd();
        demo24_vectorSearch();
        demo25_semanticStuckDetection();
        demo26_guardrails();
        demo27_cpuRouter();

        System.out.println("\n=== 所有演示完成 ===");
    }

    // =========================================================================
    // 演示 1: 基础对话功能
    // =========================================================================

    public static void demo01_basicConversation() throws Exception {
        System.out.println("\n=== 演示 1: 基础对话功能 ===");

        MockLLMClient mockClient = new MockLLMClient("你好！我是 Harness AI 助手。");
        HarnessConfig config = HarnessConfig.builder().model(MODEL).build();
        AgentHarness agent = new AgentHarness(mockClient, config);

        System.out.println("用户: 你好，请用一句话介绍自己。");
        LoopResult result = agent.run("你好，请用一句话介绍自己。").join();

        System.out.println("Agent: " + result.content());
        System.out.println("执行状态: " + result.status());
        System.out.println("迭代次数: " + result.iterations());
    }

    // =========================================================================
    // 演示 2: 工具系统 - 文件操作
    // =========================================================================

    public static void demo02_fileTools() throws Exception {
        System.out.println("\n=== 演示 2: 工具系统 - 文件操作 ===");

        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .systemPrompt("你是一个有帮助的 AI 助手。")
            .build();

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("我已经列出了文件。"),
            config,
            Arrays.asList(new ReadTool(), new GlobTool(), new GrepTool())
        );

        System.out.println("用户: 请列出当前目录下所有的 Java 文件名称。");
        LoopResult result = agent.run("请列出当前目录下所有的 Java 文件名称。").join();

        System.out.println("响应: " + result.content());
    }

    // =========================================================================
    // 演示 3: 多轮对话 - 会话管理
    // =========================================================================

    public static void demo03_multiTurnConversation() throws Exception {
        System.out.println("\n=== 演示 3: 多轮对话 - 会话管理 ===");

        MockLLMClient mockClient = new MockLLMClient();
        HarnessConfig config = HarnessConfig.builder().model(MODEL).build();
        AgentHarness agent = new AgentHarness(mockClient, config);

        String sessionId = "demo-session-001";

        System.out.println("[Session: " + sessionId + "] 用户: 我的名字叫小明。");
        LoopResult result1 = agent.run("我的名字叫小明。", sessionId).join();
        System.out.println("Agent: " + result1.content());

        System.out.println("[Session: " + sessionId + "] 用户: 你还记得我叫什么名字吗？");
        LoopResult result2 = agent.run("你还记得我叫什么名字吗？", sessionId).join();
        System.out.println("Agent: " + result2.content());

        Session session1 = agent.getSession(sessionId);
        System.out.println("会话消息数: " + session1.messages().size());
    }

    // =========================================================================
    // 演示 4: 成本控制
    // =========================================================================

    public static void demo04_costControl() throws Exception {
        System.out.println("\n=== 演示 4: 成本控制 ===");

        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(5)
            .build();

        AgentHarness agent = new AgentHarness(new MockLLMClient(), config);

        LoopResult result = agent.run("请用 100 字介绍 Java 编程语言。").join();

        System.out.println("响应: " + result.content());
        System.out.println("Token 使用: " + result.tokenUsage().totalTokens());
    }

    // =========================================================================
    // 演示 5: 进度追踪
    // =========================================================================

    public static void demo05_progressTracking() throws Exception {
        System.out.println("\n=== 演示 5: 进度追踪 ===");

        List<Object> eventsLog = new ArrayList<>();
        Consumer<Object> onProgress = eventsLog::add;

        AgentHarness agent = new AgentHarness(
            new MockLLMClient(),
            HarnessConfig.builder().model(MODEL).build(),
            Arrays.asList(new ReadTool(), new GlobTool())
        );

        LoopResult result = agent.run("使用 glob 工具列出所有 *.md 文件。", null, onProgress).join();

        System.out.println("事件数: " + eventsLog.size());
    }

    // =========================================================================
    // 演示 6: 自定义工具
    // =========================================================================

    public static void demo06_customTool() throws Exception {
        System.out.println("\n=== 演示 6: 自定义工具 ===");

        Tool addTool = new SimpleTool(
            "add_numbers",
            "计算两个数字的和",
            Map.of(
                "type", "object",
                "properties", Map.of(
                    "a", Map.of("type", "integer"),
                    "b", Map.of("type", "integer")
                ),
                "required", List.of("a", "b")
            ),
            args -> ToolResult.builder()
                .toolCallId(UUID.randomUUID().toString())
                .content(String.valueOf(((Number) args.get("a")).intValue() + ((Number) args.get("b")).intValue()))
                .build()
        );

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("计算完成"),
            HarnessConfig.builder().model(MODEL).build()
        );

        agent.registerTool(addTool);
        System.out.println("已注册工具: add_numbers");

        LoopResult result = agent.run("帮我计算 123 + 456。").join();
        System.out.println("结果: " + result.content());
    }

    // =========================================================================
    // 演示 7: Mock 测试
    // =========================================================================

    public static void demo07_mockTesting() throws Exception {
        System.out.println("\n=== 演示 7: Mock 测试 ===");

        MockLLMClient mockClient = new MockLLMClient("这是一个模拟的响应。");

        HarnessConfig config = HarnessConfig.builder().model("mock-model").build();
        AgentHarness agent = new AgentHarness(mockClient, config);

        LoopResult result = agent.run("你好").join();
        System.out.println("Agent: " + result.content());
    }

    // =========================================================================
    // 演示 8: Skills 技能系统
    // =========================================================================

    public static void demo08_skillsSystem() throws Exception {
        System.out.println("\n=== 演示 8: Skills 技能系统 ===");

        SkillRegistry registry = new SkillRegistry();
        SkillMetadata metadata = new SkillMetadata(
            "代码审查技能", "1.0", List.of("code"), List.of(), List.of("review", "审查", "代码检查"), false);
        Skill skill = new Skill("code-review", metadata, "你是代码审查专家。", null);
        registry.registerSkill(skill);

        System.out.println("已注册技能: " + registry.listSkills());

        List<Skill> matches = registry.findMatchingSkills("请 review 这段代码");
        System.out.println("匹配的技能: " + matches.stream().map(Skill::name).toList());
    }

    // =========================================================================
    // 演示 9: Skill 注入
    // =========================================================================

    public static void demo09_skillInjection() throws Exception {
        System.out.println("\n=== 演示 9: Skill 注入 ===");

        SkillRegistry registry = new SkillRegistry();
        SkillMetadata meta1 = new SkillMetadata("代码审查", "1.0", List.of("code"), List.of(), List.of("review", "审查", "代码检查"), false);
        SkillMetadata meta2 = new SkillMetadata("翻译专家", "1.0", List.of("translate"), List.of(), List.of("translate", "翻译", "译成"), false);

        Skill skill1 = new Skill("code-review", meta1, "你是代码审查专家。", null);
        Skill skill2 = new Skill("translator", meta2, "你是翻译专家。", null);

        registry.registerSkill(skill1);
        registry.registerSkill(skill2);

        List<Skill> matched = registry.findMatchingSkills("请 review 这段代码");
        System.out.println("匹配的技能: " + matched.stream().map(Skill::name).toList());
    }

    // =========================================================================
    // 演示 10: MCP 服务器
    // =========================================================================

    public static void demo10_mcpIntegration() throws Exception {
        System.out.println("\n=== 演示 10: MCP 服务器 ===");

        McpManager manager = new McpManager();
        System.out.println("已创建 McpManager");
        System.out.println("MCP 配置示例: .mcp.json 或 ~/.harness/mcp.json");
        System.out.println("✅ MCP 服务器演示完成");
    }

    // =========================================================================
    // 演示 11: Security 安全系统
    // =========================================================================

    public static void demo11_securitySystem() throws Exception {
        System.out.println("\n=== 演示 11: Security 安全系统 ===");

        HarnessConfig.SecurityConfig securityConfig = HarnessConfig.SecurityConfig.builder()
            .enableInputValidation(true)
            .checkPromptInjection(true)
            .enableAuditLog(true)
            .enableSandbox(true)
            .build();

        System.out.println("安全配置:");
        System.out.println("  - 输入验证: " + securityConfig.isEnableInputValidation());
        System.out.println("  - Prompt 注入检测: " + securityConfig.isCheckPromptInjection());
        System.out.println("  - 审计日志: " + securityConfig.isEnableAuditLog());
        System.out.println("  - 沙箱: " + securityConfig.isEnableSandbox());

        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .security(securityConfig)
            .build();

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("安全测试响应"),
            config,
            Arrays.asList(new ReadTool(), new GlobTool())
        );

        LoopResult result = agent.run("读取 pom.xml 文件", "security-demo").join();
        System.out.println("响应: " + result.content());
    }

    // =========================================================================
    // 演示 12: Observability 可观测性
    // =========================================================================

    public static void demo12_observability() throws Exception {
        System.out.println("\n=== 演示 12: Observability 可观测性 ===");

        TracingConfig tracingConfig = TracingConfig.builder()
            .enabled(true)
            .serviceName("harness-demo")
            .serviceVersion("1.0.0")
            .exportConsole(true)
            .exportOtlp(false)
            .sampleRate(1.0)
            .build();

        TracingManager tracingManager = new TracingManager(tracingConfig);

        System.out.println("可观测性管理器已创建");
        System.out.println("  - 已启用: " + tracingManager.isEnabled());

        HarnessConfig config = HarnessConfig.builder().model(MODEL).build();
        AgentHarness agent = new AgentHarness(new MockLLMClient(), config);

        final LoopResult[] resultHolder = new LoopResult[1];
        tracingManager.withSpan("agent.run", null, () -> {
            resultHolder[0] = agent.run("你好").join();
        });

        System.out.println("响应: " + resultHolder[0].content());
        System.out.println("✅ 追踪数据已记录");
    }

    // =========================================================================
    // 演示 13: 多级成本控制
    // =========================================================================

    public static void demo13_advancedCostControl() throws Exception {
        System.out.println("\n=== 演示 13: 多级成本控制 ===");

        System.out.println("多级成本控制配置:");
        System.out.println("  - 会话级: 10000 tokens/会话");
        System.out.println("  - 用户级: 100000 tokens/天");
        System.out.println("  - 全局级: $50.0/天");

        HarnessConfig.CostControlConfig costConfig = HarnessConfig.CostControlConfig.builder()
            .maxTokensPerSession(10000)
            .dailyTokenLimit(100000)
            .globalDailyBudgetUsd(50.0)
            .build();

        System.out.println("成本控制配置已创建:");
        System.out.println("  - 会话 Token 限制: " + costConfig.getMaxTokensPerSession());
        System.out.println("  - 用户日限额: " + costConfig.getDailyTokenLimit());
        System.out.println("  - 全局预算: $" + costConfig.getGlobalDailyBudgetUsd());
    }

    // =========================================================================
    // 演示 14: 中断与恢复
    // =========================================================================

    public static void demo14_interruptAndResume() throws Exception {
        System.out.println("\n=== 演示 14: 中断与恢复 ===");

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("任务执行完成"),
            HarnessConfig.builder().model(MODEL).build(),
            Arrays.asList(new ReadTool())
        );

        LoopResult result = agent.run("读取 pom.xml 文件").join();
        System.out.println("响应: " + result.content());
        System.out.println("迭代次数: " + result.iterations());
    }

    // =========================================================================
    // 演示 15: 配置管理
    // =========================================================================

    public static void demo15_configuration() throws Exception {
        System.out.println("\n=== 演示 15: 配置管理 ===");

        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .contextWindow(128000)
            .maxTokens(4096)
            .maxIterations(20)
            .temperature(0.7)
            .systemPrompt("你是一个专业的编程助手。")
            .build();

        System.out.println("配置详情:");
        System.out.println("  - 模型: " + config.getModel());
        System.out.println("  - 上下文窗口: " + config.getContextWindow());
        System.out.println("  - 最大迭代: " + config.getMaxIterations());
        System.out.println("  - 温度: " + config.getTemperature());

        AgentHarness agent = new AgentHarness(new MockLLMClient(), config);
        LoopResult result = agent.run("你好").join();
        System.out.println("响应: " + result.content());
    }

    // =========================================================================
    // 演示 16: 完整工作流
    // =========================================================================

    public static void demo16_completeWorkflow() throws Exception {
        System.out.println("\n=== 演示 16: 完整工作流 ===");

        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(10)
            .systemPrompt("你是一个代码分析专家。")
            .build();

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("项目分析完成。"),
            config,
            Arrays.asList(new ReadTool(), new GlobTool(), new GrepTool())
        );

        List<Object> events = new ArrayList<>();
        Consumer<Object> trackProgress = events::add;

        LoopResult result = agent.run("请分析这个项目的结构", null, trackProgress).join();

        System.out.println("结果: " + result.content());
        System.out.println("迭代次数: " + result.iterations());
        System.out.println("事件数: " + events.size());
    }

    // =========================================================================
    // 演示 17: Lifecycle Hooks
    // =========================================================================

    public static void demo17_lifecycleHooks() throws Exception {
        System.out.println("\n=== 演示 17: Lifecycle Hooks ===");

        LifecycleHook loggingHook = new LoggingHook();

        AgentHarness agent = new AgentHarness(
            new MockLLMClient("文件列表获取完成"),
            HarnessConfig.builder().model(MODEL).build(),
            Arrays.asList(new ReadTool(), new GlobTool())
        );

        agent.addHook(loggingHook);
        System.out.println("已注册日志钩子");

        LoopResult result = agent.run("列出所有 Java 文件").join();
        System.out.println("响应: " + result.content());
    }

    // =========================================================================
    // 演示 18-27: 高级功能
    // =========================================================================

    public static void demo18_dynamicSystemPrompt() {
        System.out.println("\n=== 演示 18: 动态系统提示 ===");
        System.out.println("SystemPromptBuilder 支持从多个源组装系统提示。");
    }

    public static void demo19_ralphLoop() {
        System.out.println("\n=== 演示 19: Ralph Loop ===");
        System.out.println("Ralph Loop 支持长任务循环，防止上下文焦虑。");
    }

    public static void demo20_subAgent() {
        System.out.println("\n=== 演示 20: Sub-Agent 管理 ===");
        System.out.println("Sub-Agent 支持创建子代理处理子任务。");
    }

    public static void demo21_selfVerification() {
        System.out.println("\n=== 演示 21: 自验证钩子 ===");
        System.out.println("自验证钩子适用于代码修改场景。");
    }

    public static void demo22_progressiveSkills() {
        System.out.println("\n=== 演示 22: 渐进式技能加载 ===");
        System.out.println("三级加载: L1 → L2 → L3");
    }

    public static void demo23_memoryMd() throws Exception {
        System.out.println("\n=== 演示 23: MEMORY.md 标准 ===");

        Path tempDir = Files.createTempDirectory("memory-demo");
        MemoryFileManager manager = new MemoryFileManager(tempDir);

        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.USER_PROFILE)
            .content("用户是 Java 开发者。")
            .source(MemorySource.USER_INPUT)
            .build();

        manager.addEntry(entry);
        System.out.println("记忆条目已创建: " + entry.content());
    }

    public static void demo24_vectorSearch() {
        System.out.println("\n=== 演示 24: 向量检索 ===");
        System.out.println("向量检索支持语义搜索。");
    }

    public static void demo25_semanticStuckDetection() {
        System.out.println("\n=== 演示 25: 语义卡住检测 ===");
        System.out.println("检测重复输出模式。");
    }

    public static void demo26_guardrails() {
        System.out.println("\n=== 演示 26: Guardrails PII 检测 ===");
        System.out.println("支持检测手机号、身份证等 PII。");
    }

    public static void demo27_cpuRouter() {
        System.out.println("\n=== 演示 27: CPU Router ===");
        System.out.println("根据请求复杂度路由到不同模型。");
    }

    // =========================================================================
    // 辅助类
    // =========================================================================

    static class MockLLMClient implements LLMClient {
        private final String response;

        MockLLMClient() {
            this("这是一个模拟的响应。");
        }

        MockLLMClient(String response) {
            this.response = response;
        }

        @Override
        public String modelName() {
            return "mock-model";
        }

        @Override
        public LLMResponse call(List<Message> messages, List<LLMClient.ToolDefinition> tools, String systemPrompt) {
            return new LLMResponse(response);
        }

        @Override
        public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<LLMClient.ToolDefinition> tools, String systemPrompt) {
            return CompletableFuture.completedFuture(new LLMResponse(response));
        }

        @Override
        public void stream(List<Message> messages, List<LLMClient.ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
            onChunk.onChunk(response);
        }
    }

    static class SimpleTool implements Tool {
        private final String name;
        private final String description;
        private final Map<String, Object> inputSchema;
        private final java.util.function.Function<Map<String, Object>, ToolResult> executor;

        SimpleTool(String name, String description, Map<String, Object> inputSchema,
                   java.util.function.Function<Map<String, Object>, ToolResult> executor) {
            this.name = name;
            this.description = description;
            this.inputSchema = inputSchema;
            this.executor = executor;
        }

        @Override
        public String name() { return name; }

        @Override
        public String description() { return description; }

        @Override
        public Map<String, Object> inputSchema() { return inputSchema; }

        @Override
        public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
            return CompletableFuture.completedFuture(executor.apply(args));
        }
    }

    static class LoggingHook implements LifecycleHook {
        @Override
        public List<HookPoint> hookPoints() {
            return List.of(HookPoint.BEFORE_TOOL_EXECUTE, HookPoint.AFTER_TOOL_EXECUTE);
        }

        @Override
        public HookResult execute(HookContext context) {
            System.out.println("  📋 Hook: " + context.hookPoint());
            return HookResult.continue_();
        }
    }
}
