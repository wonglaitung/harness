package com.harness.guardrails;

import java.util.List;
import java.util.Map;

/**
 * Custom exceptions for the guardrails module.
 *
 * Used for Judge service and stream interception.
 */
public class GuardrailExceptions {

    /**
     * Judge result containing safety assessment.
     */
    public static class JudgeResult {
        private final boolean isSafe;
        private final String riskLevel;  // "safe", "low", "medium", "high", "critical"
        private final List<String> riskCategories;
        private final String reason;
        private final double confidence;

        public JudgeResult(boolean isSafe, String riskLevel, List<String> riskCategories,
                          String reason, double confidence) {
            this.isSafe = isSafe;
            this.riskLevel = riskLevel;
            this.riskCategories = riskCategories;
            this.reason = reason;
            this.confidence = confidence;
        }

        public boolean isSafe() { return isSafe; }
        public String riskLevel() { return riskLevel; }
        public List<String> riskCategories() { return riskCategories; }
        public String reason() { return reason; }
        public double confidence() { return confidence; }

        public Map<String, Object> toMap() {
            return Map.of(
                "is_safe", isSafe,
                "risk_level", riskLevel,
                "risk_categories", riskCategories,
                "reason", reason,
                "confidence", confidence
            );
        }

        public static JudgeResult safe() {
            return new JudgeResult(true, "safe", List.of(), "", 1.0);
        }

        public static JudgeResult unsafe(String riskLevel, List<String> categories, String reason, double confidence) {
            return new JudgeResult(false, riskLevel, categories, reason, confidence);
        }
    }

    /**
     * Content risk exception - thrown when Judge detects high-risk content.
     */
    public static class ContentRiskException extends RuntimeException {
        private final JudgeResult result;

        public ContentRiskException(JudgeResult result) {
            super("Content risk detected: " + result.riskLevel() + " - " + result.reason());
            this.result = result;
        }

        public ContentRiskException(JudgeResult result, String message) {
            super(message);
            this.result = result;
        }

        public JudgeResult result() { return result; }

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
    }

    /**
     * Judge service timeout exception.
     */
    public static class JudgeTimeoutException extends RuntimeException {
        private final double timeout;
        private final String endpoint;

        public JudgeTimeoutException(double timeout, String endpoint) {
            super("Judge service timeout after " + timeout + "s: " + endpoint);
            this.timeout = timeout;
            this.endpoint = endpoint;
        }

        public double timeout() { return timeout; }
        public String endpoint() { return endpoint; }

        public Map<String, Object> toMap() {
            return Map.of(
                "error", Map.of(
                    "type", "judge_timeout",
                    "message", getMessage(),
                    "timeout", timeout
                )
            );
        }
    }

    /**
     * Judge service unavailable exception.
     */
    public static class JudgeUnavailableException extends RuntimeException {
        private final String endpoint;
        private final String reason;

        public JudgeUnavailableException(String endpoint, String reason) {
            super("Judge service unavailable: " + endpoint + " - " + reason);
            this.endpoint = endpoint;
            this.reason = reason;
        }

        public String endpoint() { return endpoint; }
        public String reason() { return reason; }

        public Map<String, Object> toMap() {
            return Map.of(
                "error", Map.of(
                    "type", "judge_unavailable",
                    "message", getMessage(),
                    "reason", reason
                )
            );
        }
    }

    /**
     * Stream interrupt exception - thrown when violating content is detected during streaming.
     */
    public static class StreamInterruptException extends RuntimeException {
        private final String reason;
        private final String partialContent;

        public StreamInterruptException(String reason) {
            super("Stream interrupted: " + reason);
            this.reason = reason;
            this.partialContent = "";
        }

        public StreamInterruptException(String reason, String partialContent) {
            super("Stream interrupted: " + reason);
            this.reason = reason;
            this.partialContent = partialContent;
        }

        public String reason() { return reason; }
        public String partialContent() { return partialContent; }

        public Map<String, Object> toMap() {
            return Map.of(
                "error", Map.of(
                    "type", "stream_interrupted",
                    "message", getMessage(),
                    "reason", reason
                )
            );
        }
    }
}
