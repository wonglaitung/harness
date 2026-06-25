package com.harness.guardrails;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Token-level stream interceptor.
 *
 * Real-time content safety monitoring during streaming output.
 * Detects and interrupts harmful content during generation.
 *
 * Example:
 * <pre>
 * ComplianceJudge judge = new ComplianceJudge(judgeConfig);
 * StreamInterceptor interceptor = new StreamInterceptor(judge, streamConfig);
 *
 * // Check streaming content
 * for (String chunk : stream) {
 *     InterceptResult result = interceptor.checkChunk(chunk).join();
 *     if (result.shouldStop()) {
 *         break;
 *     }
 *     yield chunk;
 * }
 * </pre>
 */
public class StreamInterceptor {

    private static final Logger logger = LoggerFactory.getLogger(StreamInterceptor.class);

    private final ComplianceJudge judge;
    private final GuardrailConfig.StreamInterceptConfig config;
    private final ObjectMapper objectMapper;

    public StreamInterceptor(ComplianceJudge judge, GuardrailConfig.StreamInterceptConfig config) {
        this.judge = judge;
        this.config = config;
        this.objectMapper = new ObjectMapper();

        logger.info(
            "StreamInterceptor initialized: checkInterval={}, safetyThreshold={}",
            config.getCheckInterval(),
            config.getSafetyThreshold()
        );
    }

    /**
     * Intercept result.
     */
    public static class InterceptResult {
        private final boolean shouldStop;
        private final double safetyScore;
        private final String reason;
        private final int tokensChecked;

        public InterceptResult(boolean shouldStop, double safetyScore, String reason, int tokensChecked) {
            this.shouldStop = shouldStop;
            this.safetyScore = safetyScore;
            this.reason = reason;
            this.tokensChecked = tokensChecked;
        }

        public boolean shouldStop() { return shouldStop; }
        public double safetyScore() { return safetyScore; }
        public String reason() { return reason; }
        public int tokensChecked() { return tokensChecked; }
    }

    /**
     * Check a streaming chunk for safety.
     *
     * @param chunk The SSE data line
     * @param buffer Accumulated content buffer
     * @param tokenCount Current token count
     * @return CompletableFuture with InterceptResult
     */
    public CompletableFuture<InterceptResult> checkChunk(String chunk, StringBuilder buffer, int tokenCount) {
        if (!config.isEnabled()) {
            return CompletableFuture.completedFuture(
                new InterceptResult(false, 1.0, "Stream interception disabled", tokenCount)
            );
        }

        // Extract text from SSE
        String text = extractTextFromSse(chunk);
        if (text != null && !text.isEmpty()) {
            buffer.append(text);
        }

        // Check if we should run safety check
        boolean shouldCheck = tokenCount >= config.getMinTokensBeforeCheck() &&
                              tokenCount % config.getCheckInterval() == 0;

        if (!shouldCheck) {
            return CompletableFuture.completedFuture(
                new InterceptResult(false, 1.0, "Not checking yet", tokenCount)
            );
        }

        // Run quick check
        return judge.quickCheck(buffer.toString())
            .thenApply(score -> {
                logger.debug("Stream safety check: tokens={}, score={}", tokenCount, score);

                if (score < config.getSafetyThreshold()) {
                    logger.warn(
                        "Stream interrupted: score={} < threshold={}, tokens={}",
                        score, config.getSafetyThreshold(), tokenCount
                    );
                    return new InterceptResult(true, score, "Content risk detected", tokenCount);
                }

                return new InterceptResult(false, score, "Content safe", tokenCount);
            })
            .exceptionally(e -> {
                logger.warn("Safety check failed: {}, continuing stream", e.getMessage());
                return new InterceptResult(false, 0.5, "Check failed: " + e.getMessage(), tokenCount);
            });
    }

    /**
     * Check content safety (non-streaming).
     *
     * @param content Content to check
     * @return CompletableFuture with InterceptResult
     */
    public CompletableFuture<InterceptResult> checkContent(String content) {
        if (!config.isEnabled()) {
            return CompletableFuture.completedFuture(
                new InterceptResult(false, 1.0, "Stream interception disabled", content.split("\\s+").length)
            );
        }

        return judge.quickCheck(content)
            .thenApply(score -> {
                boolean shouldStop = score < config.getSafetyThreshold();

                return new InterceptResult(
                    shouldStop,
                    score,
                    shouldStop ? "Content risk detected" : "Content safe",
                    content.split("\\s+").length
                );
            })
            .exceptionally(e -> {
                logger.warn("Content check failed: {}", e.getMessage());
                return new InterceptResult(
                    false,
                    0.5,
                    "Check failed: " + e.getMessage(),
                    content.split("\\s+").length
                );
            });
    }

    /**
     * Extract text from SSE line.
     *
     * Supports OpenAI and Claude format SSE data.
     *
     * @param line SSE data line
     * @return Extracted text, or null if not text content
     */
    public String extractTextFromSse(String line) {
        if (line == null || line.isEmpty()) {
            return null;
        }

        line = line.trim();

        // Skip empty lines and non-data lines
        if (!line.startsWith("data: ")) {
            return null;
        }

        String data = line.substring(6);  // Remove "data: " prefix

        // Skip end marker
        if ("[DONE]".equals(data)) {
            return null;
        }

        try {
            JsonNode parsed = objectMapper.readTree(data);

            // OpenAI format
            if (parsed.has("choices")) {
                JsonNode choices = parsed.path("choices");
                if (choices.isArray() && choices.size() > 0) {
                    JsonNode delta = choices.get(0).path("delta");
                    if (delta.has("content")) {
                        return delta.path("content").asText();
                    }
                }
            }

            // Claude format
            if (parsed.has("delta")) {
                JsonNode delta = parsed.path("delta");
                if (delta.has("text")) {
                    return delta.path("text").asText();
                }
            }

            return null;

        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Create interrupt message in SSE format.
     *
     * @param score Safety score
     * @return SSE-formatted interrupt message
     */
    public String createInterruptMessage(double score) {
        String message = String.format(
            "\n\n[内容安全警告：检测到潜在风险内容，输出已中断。安全评分：%.2f]",
            score
        );

        try {
            Map<String, Object> data = Map.of(
                "choices", List.of(Map.of(
                    "delta", Map.of("content", message),
                    "finish_reason", "content_filter",
                    "index", 0
                )),
                "object", "chat.completion.chunk"
            );

            return "data: " + objectMapper.writeValueAsString(data) + "\n\n";
        } catch (Exception e) {
            return "data: {\"choices\":[{\"delta\":{\"content\":\"[Content safety warning]\"},\"finish_reason\":\"content_filter\"}]}\n\n";
        }
    }
}
