package com.harness.gate.models;

import java.util.List;

/**
 * Deterministic retry policy with backoff and retryable-error filtering.
 *
 * <p>Used by goal-level and workflow-step execution. Retries are local
 * self-healing: on exhaustion the caller escalates to termination/downgrade
 * or the human review queue.</p>
 */
public record RetryPolicy(
        int maxRetries,
        Backoff backoff,
        double backoffBase,
        double backoffCap,
        List<Class<? extends Exception>> retryableErrors) {

    public RetryPolicy() {
        this(3, Backoff.EXPONENTIAL, 1.0, 30.0, List.of());
    }

    public RetryPolicy(int maxRetries, Backoff backoff) {
        this(maxRetries, backoff, 1.0, 30.0, List.of());
    }

    /**
     * Whether to retry given the (0-based) attempt count and the error.
     */
    public boolean shouldRetry(int attempt, Exception error) {
        if (attempt >= maxRetries) {
            return false;
        }
        if (retryableErrors.isEmpty()) {
            return true;
        }
        return retryableErrors.stream().anyMatch(c -> c.isInstance(error));
    }

    /**
     * Deterministic delay (seconds) before the next attempt.
     */
    public double delayFor(int attempt) {
        double d;
        if (backoff == Backoff.CONSTANT) {
            d = backoffBase;
        } else if (backoff == Backoff.LINEAR) {
            d = backoffBase * (attempt + 1);
        } else { // EXPONENTIAL
            d = backoffBase * Math.pow(2.0, attempt);
        }
        return Math.min(d, backoffCap);
    }
}
