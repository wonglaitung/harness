package com.harness.mcp;

/**
 * Result from MCP tool call.
 */
public record McpToolResult(
    boolean success,
    String content,
    JsonRpcResponse.JsonRpcError error
) {

    /**
     * Create a successful result.
     */
    public static McpToolResult success(String content) {
        return new McpToolResult(true, content, null);
    }

    /**
     * Create an error result.
     */
    public static McpToolResult error(String message, JsonRpcResponse.JsonRpcError error) {
        return new McpToolResult(false, message, error);
    }

    /**
     * Get content or error message.
     */
    public String contentOrError() {
        return success ? content : (error != null ? error.description() : content);
    }

    /**
     * Check if this is an error.
     */
    public boolean isError() {
        return !success;
    }
}