package com.harness.guardrails.exceptions;

import java.util.Map;

/**
 * Exception thrown when Judge service times out.
 */
public class JudgeTimeoutException extends RuntimeException {

    private final double timeout;
    private final String endpoint;

    public JudgeTimeoutException(double timeout, String endpoint) {
        super(String.format("Judge service timeout after %.1fs: %s", timeout, endpoint));
        this.timeout = timeout;
        this.endpoint = endpoint;
    }

    public double getTimeout() { return timeout; }
    public String getEndpoint() { return endpoint; }

    /**
     * Convert to map for API responses.
     */
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
