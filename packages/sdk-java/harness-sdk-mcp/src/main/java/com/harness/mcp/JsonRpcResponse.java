package com.harness.mcp;

import java.util.Map;

/**
 * JSON-RPC 2.0 response.
 *
 * MCP uses JSON-RPC 2.0 for communication.
 */
public record JsonRpcResponse(
    String jsonrpc,
    String id,
    Object result,
    JsonRpcError error
) {

    /**
     * Check if response is successful.
     */
    public boolean isSuccess() {
        return error == null;
    }

    /**
     * Check if response has error.
     */
    public boolean hasError() {
        return error != null;
    }

    /**
     * Get result as map.
     */
    public Map<String, Object> resultAsMap() {
        if (result instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    /**
     * Get result as list.
     */
    public java.util.List<Object> resultAsList() {
        if (result instanceof java.util.List<?> list) {
            return (java.util.List<Object>) list;
        }
        return java.util.List.of();
    }

    /**
     * Get error message.
     */
    public String errorMessage() {
        return error != null ? error.message() : null;
    }

    /**
     * JSON-RPC error object.
     */
    public record JsonRpcError(
        int code,
        String message,
        Object data
    ) {

        // Standard JSON-RPC error codes
        public static final int PARSE_ERROR = -32700;
        public static final int INVALID_REQUEST = -32600;
        public static final int METHOD_NOT_FOUND = -32601;
        public static final int INVALID_PARAMS = -32602;
        public static final int INTERNAL_ERROR = -32603;

        /**
         * Check if this is a standard JSON-RPC error.
         */
        public boolean isStandardError() {
            return code >= -32700 && code <= -32603;
        }

        /**
         * Get error description.
         */
        public String description() {
            String standardMsg = switch (code) {
                case PARSE_ERROR -> "Parse error";
                case INVALID_REQUEST -> "Invalid request";
                case METHOD_NOT_FOUND -> "Method not found";
                case INVALID_PARAMS -> "Invalid params";
                case INTERNAL_ERROR -> "Internal error";
                default -> "Unknown error";
            };
            return standardMsg + ": " + message;
        }
    }
}