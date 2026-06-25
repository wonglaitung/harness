package com.harness.core;

import java.util.Map;

/**
 * Result from stuck detection.
 *
 * @param isStuck Whether agent is stuck
 * @param reason "empty", "error", "semantic_repeat", "no_stuck", "model_unavailable", "semantic_disabled"
 * @param similarity Max similarity score (if semantic detection ran)
 * @param consecutiveCount Current consecutive similar count
 * @param details Additional diagnostic information
 */
public record StuckDetectionResult(
    boolean isStuck,
    String reason,
    Double similarity,
    int consecutiveCount,
    Map<String, Object> details
) {

    /**
     * Create a not-stuck result.
     */
    public static StuckDetectionResult notStuck(String reason) {
        return new StuckDetectionResult(false, reason, null, 0, Map.of());
    }

    /**
     * Create a not-stuck result with details.
     */
    public static StuckDetectionResult notStuck(String reason, Map<String, Object> details) {
        return new StuckDetectionResult(false, reason, null, 0, details);
    }

    /**
     * Create a stuck result.
     */
    public static StuckDetectionResult stuck(String reason, double similarity, int consecutiveCount, Map<String, Object> details) {
        return new StuckDetectionResult(true, reason, similarity, consecutiveCount, details);
    }
}
