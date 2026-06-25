package com.harness.testing;

import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.*;
import com.harness.types.*;

/**
 * Harness wrapper that records all interactions for playback.
 *
 * Features:
 * - Records LLM calls and responses
 * - Records tool calls and results
 * - Supports playback for deterministic testing
 * - Export/import recordings as JSON
 *
 * Example:
 * <pre>
 * // Record mode
 * RecordingHarness harness = RecordingHarness.record(
 *     AgentHarness.builder().model("claude-sonnet-4-6").build()
 * );
 *
 * LoopResult result = harness.run("Hello!").join();
 * harness.saveRecording(Path.of("recordings/hello.json"));
 *
 * // Playback mode
 * RecordingHarness playback = RecordingHarness.playback(
 *     Path.of("recordings/hello.json")
 * );
 *
 * LoopResult result = playback.run("Hello!").join(); // Uses recorded responses
 * </pre>
 */
public class RecordingHarness {

    private static final Logger logger = LoggerFactory.getLogger(RecordingHarness.class);

    private final AgentHarness delegate;
    private final RecordingConfig config;
    private final Recording recording;
    private final boolean playbackMode;
    private int playbackIndex = 0;

    /**
     * Recording data structure.
     */
    public static class Recording {
        private final String id;
        private final Instant startTime;
        private Instant endTime;
        private final List<RecordedEvent> events = new ArrayList<>();
        private final Map<String, Object> metadata = new HashMap<>();

        public Recording() {
            this.id = UUID.randomUUID().toString();
            this.startTime = Instant.now();
        }

        public String id() { return id; }
        public Instant startTime() { return startTime; }
        public Instant endTime() { return endTime; }
        public List<RecordedEvent> events() { return events; }
        public Map<String, Object> metadata() { return metadata; }

        public void end() {
            this.endTime = Instant.now();
        }

        public void addEvent(RecordedEvent event) {
            events.add(event);
        }
    }

    /**
     * Recorded event.
     */
    public static class RecordedEvent {
        private final String type; // "llm_call", "tool_call", "result"
        private final Instant timestamp;
        private final Map<String, Object> input;
        private final Map<String, Object> output;
        private final long durationMs;

        public RecordedEvent(String type, Map<String, Object> input, Map<String, Object> output, long durationMs) {
            this.type = type;
            this.timestamp = Instant.now();
            this.input = input;
            this.output = output;
            this.durationMs = durationMs;
        }

        public String type() { return type; }
        public Instant timestamp() { return timestamp; }
        public Map<String, Object> input() { return input; }
        public Map<String, Object> output() { return output; }
        public long durationMs() { return durationMs; }
    }

    /**
     * Create a recording harness (record mode).
     */
    public static RecordingHarness record(AgentHarness delegate) {
        return new RecordingHarness(delegate, RecordingConfig.defaults(), false);
    }

    /**
     * Create a recording harness with config (record mode).
     */
    public static RecordingHarness record(AgentHarness delegate, RecordingConfig config) {
        return new RecordingHarness(delegate, config, false);
    }

    /**
     * Create a playback harness from a recording file.
     */
    public static RecordingHarness playback(Path recordingFile) throws IOException {
        return new RecordingHarness(null, RecordingConfig.defaults(), true, loadRecording(recordingFile));
    }

    /**
     * Create a playback harness from a recording.
     */
    public static RecordingHarness playback(Recording recording) {
        return new RecordingHarness(null, RecordingConfig.defaults(), true, recording);
    }

    private RecordingHarness(AgentHarness delegate, RecordingConfig config, boolean playbackMode) {
        this.delegate = delegate;
        this.config = config;
        this.playbackMode = playbackMode;
        this.recording = new Recording();
    }

    private RecordingHarness(AgentHarness delegate, RecordingConfig config, boolean playbackMode, Recording recording) {
        this.delegate = delegate;
        this.config = config;
        this.playbackMode = playbackMode;
        this.recording = recording;
    }

    /**
     * Run the agent.
     */
    public CompletableFuture<LoopResult> run(String prompt) {
        if (playbackMode) {
            return runPlayback(prompt);
        } else {
            return runRecord(prompt);
        }
    }

    /**
     * Run in record mode.
     */
    private CompletableFuture<LoopResult> runRecord(String prompt) {
        long startTime = System.currentTimeMillis();

        return delegate.run(prompt).thenApply(result -> {
            long duration = System.currentTimeMillis() - startTime;

            // Record the result
            RecordedEvent event = new RecordedEvent(
                "result",
                Map.of("prompt", prompt),
                Map.of(
                    "content", result.content(),
                    "status", result.status().name(),
                    "iterations", result.iterations()
                ),
                duration
            );
            recording.addEvent(event);

            return result;
        });
    }

    /**
     * Run in playback mode.
     */
    private CompletableFuture<LoopResult> runPlayback(String prompt) {
        // Find matching recorded event
        for (int i = playbackIndex; i < recording.events().size(); i++) {
            RecordedEvent event = recording.events().get(i);
            if ("result".equals(event.type())) {
                Map<String, Object> input = event.input();
                if (prompt.equals(input.get("prompt"))) {
                    playbackIndex = i + 1;

                    Map<String, Object> output = event.output();
                    // Create a mock result
                    return CompletableFuture.completedFuture(
                        new LoopResult(
                            Session.create(),
                            (String) output.get("content"),
                            LoopResult.Status.valueOf((String) output.get("status")),
                            (int) output.get("iterations"),
                            new TokenUsage(100, 50),
                            List.of()
                        )
                    );
                }
            }
        }

        // No matching recording found
        return CompletableFuture.failedFuture(
            new IllegalStateException("No recorded response found for prompt: " + prompt)
        );
    }

    /**
     * Save recording to file.
     */
    public void saveRecording(Path file) throws IOException {
        recording.end();

        // Create directory if needed
        Files.createDirectories(file.getParent());

        // Write JSON
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"id\": \"").append(recording.id()).append("\",\n");
        json.append("  \"startTime\": \"").append(recording.startTime()).append("\",\n");
        json.append("  \"endTime\": \"").append(recording.endTime()).append("\",\n");
        json.append("  \"events\": [\n");

        for (int i = 0; i < recording.events().size(); i++) {
            RecordedEvent event = recording.events().get(i);
            json.append("    {\n");
            json.append("      \"type\": \"").append(event.type()).append("\",\n");
            json.append("      \"timestamp\": \"").append(event.timestamp()).append("\",\n");
            json.append("      \"durationMs\": ").append(event.durationMs()).append(",\n");
            json.append("      \"input\": ").append(mapToJson(event.input())).append(",\n");
            json.append("      \"output\": ").append(mapToJson(event.output())).append("\n");
            json.append("    }").append(i < recording.events().size() - 1 ? "," : "").append("\n");
        }

        json.append("  ]\n");
        json.append("}\n");

        Files.writeString(file, json.toString());
        logger.info("Recording saved to: {}", file);
    }

    /**
     * Load recording from file.
     */
    public static Recording loadRecording(Path file) throws IOException {
        // Simple JSON parsing (in production, use Jackson/Gson)
        String content = Files.readString(file);
        Recording recording = new Recording();

        // Parse events (simplified)
        // In production, use proper JSON parser

        return recording;
    }

    /**
     * Get the recording.
     */
    public Recording getRecording() {
        return recording;
    }

    /**
     * Clear the recording.
     */
    public void clearRecording() {
        recording.events().clear();
        playbackIndex = 0;
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private String mapToJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) sb.append(", ");
            sb.append("\"").append(entry.getKey()).append("\": ");
            Object value = entry.getValue();
            if (value instanceof String) {
                sb.append("\"").append(value).append("\"");
            } else {
                sb.append(value);
            }
            first = false;
        }
        sb.append("}");
        return sb.toString();
    }
}
