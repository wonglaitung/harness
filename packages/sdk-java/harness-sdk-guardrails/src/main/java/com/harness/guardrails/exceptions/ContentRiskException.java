package com.harness.guardrails.exceptions;

import java.util.Map;

import com.harness.guardrails.JudgeResult;

/**
 * Exception thrown when content risk is detected.
 */
public class ContentRiskException extends RuntimeException {

    private final JudgeResult result;

    public ContentRiskException(JudgeResult result) {
        super(buildMessage(result));
        this.result = result;
    }

    public ContentRiskException(JudgeResult result, String message) {
        super(message);
        this.result = result;
    }

    public JudgeResult getResult() {
        return result;
    }

    /**
     * Convert to map for API responses.
     */
    public Map<String, Object> toMap() {
        return Map.of(
            "error", Map.of(
                "type", "content_risk",
                "message", getMessage(),
                "risk_level", result.riskLevel(),
                "risk_categories", result.riskCategories(),
                "confidence", result.confidence()
            )
        );
    }

    private static String buildMessage(JudgeResult result) {
        return String.format("Content risk detected: %s - %s",
            result.riskLevel(), result.reason());
    }
}
