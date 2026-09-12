/**
 * Multi-Agent Blackboard 示例 — 基于 SharedStateStore 的黑板协作。
 *
 * 演示：多个 agent 通过「黑板」（共享状态存储）通信，而非 P2P 直连；
 * 使用 CAS（writeIfVersion）并发写入并检测冲突，权威写入记录 provenance。
 *
 * 运行方式（无需真实 LLM，使用 MockLLMClient）：
 *     cd packages/sdk-java && ./gradlew :harness-sdk-integration:runExample --args=MultiAgentBlackboard
 */
package com.harness.examples;

import com.harness.integration.AgentHarness;
import com.harness.llm.MockLLMClient;
import com.harness.llm.MockResponse;
import com.harness.loop.GoalLoop;
import com.harness.memory.BlackboardItem;
import com.harness.memory.SharedStateStore;
import com.harness.types.LoopResult;
import com.harness.types.Session;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

public class MultiAgentBlackboard {

    private static GoalLoop.AgentRunner createRunner(List<String> canned) {
        MockLLMClient client = new MockLLMClient("mock-blackboard");
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

    /** 让 runner 执行一个 agent 任务（在此仅用于演示 agent 可用性）。 */
    private static void runAgent(GoalLoop.AgentRunner runner, String role, String task) {
        LoopResult result = runner.run(task, "bb-" + role).join();
        String resp = result.content() != null ? result.content() : "";
        System.out.println("  [" + role + "] " + (resp.length() > 70 ? resp.substring(0, 70) + "..." : resp));
    }

    public static void main(String[] args) {
        System.out.println("Multi-Agent Blackboard 示例（使用 MockLLMClient 离线运行）");
        System.out.println("=".repeat(60));

        GoalLoop.AgentRunner runner = createRunner(Arrays.asList(
                "分析完成：模块 A 存在空指针风险。",
                "审查完成：建议增加防御性判空。"));

        SharedStateStore store = new SharedStateStore();

        // 1) 分析员写入初始结论（权威写入，记录 provenance）
        BlackboardItem analysis = BlackboardItem.create(
                "analysis",
                Map.of("summary", "模块 A 存在空指针风险", "risk", "high"),
                "analyzer",
                0.9f,
                "orchestrator");
        store.put(analysis);
        System.out.println("\n[黑板] 分析员写入: " + analysis.id());

        // 2) 两个 agent 并发基于同一版本更新（CAS 检测冲突）
        int baseVersion = store.getVersion(analysis.id());
        System.out.println("[黑板] 当前版本: " + baseVersion);

        boolean reviewerOk = store.writeIfVersion(analysis.id(),
                Map.of("summary", "模块 A 存在空指针风险", "risk", "high", "review", "建议判空"),
                baseVersion);
        // 第二个写入使用过期版本，应被拒绝 -> 冲突
        boolean staleOk = store.writeIfVersion(analysis.id(),
                Map.of("summary", "模块 A 存在空指针风险", "risk", "medium"),
                baseVersion);

        System.out.println("[CAS] reviewer 更新: " + (reviewerOk ? "成功" : "失败"));
        System.out.println("[CAS] 过期写入(并发): " + (staleOk ? "成功(异常)" : "被拒绝(冲突)"));

        // 3) 在新版本上重试
        int newVersion = store.getVersion(analysis.id());
        boolean retryOk = store.writeIfVersion(analysis.id(),
                Map.of("summary", "模块 A 存在空指针风险", "risk", "high", "review", "已补充判空"),
                newVersion);
        System.out.println("[CAS] 基于新版本重试: " + (retryOk ? "成功" : "失败"));

        // 4) 展示黑板状态与冲突
        System.out.println("\n[黑板] 当前记录数: " + store.listItems().size());
        for (BlackboardItem item : store.listItems()) {
            System.out.println("  item=" + item.id()
                    + " type=" + item.type()
                    + " version=" + item.baseVersion()
                    + " content=" + item.content());
        }
        System.out.println("[冲突] 检测到的冲突数: " + store.getConflicts().size());
        store.getConflicts().forEach(c -> System.out.println("  conflict: " + c));

        System.out.println("\n[Agent] 触发一次协作任务以验证 runner 可用:");
        runAgent(runner, "reviewer", "审查模块 A 的判空方案");

        System.out.println("=".repeat(60));
        System.out.println("示例运行完成");
    }
}
