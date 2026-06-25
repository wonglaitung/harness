package com.harness.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import com.harness.types.StopReason;
import com.harness.types.ToolCall;

/**
 * A mock LLM response for testing.
 */
public class MockResponse {

    private final String content;
    private final List<ToolCall> toolCalls;
    private final StopReason stopReason;
    private final int inputTokens;
    private final int outputTokens;

    public MockResponse(String content, List<ToolCall> toolCalls, StopReason stopReason, int inputTokens, int outputTokens) {
        this.content = content;
        this.toolCalls = toolCalls != null ? toolCalls : new ArrayList<>();
        this.stopReason = stopReason != null ? stopReason : StopReason.END_TURN;
        this.inputTokens = inputTokens;
        this.outputTokens = outputTokens;
    }

    /**
     * Create a text response.
     */
    public static MockResponse text(String content) {
        return new MockResponse(content, new ArrayList<>(), StopReason.END_TURN, 100, 50);
    }

    /**
     * Create a text response with custom tokens.
     */
    public static MockResponse text(String content, int inputTokens, int outputTokens) {
        return new MockResponse(content, new ArrayList<>(), StopReason.END_TURN, inputTokens, outputTokens);
    }

    /**
     * Create a tool use response.
     */
    public static MockResponse toolUse(String toolCallId, String toolName, Map<String, Object> arguments) {
        List<ToolCall> toolCalls = new ArrayList<>();
        toolCalls.add(new ToolCall(toolCallId, toolName, arguments));
        return new MockResponse("", toolCalls, StopReason.TOOL_USE, 100, 20);
    }

    /**
     * Create a tool use response with multiple tool calls.
     */
    public static MockResponse toolUse(List<ToolCall> toolCalls) {
        return new MockResponse("", toolCalls, StopReason.TOOL_USE, 100, 20);
    }

    /**
     * Check if this is a tool use response.
     */
    public boolean isToolUse() {
        return stopReason == StopReason.TOOL_USE && !toolCalls.isEmpty();
    }

    // Getters
    public String content() { return content; }
    public List<ToolCall> toolCalls() { return new ArrayList<>(toolCalls); }
    public StopReason stopReason() { return stopReason; }
    public int inputTokens() { return inputTokens; }
    public int outputTokens() { return outputTokens; }

    /**
     * Builder for mock response.
     */
    public static class Builder {
        private String content = "";
        private List<ToolCall> toolCalls = new ArrayList<>();
        private StopReason stopReason = StopReason.END_TURN;
        private int inputTokens = 100;
        private int outputTokens = 50;

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder addToolCall(String id, String name, Map<String, Object> arguments) {
            toolCalls.add(new ToolCall(id, name, arguments));
            return this;
        }

        public Builder stopReason(StopReason stopReason) {
            this.stopReason = stopReason;
            return this;
        }

        public Builder inputTokens(int inputTokens) {
            this.inputTokens = inputTokens;
            return this;
        }

        public Builder outputTokens(int outputTokens) {
            this.outputTokens = outputTokens;
            return this;
        }

        public MockResponse build() {
            return new MockResponse(content, toolCalls, stopReason, inputTokens, outputTokens);
        }
    }

    public static Builder builder() {
        return new Builder();
    }
}
