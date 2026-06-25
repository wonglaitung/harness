package com.harness.llm;

import java.util.*;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HarnessConfig.RoutingConfig;
import com.harness.types.LLMResponse;
import com.harness.types.TokenUsage;

/**
 * LLM client that routes requests to different downstream models.
 *
 * Uses a lightweight CPU model to classify request complexity,
 * then forwards to the appropriate downstream model.
 *
 * Usage:
 * <pre>
 * RoutingConfig config = RoutingConfig.builder()
 *     .highModel("gpt-4o")
 *     .lowModel("gpt-4o-mini")
 *     .routerModelPath("models/qwen2.5-1.5b.gguf")
 *     .build();
 *
 * RoutingLLMClient client = new RoutingLLMClient(
 *     config,
 *     new OpenAIClient("key", "gpt-4o"),
 *     new OpenAIClient("key", "gpt-4o-mini")
 * );
 *
 * LLMResponse response = client.call(messages).join();
 * </pre>
 */
public class RoutingLLMClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(RoutingLLMClient.class);

    private final RoutingConfig config;
    private final LLMClient highClient;
    private final LLMClient lowClient;

    // Track last routing decision for observability
    private volatile String lastRoute = "";
    private volatile double lastRouterLatencyMs = 0.0;

    public RoutingLLMClient(RoutingConfig config, LLMClient highClient, LLMClient lowClient) {
        this.config = config;
        this.highClient = highClient;
        this.lowClient = lowClient;
    }

    @Override
    public String modelName() {
        return String.format("routing(high=%s, low=%s)", config.getHighModel(), config.getLowModel());
    }

    /**
     * Route the request and call the appropriate downstream model.
     */
    @Override
    public CompletableFuture<LLMResponse> call(List<Message> messages) {
        return call(messages, null, null);
    }

    /**
     * Route the request and call the appropriate downstream model.
     */
    @Override
    public CompletableFuture<LLMResponse> call(List<Message> messages, List<ToolDefinition> tools, String system) {
        return CompletableFuture.supplyAsync(() -> {
            // Extract routing input
            String userMessage = extractUserMessage(messages);
            String conversationHistory = extractConversationHistory(messages);

            String route;
            double routerLatencyMs = 0.0;

            if (userMessage == null || userMessage.isEmpty()) {
                logger.warn("No user message found, defaulting to high");
                route = config.getDefaultRoute();
            } else {
                // Build routing prompt
                String routePrompt = buildRoutePrompt(userMessage, conversationHistory);

                // Get routing decision
                long routerStart = System.currentTimeMillis();
                route = getRouteDecision(routePrompt);
                routerLatencyMs = (System.currentTimeMillis() - routerStart);
            }

            // Store for observability
            this.lastRoute = route;
            this.lastRouterLatencyMs = routerLatencyMs;

            logger.info("Routing decision: {} (latency: {:.1f}ms)", route, routerLatencyMs);

            // Select downstream client
            LLMClient client = "high".equals(route) ? highClient : lowClient;

            // Call downstream
            return client.call(messages, tools, system).join();
        });
    }

    /**
     * Extract the last user message for routing.
     */
    private String extractUserMessage(List<Message> messages) {
        for (int i = messages.size() - 1; i >= 0; i--) {
            Message msg = messages.get(i);
            if ("user".equals(msg.role())) {
                return msg.content();
            }
        }
        return null;
    }

    /**
     * Extract conversation history for routing.
     */
    private String extractConversationHistory(List<Message> messages) {
        int historyWindow = config.getHistoryWindow();
        int start = Math.max(0, messages.size() - historyWindow);

        StringBuilder sb = new StringBuilder();
        for (int i = start; i < messages.size(); i++) {
            Message msg = messages.get(i);
            String preview = msg.content();
            if (preview.length() > 200) {
                preview = preview.substring(0, 200) + "...";
            }
            sb.append("[").append(msg.role()).append("]: ").append(preview).append("\n");
        }

        return sb.length() > 0 ? sb.toString() : "(无历史对话)";
    }

    /**
     * Build the routing prompt.
     */
    private String buildRoutePrompt(String userMessage, String conversationHistory) {
        return String.format(
            "你是一个请求路由器。根据用户请求的复杂度，决定应该使用哪个模型处理。\n\n" +
            "可用模型：\n" +
            "- high: %s\n" +
            "- low: %s\n\n" +
            "判断标准：\n" +
            "1. 需要多步推理 → high\n" +
            "2. 需要调用多个工具 → high\n" +
            "3. 需要代码生成或修改 → high\n" +
            "4. 需要深度分析或报告 → high\n" +
            "5. 简单问答、查询、翻译 → low\n\n" +
            "**重要**：当不确定时，选择 high。宁可浪费也不要牺牲质量。\n\n" +
            "历史对话：\n%s\n\n" +
            "当前用户请求：\n%s\n\n" +
            "请输出路由决策（仅输出一个标签：high 或 low）：",
            config.getHighDescription(),
            config.getLowDescription(),
            conversationHistory,
            userMessage
        );
    }

    /**
     * Get routing decision from the router model.
     *
     * Note: In a real implementation, this would call the router model.
     * For now, we use a simple heuristic based on message length and keywords.
     */
    private String getRouteDecision(String prompt) {
        // Simple heuristic routing (can be replaced with actual router model)
        String lowerPrompt = prompt.toLowerCase();

        // Keywords that suggest complex tasks
        String[] complexKeywords = {
            "分析", "设计", "实现", "重构", "优化",
            "debug", "debugging", "fix", "修复",
            "架构", "系统", "多个", "复杂",
            "代码", "实现", "编写", "开发"
        };

        for (String keyword : complexKeywords) {
            if (lowerPrompt.contains(keyword)) {
                return "high";
            }
        }

        // Check message length
        if (prompt.length() > 500) {
            return "high";
        }

        // Default based on config
        return config.getDefaultRoute();
    }

    /**
     * Parse the route label from router response.
     */
    private String parseRouteLabel(String content) {
        if (content == null) {
            return config.getDefaultRoute();
        }

        String lower = content.toLowerCase().trim();

        if (lower.contains("high")) {
            return "high";
        } else if (lower.contains("low")) {
            return "low";
        }

        logger.warn("Could not parse route label from: {}, defaulting to {}", content.substring(0, Math.min(50, content.length())), config.getDefaultRoute());
        return config.getDefaultRoute();
    }

    /**
     * Get last routing decision.
     */
    public String getLastRoute() {
        return lastRoute;
    }

    /**
     * Get last router latency in milliseconds.
     */
    public double getLastRouterLatencyMs() {
        return lastRouterLatencyMs;
    }
}
