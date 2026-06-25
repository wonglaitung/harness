package com.harness.types;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Snapshot of agent loop state for interruption and recovery.
 *
 * Captures all state needed to resume execution after interruption.
 *
 * Example:
 * <pre>
 * // Create snapshot
 * LoopSnapshot snapshot = new LoopSnapshot(
 *     "session-123",
 *     messages,
 *     5,
 *     pendingToolCalls
 * );
 *
 * // Serialize
 * Map&lt;String, Object&gt; data = snapshot.toMap();
 *
 * // Deserialize
 * LoopSnapshot restored = LoopSnapshot.fromMap(data);
 * </pre>
 */
public class LoopSnapshot {

    private final String sessionId;
    private final List<Message> messages;
    private final int currentIteration;
    private final List<ToolCall> pendingToolCalls;
    private final String lastLlmResponse;
    private final LocalDateTime createdAt;

    public LoopSnapshot(String sessionId, List<Message> messages, int currentIteration,
                        List<ToolCall> pendingToolCalls, String lastLlmResponse) {
        this.sessionId = sessionId;
        this.messages = messages != null ? new ArrayList<>(messages) : new ArrayList<>();
        this.currentIteration = currentIteration;
        this.pendingToolCalls = pendingToolCalls != null ? new ArrayList<>(pendingToolCalls) : new ArrayList<>();
        this.lastLlmResponse = lastLlmResponse;
        this.createdAt = LocalDateTime.now();
    }

    public LoopSnapshot(String sessionId) {
        this(sessionId, List.of(), 0, List.of(), null);
    }

    public String sessionId() { return sessionId; }
    public List<Message> messages() { return messages; }
    public int currentIteration() { return currentIteration; }
    public List<ToolCall> pendingToolCalls() { return pendingToolCalls; }
    public String lastLlmResponse() { return lastLlmResponse; }
    public LocalDateTime createdAt() { return createdAt; }

    /**
     * Serialize snapshot to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("session_id", sessionId);
        map.put("current_iteration", currentIteration);
        map.put("last_llm_response", lastLlmResponse);
        map.put("created_at", createdAt.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));

        // Serialize messages
        List<Map<String, Object>> messageList = new ArrayList<>();
        for (Message msg : messages) {
            Map<String, Object> msgMap = new LinkedHashMap<>();
            msgMap.put("role", msg.role());
            msgMap.put("content", msg.content());
            messageList.add(msgMap);
        }
        map.put("messages", messageList);

        // Serialize pending tool calls
        List<Map<String, Object>> toolCallList = new ArrayList<>();
        for (ToolCall tc : pendingToolCalls) {
            Map<String, Object> tcMap = new LinkedHashMap<>();
            tcMap.put("id", tc.id());
            tcMap.put("name", tc.name());
            tcMap.put("arguments", tc.arguments());
            toolCallList.add(tcMap);
        }
        map.put("pending_tool_calls", toolCallList);

        return map;
    }

    /**
     * Deserialize snapshot from map.
     */
    @SuppressWarnings("unchecked")
    public static LoopSnapshot fromMap(Map<String, Object> map) {
        String sessionId = (String) map.get("session_id");
        int currentIteration = map.get("current_iteration") != null ? (Integer) map.get("current_iteration") : 0;
        String lastLlmResponse = (String) map.get("last_llm_response");

        // Deserialize messages
        List<Message> messages = new ArrayList<>();
        Object messagesObj = map.get("messages");
        if (messagesObj instanceof List) {
            for (Object msgObj : (List<?>) messagesObj) {
                if (msgObj instanceof Map) {
                    Map<String, Object> msgMap = (Map<String, Object>) msgObj;
                    messages.add(new Message(
                        (String) msgMap.get("role"),
                        (String) msgMap.get("content"),
                        null
                    ));
                }
            }
        }

        // Deserialize pending tool calls
        List<ToolCall> pendingToolCalls = new ArrayList<>();
        Object toolCallsObj = map.get("pending_tool_calls");
        if (toolCallsObj instanceof List) {
            for (Object tcObj : (List<?>) toolCallsObj) {
                if (tcObj instanceof Map) {
                    Map<String, Object> tcMap = (Map<String, Object>) tcObj;
                    @SuppressWarnings("unchecked")
                    Map<String, Object> args = (Map<String, Object>) tcMap.get("arguments");
                    pendingToolCalls.add(new ToolCall(
                        (String) tcMap.get("id"),
                        (String) tcMap.get("name"),
                        args != null ? args : Map.of()
                    ));
                }
            }
        }

        return new LoopSnapshot(sessionId, messages, currentIteration, pendingToolCalls, lastLlmResponse);
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String sessionId;
        private List<Message> messages = new ArrayList<>();
        private int currentIteration = 0;
        private List<ToolCall> pendingToolCalls = new ArrayList<>();
        private String lastLlmResponse;

        public Builder sessionId(String v) { this.sessionId = v; return this; }
        public Builder messages(List<Message> v) { this.messages = v; return this; }
        public Builder currentIteration(int v) { this.currentIteration = v; return this; }
        public Builder pendingToolCalls(List<ToolCall> v) { this.pendingToolCalls = v; return this; }
        public Builder lastLlmResponse(String v) { this.lastLlmResponse = v; return this; }

        public LoopSnapshot build() {
            return new LoopSnapshot(sessionId, messages, currentIteration, pendingToolCalls, lastLlmResponse);
        }
    }
}
