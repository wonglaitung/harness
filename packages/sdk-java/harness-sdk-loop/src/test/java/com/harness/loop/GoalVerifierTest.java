package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.VerificationResult;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for GoalVerifier.
 */
class GoalVerifierTest {

    private GoalConfig.Builder configBuilder;

    @BeforeEach
    void setUp() {
        configBuilder = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.CUSTOM);
    }

    @Test
    void testCustomVerifierAchieved() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> true)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestResult("Goal completed successfully");

        VerificationResult result = verifier.verify(goalResult).join();

        assertTrue(result.isAchieved());
        assertEquals(1.0, result.getConfidence());
        assertEquals("Custom verifier result", result.getReasoning());
    }

    @Test
    void testCustomVerifierNotAchieved() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> false)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestResult("Work in progress");

        VerificationResult result = verifier.verify(goalResult).join();

        assertFalse(result.isAchieved());
        assertEquals(0.0, result.getConfidence());
    }

    @Test
    void testCustomVerifierNullResult() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> null)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestResult("Unclear result");

        VerificationResult result = verifier.verify(goalResult).join();

        assertFalse(result.isAchieved()); // null should be treated as false
    }

    @Test
    void testCustomVerifierException() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> {
                    throw new RuntimeException("Test exception");
                })
                .verifierMaxRetries(0) // No retries for faster test
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestResult("Test");

        // Exception results in a fault result, not a thrown exception
        VerificationResult result = verifier.verify(goalResult).join();

        assertFalse(result.isAchieved());
        assertTrue(result.getError() != null || result.getReasoning().contains("fault"));
    }

    @Test
    void testMissingCustomVerifier() {
        // Validation happens in GoalConfig.build(), not in GoalVerifier constructor
        assertThrows(IllegalArgumentException.class, () -> GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.CUSTOM)
                .build());
    }

    @Test
    void testVerificationHistory() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> result.finalResponse().contains("success"))
                .build();

        GoalVerifier verifier = new GoalVerifier(config);

        // First verification - not achieved
        GoalResult result1 = createTestResult("Working...");
        verifier.verify(result1).join();

        // Second verification - achieved
        GoalResult result2 = createTestResult("Task success!");
        verifier.verify(result2).join();

        assertEquals(2, verifier.getVerificationHistory().size());
        assertFalse(verifier.getVerificationHistory().get(0).isAchieved());
        assertTrue(verifier.getVerificationHistory().get(1).isAchieved());
    }

    @Test
    void testClearHistory() throws Exception {
        GoalConfig config = configBuilder
                .customVerifier(result -> true)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        verifier.verify(createTestResult("Test")).join();

        assertEquals(1, verifier.getVerificationHistory().size());

        verifier.clearHistory();

        assertEquals(0, verifier.getVerificationHistory().size());
    }

    @Test
    void testRetryOnFault() throws Exception {
        int[] callCount = {0};

        GoalConfig config = configBuilder
                .customVerifier(result -> {
                    callCount[0]++;
                    if (callCount[0] < 3) {
                        throw new RuntimeException("Rate limit exceeded");
                    }
                    return true;
                })
                .verifierMaxRetries(3)
                .verifierRetryDelay(0.1) // Fast retry for testing
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestResult("Test");

        VerificationResult result = verifier.verify(goalResult).join();

        assertTrue(result.isAchieved());
        assertEquals(3, callCount[0]);
    }

    @Test
    void testSuccessCriteriaInConfig() {
        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .successCriteria("All tests pass and coverage > 80%")
                .verificationMethod(VerificationMethod.CUSTOM)
                .customVerifier(result -> true)
                .build();

        assertEquals("All tests pass and coverage > 80%", config.getSuccessCriteria());
    }

    private GoalResult createTestResult(String response) {
        Map<String, Integer> tokens = new HashMap<>();
        tokens.put("input", 100);
        tokens.put("output", 50);

        return new GoalResult.Builder()
                .goal("Test goal")
                .status(GoalStatus.ACHIEVED)
                .totalIterations(1)
                .finalResponse(response)
                .totalTokens(tokens)
                .durationSeconds(1.0)
                .build();
    }
}
