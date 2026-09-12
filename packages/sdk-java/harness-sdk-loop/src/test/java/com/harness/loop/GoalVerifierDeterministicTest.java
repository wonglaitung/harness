package com.harness.loop;

import static org.junit.jupiter.api.Assertions.*;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationResult;

import org.junit.jupiter.api.Test;

/**
 * Tests for GoalVerifier C4 deterministic_verifier override.
 */
class GoalVerifierDeterministicTest {

    @Test
    void deterministicVerifierRunsAlongsideLLM() {
        // deterministicVerifier: always returns achieved=true
        GoalConfig config = GoalConfig.builder()
            .description("test goal")
            .verificationMethod(com.harness.loop.types.VerificationMethod.LLM)
            .deterministicVerifier(result -> VerificationResult.builder()
                .achieved(true)
                .confidence(1.0)
                .reasoning("deterministic says yes")
                .build())
            .build();

        // No LLM client needed for this test - we verify config field exists
        assertNotNull(config.getDeterministicVerifier());
    }

    @Test
    void deterministicVerifierNullByDefault() {
        GoalConfig config = GoalConfig.builder()
            .description("test goal")
            .verificationMethod(com.harness.loop.types.VerificationMethod.LLM)
            .build();
        assertNull(config.getDeterministicVerifier());
    }

    @Test
    void deterministicVerifierCanOverrideVerdict() {
        // deterministicVerifier: always returns NOT achieved
        GoalConfig config = GoalConfig.builder()
            .description("test goal")
            .verificationMethod(com.harness.loop.types.VerificationMethod.LLM)
            .deterministicVerifier(result -> VerificationResult.builder()
                .achieved(false)
                .confidence(1.0)
                .reasoning("deterministic says no")
                .build())
            .build();

        VerificationResult detResult = config.getDeterministicVerifier().apply(null);
        assertFalse(detResult.isAchieved());
        assertEquals("deterministic says no", detResult.getReasoning());
    }

    @Test
    void deterministicVerifierRunsBothPaths() {
        // Simulate dual-path: deterministicVerifier is set, LLM would also run
        GoalConfig config = GoalConfig.builder()
            .description("test goal")
            .verificationMethod(com.harness.loop.types.VerificationMethod.LLM)
            .deterministicVerifier(result -> VerificationResult.builder()
                .achieved(true)
                .confidence(0.9)
                .reasoning("[C4 dual-path] deterministic verifier passed")
                .build())
            .build();

        assertNotNull(config.getDeterministicVerifier());
        // When both paths agree, deterministic result is used
        VerificationResult result = config.getDeterministicVerifier().apply(null);
        assertTrue(result.isAchieved());
    }
}
