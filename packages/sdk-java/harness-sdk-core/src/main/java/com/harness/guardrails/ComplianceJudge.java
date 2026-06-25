package com.harness.guardrails;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Compliance Judge - interacts with LLM-based content safety service.
 *
 * Implements Layer 2 semantic content safety detection with caching.
 *
 * Example:
 * <pre>
 * GuardrailConfig.JudgeConfig config = new GuardrailConfig.JudgeConfig(
 *     true, "http://localhost:8000/v1/chat/completions", "qwen3guard-8b", 5.0, "pass", null
 * );
 *
 * ComplianceJudge judge = new ComplianceJudge(config);
 *
 * JudgeResult result = judge.judge("Content to check").join();
 * if (!result.isSafe()) {
 *     System.out.println("Risk detected: " + result.riskLevel());
 * }
 * </pre>
 */
public class ComplianceJudge {

    private static final Logger logger = LoggerFactory.getLogger(ComplianceJudge.class);

    private static final int CACHE_TTL = 300;  // 5 minutes
    private static final int CACHE_MAX_SIZE = 1000;

    // Fast detection prompt (no CoT, optimized for speed)
    private static final String FAST_JUDGE_PROMPT = """
        你是内容安全审核系统。请快速判断以下内容是否安全。

        内容：
        %s

        请直接输出 JSON 格式结果（不要输出其他内容）：
        {"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}

        风险类别可选：prompt_injection, harmful_content, pii_leakage, bias_discrimination, illegal_content, other""";

    // Context-aware detection prompt
    private static final String CONTEXT_JUDGE_PROMPT = """
        你是内容安全审核系统。请结合上下文判断用户输入是否安全。

        上下文：
        %s

        用户输入：
        %s

        请直接输出 JSON 格式结果（不要输出其他内容）：
        {"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}""";

    // Quick score prompt for stream interception
    private static final String QUICK_SCORE_PROMPT = """
        请快速评估以下内容的安全程度，只输出一个 0-1 之间的数字（0=完全危险，1=完全安全）：

        %s

        安全分数：""";

    private final GuardrailConfig.JudgeConfig config;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final Map<String, CacheEntry<GuardrailExceptions.JudgeResult>> judgeCache;
    private final Map<String, CacheEntry<Double>> scoreCache;

    public ComplianceJudge(GuardrailConfig.JudgeConfig config) {
        this.config = config;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds((long) config.getTimeout()))
            .build();
        this.objectMapper = new ObjectMapper();
        this.judgeCache = new ConcurrentHashMap<>();
        this.scoreCache = new ConcurrentHashMap<>();

        logger.info("ComplianceJudge initialized, endpoint: {}", config.getEndpoint());
    }

    /**
     * Judge content safety.
     *
     * @param content Content to check
     * @return CompletableFuture with JudgeResult
     */
    public CompletableFuture<GuardrailExceptions.JudgeResult> judge(String content) {
        return judge(content, null);
    }

    /**
     * Judge content safety with context.
     *
     * @param content Content to check
     * @param context Optional context (e.g., conversation history)
     * @return CompletableFuture with JudgeResult
     */
    public CompletableFuture<GuardrailExceptions.JudgeResult> judge(String content, String context) {
        if (!config.isEnabled()) {
            return CompletableFuture.completedFuture(GuardrailExceptions.JudgeResult.safe());
        }

        String cacheKey = makeCacheKey(content, context);

        // Check cache
        CacheEntry<GuardrailExceptions.JudgeResult> cached = judgeCache.get(cacheKey);
        if (cached != null && !cached.isExpired()) {
            logger.debug("Judge cache hit for content hash: {}...", cacheKey.substring(0, Math.min(16, cacheKey.length())));
            return CompletableFuture.completedFuture(cached.value);
        }

        // Build prompt
        String prompt = context != null && !context.isEmpty()
            ? String.format(CONTEXT_JUDGE_PROMPT, context, content)
            : String.format(FAST_JUDGE_PROMPT, content);

        // Call Judge service
        return callJudgeService(prompt)
            .thenApply(result -> {
                // Cache result
                judgeCache.put(cacheKey, new CacheEntry<>(result, CACHE_TTL));
                logger.debug("Judge result cached: {}...", cacheKey.substring(0, Math.min(16, cacheKey.length())));
                return result;
            });
    }

    /**
     * Quick safety score check (for stream interception).
     *
     * Returns a score between 0-1, where 1 is completely safe and 0 is completely unsafe.
     * This method is optimized for speed and doesn't return detailed analysis.
     *
     * @param content Content to check
     * @return CompletableFuture with safety score
     */
    public CompletableFuture<Double> quickCheck(String content) {
        if (!config.isEnabled()) {
            return CompletableFuture.completedFuture(1.0);
        }

        String cacheKey = makeCacheKey(content, null);

        // Check cache
        CacheEntry<Double> cached = scoreCache.get(cacheKey);
        if (cached != null && !cached.isExpired()) {
            logger.debug("Quick check cache hit: {}...", cacheKey.substring(0, Math.min(16, cacheKey.length())));
            return CompletableFuture.completedFuture(cached.value);
        }

        String prompt = String.format(QUICK_SCORE_PROMPT, content);

        return callQuickScoreService(prompt)
            .thenApply(score -> {
                // Cache result
                scoreCache.put(cacheKey, new CacheEntry<>(score, CACHE_TTL));
                return score;
            });
    }

    // -------------------------------------------------------------------------

    private CompletableFuture<GuardrailExceptions.JudgeResult> callJudgeService(String prompt) {
        try {
            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", config.getModel());
            requestBody.put("messages", List.of(Map.of("role", "user", "content", prompt)));
            requestBody.put("temperature", 0.1);
            requestBody.put("max_tokens", 256);

            String jsonBody = objectMapper.writeValueAsString(requestBody);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(config.getEndpoint()))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .timeout(Duration.ofSeconds((long) config.getTimeout()))
                .build();

            return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8))
                .thenApply(response -> {
                    if (response.statusCode() >= 400) {
                        throw new GuardrailExceptions.JudgeUnavailableException(
                            config.getEndpoint(),
                            "HTTP " + response.statusCode()
                        );
                    }

                    try {
                        JsonNode root = objectMapper.readTree(response.body());
                        String assistantMessage = root.path("choices").get(0).path("message").path("content").asText();
                        return parseJudgeResponse(assistantMessage);
                    } catch (Exception e) {
                        logger.warn("Failed to parse judge response: {}", e.getMessage());
                        return GuardrailExceptions.JudgeResult.safe();
                    }
                })
                .exceptionally(e -> {
                    if (e.getCause() instanceof java.net.http.HttpTimeoutException) {
                        throw new GuardrailExceptions.JudgeTimeoutException(config.getTimeout(), config.getEndpoint());
                    }
                    throw new GuardrailExceptions.JudgeUnavailableException(config.getEndpoint(), e.getMessage());
                });

        } catch (Exception e) {
            return CompletableFuture.failedFuture(
                new GuardrailExceptions.JudgeUnavailableException(config.getEndpoint(), e.getMessage())
            );
        }
    }

    private CompletableFuture<Double> callQuickScoreService(String prompt) {
        try {
            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", config.getModel());
            requestBody.put("messages", List.of(Map.of("role", "user", "content", prompt)));
            requestBody.put("temperature", 0.1);
            requestBody.put("max_tokens", 10);

            String jsonBody = objectMapper.writeValueAsString(requestBody);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(config.getEndpoint()))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .timeout(Duration.ofSeconds((long) config.getTimeout()))
                .build();

            return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8))
                .thenApply(response -> {
                    try {
                        JsonNode root = objectMapper.readTree(response.body());
                        String assistantMessage = root.path("choices").get(0).path("message").path("content").asText().trim();

                        // Try to parse as number
                        try {
                            double score = Double.parseDouble(assistantMessage.split("\\s+")[0]);
                            return Math.max(0.0, Math.min(1.0, score));
                        } catch (NumberFormatException e) {
                            logger.warn("Failed to parse quick_check score: {}", assistantMessage);
                            return 0.5;
                        }
                    } catch (Exception e) {
                        logger.warn("Failed to parse quick check response: {}", e.getMessage());
                        return 0.5;
                    }
                })
                .exceptionally(e -> {
                    logger.warn("Quick check error: {}, defaulting to safe", e.getMessage());
                    return 0.5;
                });

        } catch (Exception e) {
            return CompletableFuture.completedFuture(0.5);
        }
    }

    private GuardrailExceptions.JudgeResult parseJudgeResponse(String response) {
        try {
            // Try to parse as JSON directly
            JsonNode data = objectMapper.readTree(response);

            return new GuardrailExceptions.JudgeResult(
                data.path("is_safe").asBoolean(true),
                data.path("risk_level").asText("safe"),
                parseStringList(data.path("risk_categories")),
                data.path("reason").asText(""),
                data.path("confidence").asDouble(0.5)
            );

        } catch (Exception e) {
            // Try to extract JSON from text
            try {
                int start = response.indexOf('{');
                int end = response.lastIndexOf('}');
                if (start >= 0 && end > start) {
                    String json = response.substring(start, end + 1);
                    JsonNode data = objectMapper.readTree(json);

                    return new GuardrailExceptions.JudgeResult(
                        data.path("is_safe").asBoolean(true),
                        data.path("risk_level").asText("safe"),
                        parseStringList(data.path("risk_categories")),
                        data.path("reason").asText(""),
                        data.path("confidence").asDouble(0.5)
                    );
                }
            } catch (Exception ex) {
                // Fall through
            }

            logger.warn("Failed to parse judge response: {}", response);
            return GuardrailExceptions.JudgeResult.safe();
        }
    }

    private List<String> parseStringList(JsonNode node) {
        if (!node.isArray()) {
            return List.of();
        }
        List<String> result = new ArrayList<>();
        for (JsonNode item : node) {
            result.add(item.asText());
        }
        return result;
    }

    private String makeCacheKey(String content, String context) {
        try {
            String keyData = content + "||" + (context != null ? context : "");
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(keyData.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(hash);
        } catch (Exception e) {
            return UUID.randomUUID().toString();
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    /**
     * Close the HTTP client.
     */
    public void close() {
        // HttpClient doesn't need explicit close in Java 11+
        judgeCache.clear();
        scoreCache.clear();
    }

    // Cache entry with TTL
    private static class CacheEntry<T> {
        final T value;
        final long expiresAt;

        CacheEntry(T value, int ttlSeconds) {
            this.value = value;
            this.expiresAt = System.currentTimeMillis() + ttlSeconds * 1000L;
        }

        boolean isExpired() {
            return System.currentTimeMillis() > expiresAt;
        }
    }
}
