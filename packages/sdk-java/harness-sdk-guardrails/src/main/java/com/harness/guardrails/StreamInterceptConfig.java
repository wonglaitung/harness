package com.harness.guardrails;

/**
 * Configuration for stream interception.
 *
 * Used for real-time content safety checking during streaming responses.
 */
public class StreamInterceptConfig {

    private final boolean enabled;
    private final int checkInterval;         // Check every N tokens
    private final double safetyThreshold;    // Safety threshold (interrupt if below)
    private final int minTokensBeforeCheck;  // Minimum tokens before first check

    private StreamInterceptConfig(Builder builder) {
        this.enabled = builder.enabled;
        this.checkInterval = builder.checkInterval;
        this.safetyThreshold = builder.safetyThreshold;
        this.minTokensBeforeCheck = builder.minTokensBeforeCheck;
    }

    public boolean isEnabled() { return enabled; }
    public int getCheckInterval() { return checkInterval; }
    public double getSafetyThreshold() { return safetyThreshold; }
    public int getMinTokensBeforeCheck() { return minTokensBeforeCheck; }

    public static Builder builder() { return new Builder(); }

    public static StreamInterceptConfig defaults() { return builder().build(); }

    public static class Builder {
        private boolean enabled = false;
        private int checkInterval = 10;          // Check every 10 tokens
        private double safetyThreshold = 0.3;   // Interrupt if score < 0.3
        private int minTokensBeforeCheck = 5;   // Wait for 5 tokens before checking

        public Builder enabled(boolean enabled) {
            this.enabled = enabled;
            return this;
        }

        public Builder checkInterval(int checkInterval) {
            this.checkInterval = checkInterval;
            return this;
        }

        public Builder safetyThreshold(double safetyThreshold) {
            this.safetyThreshold = safetyThreshold;
            return this;
        }

        public Builder minTokensBeforeCheck(int minTokensBeforeCheck) {
            this.minTokensBeforeCheck = minTokensBeforeCheck;
            return this;
        }

        public StreamInterceptConfig build() {
            return new StreamInterceptConfig(this);
        }
    }
}
