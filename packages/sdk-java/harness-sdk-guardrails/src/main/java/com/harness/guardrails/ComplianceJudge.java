package com.harness.guardrails;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.harness.guardrails.exceptions.JudgeTimeoutException;
import com.harness.guardrails.exceptions.JudgeUnavailableException;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * Compliance Judge - interacts with LLM-based content safety service.
 *
 * Uses an LLM (e.g., Qwen3Guard-8B-Stream) to evaluate content safety.
 * Supports quick safety score checks and detailed analysis.
 *
 * Example:
 * <pre>
 * JudgeConfig config = JudgeConfig.builder()
 *     .enabled(true)
 *     .endpoint("http://localhost:8000/v1/chat/completions")
 *     .model("Qwen3Guard-8B")
 *     .timeout(5.0)
 *     .build();
 *
 * ComplianceJudge judge = new ComplianceJudge(config);
 *
 * JudgeResult result = judge.judge("Some content to check");
 * if (!result.isSafe()) {
 *     throw new ContentRiskException(result);
 * }
 *
 * double score = judge.quickCheck("Quick safety score");
 * </pre>
 */
public class ComplianceJudge {

    private static final Logger logger = LoggerFactory.getLogger(ComplianceJudge.class);

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    // Cache configuration
    private static final int CACHE_TTL_SECONDS = 300;  // 5 minutes
    private static final int CACHE_MAX_SIZE = 1000;

    // Prompts
    private static final String FAST_JUDGE_PROMPT = """
        你是内容安全审核系统。请快速判断以下内容是否安全。

        内容：
        %s

        请直接输出 JSON 格式结果（不要输出其他内容）：
        {"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}

        风险类别可选：prompt_injection, harmful_content, pii_leakage, bias_discrimination, illegal_content, other""";

    private static final String CONTEXT_JUDGE_PROMPT = """
        你是内容安全审核系统。请结合上下文判断用户输入是否安全。

        上下文：
        %s

        用户输入：
        %s

        请直接输出 JSON 格式结果（不要输出其他内容）：
        {"is_safe": true/false, "risk_level": "safe/low/medium/high/critical", "risk_categories": ["category1", ...], "reason": "简短原因", "confidence": 0.0-1.0}""";

    private static final String QUICK_SCORE_PROMPT = """
        请快速评估以下内容的安全程度，只输出一个 0-1 之间的数字（0=完全危险，1=完全安全）：

        %s

        安全分数：""";

    private final JudgeConfig config;
    private final OkHttpClient client;
    private final ConcurrentHashMap<String, CachedResult> judgeCache;
    private final ConcurrentHashMap<String, Double> scoreCache;

    /**
     * Cached result with expiry time.
     */
    private record CachedResult(JudgeResult result, long expiryTime) {
        boolean isExpired() {
            return System.currentTimeMillis() > expiryTime;
        }
    }

    /**
     * Create a ComplianceJudge with configuration.
     */
    public ComplianceJudge(JudgeConfig config) {
        this.config = config;
        this.client = new OkHttpClient.Builder()
            .connectTimeout((long) (config.getTimeout() * 1000), TimeUnit.MILLISECONDS)
            .readTimeout((long) (config.getTimeout() * 1000), TimeUnit.MILLISECONDS)
            .writeTimeout((long) (config.getTimeout() * 1000), TimeUnit.MILLISECONDS)
            .build();
        this.judgeCache = new ConcurrentHashMap<>();
        this.scoreCache = new ConcurrentHashMap<>();

        logger.info("ComplianceJudge initialized, endpoint: {}", config.getEndpoint());
    }

    /**
     * Judge content safety.
     *
     * @param content Content to check
     * @return JudgeResult with safety assessment
     */
    public JudgeResult judge(String content) throws JudgeTimeoutException, JudgeUnavailableException {
        return judge(content, null);
    }

    /**
     * Judge content safety with context.
     *
     * @param content Content to check
     * @param context Optional context (conversation history)
     * @return JudgeResult with safety assessment
     */
    public JudgeResult judge(String content, String context) throws JudgeTimeoutException, JudgeUnavailableException {
        // Generate cache key
        String cacheKey = makeCacheKey(content, context);

        // Check cache
        CachedResult cached = judgeCache.get(cacheKey);
        if (cached != null && !cached.isExpired()) {
            logger.debug("Judge cache hit for content hash: {}...", cacheKey.substring(0, Math.min(16, cacheKey.length())));
            return cached.result();
        }

        // Build prompt
        String prompt = context != null && !context.isEmpty()
            ? String.format(CONTEXT_JUDGE_PROMPT, context, content)
            : String.format(FAST_JUDGE_PROMPT, content);

        try {
            // Call Judge service
            String response = callJudgeService(prompt);

            // Parse response
            JudgeResult result = parseJudgeResponse(response);
            logger.info("Judge result: is_safe={}, risk_level={}, confidence={}",
                result.isSafe(), result.riskLevel(), result.confidence());

            // Cache result
            judgeCache.put(cacheKey, new CachedResult(result,
                System.currentTimeMillis() + CACHE_TTL_SECONDS * 1000L));

            return result;

        } catch (JudgeTimeoutException | JudgeUnavailableException e) {
            throw e;
        } catch (Exception e) {
            logger.error("Unexpected error in judge: {}", e.getMessage());
            // Return safe result on unexpected error (conservative)
            return JudgeResult.builder()
                .isSafe(true)
                .riskLevel(JudgeResult.RISK_SAFE)
                .reason("Judge error: " + e.getMessage())
                .confidence(0.5)
                .build();
        }
    }

    /**
     * Quick safety score check (for stream interception).
     *
     * @param content Content to check
     * @return Safety score (0-1, 1=safe, 0=dangerous)
     */
    public double quickCheck(String content) {
        String cacheKey = makeCacheKey(content, null);

        // Check cache
        Double cached = scoreCache.get(cacheKey);
        if (cached != null) {
            logger.debug("Quick check cache hit");
            return cached;
        }

        String prompt = String.format(QUICK_SCORE_PROMPT, content);

        try {
            String response = callJudgeService(prompt, 10);  // Only need 10 tokens

            // Parse score
            double score = parseScore(response);
            score = Math.max(0.0, Math.min(1.0, score));  // Clamp to 0-1

            // Cache result
            scoreCache.put(cacheKey, score);

            return score;

        } catch (Exception e) {
            logger.warn("Quick check error: {}, defaulting to 0.5", e.getMessage());
            return 0.5;  // Default to medium score on error
        }
    }

    /**
     * Clear all caches.
     */
    public void clearCache() {
        judgeCache.clear();
        scoreCache.clear();
        logger.debug("All caches cleared");
    }

    /**
     * Close the HTTP client.
     */
    public void close() {
        client.dispatcher().executorService().shutdown();
        client.connectionPool().evictAll();
    }

    // === Private methods ===

    private String callJudgeService(String prompt) throws JudgeTimeoutException, JudgeUnavailableException {
        return callJudgeService(prompt, 256);
    }

    private String callJudgeService(String prompt, int maxTokens) throws JudgeTimeoutException, JudgeUnavailableException {
        try {
            Map<String, Object> requestBody = Map.of(
                "model", config.getModel(),
                "messages", List.of(Map.of("role", "user", "content", prompt)),
                "temperature", 0.1,
                "max_tokens", maxTokens
            );

            String json = MAPPER.writeValueAsString(requestBody);

            Request request = new Request.Builder()
                .url(config.getEndpoint())
                .post(RequestBody.create(json, JSON))
                .header("Content-Type", "application/json")
                .build();

            try (Response response = client.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    throw new JudgeUnavailableException(config.getEndpoint(),
                        "HTTP " + response.code());
                }

                JsonNode root = MAPPER.readTree(response.body().string());
                return root.path("choices").get(0).path("message").path("content").asText();
            }

        } catch (java.net.SocketTimeoutException e) {
            throw new JudgeTimeoutException(config.getTimeout(), config.getEndpoint());
        } catch (IOException e) {
            throw new JudgeUnavailableException(config.getEndpoint(), e.getMessage());
        }
    }

    private JudgeResult parseJudgeResponse(String response) {
        try {
            // Try to parse as JSON directly
            JsonNode node = MAPPER.readTree(response);

            return JudgeResult.builder()
                .isSafe(node.path("is_safe").asBoolean(true))
                .riskLevel(node.path("risk_level").asText("safe"))
                .riskCategories(parseCategories(node.path("risk_categories")))
                .reason(node.path("reason").asText(""))
                .confidence(node.path("confidence").asDouble(0.5))
                .build();

        } catch (Exception e) {
            logger.warn("Failed to parse judge response: {}", response);
            // Return default safe result
            return JudgeResult.builder()
                .isSafe(true)
                .riskLevel(JudgeResult.RISK_SAFE)
                .reason("Unable to parse judge response")
                .confidence(0.5)
                .build();
        }
    }

    private List<String> parseCategories(JsonNode node) {
        List<String> categories = new ArrayList<>();
        if (node.isArray()) {
            for (JsonNode item : node) {
                categories.add(item.asText());
            }
        }
        return categories;
    }

    private double parseScore(String response) {
        try {
            // Try to extract a number from the response
            String trimmed = response.trim();
            String[] parts = trimmed.split("\\s+");
            return Double.parseDouble(parts[0]);
        } catch (Exception e) {
            logger.warn("Failed to parse score: {}", response);
            return 0.5;
        }
    }

    private String makeCacheKey(String content, String context) {
        String data = content + "||" + (context != null ? context : "");
        return Integer.toHexString(data.hashCode());
    }
}
