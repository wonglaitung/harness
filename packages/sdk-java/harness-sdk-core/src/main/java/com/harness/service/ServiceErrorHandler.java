package com.harness.service;

import java.time.*;
import java.util.*;

/**
 * Unified error handling for Harness service.
 *
 * Provides standardized error responses for REST APIs with:
 * - Error codes
 * - Trace ID propagation
 * - Detailed error messages
 *
 * Example:
 * <pre>
 * // Create error response
 * ErrorResponse error = ServiceErrorHandler.createError(
 *     ErrorCode.INVALID_INPUT,
 *     "Invalid parameter: name is required",
 *     traceId
 * );
 *
 * // Handle exception
 * ErrorResponse error = ServiceErrorHandler.handleException(e, traceId);
 * </pre>
 */
public class ServiceErrorHandler {

    /**
     * Error codes for Harness service.
     */
    public enum ErrorCode {
        INVALID_INPUT("INVALID_INPUT", 400, "Invalid input parameter"),
        NOT_FOUND("NOT_FOUND", 404, "Resource not found"),
        UNAUTHORIZED("UNAUTHORIZED", 401, "Authentication required"),
        FORBIDDEN("FORBIDDEN", 403, "Permission denied"),
        RATE_LIMITED("RATE_LIMITED", 429, "Rate limit exceeded"),
        INTERNAL_ERROR("INTERNAL_ERROR", 500, "Internal server error"),
        SERVICE_UNAVAILABLE("SERVICE_UNAVAILABLE", 503, "Service unavailable"),
        TIMEOUT("TIMEOUT", 504, "Request timeout"),
        LLM_ERROR("LLM_ERROR", 502, "LLM service error"),
        TOOL_ERROR("TOOL_ERROR", 500, "Tool execution error");

        private final String code;
        private final int httpStatus;
        private final String message;

        ErrorCode(String code, int httpStatus, String message) {
            this.code = code;
            this.httpStatus = httpStatus;
            this.message = message;
        }

        public String code() { return code; }
        public int httpStatus() { return httpStatus; }
        public String message() { return message; }
    }

    /**
     * Standard error response.
     */
    public static class ErrorResponse {
        private final String code;
        private final String message;
        private final String traceId;
        private final String timestamp;
        private final Map<String, Object> details;

        public ErrorResponse(String code, String message, String traceId, Map<String, Object> details) {
            this.code = code;
            this.message = message;
            this.traceId = traceId;
            this.timestamp = Instant.now().toString();
            this.details = details != null ? details : Map.of();
        }

        public String code() { return code; }
        public String message() { return message; }
        public String traceId() { return traceId; }
        public String timestamp() { return timestamp; }
        public Map<String, Object> details() { return details; }

        /**
         * Convert to map for JSON serialization.
         */
        public Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("code", code);
            map.put("message", message);
            map.put("traceId", traceId);
            map.put("timestamp", timestamp);
            if (!details.isEmpty()) {
                map.put("details", details);
            }
            return map;
        }
    }

    /**
     * Create an error response.
     */
    public static ErrorResponse createError(ErrorCode errorCode, String message, String traceId) {
        return createError(errorCode, message, traceId, null);
    }

    /**
     * Create an error response with details.
     */
    public static ErrorResponse createError(ErrorCode errorCode, String message, String traceId, Map<String, Object> details) {
        return new ErrorResponse(errorCode.code(), message, traceId, details);
    }

    /**
     * Handle an exception and create error response.
     */
    public static ErrorResponse handleException(Exception e, String traceId) {
        ErrorCode code;
        String message;

        if (e instanceof IllegalArgumentException) {
            code = ErrorCode.INVALID_INPUT;
            message = e.getMessage();
        } else if (e instanceof java.util.concurrent.TimeoutException) {
            code = ErrorCode.TIMEOUT;
            message = "Operation timed out";
        } else if (e instanceof java.util.concurrent.RejectedExecutionException) {
            code = ErrorCode.RATE_LIMITED;
            message = "Too many concurrent requests";
        } else {
            code = ErrorCode.INTERNAL_ERROR;
            message = "Internal server error";
        }

        return createError(code, message, traceId, Map.of("exception", e.getClass().getSimpleName()));
    }

    /**
     * Create a validation error.
     */
    public static ErrorResponse validationError(String field, String reason, String traceId) {
        return createError(
            ErrorCode.INVALID_INPUT,
            "Validation failed for field: " + field,
            traceId,
            Map.of("field", field, "reason", reason)
        );
    }

    /**
     * Create a not found error.
     */
    public static ErrorResponse notFound(String resourceType, String resourceId, String traceId) {
        return createError(
            ErrorCode.NOT_FOUND,
            resourceType + " not found: " + resourceId,
            traceId,
            Map.of("resourceType", resourceType, "resourceId", resourceId)
        );
    }

    /**
     * Create a rate limited error.
     */
    public static ErrorResponse rateLimited(String limitType, long retryAfterSeconds, String traceId) {
        return createError(
            ErrorCode.RATE_LIMITED,
            "Rate limit exceeded: " + limitType,
            traceId,
            Map.of("limitType", limitType, "retryAfterSeconds", retryAfterSeconds)
        );
    }
}
