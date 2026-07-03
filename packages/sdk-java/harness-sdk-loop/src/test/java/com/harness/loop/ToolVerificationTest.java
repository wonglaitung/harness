package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.ToolVerificationConfig;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.VerificationResult;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for tool-based goal verification.
 */
class ToolVerificationTest {

    @TempDir
    Path tempDir;

    @Test
    void testToolVerificationSuccess() throws Exception {
        // Create a simple verification script that always succeeds
        Path scriptPath = tempDir.resolve("verify_success.sh");
        Files.writeString(scriptPath, "#!/bin/bash\necho 'All tests passed'\nexit 0\n");
        scriptPath.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("verify", "/bin/bash", scriptPath.toString())
                .workingDirectory(tempDir.toString())
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        CompletableFuture<VerificationResult> future = verifier.verify(goalResult);
        VerificationResult result = future.join();

        assertTrue(result.isAchieved());
        assertEquals(1.0, result.getConfidence());
        assertTrue(result.getReasoning().contains("PASSED"));
        assertFalse(result.shouldRetry());
    }

    @Test
    void testToolVerificationFailure() throws Exception {
        // Create a script that fails
        Path scriptPath = tempDir.resolve("verify_fail.sh");
        Files.writeString(scriptPath, "#!/bin/bash\necho 'Test failed'\nexit 1\n");
        scriptPath.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("verify", "/bin/bash", scriptPath.toString())
                .workingDirectory(tempDir.toString())
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        CompletableFuture<VerificationResult> future = verifier.verify(goalResult);
        VerificationResult result = future.join();

        assertFalse(result.isAchieved());
        assertTrue(result.getReasoning().contains("FAILED") || result.getReasoning().contains("failed"));
    }

    @Test
    void testMultipleCommandsAllPass() throws Exception {
        Path script1 = tempDir.resolve("test1.sh");
        Files.writeString(script1, "#!/bin/bash\necho 'Test 1 passed'\nexit 0\n");
        script1.toFile().setExecutable(true);

        Path script2 = tempDir.resolve("test2.sh");
        Files.writeString(script2, "#!/bin/bash\necho 'Test 2 passed'\nexit 0\n");
        script2.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("test1", "/bin/bash", script1.toString())
                .addCommand("test2", "/bin/bash", script2.toString())
                .workingDirectory(tempDir.toString())
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        VerificationResult result = verifier.verify(goalResult).join();

        assertTrue(result.isAchieved());
        assertTrue(result.getReasoning().contains("test1: PASSED"));
        assertTrue(result.getReasoning().contains("test2: PASSED"));
    }

    @Test
    void testMultipleCommandsFailFast() throws Exception {
        Path script1 = tempDir.resolve("test1.sh");
        Files.writeString(script1, "#!/bin/bash\necho 'Test 1 failed'\nexit 1\n");
        script1.toFile().setExecutable(true);

        Path script2 = tempDir.resolve("test2.sh");
        Files.writeString(script2, "#!/bin/bash\necho 'Test 2 passed'\nexit 0\n");
        script2.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("test1", "/bin/bash", script1.toString())
                .addCommand("test2", "/bin/bash", script2.toString())
                .workingDirectory(tempDir.toString())
                .failFast(true)
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        VerificationResult result = verifier.verify(goalResult).join();

        // Should fail fast, not run test2
        assertFalse(result.isAchieved());
        assertTrue(result.getReasoning().contains("test1: FAILED"));
        // test2 should not be mentioned since failFast is true
    }

    @Test
    void testCommandTimeout() throws Exception {
        // Create a script that sleeps for too long
        Path scriptPath = tempDir.resolve("timeout.sh");
        Files.writeString(scriptPath, "#!/bin/bash\necho 'Starting...'\nsleep 10\nexit 0\n");
        scriptPath.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("slow", "/bin/bash", scriptPath.toString())
                .workingDirectory(tempDir.toString())
                .timeoutSeconds(1)
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        // Should fail with timeout
        VerificationResult result = verifier.verify(goalResult).join();

        assertFalse(result.isAchieved());
        assertTrue(result.getReasoning().toLowerCase().contains("timeout")
                || result.getReasoning().contains("error"));
    }

    @Test
    void testMissingToolConfigThrows() {
        assertThrows(IllegalArgumentException.class, () -> {
            GoalConfig.builder()
                    .description("Test goal")
                    .verificationMethod(VerificationMethod.TOOL)
                    // Missing toolVerificationConfig
                    .build();
        });
    }

    @Test
    void testPythonDefaultsConfig() {
        ToolVerificationConfig config = ToolVerificationConfig.pythonDefaults();

        assertEquals(3, config.getCommands().size());
        assertEquals("pytest", config.getCommands().get(0).getName());
        assertEquals("mypy", config.getCommands().get(1).getName());
        assertEquals("ruff", config.getCommands().get(2).getName());
        assertTrue(config.isFailFast());
    }

    @Test
    void testGradleDefaultsConfig() {
        ToolVerificationConfig config = ToolVerificationConfig.gradleDefaults();

        assertEquals(2, config.getCommands().size());
        assertEquals(600, config.getTimeoutSeconds());
    }

    @Test
    void testWorkspaceDirFromContext() throws Exception {
        Path scriptPath = tempDir.resolve("verify.sh");
        Files.writeString(scriptPath, "#!/bin/bash\necho 'OK'\nexit 0\n");
        scriptPath.toFile().setExecutable(true);

        ToolVerificationConfig toolConfig = ToolVerificationConfig.builder()
                .addCommand("verify", "/bin/bash", scriptPath.toString())
                .workingDirectory("/wrong/path")  // Will be overridden
                .build();

        GoalConfig config = GoalConfig.builder()
                .description("Test goal")
                .verificationMethod(VerificationMethod.TOOL)
                .toolVerificationConfig(toolConfig)
                .build();

        GoalVerifier verifier = new GoalVerifier(config);
        GoalResult goalResult = createTestGoalResult();

        // Pass workspace_dir via context
        Map<String, Object> context = Map.of("workspace_dir", tempDir.toString());

        VerificationResult result = verifier.verify(goalResult, context).join();
        assertTrue(result.isAchieved());
    }

    private GoalResult createTestGoalResult() {
        return GoalResult.builder()
                .goal("test-goal")
                .status(GoalStatus.ACHIEVED)
                .finalResponse("Test completed")
                .totalIterations(1)
                .build();
    }
}
