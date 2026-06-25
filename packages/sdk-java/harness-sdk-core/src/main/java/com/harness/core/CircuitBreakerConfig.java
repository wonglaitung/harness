package com.harness.core;

/**
 * Configuration for circuit breaker.
 *
 * Following Bitter Lesson: keep it simple, trust the model.
 *
 * @param sameArgsThreshold Same tool + args threshold.
 *                          Only trigger when calling same tool with same arguments repeatedly.
 *                          Default: 3
 * @param errorThreshold Error threshold. Default: 5
 * @param errorWindowSeconds Error window in seconds. Default: 60
 * @param recoveryTimeoutSeconds Recovery timeout in seconds. Default: 30
 * @param halfOpenMaxCalls Max calls in half-open state. Default: 1
 */
public record CircuitBreakerConfig(
    int sameArgsThreshold,
    int errorThreshold,
    int errorWindowSeconds,
    int recoveryTimeoutSeconds,
    int halfOpenMaxCalls
) {

    public static final int DEFAULT_SAME_ARGS_THRESHOLD = 3;
    public static final int DEFAULT_ERROR_THRESHOLD = 5;
    public static final int DEFAULT_ERROR_WINDOW = 60;
    public static final int DEFAULT_RECOVERY_TIMEOUT = 30;
    public static final int DEFAULT_HALF_OPEN_MAX_CALLS = 1;

    public CircuitBreakerConfig() {
        this(
            DEFAULT_SAME_ARGS_THRESHOLD,
            DEFAULT_ERROR_THRESHOLD,
            DEFAULT_ERROR_WINDOW,
            DEFAULT_RECOVERY_TIMEOUT,
            DEFAULT_HALF_OPEN_MAX_CALLS
        );
    }

    public static CircuitBreakerConfig defaults() {
        return new CircuitBreakerConfig();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int sameArgsThreshold = DEFAULT_SAME_ARGS_THRESHOLD;
        private int errorThreshold = DEFAULT_ERROR_THRESHOLD;
        private int errorWindowSeconds = DEFAULT_ERROR_WINDOW;
        private int recoveryTimeoutSeconds = DEFAULT_RECOVERY_TIMEOUT;
        private int halfOpenMaxCalls = DEFAULT_HALF_OPEN_MAX_CALLS;

        public Builder sameArgsThreshold(int sameArgsThreshold) {
            this.sameArgsThreshold = sameArgsThreshold;
            return this;
        }

        public Builder errorThreshold(int errorThreshold) {
            this.errorThreshold = errorThreshold;
            return this;
        }

        public Builder errorWindowSeconds(int errorWindowSeconds) {
            this.errorWindowSeconds = errorWindowSeconds;
            return this;
        }

        public Builder recoveryTimeoutSeconds(int recoveryTimeoutSeconds) {
            this.recoveryTimeoutSeconds = recoveryTimeoutSeconds;
            return this;
        }

        public Builder halfOpenMaxCalls(int halfOpenMaxCalls) {
            this.halfOpenMaxCalls = halfOpenMaxCalls;
            return this;
        }

        public CircuitBreakerConfig build() {
            return new CircuitBreakerConfig(
                sameArgsThreshold, errorThreshold, errorWindowSeconds,
                recoveryTimeoutSeconds, halfOpenMaxCalls
            );
        }
    }
}
