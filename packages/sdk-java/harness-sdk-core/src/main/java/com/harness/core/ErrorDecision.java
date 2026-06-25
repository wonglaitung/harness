package com.harness.core;

import java.util.Map;

/**
 * Decision on how to handle an error.
 *
 * @param action The action to take
 * @param delaySeconds Delay before retry (if applicable)
 * @param message Human-readable message
 * @param metadata Additional metadata
 */
public record ErrorDecision(
    ErrorAction action,
    double delaySeconds,
    String message,
    Map<String, Object> metadata
) {

    /**
     * Create a retry decision with delay.
     */
    public static ErrorDecision retry(double delaySeconds, String message) {
        return new ErrorDecision(ErrorAction.RETRY, delaySeconds, message, Map.of());
    }

    /**
     * Create a retry decision with delay and metadata.
     */
    public static ErrorDecision retry(double delaySeconds, String message, Map<String, Object> metadata) {
        return new ErrorDecision(ErrorAction.RETRY, delaySeconds, message, metadata);
    }

    /**
     * Create an abort decision.
     */
    public static ErrorDecision abort(String message) {
        return new ErrorDecision(ErrorAction.ABORT, 0, message, Map.of());
    }

    /**
     * Create a skip decision.
     */
    public static ErrorDecision skip(String message) {
        return new ErrorDecision(ErrorAction.SKIP, 0, message, Map.of());
    }

    /**
     * Create a compress context decision.
     */
    public static ErrorDecision compressContext(String message) {
        return new ErrorDecision(ErrorAction.COMPRESS_CONTEXT, 0, message, Map.of());
    }
}
