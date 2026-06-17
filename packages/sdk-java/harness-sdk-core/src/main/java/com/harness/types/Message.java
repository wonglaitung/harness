package com.harness.types;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * A single message in the conversation.
 */
public record Message(
    String role,
    Object content,
    Instant timestamp,
    Map<String, Object> metadata
) {

    public Message(String role, String content) {
        this(role, content, Instant.now(), Map.of());
    }

    public Message(String role, String content, Map<String, Object> metadata) {
        this(role, content, Instant.now(), metadata);
    }

    /**
     * Create a system message.
     */
    public static Message system(String content) {
        return new Message("system", content, Instant.now(), Map.of());
    }

    /**
     * Create a user message.
     */
    public static Message user(String content) {
        return new Message("user", content, Instant.now(), Map.of());
    }

    /**
     * Create an assistant message.
     */
    public static Message assistant(String content) {
        return new Message("assistant", content, Instant.now(), Map.of());
    }

    /**
     * Create a tool result message.
     */
    public static Message tool(String content, String toolCallId, String toolName) {
        return new Message("tool", content, Instant.now(), Map.of(
            "tool_call_id", toolCallId,
            "tool_name", toolName
        ));
    }

    /**
     * Create a tool result message from ToolResult.
     */
    public static Message fromToolResult(ToolResult result) {
        String content = result.success() ? result.content() : "Error: " + result.error();
        return new Message("tool", content, Instant.now(), Map.of(
            "tool_call_id", result.toolCallId(),
            "tool_name", result.toolName() != null ? result.toolName() : "",
            "is_error", !result.success()
        ));
    }

    /**
     * Get content as string.
     */
    public String contentAsString() {
        if (content instanceof String s) {
            return s;
        }
        if (content instanceof List<?> list) {
            // Handle structured content (e.g., multi-modal)
            StringBuilder sb = new StringBuilder();
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    Object text = map.get("text");
                    if (text != null) {
                        sb.append(text);
                    }
                }
            }
            return sb.toString();
        }
        return content != null ? content.toString() : "";
    }

    /**
     * Validate role.
     */
    public Message {
        if (!List.of("system", "user", "assistant", "tool").contains(role)) {
            throw new IllegalArgumentException("Invalid message role: " + role);
        }
    }

    /**
     * Builder for Message.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String role;
        private Object content;
        private Instant timestamp = Instant.now();
        private Map<String, Object> metadata = Map.of();

        public Builder role(String role) {
            this.role = role;
            return this;
        }

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder content(Object content) {
            this.content = content;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Message build() {
            return new Message(role, content, timestamp, metadata);
        }
    }
}
