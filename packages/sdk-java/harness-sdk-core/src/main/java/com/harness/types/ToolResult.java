package com.harness.types;

import java.util.Map;

/**
 * Result from a tool execution.
 */
public record ToolResult(
    String toolCallId,
    boolean success,
    String content,
    String error,
    String toolName,
    Map<String, Object> metadata
) {

    /**
     * Create a successful result.
     */
    public static ToolResult success(String toolCallId, String content) {
        return new ToolResult(toolCallId, true, content, null, null, Map.of());
    }

    /**
     * Create a successful result with tool name.
     */
    public static ToolResult success(String toolCallId, String content, String toolName) {
        return new ToolResult(toolCallId, true, content, null, toolName, Map.of());
    }

    /**
     * Create a successful result with metadata.
     */
    public static ToolResult success(String toolCallId, String content, String toolName, Map<String, Object> metadata) {
        return new ToolResult(toolCallId, true, content, null, toolName, metadata);
    }

    /**
     * Create a failed result.
     */
    public static ToolResult failure(String toolCallId, String error) {
        return new ToolResult(toolCallId, false, null, error, null, Map.of());
    }

    /**
     * Create a failed result with tool name.
     */
    public static ToolResult failure(String toolCallId, String error, String toolName) {
        return new ToolResult(toolCallId, false, null, error, toolName, Map.of());
    }

    /**
     * Create an error result (alias for failure).
     */
    public static ToolResult error(String toolCallId, String toolName, String error) {
        return new ToolResult(toolCallId, false, null, error, toolName, Map.of());
    }

    /**
     * Convert to API format for Anthropic/OpenAI.
     */
    public Map<String, Object> toApiFormat() {
        return Map.of(
            "type", "tool_result",
            "tool_use_id", toolCallId,
            "content", success ? content : "Error: " + error,
            "is_error", !success
        );
    }

    /**
     * Builder for ToolResult.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String toolCallId;
        private boolean success = true;
        private String content;
        private String error;
        private String toolName;
        private Map<String, Object> metadata = Map.of();

        public Builder toolCallId(String toolCallId) {
            this.toolCallId = toolCallId;
            return this;
        }

        public Builder success(boolean success) {
            this.success = success;
            return this;
        }

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            this.success = false;
            return this;
        }

        public Builder toolName(String toolName) {
            this.toolName = toolName;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public ToolResult build() {
            return new ToolResult(toolCallId, success, content, error, toolName, metadata);
        }
    }
}