package com.harness.llm;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.harness.types.StopReason;

/**
 * Predefined mock response for testing.
 */
public class MockResponse {

    private final String content;
    private final List<Map<String, Object>> toolCalls;
    private final StopReason stopReason;

    public MockResponse(String content) {
        this(content, new ArrayList<>(), StopReason.END_TURN);
    }

    public MockResponse(String content, List<Map<String, Object>> toolCalls, StopReason stopReason) {
        this.content = content;
        this.toolCalls = toolCalls;
        this.stopReason = stopReason;
    }

    public String getContent() {
        return content;
    }

    public List<Map<String, Object>> getToolCalls() {
        return toolCalls;
    }

    public StopReason getStopReason() {
        return stopReason;
    }

    /**
     * Create a text response.
     */
    public static MockResponse text(String content) {
        return new MockResponse(content, new ArrayList<>(), StopReason.END_TURN);
    }

    /**
     * Create a tool use response.
     */
    public static MockResponse toolUse(String toolCallId, String toolName, Map<String, Object> arguments) {
        List<Map<String, Object>> toolCalls = new ArrayList<>();
        Map<String, Object> tc = new HashMap<>();
        tc.put("id", toolCallId);
        tc.put("name", toolName);
        tc.put("arguments", arguments);
        toolCalls.add(tc);
        return new MockResponse("", toolCalls, StopReason.TOOL_USE);
    }

    /**
     * Builder for mock response.
     */
    public static class Builder {
        private String content = "";
        private List<Map<String, Object>> toolCalls = new ArrayList<>();
        private StopReason stopReason = StopReason.END_TURN;

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder addToolCall(String id, String name, Map<String, Object> arguments) {
            Map<String, Object> tc = new HashMap<>();
            tc.put("id", id);
            tc.put("name", name);
            tc.put("arguments", arguments);
            toolCalls.add(tc);
            return this;
        }

        public Builder stopReason(StopReason stopReason) {
            this.stopReason = stopReason;
            return this;
        }

        public MockResponse build() {
            return new MockResponse(content, toolCalls, stopReason);
        }
    }

    public static Builder builder() {
        return new Builder();
    }
}
