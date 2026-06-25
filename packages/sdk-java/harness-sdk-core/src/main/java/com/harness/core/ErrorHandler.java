package com.harness.core;

import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Intelligent error handler with recovery strategies.
 *
 * Maps error types to appropriate recovery actions:
 * - RateLimitError → RETRY with exponential backoff
 * - ContextTooLongError → COMPRESS_CONTEXT
 * - PermissionDeniedError → ABORT
 * - TimeoutError → RETRY (max 3 times)
 * - NetworkError → RETRY with backoff
 * - ToolExecutionError → SKIP or RETRY
 *
 * Example:
 * <pre>
 * ErrorHandler handler = new ErrorHandler();
 * ErrorDecision decision = handler.handle(error, context);
 * if (decision.action() == ErrorAction.RETRY) {
 *     Thread.sleep((long) (decision.delaySeconds() * 1000));
 *     // retry the operation
 * }
 * </pre>
 */
public class ErrorHandler {

    private static final Logger logger = LoggerFactory.getLogger(ErrorHandler.class);

    private final int maxRetries;
    private final double baseDelay;
    private final double maxDelay;

    // Track retry attempts per operation
    private final Map<String, Integer> retryCounts = new HashMap<>();

    public ErrorHandler() {
        this(3, 1.0, 60.0);
    }

    public ErrorHandler(int maxRetries, double baseDelay, double maxDelay) {
        this.maxRetries = maxRetries;
        this.baseDelay = baseDelay;
        this.maxDelay = maxDelay;
    }

    /**
     * Determine how to handle an error.
     *
     * @param error The exception that occurred
     * @param context Context about the error situation
     * @return ErrorDecision with action and parameters
     */
    public ErrorDecision handle(Exception error, ErrorContext context) {
        String errorType = error.getClass().getSimpleName();
        String errorMessage = error.getMessage() != null ? error.getMessage().toLowerCase() : "";

        // Check for rate limit errors
        if (isRateLimitError(errorType, errorMessage)) {
            return handleRateLimit(context);
        }

        // Check for context overflow
        if (isContextError(errorType, errorMessage, context)) {
            return handleContextOverflow(context);
        }

        // Check for permission errors
        if (isPermissionError(errorType, errorMessage)) {
            return handlePermissionError(error, context);
        }

        // Check for timeout errors
        if (isTimeoutError(errorType, errorMessage)) {
            return handleTimeout(context);
        }

        // Check for network errors
        if (isNetworkError(errorType, errorMessage)) {
            return handleNetworkError(context);
        }

        // Check for tool errors
        if (context.toolName() != null) {
            return handleToolError(error, context);
        }

        // Default: abort on unknown errors
        return ErrorDecision.abort("Unhandled error type: " + errorType + ": " + error.getMessage());
    }

    /**
     * Reset retry counters.
     */
    public void reset() {
        retryCounts.clear();
    }

    // === Error Type Detection ===

    private boolean isRateLimitError(String errorType, String message) {
        String[] indicators = {"ratelimit", "rate_limit", "429", "too many requests", "rate limit", "quota exceeded"};
        return errorType.toLowerCase().contains("rate") ||
               containsAny(message, indicators);
    }

    private boolean isContextError(String errorType, String message, ErrorContext context) {
        if (context.isContextOverflow()) {
            return true;
        }
        String[] indicators = {"context", "token limit", "max_tokens", "too long", "length", "context_length_exceeded"};
        return containsAny(message, indicators);
    }

    private boolean isPermissionError(String errorType, String message) {
        String[] indicators = {"permission", "forbidden", "403", "unauthorized", "access denied", "not allowed"};
        return errorType.toLowerCase().contains("permission") ||
               containsAny(message, indicators);
    }

    private boolean isTimeoutError(String errorType, String message) {
        String[] indicators = {"timeout", "timed out", "deadline"};
        return errorType.toLowerCase().contains("timeout") ||
               containsAny(message, indicators);
    }

    private boolean isNetworkError(String errorType, String message) {
        String[] typeIndicators = {"connection", "network", "socket"};
        String[] messageIndicators = {"connection", "network", "socket", "dns", "refused", "unreachable"};

        return containsAny(errorType.toLowerCase(), typeIndicators) ||
               containsAny(message, messageIndicators);
    }

    private boolean containsAny(String text, String[] patterns) {
        for (String pattern : patterns) {
            if (text.contains(pattern)) {
                return true;
            }
        }
        return false;
    }

    // === Error Handlers ===

    private ErrorDecision handleRateLimit(ErrorContext context) {
        String key = "ratelimit_" + context.iteration();
        int attempts = retryCounts.getOrDefault(key, 0);

        if (attempts >= maxRetries) {
            return ErrorDecision.abort("Rate limit persisted after " + attempts + " retries");
        }

        // Exponential backoff
        double delay = Math.min(baseDelay * Math.pow(2, attempts), maxDelay);
        retryCounts.put(key, attempts + 1);

        logger.warn("Rate limited, waiting {}s before retry (attempt {})", delay, attempts + 1);
        return ErrorDecision.retry(delay, "Rate limited, waiting " + String.format("%.1f", delay) + "s before retry");
    }

    private ErrorDecision handleContextOverflow(ErrorContext context) {
        if (context.iteration() > 3) {
            return ErrorDecision.abort("Context overflow persists after compression attempts");
        }

        logger.warn("Context too long ({} tokens), attempting compression", context.contextTokens());
        return ErrorDecision.compressContext("Context too long, attempting compression");
    }

    private ErrorDecision handlePermissionError(Exception error, ErrorContext context) {
        logger.error("Permission denied: {}", error.getMessage());
        return ErrorDecision.abort("Permission denied: " + error.getMessage());
    }

    private ErrorDecision handleTimeout(ErrorContext context) {
        String key = "timeout_" + context.iteration();
        int attempts = retryCounts.getOrDefault(key, 0);

        if (attempts >= maxRetries) {
            return ErrorDecision.abort("Operation timed out after " + attempts + " retries");
        }

        double delay = Math.min(baseDelay * Math.pow(2, attempts), maxDelay);
        retryCounts.put(key, attempts + 1);

        logger.warn("Timeout, retrying in {}s (attempt {})", delay, attempts + 1);
        return ErrorDecision.retry(delay, "Timeout, retrying in " + String.format("%.1f", delay) + "s");
    }

    private ErrorDecision handleNetworkError(ErrorContext context) {
        String key = "network_" + context.iteration();
        int attempts = retryCounts.getOrDefault(key, 0);

        if (attempts >= maxRetries) {
            return ErrorDecision.abort("Network error persisted after " + attempts + " retries");
        }

        double delay = Math.min(baseDelay * Math.pow(2, attempts), maxDelay);
        retryCounts.put(key, attempts + 1);

        logger.warn("Network error, retrying in {}s (attempt {})", delay, attempts + 1);
        return ErrorDecision.retry(delay, "Network error, retrying in " + String.format("%.1f", delay) + "s");
    }

    private ErrorDecision handleToolError(Exception error, ErrorContext context) {
        String errorMessage = error.getMessage() != null ? error.getMessage().toLowerCase() : "";

        // Some tool errors are recoverable
        if (errorMessage.contains("not found") || errorMessage.contains("does not exist")) {
            return ErrorDecision.skip("Tool " + context.toolName() + ": resource not found");
        }

        if (errorMessage.contains("invalid") || errorMessage.contains("invalid argument")) {
            // Bad arguments, don't retry
            return ErrorDecision.skip("Tool " + context.toolName() + ": invalid arguments");
        }

        // Other tool errors: try once more
        String key = "tool_" + context.toolName() + "_" + context.iteration();
        int attempts = retryCounts.getOrDefault(key, 0);

        if (attempts >= 1) {
            return ErrorDecision.skip("Tool " + context.toolName() + " failed, skipping");
        }

        retryCounts.put(key, attempts + 1);
        logger.warn("Tool {} failed, retrying", context.toolName());
        return ErrorDecision.retry(baseDelay, "Tool " + context.toolName() + " failed, retrying");
    }
}
