package com.harness.guardrails;

/**
 * Configuration for Layer 2 LLM Judge.
 *
 * The Judge uses an LLM (e.g., Qwen3Guard-8B-Stream) to evaluate
 * content safety in real-time.
 */
public class JudgeConfig {

    private final boolean enabled;
    private final String endpoint;            // Judge service endpoint
    private final String model;               // Model name
    private final double timeout;             // Timeout in seconds
    private final String timeoutAction;       // "pass" or "block" on timeout
    private final StreamInterceptConfig streamIntercept;

    private JudgeConfig(Builder builder) {
        this.enabled = builder.enabled;
        this.endpoint = builder.endpoint;
        this.model = builder.model;
        this.timeout = builder.timeout;
        this.timeoutAction = builder.timeoutAction;
        this.streamIntercept = builder.streamIntercept;
    }

    public boolean isEnabled() { return enabled; }
    public String getEndpoint() { return endpoint; }
    public String getModel() { return model; }
    public double getTimeout() { return timeout; }
    public String getTimeoutAction() { return timeoutAction; }
    public StreamInterceptConfig getStreamIntercept() { return streamIntercept; }

    public static Builder builder() { return new Builder(); }

    public static JudgeConfig defaults() { return builder().build(); }

    public static class Builder {
        private boolean enabled = false;
        private String endpoint = "";
        private String model = "";
        private double timeout = 5.0;
        private String timeoutAction = "pass";  // Pass on timeout (conservative)
        private StreamInterceptConfig streamIntercept = StreamInterceptConfig.defaults();

        public Builder enabled(boolean enabled) {
            this.enabled = enabled;
            return this;
        }

        public Builder endpoint(String endpoint) {
            this.endpoint = endpoint;
            return this;
        }

        public Builder model(String model) {
            this.model = model;
            return this;
        }

        public Builder timeout(double timeout) {
            this.timeout = timeout;
            return this;
        }

        public Builder timeoutAction(String timeoutAction) {
            this.timeoutAction = timeoutAction;
            return this;
        }

        public Builder streamIntercept(StreamInterceptConfig streamIntercept) {
            this.streamIntercept = streamIntercept;
            return this;
        }

        public JudgeConfig build() {
            return new JudgeConfig(this);
        }
    }
}
