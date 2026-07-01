package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationMethod;
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for GoalLoop.
 */
class GoalLoopTest {

    private GoalConfig.Builder configBuilder;

    @BeforeEach
    void setUp() {
        configBuilder = GoalConfig.builder()
                .description("Test goal: Complete the task")
                .maxIterations(10)
                .maxContextResets(2)
                .timeoutSeconds(60)
                .verificationMethod(VerificationMethod.CUSTOM);
    }

    @Test
    void testGoalAchievedImmediately() {
        GoalConfig config = configBuilder
                .customVerifier(result -> result.finalResponse().contains("done"))
                .build();

        // Agent that immediately succeeds
        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Task is done!", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertTrue(result.achieved());
        assertEquals(GoalStatus.ACHIEVED, result.status());
        assertEquals(1, result.totalIterations());
    }

    @Test
    void testGoalAchievedAfterIterations() {
        GoalConfig config = configBuilder
                .customVerifier(result -> result.finalResponse().contains("success"))
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Working on it...", 1);
        agent.addResponse("Still working...", 1);
        agent.addResponse("Task is a success!", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertTrue(result.achieved());
        assertEquals(3, result.totalIterations());
        assertEquals(3, result.verificationLog().size());
    }

    @Test
    void testMaxIterationsReached() {
        GoalConfig config = configBuilder
                .maxIterations(3)
                .customVerifier(result -> false) // Never achieved
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Attempt 1", 1);
        agent.addResponse("Attempt 2", 1);
        agent.addResponse("Attempt 3", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertFalse(result.achieved());
        assertEquals(GoalStatus.MAX_ITERATIONS, result.status());
        assertEquals(3, result.totalIterations());
    }

    @Test
    void testTimeout() {
        GoalConfig config = configBuilder
                .timeoutSeconds(1) // Very short timeout
                .customVerifier(result -> false)
                .build();

        MockAgentRunner agent = new MockAgentRunner(500); // 500ms delay per iteration
        agent.addResponse("Working...", 1);
        agent.addResponse("Still working...", 1);
        agent.addResponse("Continue...", 1);
        agent.addResponse("More work...", 1);
        agent.addResponse("Almost there...", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertFalse(result.achieved());
        assertEquals(GoalStatus.TIMEOUT, result.status());
    }

    @Test
    void testContextReset() {
        GoalConfig config = configBuilder
                .maxIterations(5)
                .contextResetThreshold(0.1) // Very low threshold to trigger reset
                .customVerifier(result -> result.finalResponse().contains("complete"))
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Starting...", 1, 50000, 50000); // High token usage to trigger reset
        agent.addResponse("Work complete!", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertTrue(result.achieved());
        assertTrue(result.contextResets() > 0);
    }

    @Test
    void testMaxContextResets() {
        GoalConfig config = configBuilder
                .maxIterations(10)
                .maxContextResets(1)
                .contextResetThreshold(0.05) // Very low threshold
                .customVerifier(result -> false) // Never achieved
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Attempt 1", 1, 50000, 50000);
        agent.addResponse("Attempt 2", 1, 50000, 50000);
        agent.addResponse("Attempt 3", 1, 50000, 50000);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertFalse(result.achieved());
        assertEquals(GoalStatus.MAX_RESETS, result.status());
    }

    @Test
    void testVerificationHistoryTracking() {
        GoalConfig config = configBuilder
                .customVerifier(result -> result.finalResponse().contains("done"))
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Step 1", 1);
        agent.addResponse("Step 2", 1);
        agent.addResponse("All done!", 1);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertEquals(3, result.verificationLog().size());

        // Check first two are not achieved
        assertFalse(result.verificationLog().get(0).isAchieved());
        assertFalse(result.verificationLog().get(1).isAchieved());

        // Check last is achieved
        assertTrue(result.verificationLog().get(2).isAchieved());
    }

    @Test
    void testProgressCallback() {
        List<Object> progressEvents = new ArrayList<>();

        GoalConfig config = configBuilder
                .customVerifier(result -> result.finalResponse().contains("done"))
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Working...", 1);
        agent.addResponse("All done!", 1);

        GoalLoop loop = new GoalLoop(agent, config, progressEvents::add);
        GoalResult result = loop.run().join();

        assertTrue(result.achieved());
        assertFalse(progressEvents.isEmpty());
    }

    @Test
    void testTokenTracking() {
        GoalConfig config = configBuilder
                .customVerifier(result -> true)
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.addResponse("Done", 1, 1000, 500);

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertEquals(1000, result.totalTokens().get("input"));
        assertEquals(500, result.totalTokens().get("output"));
    }

    @Test
    void testAgentError() {
        GoalConfig config = configBuilder
                .customVerifier(result -> true)
                .build();

        MockAgentRunner agent = new MockAgentRunner();
        agent.setError(new RuntimeException("Agent failed"));

        GoalLoop loop = new GoalLoop(agent, config);
        GoalResult result = loop.run().join();

        assertFalse(result.achieved());
        assertEquals(GoalStatus.ERROR, result.status());
        assertTrue(result.error().contains("Agent failed"));
    }

    /**
     * Mock AgentRunner for testing.
     */
    private static class MockAgentRunner implements GoalLoop.AgentRunner {
        private final List<LoopResult> responses = new ArrayList<>();
        private final long delayMs;
        private int index = 0;
        private RuntimeException error = null;

        MockAgentRunner() {
            this(0);
        }

        MockAgentRunner(long delayMs) {
            this.delayMs = delayMs;
        }

        void addResponse(String content, int iterations) {
            addResponse(content, iterations, 100, 50);
        }

        void addResponse(String content, int iterations, int inputTokens, int outputTokens) {
            Session session = Session.create("test-session-" + index);
            responses.add(LoopResult.completed(
                    session,
                    content,
                    iterations,
                    new TokenUsage(inputTokens, outputTokens)
            ));
        }

        void setError(RuntimeException error) {
            this.error = error;
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
            return run(prompt, sessionId, null);
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress) {
            if (error != null) {
                return CompletableFuture.failedFuture(error);
            }

            if (index >= responses.size()) {
                // Default response if we run out
                Session session = Session.create(sessionId);
                return CompletableFuture.completedFuture(
                        LoopResult.completed(session, "Default response", 1, new TokenUsage(100, 50))
                );
            }

            LoopResult result = responses.get(index++);

            if (delayMs > 0) {
                return CompletableFuture.supplyAsync(() -> {
                    try {
                        Thread.sleep(delayMs);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                    return result;
                });
            }

            return CompletableFuture.completedFuture(result);
        }

        @Override
        public Session getSession(String sessionId) {
            return Session.create(sessionId);
        }

        @Override
        public int getContextWindow() {
            return 100000; // Default context window
        }
    }
}
