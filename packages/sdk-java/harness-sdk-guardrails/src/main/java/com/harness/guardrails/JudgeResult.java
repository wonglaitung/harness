package com.harness.guardrails;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Result from the Judge service.
 *
 * Contains the safety assessment of content.
 */
public record JudgeResult(
    boolean isSafe,
    String riskLevel,           // "safe", "low", "medium", "high", "critical"
    List<String> riskCategories,
    String reason,
    double confidence
) {

    /**
     * Risk level constants.
     */
    public static final String RISK_SAFE = "safe";
    public static final String RISK_LOW = "low";
    public static final String RISK_MEDIUM = "medium";
    public static final String RISK_HIGH = "high";
    public static final String RISK_CRITICAL = "critical";

    /**
     * Create a safe result.
     */
    public static JudgeResult safe() {
        return new JudgeResult(true, RISK_SAFE, List.of(), "Content is safe", 1.0);
    }

    /**
     * Create a safe result with custom confidence.
     */
    public static JudgeResult safe(double confidence) {
        return new JudgeResult(true, RISK_SAFE, List.of(), "Content is safe", confidence);
    }

    /**
     * Create an unsafe result.
     */
    public static JudgeResult unsafe(String riskLevel, List<String> categories, String reason, double confidence) {
        return new JudgeResult(false, riskLevel, categories, reason, confidence);
    }

    /**
     * Create an unsafe result with high risk.
     */
    public static JudgeResult highRisk(String reason, List<String> categories) {
        return new JudgeResult(false, RISK_HIGH, categories, reason, 0.9);
    }

    /**
     * Create an unsafe result with critical risk.
     */
    public static JudgeResult criticalRisk(String reason, List<String> categories) {
        return new JudgeResult(false, RISK_CRITICAL, categories, reason, 0.95);
    }

    /**
     * Check if this is a high or critical risk.
     */
    public boolean isHighRisk() {
        return RISK_HIGH.equals(riskLevel) || RISK_CRITICAL.equals(riskLevel);
    }

    /**
     * Convert to map for serialization.
     */
    public Map<String, Object> toMap() {
        return Map.of(
            "is_safe", isSafe,
            "risk_level", riskLevel,
            "risk_categories", riskCategories,
            "reason", reason,
            "confidence", confidence
        );
    }

    /**
     * Create builder.
     */
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private boolean isSafe = true;
        private String riskLevel = RISK_SAFE;
        private List<String> riskCategories = new ArrayList<>();
        private String reason = "";
        private double confidence = 1.0;

        public Builder isSafe(boolean isSafe) {
            this.isSafe = isSafe;
            return this;
        }

        public Builder riskLevel(String riskLevel) {
            this.riskLevel = riskLevel;
            return this;
        }

        public Builder riskCategories(List<String> riskCategories) {
            this.riskCategories = new ArrayList<>(riskCategories);
            return this;
        }

        public Builder addRiskCategory(String category) {
            this.riskCategories.add(category);
            return this;
        }

        public Builder reason(String reason) {
            this.reason = reason;
            return this;
        }

        public Builder confidence(double confidence) {
            this.confidence = confidence;
            return this;
        }

        public JudgeResult build() {
            return new JudgeResult(isSafe, riskLevel, riskCategories, reason, confidence);
        }
    }
}
