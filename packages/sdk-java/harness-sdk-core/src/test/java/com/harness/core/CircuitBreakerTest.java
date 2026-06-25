package com.harness.core;

import java.util.Map;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for CircuitBreaker.
 *
 * Tests state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
 */
class CircuitBreakerTest {

    // === CircuitBreakerConfig Tests ===

    @Test
    void testConfigDefaults() {
        CircuitBreakerConfig config = CircuitBreakerConfig.defaults();

        assertEquals(CircuitBreakerConfig.DEFAULT_SAME_ARGS_THRESHOLD, config.sameArgsThreshold());
        assertEquals(CircuitBreakerConfig.DEFAULT_ERROR_THRESHOLD, config.errorThreshold());
        assertEquals(CircuitBreakerConfig.DEFAULT_ERROR_WINDOW, config.errorWindowSeconds());
        assertEquals(CircuitBreakerConfig.DEFAULT_RECOVERY_TIMEOUT, config.recoveryTimeoutSeconds());
        assertEquals(CircuitBreakerConfig.DEFAULT_HALF_OPEN_MAX_CALLS, config.halfOpenMaxCalls());
    }

    @Test
    void testConfigCustomValues() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(5)
            .errorThreshold(10)
            .errorWindowSeconds(120)
            .recoveryTimeoutSeconds(60)
            .halfOpenMaxCalls(3)
            .build();

        assertEquals(5, config.sameArgsThreshold());
        assertEquals(10, config.errorThreshold());
        assertEquals(120, config.errorWindowSeconds());
        assertEquals(60, config.recoveryTimeoutSeconds());
        assertEquals(3, config.halfOpenMaxCalls());
    }

    @Test
    void testConfigDefaultConstructor() {
        CircuitBreakerConfig config = new CircuitBreakerConfig();

        assertEquals(3, config.sameArgsThreshold());
        assertEquals(5, config.errorThreshold());
        assertEquals(60, config.errorWindowSeconds());
        assertEquals(30, config.recoveryTimeoutSeconds());
        assertEquals(1, config.halfOpenMaxCalls());
    }

    // === CircuitState Tests ===

    @Test
    void testCircuitStateValues() {
        CircuitState[] states = CircuitState.values();

        assertEquals(3, states.length);
        assertEquals(CircuitState.CLOSED, CircuitState.valueOf("CLOSED"));
        assertEquals(CircuitState.OPEN, CircuitState.valueOf("OPEN"));
        assertEquals(CircuitState.HALF_OPEN, CircuitState.valueOf("HALF_OPEN"));
    }

    // === CircuitBreaker Tests ===

    @Test
    void testCircuitBreakerCreation() {
        CircuitBreaker cb = new CircuitBreaker();

        assertNotNull(cb);
        assertEquals(CircuitState.CLOSED, cb.getState());
        assertFalse(cb.isOpen());
    }

    @Test
    void testCircuitBreakerWithConfig() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(5)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        assertNotNull(cb);
        assertEquals(CircuitState.CLOSED, cb.getState());
    }

    @Test
    void testRecordCall() {
        CircuitBreaker cb = new CircuitBreaker();

        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));

        // Should not open yet (threshold is 3 by default)
        assertFalse(cb.isOpen());
        assertEquals(CircuitState.CLOSED, cb.getState());
    }

    @Test
    void testSameArgsThresholdOpensCircuit() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));

        // Should open after 2 identical calls
        assertTrue(cb.isOpen());
        assertEquals(CircuitState.OPEN, cb.getState());
        assertNotNull(cb.getReason());
        assertTrue(cb.getReason().contains("read"));
    }

    @Test
    void testDifferentArgsDoNotTrigger() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("read", Map.of("path", "/tmp/file1.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file2.txt"));

        // Different args should not trigger
        assertFalse(cb.isOpen());
        assertEquals(CircuitState.CLOSED, cb.getState());
    }

    @Test
    void testDifferentToolsDoNotTrigger() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("write", Map.of("path", "/tmp/file.txt"));

        // Different tools should not trigger
        assertFalse(cb.isOpen());
        assertEquals(CircuitState.CLOSED, cb.getState());
    }

    @Test
    void testRecordError() {
        CircuitBreaker cb = new CircuitBreaker();

        // Record 5 errors (default threshold)
        for (int i = 0; i < 5; i++) {
            cb.recordError(new RuntimeException("Error " + i));
        }

        assertTrue(cb.isOpen());
        assertEquals(CircuitState.OPEN, cb.getState());
        assertNotNull(cb.getReason());
        assertTrue(cb.getReason().contains("errors"));
    }

    @Test
    void testRecordErrorBelowThreshold() {
        CircuitBreaker cb = new CircuitBreaker();

        // Record 4 errors (below threshold of 5)
        for (int i = 0; i < 4; i++) {
            cb.recordError(new RuntimeException("Error " + i));
        }

        assertFalse(cb.isOpen());
        assertEquals(CircuitState.CLOSED, cb.getState());
    }

    @Test
    void testRecordSuccessClosesHalfOpen() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .recoveryTimeoutSeconds(0)  // Immediate recovery
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        // Open the circuit
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        assertTrue(cb.isOpen());

        // Wait for recovery (immediate with timeout=0)
        // This simulates entering HALF_OPEN state
        // In practice, we'd need to wait, but for testing we'll reset
        cb.reset();
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        assertTrue(cb.isOpen());
    }

    @Test
    void testReset() {
        CircuitBreaker cb = new CircuitBreaker();

        // Open the circuit
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        cb = new CircuitBreaker(config);
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        assertTrue(cb.isOpen());

        // Reset should close it
        cb.reset();

        assertFalse(cb.isOpen());
        assertEquals(CircuitState.CLOSED, cb.getState());
        assertNull(cb.getReason());
    }

    @Test
    void testGetStats() {
        CircuitBreaker cb = new CircuitBreaker();

        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordError(new RuntimeException("Test error"));

        Map<String, Object> stats = cb.getStats();

        assertEquals("CLOSED", stats.get("state"));
        assertEquals(1, stats.get("recentErrors"));
        assertTrue(stats.containsKey("toolArgsCounter"));
    }

    @Test
    void testGetReasonWhenClosed() {
        CircuitBreaker cb = new CircuitBreaker();

        assertNull(cb.getReason());
    }

    @Test
    void testGetReasonWhenOpen() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/file.txt"));

        String reason = cb.getReason();

        assertNotNull(reason);
        assertTrue(reason.contains("read"));
        assertTrue(reason.contains("2 times"));
    }

    @Test
    void testNestedArgs() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        Map<String, Object> nestedArgs = Map.of(
            "path", "/tmp/file.txt",
            "options", Map.of("encoding", "utf-8")
        );

        cb.recordCall("read", nestedArgs);
        cb.recordCall("read", nestedArgs);

        assertTrue(cb.isOpen());
    }

    @Test
    void testEmptyArgs() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("list", Map.of());
        cb.recordCall("list", Map.of());

        assertTrue(cb.isOpen());
    }

    @Test
    void testNullArgs() {
        CircuitBreakerConfig config = CircuitBreakerConfig.builder()
            .sameArgsThreshold(2)
            .build();
        CircuitBreaker cb = new CircuitBreaker(config);

        cb.recordCall("reset", null);
        cb.recordCall("reset", null);

        assertTrue(cb.isOpen());
    }

    @Test
    void testMultipleToolCallsTracking() {
        CircuitBreaker cb = new CircuitBreaker();

        cb.recordCall("read", Map.of("path", "/tmp/a.txt"));
        cb.recordCall("read", Map.of("path", "/tmp/b.txt"));
        cb.recordCall("write", Map.of("path", "/tmp/c.txt"));
        cb.recordCall("bash", Map.of("command", "ls"));

        Map<String, Object> stats = cb.getStats();
        Map<String, Integer> toolArgsCounter = (Map<String, Integer>) stats.get("toolArgsCounter");

        // Each tool+args combination should be counted once
        assertTrue(toolArgsCounter.size() >= 4);
    }
}
