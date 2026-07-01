package com.harness.recording;

import com.harness.types.LLMResponse;
import com.harness.types.LoopResult;
import com.harness.types.ToolCall;
import com.harness.types.TokenUsage;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Wraps AgentHarness to record all interactions.
 *
 * <p>Records:</p>
 * <ul>
 *   <li>LLM requests and responses</li>
 *   <li>Tool calls and results</li>
 *   <li>Agent loop iterations</li>
 *   <li>Token usage</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * RecordingHarness recorder = new RecordingHarness(harness);
 *
 * // Run and record
 * recorder.startRecording("my_session");
 * LoopResult result = harness.run("Read the main.py file");
 * recorder.saveRecording("test_fixture.json");
 *
 * // Get summary
 * Map<String, Object> summary = recorder.getRecordingSummary();
 * }</pre>
 */
public class RecordingHarness {
    private static final Logger logger = LoggerFactory.getLogger(RecordingHarness.class);

    private final Object harness;
    private final RecordingConfig config;
    private final List<RecordedInteraction> interactions = new ArrayList<>();
    private String currentSessionId;

    /**
     * Create a new RecordingHarness.
     *
     * @param harness The harness to wrap
     */
    public RecordingHarness(Object harness) {
        this(harness, null);
    }

    /**
     * Create a new RecordingHarness.
     *
     * @param harness The harness to wrap
     * @param config Recording configuration
     */
    public RecordingHarness(Object harness, RecordingConfig config) {
        this.harness = harness;
        this.config = config != null ? config : new RecordingConfig.Builder().build();
    }

    /**
     * Start recording.
     *
     * @param sessionId Optional session ID
     */
    public void startRecording(String sessionId) {
        this.currentSessionId = sessionId != null ? sessionId : "recording";
        this.interactions.clear();
    }

    /**
     * Record an LLM request.
     *
     * @param messages The messages sent
     * @param tools The tools available
     * @param system The system prompt
     */
    public void recordLlmRequest(List<Map<String, Object>> messages, List<Map<String, Object>> tools, String system) {
        Map<String, Object> data = new HashMap<>();
        data.put("messages", messages);
        data.put("tools", tools);
        data.put("system", system);

        interactions.add(new RecordedInteraction.Builder()
                .type("llm_request")
                .timestamp(Instant.now())
                .data(data)
                .build());
    }

    /**
     * Record an LLM response.
     *
     * @param response The LLM response
     */
    public void recordLlmResponse(LLMResponse response) {
        Map<String, Object> data = new HashMap<>();
        data.put("content", response.content());
        data.put("stop_reason", response.stopReason().getValue());

        if (response.toolCalls() != null) {
            List<Map<String, Object>> toolCalls = new ArrayList<>();
            for (ToolCall tc : response.toolCalls()) {
                Map<String, Object> tcMap = new HashMap<>();
                tcMap.put("id", tc.id());
                tcMap.put("name", tc.name());
                tcMap.put("arguments", tc.arguments());
                toolCalls.add(tcMap);
            }
            data.put("tool_calls", toolCalls);
        }

        if (response.usage() != null) {
            Map<String, Integer> usage = new HashMap<>();
            usage.put("input_tokens", response.usage().inputTokens());
            usage.put("output_tokens", response.usage().outputTokens());
            data.put("usage", usage);
        }

        interactions.add(new RecordedInteraction.Builder()
                .type("llm_response")
                .timestamp(Instant.now())
                .data(data)
                .build());
    }

    /**
     * Record a tool call.
     *
     * @param toolCall The tool call
     */
    public void recordToolCall(ToolCall toolCall) {
        Map<String, Object> data = new HashMap<>();
        data.put("id", toolCall.id());
        data.put("name", toolCall.name());
        data.put("arguments", toolCall.arguments());

        interactions.add(new RecordedInteraction.Builder()
                .type("tool_call")
                .timestamp(Instant.now())
                .data(data)
                .build());
    }

    /**
     * Record a tool result.
     *
     * @param toolCallId The tool call ID
     * @param toolName The tool name
     * @param result The result
     * @param success Whether the call succeeded
     */
    public void recordToolResult(String toolCallId, String toolName, String result, boolean success) {
        Map<String, Object> data = new HashMap<>();
        data.put("tool_call_id", toolCallId);
        data.put("tool_name", toolName);
        // Truncate large results
        data.put("result", result != null && result.length() > 5000 ? result.substring(0, 5000) : result);
        data.put("success", success);

        interactions.add(new RecordedInteraction.Builder()
                .type("tool_result")
                .timestamp(Instant.now())
                .data(data)
                .build());
    }

    /**
     * Record final loop result.
     *
     * @param result The loop result
     */
    public void recordLoopResult(LoopResult result) {
        Map<String, Object> data = new HashMap<>();
        data.put("status", result.status().getValue());
        data.put("iterations", result.iterations());
        data.put("final_response", result.finalResponse());

        if (result.tokenUsage() != null) {
            Map<String, Integer> usage = new HashMap<>();
            usage.put("input_tokens", result.tokenUsage().inputTokens());
            usage.put("output_tokens", result.tokenUsage().outputTokens());
            data.put("token_usage", usage);
        }

        interactions.add(new RecordedInteraction.Builder()
                .type("loop_result")
                .timestamp(Instant.now())
                .data(data)
                .build());
    }

    /**
     * Save recording to file.
     *
     * @param name Recording name (without extension)
     * @return Path to saved recording
     */
    public Path saveRecording(String name) {
        if (interactions.isEmpty()) {
            logger.warn("No interactions to save");
            return null;
        }

        // Create recording directory
        try {
            Files.createDirectories(config.getRecordingDir());
        } catch (IOException e) {
            logger.error("Failed to create recording directory: {}", e.getMessage());
            return null;
        }

        // Build recording data
        Map<String, Object> recordingData = new HashMap<>();
        recordingData.put("version", "1.0");
        recordingData.put("session_id", currentSessionId);
        recordingData.put("created_at", Instant.now().toString());

        List<Map<String, Object>> interactionList = new ArrayList<>();
        for (RecordedInteraction i : interactions) {
            Map<String, Object> iMap = new HashMap<>();
            iMap.put("type", i.getType());
            iMap.put("timestamp", i.getTimestamp().toString());
            iMap.put("data", i.getData());
            interactionList.add(iMap);
        }
        recordingData.put("interactions", interactionList);

        // Add metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("total_interactions", interactions.size());
        recordingData.put("metadata", metadata);

        // Save to file
        Path path = config.getRecordingDir().resolve(name + ".json");
        try (BufferedWriter writer = Files.newBufferedWriter(path)) {
            // Simple JSON serialization
            writer.write(toJson(recordingData));
            logger.info("Saved recording to {}", path);
            return path;
        } catch (IOException e) {
            logger.error("Failed to save recording: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Get summary of current recording.
     *
     * @return Summary map
     */
    public Map<String, Object> getRecordingSummary() {
        Map<String, Object> summary = new HashMap<>();

        if (interactions.isEmpty()) {
            summary.put("total_interactions", 0);
            return summary;
        }

        int llmRequests = 0;
        int toolCalls = 0;
        int totalInput = 0;
        int totalOutput = 0;

        for (RecordedInteraction i : interactions) {
            if ("llm_request".equals(i.getType())) {
                llmRequests++;
            } else if ("tool_call".equals(i.getType())) {
                toolCalls++;
            } else if ("llm_response".equals(i.getType())) {
                @SuppressWarnings("unchecked")
                Map<String, Integer> usage = (Map<String, Integer>) i.getData().get("usage");
                if (usage != null) {
                    totalInput += usage.getOrDefault("input_tokens", 0);
                    totalOutput += usage.getOrDefault("output_tokens", 0);
                }
            }
        }

        summary.put("total_interactions", interactions.size());
        summary.put("llm_requests", llmRequests);
        summary.put("tool_calls", toolCalls);
        summary.put("total_input_tokens", totalInput);
        summary.put("total_output_tokens", totalOutput);

        return summary;
    }

    /**
     * Clear current recording.
     */
    public void clearRecording() {
        interactions.clear();
        currentSessionId = null;
    }

    /**
     * Get all interactions.
     */
    public List<RecordedInteraction> getInteractions() {
        return new ArrayList<>(interactions);
    }

    /**
     * Simple JSON serialization.
     */
    private String toJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            sb.append("\"").append(entry.getKey()).append("\":");
            sb.append(toJsonValue(entry.getValue()));
        }
        sb.append("}");
        return sb.toString();
    }

    private String toJsonValue(Object value) {
        if (value == null) {
            return "null";
        } else if (value instanceof String) {
            return "\"" + escapeJson((String) value) + "\"";
        } else if (value instanceof Number || value instanceof Boolean) {
            return value.toString();
        } else if (value instanceof List) {
            StringBuilder sb = new StringBuilder("[");
            boolean first = true;
            for (Object item : (List<?>) value) {
                if (!first) sb.append(",");
                first = false;
                sb.append(toJsonValue(item));
            }
            sb.append("]");
            return sb.toString();
        } else if (value instanceof Map) {
            return toJson((Map<String, Object>) value);
        } else {
            return "\"" + escapeJson(value.toString()) + "\"";
        }
    }

    private String escapeJson(String s) {
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
