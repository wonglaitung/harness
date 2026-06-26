package com.harness.guardrails.exceptions;

import java.util.Map;

/**
 * Exception thrown when Judge service is unavailable.
 */
public class JudgeUnavailableException extends RuntimeException {

    private final String endpoint;
    private final String reason;

    public JudgeUnavailableException(String endpoint, String reason) {
        super(String.format("Judge service unavailable: %s - %s", endpoint, reason));
        this.endpoint = endpoint;
        this.reason = reason;
    }

    public String getEndpoint() { return endpoint; }
    public String getReason() { return reason; }

    /**
     * Convert to map for API responses.
     */
    public Map<String, Object> toMap() {
        return Map.of(
            "error", Map.of(
                "type", "judge_unavailable",
                "message", getMessage(),
                "reason", reason
            )
        );
    }
}
