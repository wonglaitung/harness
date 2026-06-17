package com.harness.types;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Response from LLM.
 */
public record LLMResponse(
    String content,
    List<ToolCall> toolCalls,
    StopReason stopReason,
    TokenUsage usage,
    Map<String, Object> rawResponse
) {

    public LLMResponse(String content) {
        this(content, List.of(), StopReason.END_TURN, new TokenUsage(), Map.of());
    }

    public LLMResponse(String content, StopReason stopReason) {
        this(content, List.of(), stopReason, new TokenUsage(), Map.of());
    }

    /**
     * Check if response requires tool use.
     */
    public boolean isToolUse() {
        return stopReason == StopReason.TOOL_USE && !toolCalls.isEmpty();
    }

    /**
     * Check if response is complete (no more tools needed).
     */
    public boolean isComplete() {
        return stopReason == StopReason.END_TURN ||
               stopReason == StopReason.MAX_TOKENS ||
               stopReason == StopReason.STOP_SEQUENCE;
    }

    /**
     * Builder for LLMResponse.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String content;
        private List<ToolCall> toolCalls = new ArrayList<>();
        private StopReason stopReason = StopReason.END_TURN;
        private TokenUsage usage = new TokenUsage();
        private Map<String, Object> rawResponse = Map.of();

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder addToolCall(ToolCall toolCall) {
            this.toolCalls.add(toolCall);
            return this;
        }

        public Builder toolCalls(List<ToolCall> toolCalls) {
            this.toolCalls = toolCalls;
            return this;
        }

        public Builder stopReason(StopReason stopReason) {
            this.stopReason = stopReason;
            return this;
        }

        public Builder stopReason(String value) {
            this.stopReason = StopReason.fromValue(value);
            return this;
        }

        public Builder usage(TokenUsage usage) {
            this.usage = usage;
            return this;
        }

        public Builder inputTokens(int tokens) {
            this.usage = new TokenUsage(tokens, this.usage.outputTokens());
            return this;
        }

        public Builder outputTokens(int tokens) {
            this.usage = new TokenUsage(this.usage.inputTokens(), tokens);
            return this;
        }

        public Builder rawResponse(Map<String, Object> rawResponse) {
            this.rawResponse = rawResponse;
            return this;
        }

        public LLMResponse build() {
            return new LLMResponse(content, toolCalls, stopReason, usage, rawResponse);
        }
    }
}