/**
 * Multi-Agent 流式协作示例 — AgentHarness.stream / streamGoal + 黑板。
 *
 * 演示：通过结构化 StreamEvent 信封（source/category/seq/event_id/parent_id）
 * 消费流式输出，并将目标完成结果写入黑板（SharedStateStore）。
 *
 * 运行方式（无需真实 LLM，使用 MockLLMClient）：
 *     cd packages/sdk-java && ./gradlew :harness-sdk-integration:runExample --args=MultiAgentStreamingTeam
 */
package com.harness.examples;

import com.harness.core.StreamEvent;
import com.harness.integration.AgentHarness;
import com.harness.llm.MockLLMClient;
import com.harness.llm.MockResponse;
import com.harness.loop.types.GoalResult;
import com.harness.memory.BlackboardItem;
import com.harness.memory.SharedStateStore;
import com.harness.types.TokenUsage;

import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

public class MultiAgentStreamingTeam {

    /**
     * 打印一个 StreamEvent 的结构化信封。
     */
    private static void printEvent(StreamEvent ev) {
        StringBuilder sb = new StringBuilder();
        sb.append("  StreamEvent[type=").append(ev.type())
                .append(", source=").append(ev.source())
                .append(", category=").append(ev.category())
                .append(", seq=").append(ev.seq());
        if (ev.eventId() != null) sb.append(", eventId=").append(ev.eventId());
        if (ev.parentId() != null) sb.append(", parentId=").append(ev.parentId());
        if (ev.text() != null) sb.append(", text='").append(truncate(ev.text(), 50)).append('\'');
        if (ev.achieved() != null) sb.append(", achieved=").append(ev.achieved());
        sb.append(']');
        System.out.println(sb);
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }

    public static void main(String[] args) {
        System.out.println("Multi-Agent 流式协作示例（使用 MockLLMClient 离线运行）");
        System.out.println("=".repeat(60));

        MockLLMClient client = new MockLLMClient("mock-streaming");
        client.setResponses(List.of(
                MockResponse.text("我将先分析任务，再逐步实施。"),
                MockResponse.text("实施完成：已生成登录接口与前端页面。")));

        AgentHarness harness = AgentHarness.builder()
                .llmClient(client)
                .build();

        SharedStateStore store = new SharedStateStore();

        // 1) 单 agent 流式输出
        System.out.println("\n[1] AgentHarness.stream — 结构化流式输出:");
        Consumer<StreamEvent> printer = MultiAgentStreamingTeam::printEvent;
        harness.stream("请实现用户登录功能", printer).join();

        // 2) 目标驱动流式 + 黑板写入
        System.out.println("\n[2] AgentHarness.streamGoal — goal_* 信封 + 黑板:");
        GoalResult finalResult = harness.streamGoal("实现用户登录：JWT + 密码加密 + 登录页", ev -> {
            printEvent(ev);
            if ("goal_done".equals(ev.type()) && ev.goalResult() instanceof GoalResult gr) {
                // 目标完成 -> 写入黑板（权威写入，记录 provenance）
                BlackboardItem item = BlackboardItem.create(
                        "goal_outcome",
                        Map.of(
                                "goal", gr.goal(),
                                "status", gr.status().name(),
                                "achieved", gr.status().name().equals("ACHIEVED")),
                        "goal_loop",
                        0.95f,
                        "orchestrator");
                store.put(item);
                System.out.println("  [黑板] 已写入 goal_outcome: " + item.id());
            }
        }).join();

        System.out.println("\n目标结果: " + (finalResult.status() != null ? finalResult.status() : "null"));
        System.out.println("黑板记录数: " + store.listItems().size());

        System.out.println("=".repeat(60));
        System.out.println("示例运行完成");
    }
}
