package com.harness.types;

import java.util.List;
import java.util.Map;

/**
 * A tool call request from the LLM.
 */
public record ToolCall(
    String id,
    String name,
    Map<String, Object> arguments
) {

    /**
     * Convert to API format for Anthropic/OpenAI.
     */
    public Map<String, Object> toApiFormat() {
        return Map.of(
            "type", "tool_use",
            "id", id,
            "name", name,
            "input", arguments
        );
    }

    /**
     * Create from API response.
     */
    public static ToolCall fromApiFormat(Map<String, Object> data) {
        return new ToolCall(
            (String) data.get("id"),
            (String) data.get("name"),
            (Map<String, Object>) data.getOrDefault("input", Map.of())
        );
    }

    /**
     * Builder for ToolCall.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String id;
        private String name;
        private Map<String, Object> arguments = Map.of();

        public Builder id(String id) {
            this.id = id;
            return this;
        }

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder arguments(Map<String, Object> arguments) {
            this.arguments = arguments;
            return this;
        }

        public ToolCall build() {
            return new ToolCall(id, name, arguments);
        }
    }
}