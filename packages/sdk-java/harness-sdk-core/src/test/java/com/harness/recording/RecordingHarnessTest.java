package com.harness.recording;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for RecordingHarness.
 */
class RecordingHarnessTest {

    private RecordingHarness recorder;

    @BeforeEach
    void setUp() {
        recorder = new RecordingHarness(null);
    }

    @Test
    void testStartRecording() {
        recorder.startRecording("test_session");

        assertTrue(recorder.getInteractions().isEmpty());
    }

    @Test
    void testRecordLlmRequest() {
        recorder.startRecording("test");

        List<Map<String, Object>> messages = List.of(
                Map.of("role", "user", "content", "Hello")
        );

        recorder.recordLlmRequest(messages, null, "You are a helpful assistant.");

        assertEquals(1, recorder.getInteractions().size());
        RecordedInteraction interaction = recorder.getInteractions().get(0);
        assertEquals("llm_request", interaction.getType());
        assertNotNull(interaction.getTimestamp());
    }

    @Test
    void testRecordToolCall() {
        recorder.startRecording("test");

        recorder.recordToolResult("call_123", "read", "file contents", true);

        assertEquals(1, recorder.getInteractions().size());
        RecordedInteraction interaction = recorder.getInteractions().get(0);
        assertEquals("tool_result", interaction.getType());
        assertEquals("call_123", interaction.getData().get("tool_call_id"));
        assertEquals("read", interaction.getData().get("tool_name"));
    }

    @Test
    void testRecordingSummary() {
        recorder.startRecording("test");

        // Record some interactions
        recorder.recordLlmRequest(List.of(), null, "system");
        recorder.recordLlmRequest(List.of(), null, "system");
        recorder.recordToolResult("call_1", "read", "result", true);

        Map<String, Object> summary = recorder.getRecordingSummary();

        assertEquals(3, summary.get("total_interactions"));
        assertEquals(2, summary.get("llm_requests"));
        assertEquals(0, summary.get("tool_calls")); // tool_result != tool_call
    }

    @Test
    void testRecordingSummaryEmpty() {
        Map<String, Object> summary = recorder.getRecordingSummary();

        assertEquals(0, summary.get("total_interactions"));
    }

    @Test
    void testClearRecording() {
        recorder.startRecording("test");
        recorder.recordLlmRequest(List.of(), null, "system");

        assertEquals(1, recorder.getInteractions().size());

        recorder.clearRecording();

        assertTrue(recorder.getInteractions().isEmpty());
    }

    @Test
    void testRecordedInteractionBuilder() {
        RecordedInteraction interaction = new RecordedInteraction.Builder()
                .type("test_type")
                .addData("key1", "value1")
                .addData("key2", 42)
                .build();

        assertEquals("test_type", interaction.getType());
        assertEquals("value1", interaction.getData().get("key1"));
        assertEquals(42, interaction.getData().get("key2"));
    }

    @Test
    void testRecordedInteractionValidation() {
        // Missing type
        assertThrows(IllegalArgumentException.class, () ->
                new RecordedInteraction.Builder()
                        .addData("key", "value")
                        .build());
    }

    @Test
    void testRecordingConfigDefaults() {
        RecordingConfig config = new RecordingConfig.Builder().build();

        assertEquals(Path.of(".harness_recordings"), config.getRecordingDir());
        assertTrue(config.isAutoSave());
        assertTrue(config.isIncludeMetadata());
        assertEquals(100, config.getMaxRecordingSize());
    }

    @Test
    void testRecordingConfigBuilder() {
        RecordingConfig config = new RecordingConfig.Builder()
                .recordingDir(Path.of("/tmp/recordings"))
                .autoSave(false)
                .includeMetadata(false)
                .maxRecordingSize(50)
                .build();

        assertEquals(Path.of("/tmp/recordings"), config.getRecordingDir());
        assertFalse(config.isAutoSave());
        assertFalse(config.isIncludeMetadata());
        assertEquals(50, config.getMaxRecordingSize());
    }
}
