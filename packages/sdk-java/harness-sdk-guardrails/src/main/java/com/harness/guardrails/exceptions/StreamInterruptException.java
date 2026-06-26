package com.harness.guardrails.exceptions;

import java.util.Map;

/**
 * Exception thrown when streaming output is interrupted due to content safety.
 */
public class StreamInterruptException extends RuntimeException {

    private final String reason;
    private final String partialContent;

    public StreamInterruptException(String reason) {
        this(reason, "");
    }

    public StreamInterruptException(String reason, String partialContent) {
        super(String.format("Stream interrupted: %s", reason));
        this.reason = reason;
        this.partialContent = partialContent;
    }

    public String getReason() { return reason; }
    public String getPartialContent() { return partialContent; }

    /**
     * Convert to map for API responses.
     */
    public Map<String, Object> toMap() {
        return Map.of(
            "error", Map.of(
                "type", "stream_interrupted",
                "message", getMessage(),
                "reason", reason
            )
        );
    }
}
