/**
 * Multi-Agent Workflow 示例 — WorkflowEngine 有向无环图（DAG）编排。
 *
 * 演示：将一个复杂任务拆分为有依赖关系的步骤，由引擎按依赖顺序/并行执行，
 * 并通过黑名单板（SharedStateStore）在步骤间传递产物。
 *
 * 运行方式（无需真实 LLM，使用 MockLLMClient）：
 *     cd packages/sdk-java && ./gradlew :harness-sdk-integration:runExample --args=MultiAgentWorkflow
 */
package com.harness.examples;

import com.harness.integration.AgentHarness;
import com.harness.llm.MockLLMClient;
import com.harness.llm.MockResponse;
import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalResult;
import com.harness.memory.SharedStateStore;
import com.harness.orchestrator.ExecutionMode;
import com.harness.orchestrator.WorkflowConfig;
import com.harness.orchestrator.WorkflowEngine;
import com.harness.orchestrator.WorkflowResult;
import com.harness.orchestrator.WorkflowStep;
import com.harness.types.LoopResult;
import com.harness.types.Session;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import java.util.function.Function;

public class MultiAgentWorkflow {

    private static GoalLoop.AgentRunner createRunner(List<String> canned) {
        MockLLMClient client = new MockLLMClient("mock-workflow");
        client.setResponses(canned.stream().map(MockResponse::text).toList());

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

    public static void main(String[] args) {
        System.out.println("Multi-Agent Workflow 示例（使用 MockLLMClient 离线运行）");
        System.out.println("=".repeat(60));

        GoalLoop.AgentRunner runner = createRunner(Arrays.asList(
                "分析完成：识别出 3 个核心模块。",
                "Lint 完成：0 error，2 warning。",
                "测试完成：10 passed。",
                "审查完成：代码可合并。"));

        // 步骤间通过黑板共享产物（非 P2P）
        SharedStateStore store = new SharedStateStore();
        WorkflowEngine engine = new WorkflowEngine(runner, store);

        WorkflowConfig config = WorkflowConfig.builder()
                .name("release-pipeline")
                .description("代码发布流水线：分析 -> lint -> 测试 -> 审查")
                .addStep(WorkflowStep.builder()
                        .name("analyze")
                        .goal("分析代码仓库结构，识别核心模块")
                        .mode(ExecutionMode.SEQUENTIAL)
                        .maxIterations(3)
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("lint")
                        .goal("运行静态检查，导出问题列表")
                        .addDependsOn("analyze")
                        .maxIterations(3)
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("test")
                        .goal("运行单元测试，导出通过率")
                        .addDependsOn("analyze")
                        .maxIterations(3)
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("review")
                        .goal("基于 lint 与测试结果给出综合评审")
                        .addDependsOn("lint")
                        .addDependsOn("test")
                        .customVerifier((GoalResult r) -> r.finalResponse() != null
                                && r.finalResponse().contains("可合并"))
                        .maxIterations(3)
                        .build())
                .build();

        engine.execute(config).thenAccept(result -> {
            System.out.println("\n工作流结果: " + (result.isSuccess() ? "成功" : "失败"));
            System.out.println("状态: " + result.getStatus());
            System.out.println("总耗时: " + String.format("%.1f", result.getDurationSeconds()) + "s");
            if (result.getError() != null) {
                System.out.println("错误: " + result.getError());
            }
            System.out.println("\n各步骤状态:");
            for (Map.Entry<String, ?> entry : result.getSteps().entrySet()) {
                System.out.println("  " + entry.getKey() + " -> " + entry.getValue());
            }
            System.out.println("\n黑板记录数: " + store.listItems().size());
        }).join();

        System.out.println("=".repeat(60));
        System.out.println("示例运行完成");
    }
}
