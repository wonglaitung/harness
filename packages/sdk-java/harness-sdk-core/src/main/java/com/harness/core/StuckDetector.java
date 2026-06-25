package com.harness.core;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.Message;

/**
 * Detect when agent is stuck using semantic similarity.
 *
 * Uses embedding model to detect repetitive outputs that indicate
 * the agent is not making progress.
 *
 * Example:
 * <pre>
 * StuckDetectorConfig config = StuckDetectorConfig.builder()
 *     .enableSemantic(true)
 *     .similarityThreshold(0.92)
 *     .consecutiveRounds(3)
 *     .build();
 *
 * StuckDetector detector = new StuckDetector(config, embeddingModel);
 *
 * // Check after each tool execution
 * StuckDetectionResult result = detector.check(sessionId, session.messages(), iteration);
 * if (result.isStuck()) {
 *     // Inject feedback or terminate
 * }
 * </pre>
 */
public class StuckDetector {

    private static final Logger logger = LoggerFactory.getLogger(StuckDetector.class);

    private final StuckDetectorConfig config;
    private final EmbeddingModel embeddingModel;

    // Per-session state
    private final Map<String, Deque<float[]>> windows = new HashMap<>();
    private final Map<String, Integer> consecutive = new HashMap<>();

    // Embedding cache (text_hash -> embedding)
    private final Map<String, float[]> cache = new LinkedHashMap<>();
    private static final int MAX_CACHE_SIZE = 10000;

    public StuckDetector() {
        this(StuckDetectorConfig.defaults(), null);
    }

    public StuckDetector(StuckDetectorConfig config) {
        this(config, null);
    }

    public StuckDetector(StuckDetectorConfig config, EmbeddingModel embeddingModel) {
        this.config = config;
        this.embeddingModel = embeddingModel;
    }

    /**
     * Check if agent is stuck using semantic similarity.
     *
     * @param sessionId Session identifier
     * @param messages Recent messages (tool outputs, assistant responses)
     * @param iteration Current iteration number
     * @return StuckDetectionResult with detection outcome
     */
    public StuckDetectionResult check(String sessionId, List<Message> messages, int iteration) {
        // Check if semantic detection is enabled
        if (!config.enableSemantic()) {
            return StuckDetectionResult.notStuck("semantic_disabled");
        }

        // Check if embedding model is available
        if (embeddingModel == null || !embeddingModel.isAvailable()) {
            return StuckDetectionResult.notStuck("model_unavailable");
        }

        // Extract candidate texts
        List<String> texts = extractTexts(messages);
        if (texts.isEmpty()) {
            return StuckDetectionResult.notStuck("no_candidates", Map.of("messageCount", messages.size()));
        }

        // Combine texts for embedding (one embedding per iteration)
        String combinedText = String.join("\n", texts.subList(Math.max(0, texts.size() - 3), texts.size()));

        // Get embedding
        float[] embedding = getEmbedding(combinedText);
        if (embedding == null) {
            return StuckDetectionResult.notStuck("embedding_failed");
        }

        // Get or create window
        Deque<float[]> window = windows.computeIfAbsent(
            sessionId,
            k -> new ArrayDeque<>(config.windowSize())
        );

        // Calculate max similarity against window
        double maxSim = 0.0;
        List<Double> similarities = new ArrayList<>();
        for (float[] prevEmb : window) {
            double sim = cosineSimilarity(embedding, prevEmb);
            similarities.add(sim);
            maxSim = Math.max(maxSim, sim);
        }

        // Update window
        window.addLast(embedding);
        if (window.size() > config.windowSize()) {
            window.removeFirst();
        }

        // Update consecutive count
        int consecutiveCount = this.consecutive.getOrDefault(sessionId, 0);
        if (maxSim >= config.similarityThreshold()) {
            consecutiveCount++;
        } else {
            consecutiveCount = 0;
        }
        this.consecutive.put(sessionId, consecutiveCount);

        // Determine if stuck
        boolean isStuck = consecutiveCount >= config.consecutiveRounds();

        double avgSim = similarities.isEmpty() ? 0.0 : similarities.stream().mapToDouble(d -> d).average().orElse(0.0);

        Map<String, Object> details = new HashMap<>();
        details.put("maxSimilarity", maxSim);
        details.put("avgSimilarity", avgSim);
        details.put("windowSize", window.size());
        details.put("consecutive", consecutiveCount);
        details.put("textPreview", combinedText.length() > 200 ? combinedText.substring(0, 200) : combinedText);

        if (isStuck) {
            return StuckDetectionResult.stuck("semantic_repeat", maxSim, consecutiveCount, details);
        }

        return new StuckDetectionResult(false, "no_stuck", maxSim, consecutiveCount, details);
    }

    /**
     * Clear session state.
     *
     * Call when session ends or after feedback injection.
     */
    public void clearSession(String sessionId) {
        windows.remove(sessionId);
        consecutive.remove(sessionId);
    }

    /**
     * Reset all state.
     */
    public void reset() {
        windows.clear();
        consecutive.clear();
        cache.clear();
    }

    // === Private Methods ===

    private List<String> extractTexts(List<Message> messages) {
        List<String> candidates = new ArrayList<>();
        for (Message msg : messages) {
            if ("tool".equals(msg.role()) || "assistant".equals(msg.role())) {
                String content = msg.contentAsString();
                if (content != null) {
                    String normalized = normalizeText(content);
                    if (normalized.length() >= config.minChars()) {
                        candidates.add(normalized);
                    }
                }
            }
        }
        return candidates;
    }

    private float[] getEmbedding(String text) {
        String hash = textHash(text);

        // Check cache
        if (cache.containsKey(hash)) {
            return cache.get(hash);
        }

        try {
            float[] embedding = embeddingModel.embed(text);
            if (embedding != null) {
                // Cache it
                if (cache.size() >= MAX_CACHE_SIZE) {
                    // Simple LRU: remove first entry
                    String firstKey = cache.keySet().iterator().next();
                    cache.remove(firstKey);
                }
                cache.put(hash, embedding);
            }
            return embedding;
        } catch (Exception e) {
            logger.warn("StuckDetector: Embedding failed: {}", e.getMessage());
            return null;
        }
    }

    private static String normalizeText(String s) {
        return s.trim().replaceAll("\\s+", " ");
    }

    private static String textHash(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(s.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            // Fallback to simple hash
            return String.valueOf(s.hashCode());
        }
    }

    private static double cosineSimilarity(float[] a, float[] b) {
        if (a == null || b == null || a.length != b.length) {
            return 0.0;
        }

        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < a.length; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }

        if (normA == 0 || normB == 0) {
            return 0.0;
        }

        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}
