package com.harness.guardrails;

import java.util.Map;

/**
 * Configuration for guardrails (PII detection and content safety).
 *
 * Supports:
 * - Layer 1: PII rule detection (phone, ID card, bank card, etc.) - Fast, <1ms
 * - Layer 2: LLM Judge semantic detection (optional) - ~100ms
 * - Stream interception for real-time content safety
 *
 * Example:
 * <pre>
 * GuardrailConfig config = GuardrailConfig.builder()
 *     .enabled(true)
 *     .layer1Enabled(true)
 *     .layer2Enabled(false)
 *     .streamIntercept(StreamInterceptConfig.defaults())
 *     .build();
 *
 * GuardrailHook hook = new GuardrailHook(config);
 * agent.addHook(hook);
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
        this.placeholders = builder.placeholders;
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
    public Map<String, String> getPlaceholders() { return placeholders; }
    public StreamInterceptConfig getStreamIntercept() { return streamIntercept; }

    /**
     * Get Judge configuration.
     */
    public JudgeConfig getJudgeConfig() {
        return new JudgeConfig(
            layer2Enabled,
            judgeEndpoint != null ? judgeEndpoint : "",
            judgeModel != null ? judgeModel : "",
            judgeTimeout,
            "pass",
            streamIntercept
        );
    }

    public static GuardrailConfig defaults() {
        return builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    // -------------------------------------------------------------------------
    // Stream Intercept Config
    // -------------------------------------------------------------------------

    /**
     * Configuration for stream interception.
     */
    public static class StreamInterceptConfig {
        private final boolean enabled;
        private final int checkInterval;        // Check every N tokens
        private final double safetyThreshold;   // Interrupt if score < threshold
        private final int minTokensBeforeCheck; // Minimum tokens before first check

        public StreamInterceptConfig(boolean enabled, int checkInterval,
                                    double safetyThreshold, int minTokensBeforeCheck) {
            this.enabled = enabled;
            this.checkInterval = checkInterval;
            this.safetyThreshold = safetyThreshold;
            this.minTokensBeforeCheck = minTokensBeforeCheck;
        }

        public boolean isEnabled() { return enabled; }
        public int getCheckInterval() { return checkInterval; }
        public double getSafetyThreshold() { return safetyThreshold; }
        public int getMinTokensBeforeCheck() { return minTokensBeforeCheck; }

        public static StreamInterceptConfig defaults() {
            return new StreamInterceptConfig(false, 10, 0.3, 5);
        }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private boolean enabled = false;
            private int checkInterval = 10;
            private double safetyThreshold = 0.3;
            private int minTokensBeforeCheck = 5;

            public Builder enabled(boolean v) { this.enabled = v; return this; }
            public Builder checkInterval(int v) { this.checkInterval = v; return this; }
            public Builder safetyThreshold(double v) { this.safetyThreshold = v; return this; }
            public Builder minTokensBeforeCheck(int v) { this.minTokensBeforeCheck = v; return this; }

            public StreamInterceptConfig build() {
                return new StreamInterceptConfig(enabled, checkInterval, safetyThreshold, minTokensBeforeCheck);
            }
        }
    }

    // -------------------------------------------------------------------------
    // Judge Config
    // -------------------------------------------------------------------------

    /**
     * Configuration for Layer 2 Judge.
     */
    public static class JudgeConfig {
        private final boolean enabled;
        private final String endpoint;
        private final String model;
        private final double timeout;
        private final String timeoutAction;  // "pass" or "block"
        private final StreamInterceptConfig streamIntercept;

        public JudgeConfig(boolean enabled, String endpoint, String model,
                          double timeout, String timeoutAction, StreamInterceptConfig streamIntercept) {
            this.enabled = enabled;
            this.endpoint = endpoint;
            this.model = model;
            this.timeout = timeout;
            this.timeoutAction = timeoutAction;
            this.streamIntercept = streamIntercept;
        }

        public boolean isEnabled() { return enabled; }
        public String getEndpoint() { return endpoint; }
        public String getModel() { return model; }
        public double getTimeout() { return timeout; }
        public String getTimeoutAction() { return timeoutAction; }
        public StreamInterceptConfig getStreamIntercept() { return streamIntercept; }
    }

    // -------------------------------------------------------------------------
    // Builder
    // -------------------------------------------------------------------------

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
        private Map<String, String> placeholders = Map.of();
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
        public Builder placeholders(Map<String, String> v) { this.placeholders = v; return this; }
        public Builder streamIntercept(StreamInterceptConfig v) { this.streamIntercept = v; return this; }

        public GuardrailConfig build() {
            return new GuardrailConfig(this);
        }
    }
}
