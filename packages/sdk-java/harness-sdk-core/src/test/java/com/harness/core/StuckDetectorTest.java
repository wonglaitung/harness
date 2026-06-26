package com.harness.core;

import java.util.List;
import java.util.Map;

import com.harness.types.Message;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StuckDetector.
 *
 * Reference: packages/sdk/tests/test_stuck_detector.py
 */
class StuckDetectorTest {

    // === StuckDetectorConfig Tests ===

    @Test
    void testConfigDefaults() {
        StuckDetectorConfig config = StuckDetectorConfig.defaults();

        assertFalse(config.enableSemantic());
        assertEquals(StuckDetectorConfig.DEFAULT_SIMILARITY_THRESHOLD, config.similarityThreshold(), 0.001);
        assertEquals(StuckDetectorConfig.DEFAULT_CONSECUTIVE_ROUNDS, config.consecutiveRounds());
        assertEquals(StuckDetectorConfig.DEFAULT_WINDOW_SIZE, config.windowSize());
        assertEquals(StuckDetectorConfig.DEFAULT_MIN_CHARS, config.minChars());
    }

    @Test
    void testConfigCustomValues() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .similarityThreshold(0.88)
            .consecutiveRounds(2)
            .windowSize(10)
            .minChars(50)
            .build();

        assertTrue(config.enableSemantic());
        assertEquals(0.88, config.similarityThreshold(), 0.001);
        assertEquals(2, config.consecutiveRounds());
        assertEquals(10, config.windowSize());
        assertEquals(50, config.minChars());
    }

    @Test
    void testConfigDefaultConstructor() {
        StuckDetectorConfig config = new StuckDetectorConfig();

        assertFalse(config.enableSemantic());
        assertEquals(0.92, config.similarityThreshold(), 0.001);
        assertEquals(3, config.consecutiveRounds());
        assertEquals(6, config.windowSize());
        assertEquals(30, config.minChars());
    }

    // === StuckDetectionResult Tests ===

    @Test
    void testResultNotStuck() {
        StuckDetectionResult result = StuckDetectionResult.notStuck("no_stuck");

        assertFalse(result.isStuck());
        assertEquals("no_stuck", result.reason());
        assertNull(result.similarity());
        assertEquals(0, result.consecutiveCount());
        assertTrue(result.details().isEmpty());
    }

    @Test
    void testResultNotStuckWithDetails() {
        Map<String, Object> details = Map.of("messageCount", 5);
        StuckDetectionResult result = StuckDetectionResult.notStuck("no_candidates", details);

        assertFalse(result.isStuck());
        assertEquals("no_candidates", result.reason());
        assertEquals(details, result.details());
    }

    @Test
    void testResultStuck() {
        Map<String, Object> details = Map.of("maxSimilarity", 0.95);
        StuckDetectionResult result = StuckDetectionResult.stuck("semantic_repeat", 0.95, 3, details);

        assertTrue(result.isStuck());
        assertEquals("semantic_repeat", result.reason());
        assertEquals(0.95, result.similarity(), 0.001);
        assertEquals(3, result.consecutiveCount());
        assertEquals(details, result.details());
    }

    @Test
    void testResultCreation() {
        StuckDetectionResult result = new StuckDetectionResult(
            true, "semantic_repeat", 0.95, 3, Map.of()
        );

        assertTrue(result.isStuck());
        assertEquals("semantic_repeat", result.reason());
        assertEquals(0.95, result.similarity(), 0.001);
        assertEquals(3, result.consecutiveCount());
    }

    // === StuckDetector Tests ===

    @Test
    void testDetectorCreation() {
        StuckDetector detector = new StuckDetector();

        assertNotNull(detector);
    }

    @Test
    void testDetectorWithConfig() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .similarityThreshold(0.90)
            .build();
        StuckDetector detector = new StuckDetector(config);

        assertNotNull(detector);
    }

    @Test
    void testCheckDisabled() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(false)
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages = List.of(
            Message.tool("Result 1", "call-1", "tool"),
            Message.tool("Result 2", "call-2", "tool")
        );

        StuckDetectionResult result = detector.check("session-1", messages, 3);

        assertFalse(result.isStuck());
        assertEquals("semantic_disabled", result.reason());
    }

    @Test
    void testCheckModelUnavailable() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages = List.of(
            Message.tool("This is a tool output for testing", "call-1", "tool")
        );

        StuckDetectionResult result = detector.check("session-1", messages, 3);

        // Without embedding model, should return model_unavailable
        assertFalse(result.isStuck());
        assertEquals("model_unavailable", result.reason());
    }

    @Test
    void testCheckNoCandidates() {
        // Test that messages below minChars threshold are filtered out
        // Note: This test expects model_unavailable because no EmbeddingModel is provided.
        // The "no_candidates" reason is only returned when:
        // 1. enableSemantic is true
        // 2. embeddingModel is available
        // 3. All messages are filtered out by minChars
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .minChars(100)  // High threshold
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages = List.of(
            Message.tool("Short", "call-1", "tool")  // Too short
        );

        StuckDetectionResult result = detector.check("session-1", messages, 3);

        // Without an embedding model, returns model_unavailable (before checking candidates)
        assertFalse(result.isStuck());
        assertEquals("model_unavailable", result.reason());
    }

    @Test
    void testCheckNoCandidatesWithMockModel() {
        // To properly test "no_candidates", we need a mock embedding model
        // This test verifies the candidate filtering logic works correctly
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .minChars(100)  // High threshold
            .build();

        // Create a mock embedding model that returns availability
        EmbeddingModel mockModel = new EmbeddingModel() {
            @Override
            public int getDimension() {
                return 384;
            }

            @Override
            public float[] embed(String text) {
                return new float[384];  // Dummy embedding
            }

            @Override
            public List<float[]> embedBatch(List<String> texts) {
                return texts.stream().map(t -> new float[384]).toList();
            }

            @Override
            public boolean isAvailable() {
                return true;
            }
        };

        StuckDetector detector = new StuckDetector(config, mockModel);

        List<Message> messages = List.of(
            Message.tool("Short", "call-1", "tool")  // Too short for minChars=100
        );

        StuckDetectionResult result = detector.check("session-1", messages, 3);

        // With model available but no candidates, should return no_candidates
        assertFalse(result.isStuck());
        assertEquals("no_candidates", result.reason());
    }

    @Test
    void testClearSession() {
        StuckDetector detector = new StuckDetector();

        // Check once to create session state
        List<Message> messages = List.of(Message.tool("test", "call-1", "tool"));
        detector.check("session-to-clear", messages, 1);

        // Clear should not throw
        assertDoesNotThrow(() -> detector.clearSession("session-to-clear"));
    }

    @Test
    void testClearUnknownSession() {
        StuckDetector detector = new StuckDetector();

        // Clearing unknown session should not throw
        assertDoesNotThrow(() -> detector.clearSession("unknown-session"));
    }

    @Test
    void testReset() {
        StuckDetector detector = new StuckDetector();

        // Check to create some state
        List<Message> messages = List.of(Message.tool("test output", "call-1", "tool"));
        detector.check("session-1", messages, 1);
        detector.check("session-2", messages, 1);

        // Reset should not throw
        assertDoesNotThrow(detector::reset);
    }

    @Test
    void testMultipleSessions() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(false)
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages1 = List.of(Message.tool("output 1", "call-1", "tool"));
        List<Message> messages2 = List.of(Message.tool("output 2", "call-2", "tool"));

        StuckDetectionResult result1 = detector.check("session-1", messages1, 1);
        StuckDetectionResult result2 = detector.check("session-2", messages2, 1);

        // Both should return semantic_disabled
        assertEquals("semantic_disabled", result1.reason());
        assertEquals("semantic_disabled", result2.reason());
    }

    @Test
    void testCheckWithAssistantMessage() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .minChars(1)
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages = List.of(
            Message.user("hello"),
            Message.assistant("This is a long assistant response for testing purposes"),
            Message.tool("Tool output here", "call-1", "tool")
        );

        StuckDetectionResult result = detector.check("session-1", messages, 2);

        // Without model, should return model_unavailable
        assertFalse(result.isStuck());
        assertEquals("model_unavailable", result.reason());
    }

    @Test
    void testCheckFiltersShortMessages() {
        StuckDetectorConfig config = StuckDetectorConfig.builder()
            .enableSemantic(true)
            .minChars(100)  // Only messages with 100+ chars
            .build();
        StuckDetector detector = new StuckDetector(config);

        List<Message> messages = List.of(
            Message.tool("Short", "call-1", "tool"),  // Too short
            Message.tool("This is a longer tool output that should be included because it has many characters", "call-2", "tool")
        );

        StuckDetectionResult result = detector.check("session-1", messages, 3);

        // Should process but fail due to no model
        assertEquals("model_unavailable", result.reason());
    }
}
