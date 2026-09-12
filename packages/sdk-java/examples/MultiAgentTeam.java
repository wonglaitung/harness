/**
 * Multi-Agent Team 示例 — TeamOrchestrator 三种协调模式。
 *
 * 演示：
 *  1. Broadcast 模式：多 agent 同时分析同一任务（多视角）
 *  2. Sequential 模式：agent 按顺序传递结论（pipeline）
 *  3. Hierarchical 模式：leader 动态分配任务给 worker
 *
 * 运行方式（无需真实 LLM，使用 MockLLMClient）：
 *     cd packages/sdk-java && ./gradlew :harness-sdk-integration:runExample --args=MultiAgentTeam
 *
 * 注：本示例通过 MockLLMClient 提供固定回复，可在无 API key 环境运行。
 */
package com.harness.examples;

import com.harness.core.LLMClient;
import com.harness.integration.AgentHarness;
import com.harness.llm.MockLLMClient;
import com.harness.llm.MockResponse;
import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalResult;
import com.harness.orchestrator.AgentRole;
import com.harness.orchestrator.CoordinationMode;
import com.harness.orchestrator.TeamConfig;
import com.harness.orchestrator.TeamOrchestrator;
import com.harness.orchestrator.TeamResult;
import com.harness.types.LoopResult;
import com.harness.types.Session;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

public class MultiAgentTeam {

    /**
     * 用给定的固定回复创建一个离线可运行的 AgentRunner。
     */
    private static GoalLoop.AgentRunner createRunner(List<String> canned) {
        MockLLMClient client = new MockLLMClient("mock-team");
        List<MockResponse> responses = canned.stream().map(MockResponse::text).toList();
        client.setResponses(responses);

        AgentHarness harness = AgentHarness.builder()
                .llmClient(client)
                .build();

        return new GoalLoop.AgentRunner() {
            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
                return harness.run(prompt, sessionId);
            }

            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> progress) {
                return harness.run(prompt, sessionId, progress);
            }

            @Override
            public Session getSession(String sessionId) {
                return harness.getSession(sessionId);
            }

            @Override
            public int getContextWindow() {
                return harness.getConfig().getContextWindow();
            }
        };
    }

    private static void printResult(String title, TeamResult result) {
        System.out.println("\n团队结果: " + (result.isSuccess() ? "成功" : "失败"));
        System.out.println("总耗时: " + String.format("%.1f", result.getDurationSeconds()) + "s");
        if (result.getError() != null) {
            System.out.println("错误: " + result.getError());
        }
        for (Map.Entry<String, GoalResult> entry : result.getAgentResults().entrySet()) {
            String resp = entry.getValue().finalResponse();
            String preview = resp != null && resp.length() > 80 ? resp.substring(0, 80) + "..." : resp;
            System.out.println("  [" + entry.getKey() + "] " + preview);
        }
    }

    /** 示例 1: Broadcast 模式（多视角分析） */
    private static void demoBroadcast() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 1: Broadcast 模式（多视角分析）");
        System.out.println("=".repeat(60));

        GoalLoop.AgentRunner runner = createRunner(Arrays.asList(
                "分析结果：代码结构清晰，模块划分合理。",
                "Lint 结果：发现 3 个 warning，0 个 error。",
                "审查结论：代码质量良好，建议补充单元测试。"));

        TeamOrchestrator orchestrator = new TeamOrchestrator(runner);

        TeamConfig config = TeamConfig.builder()
                .name("review-team")
                .coordinationMode(CoordinationMode.BROADCAST)
                .addRole(AgentRole.builder()
                        .name("security-reviewer")
                        .systemPrompt("你是安全审查员，专注于发现安全漏洞。")
                        .description("审查代码安全性")
                        .build())
                .addRole(AgentRole.builder()
                        .name("perf-reviewer")
                        .systemPrompt("你是性能审查员，专注于发现性能问题。")
                        .description("审查代码性能")
                        .build())
                .addRole(AgentRole.builder()
                        .name("maint-reviewer")
                        .systemPrompt("你是可维护性审查员，专注于代码可读性和结构。")
                        .description("审查代码可维护性")
                        .build())
                .build();

        orchestrator.createTeam(config);
        TeamResult result = orchestrator.run("review-team",
                "审查以下 Python 函数的安全性、性能和可维护性：\n\ndef process(data): return eval(data)").join();

        printResult("Broadcast", result);
    }

    /** 示例 2: Sequential 模式（流水线） */
    private static void demoSequential() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 2: Sequential 模式（流水线）");
        System.out.println("=".repeat(60));

        GoalLoop.AgentRunner runner = createRunner(Arrays.asList(
                "分析结论：auth.py 包含登录与鉴权逻辑。",
                "Lint 结论：发现未使用的导入与一行过长。",
                "综合评审：整体质量良好，建议移除未使用导入。"));

        TeamOrchestrator orchestrator = new TeamOrchestrator(runner);

        TeamConfig config = TeamConfig.builder()
                .name("pipeline")
                .coordinationMode(CoordinationMode.SEQUENTIAL)
                .sharedMemory(true)
                .addRole(AgentRole.builder()
                        .name("analyzer")
                        .systemPrompt("你是代码分析师，分析代码结构并导出关键信息。")
                        .description("分析代码结构")
                        .build())
                .addRole(AgentRole.builder()
                        .name("linter")
                        .systemPrompt("你是 lint 专家，运行代码检查并导出问题列表。")
                        .description("运行 lint 检查")
                        .build())
                .addRole(AgentRole.builder()
                        .name("reviewer")
                        .systemPrompt("你是代码审查员，基于分析和 lint 结果给出综合评审。")
                        .description("综合审查")
                        .build())
                .build();

        orchestrator.createTeam(config);
        TeamResult result = orchestrator.run("pipeline", "审查 src/auth.py 的代码质量").join();

        printResult("Sequential", result);
    }

    /** 示例 3: Hierarchical 模式（动态分工） */
    private static void demoHierarchical() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 3: Hierarchical 模式（动态分工）");
        System.out.println("=".repeat(60));

        GoalLoop.AgentRunner runner = createRunner(Arrays.asList(
                "任务已拆解：后端负责 JWT，前端负责登录页面。",
                "后端实现：完成 JWT 签发与密码哈希。",
                "前端实现：完成登录表单与提交逻辑。"));

        TeamOrchestrator orchestrator = new TeamOrchestrator(runner);

        TeamConfig config = TeamConfig.builder()
                .name("dev-team")
                .coordinationMode(CoordinationMode.HIERARCHICAL)
                .addRole(AgentRole.builder()
                        .name("tech-lead")
                        .systemPrompt("你是技术负责人，分析任务并分配给团队成员。")
                        .description("任务分析和分配")
                        .build())
                .addRole(AgentRole.builder()
                        .name("backend-dev")
                        .systemPrompt("你是后端开发，专注于 API 和数据库。")
                        .description("后端开发")
                        .build())
                .addRole(AgentRole.builder()
                        .name("frontend-dev")
                        .systemPrompt("你是前端开发，专注于 UI 和交互。")
                        .description("前端开发")
                        .build())
                .build();

        orchestrator.createTeam(config);
        TeamResult result = orchestrator.run("dev-team",
                "实现用户登录功能：包含 JWT 认证、密码加密、登录页面").join();

        printResult("Hierarchical", result);
    }

    public static void main(String[] args) {
        System.out.println("Multi-Agent Team 示例（使用 MockLLMClient 离线运行）");
        demoBroadcast();
        demoSequential();
        demoHierarchical();
        System.out.println("\n" + "=".repeat(60));
        System.out.println("所有示例运行完成");
    }
}
