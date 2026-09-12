package com.harness.gate.retry;

import com.harness.gate.models.RetryPolicy;

import java.util.concurrent.Callable;

/**
 * Retry policy (defined in {@link com.harness.gate.models.RetryPolicy}) —
 * convenience helpers. This is the local self-healing primitive; escalation
 * (terminate/downgrade/review) is the caller's responsibility after exhaustion.
 */
public final class RetrySupport {

    private RetrySupport() {
    }

    /**
     * Run {@code fn} under a deterministic {@link RetryPolicy}. Retries up to
     * {@code maxRetries} with the configured backoff. Non-retryable errors or
     * exhaustion re-throws the last error.
     */
    public static <T> T withRetry(RetryPolicy policy, Callable<T> fn) throws Exception {
        Exception lastErr = null;
        for (int attempt = 0; attempt <= policy.maxRetries(); attempt++) {
            try {
                return fn.call();
            } catch (Exception e) {
                lastErr = e;
                if (!policy.shouldRetry(attempt, e)) {
                    break;
                }
                long delayMs = (long) (policy.delayFor(attempt) * 1000L);
                if (delayMs > 0) {
                    Thread.sleep(delayMs);
                }
            }
        }
        throw lastErr;
    }
}
