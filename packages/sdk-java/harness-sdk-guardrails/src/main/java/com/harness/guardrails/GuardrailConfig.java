package com.harness.guardrails;

import java.util.HashMap;
import java.util.Map;

/**
 * Complete guardrails configuration.
 *
 * Guardrails provides two layers of content safety:
 * - Layer 1: PII detection using regex and NLP rules
 * - Layer 2: LLM-based content judge for complex cases
 *
 * Example:
 * <pre>
 * GuardrailConfig config = GuardrailConfig.builder()
 *     .enabled(true)
 *     .layer1Enabled(true)
 *     .layer2Enabled(true)
 *     .judgeEndpoint("http://localhost:8000/v1/chat/completions")
 *     .judgeModel("Qwen3Guard-8B")
 *     .build();
 * </pre>
 */
public class GuardrailConfig {

    private final boolean enabled;
    private final boolean layer1Enabled;      // PII rule-based detection
    private final boolean layer2Enabled;      // LLM Judge
    private final String judgeEndpoint;
    private final double judgeTimeout;
    private final double minScore;            // Minimum confidence for PII detection
    private final String language;            // "auto", "zh", "zh-tw", "en"
    private final Map<String, String> placeholders;  // Custom placeholders for masking
    private final JudgeConfig judgeConfig;

    private GuardrailConfig(Builder builder) {
        this.enabled = builder.enabled;
        this.layer1Enabled = builder.layer1Enabled;
        this.layer2Enabled = builder.layer2Enabled;
        this.judgeEndpoint = builder.judgeEndpoint;
        this.judgeTimeout = builder.judgeTimeout;
        this.minScore = builder.minScore;
        this.language = builder.language;
        this.placeholders = new HashMap<>(builder.placeholders);
        this.judgeConfig = JudgeConfig.builder()
            .enabled(layer2Enabled)
            .endpoint(judgeEndpoint)
            .timeout(judgeTimeout)
            .build();
    }

    public boolean isEnabled() { return enabled; }
    public boolean isLayer1Enabled() { return layer1Enabled; }
    public boolean isLayer2Enabled() { return layer2Enabled; }
    public String getJudgeEndpoint() { return judgeEndpoint; }
    public double getJudgeTimeout() { return judgeTimeout; }
    public double getMinScore() { return minScore; }
    public String getLanguage() { return language; }
    public Map<String, String> getPlaceholders() { return new HashMap<>(placeholders); }
    public JudgeConfig getJudgeConfig() { return judgeConfig; }

    public static Builder builder() { return new Builder(); }

    public static GuardrailConfig defaults() { return builder().build(); }

    public static class Builder {
        private boolean enabled = false;
        private boolean layer1Enabled = true;
        private boolean layer2Enabled = false;
        private String judgeEndpoint = "";
        private double judgeTimeout = 5.0;
        private double minScore = 0.5;
        private String language = "auto";
        private Map<String, String> placeholders = new HashMap<>();

        public Builder enabled(boolean enabled) {
            this.enabled = enabled;
            return this;
        }

        public Builder layer1Enabled(boolean layer1Enabled) {
            this.layer1Enabled = layer1Enabled;
            return this;
        }

        public Builder layer2Enabled(boolean layer2Enabled) {
            this.layer2Enabled = layer2Enabled;
            return this;
        }

        public Builder judgeEndpoint(String judgeEndpoint) {
            this.judgeEndpoint = judgeEndpoint;
            return this;
        }

        public Builder judgeTimeout(double judgeTimeout) {
            this.judgeTimeout = judgeTimeout;
            return this;
        }

        public Builder minScore(double minScore) {
            this.minScore = minScore;
            return this;
        }

        public Builder language(String language) {
            this.language = language;
            return this;
        }

        public Builder placeholders(Map<String, String> placeholders) {
            this.placeholders = new HashMap<>(placeholders);
            return this;
        }

        public Builder addPlaceholder(String key, String value) {
            this.placeholders.put(key, value);
            return this;
        }

        public GuardrailConfig build() {
            return new GuardrailConfig(this);
        }
    }
}
