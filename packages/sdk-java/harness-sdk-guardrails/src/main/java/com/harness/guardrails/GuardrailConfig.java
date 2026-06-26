package com.harness.guardrails;

import java.util.HashMap;
import java.util.Map;

/**
 * Configuration for guardrails (PII detection and content safety).
 *
 * Guardrails provides two layers of content safety:
 * - Layer 1: PII detection using regex and NLP rules (fast, <1ms)
 * - Layer 2: LLM-based content judge for complex cases (~100ms)
 *
 * Example:
 * <pre>
 * GuardrailConfig config = GuardrailConfig.builder()
 *     .enabled(true)
 *     .layer1Enabled(true)
 *     .layer2Enabled(true)
 *     .judgeEndpoint("http://localhost:8001/v1/chat/completions")
 *     .judgeModel("Qwen3Guard-8B")
 *     .build();
 * </pre>
 */
public class GuardrailConfig {

    private final boolean enabled;
    private final boolean layer1Enabled;
    private final boolean layer2Enabled;
    private final String judgeEndpoint;
    private final double judgeTimeout;
    private final String judgeModel;
    private final boolean redactPii;
    private final boolean auditLog;
    private final double minScore;
    private final String language;
    private final Map<String, String> placeholders;
    private final StreamInterceptConfig streamIntercept;

    private GuardrailConfig(Builder builder) {
        this.enabled = builder.enabled;
        this.layer1Enabled = builder.layer1Enabled;
        this.layer2Enabled = builder.layer2Enabled;
        this.judgeEndpoint = builder.judgeEndpoint;
        this.judgeTimeout = builder.judgeTimeout;
        this.judgeModel = builder.judgeModel;
        this.redactPii = builder.redactPii;
        this.auditLog = builder.auditLog;
        this.minScore = builder.minScore;
        this.language = builder.language;
        this.placeholders = new HashMap<>(builder.placeholders);
        this.streamIntercept = builder.streamIntercept;
    }

    public boolean isEnabled() { return enabled; }
    public boolean isLayer1Enabled() { return layer1Enabled; }
    public boolean isLayer2Enabled() { return layer2Enabled; }
    public String getJudgeEndpoint() { return judgeEndpoint; }
    public double getJudgeTimeout() { return judgeTimeout; }
    public String getJudgeModel() { return judgeModel; }
    public boolean isRedactPii() { return redactPii; }
    public boolean isAuditLog() { return auditLog; }
    public double getMinScore() { return minScore; }
    public String getLanguage() { return language; }
    public Map<String, String> getPlaceholders() { return new HashMap<>(placeholders); }
    public StreamInterceptConfig getStreamIntercept() { return streamIntercept; }

    /**
     * Get Judge configuration.
     */
    public JudgeConfig getJudgeConfig() {
        return JudgeConfig.builder()
            .enabled(layer2Enabled)
            .endpoint(judgeEndpoint != null ? judgeEndpoint : "")
            .model(judgeModel != null ? judgeModel : "")
            .timeout(judgeTimeout)
            .streamIntercept(streamIntercept)
            .build();
    }

    public static GuardrailConfig defaults() {
        return builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean enabled = true;
        private boolean layer1Enabled = true;
        private boolean layer2Enabled = false;
        private String judgeEndpoint = null;
        private double judgeTimeout = 5.0;
        private String judgeModel = null;
        private boolean redactPii = true;
        private boolean auditLog = true;
        private double minScore = 0.5;
        private String language = "auto";
        private Map<String, String> placeholders = new HashMap<>();
        private StreamInterceptConfig streamIntercept = StreamInterceptConfig.defaults();

        public Builder enabled(boolean v) { this.enabled = v; return this; }
        public Builder layer1Enabled(boolean v) { this.layer1Enabled = v; return this; }
        public Builder layer2Enabled(boolean v) { this.layer2Enabled = v; return this; }
        public Builder judgeEndpoint(String v) { this.judgeEndpoint = v; return this; }
        public Builder judgeTimeout(double v) { this.judgeTimeout = v; return this; }
        public Builder judgeModel(String v) { this.judgeModel = v; return this; }
        public Builder redactPii(boolean v) { this.redactPii = v; return this; }
        public Builder auditLog(boolean v) { this.auditLog = v; return this; }
        public Builder minScore(double v) { this.minScore = v; return this; }
        public Builder language(String v) { this.language = v; return this; }
        public Builder placeholders(Map<String, String> v) { this.placeholders = new HashMap<>(v); return this; }
        public Builder addPlaceholder(String key, String value) { this.placeholders.put(key, value); return this; }
        public Builder streamIntercept(StreamInterceptConfig v) { this.streamIntercept = v; return this; }

        public GuardrailConfig build() {
            return new GuardrailConfig(this);
        }
    }
}
