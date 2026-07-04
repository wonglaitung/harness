package com.harness.loop.automation;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Automation.
 */
class AutomationTest {

    private MockAgentRunner agent;

    @BeforeEach
    void setUp() {
        agent = new MockAgentRunner();
    }

    @AfterEach
    void tearDown() {
        agent = null;
    }

    @Test
    void testIntervalBasedAutomation() throws Exception {
        Automation automation = Automation.builder()
                .name("test-interval")
                .goal("Test goal")
                .intervalSeconds(1) // 1 second interval
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("Done", 1);

        // Start automation
        automation.start(agent).join();

        // Give scheduler time to start
        Thread.sleep(100);

        assertEquals(AutomationStatus.RUNNING, automation.getStatus());

        // Wait for at least one scheduled execution
        Thread.sleep(1500);

        // Stop automation
        automation.stop().join();

        assertEquals(AutomationStatus.STOPPED, automation.getStatus());
        // At least one execution should have happened via scheduler
        assertTrue(automation.getResult().getRunCount() >= 1,
                "Expected at least 1 run, got " + automation.getResult().getRunCount());
    }

    @Test
    void testCronBasedAutomation() throws Exception {
        Automation automation = Automation.builder()
                .name("test-cron")
                .goal("Test goal")
                .schedule("*/1 * * * *") // Every minute
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("Done", 1);

        automation.start(agent).join();

        assertTrue(automation.isRunning());

        // Stop immediately for unit test
        automation.stop().join();

        assertEquals(AutomationStatus.STOPPED, automation.getStatus());
    }

    @Test
    void testPauseAndResume() throws Exception {
        Automation automation = Automation.builder()
                .name("test-pause")
                .goal("Test goal")
                .intervalSeconds(1)
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("Done", 1);

        automation.start(agent).join();
        assertTrue(automation.isRunning());

        // Pause
        automation.pause();
        assertEquals(AutomationStatus.PAUSED, automation.getStatus());

        // Resume
        automation.resume();
        assertEquals(AutomationStatus.RUNNING, automation.getStatus());

        // Stop
        automation.stop().join();
        assertEquals(AutomationStatus.STOPPED, automation.getStatus());
    }

    @Test
    void testManualExecution() throws Exception {
        Automation automation = Automation.builder()
                .name("test-manual")
                .goal("Test goal")
                .intervalSeconds(3600) // Long interval
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("Manual execution done", 1);

        // Start automation
        automation.start(agent).join();

        // Execute manually
        GoalResult result = automation.executeNow().join();

        assertTrue(result.achieved());
        assertEquals(1, automation.getResult().getRunCount());

        automation.stop().join();
    }

    @Test
    void testOutputChannels() throws Exception {
        List<String> outputs = new ArrayList<>();

        Automation automation = Automation.builder()
                .name("test-output")
                .goal("Test goal")
                .intervalSeconds(3600)
                .addOutputChannel("console")
                .addOutputChannel("log")
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("Output test result", 1);

        automation.start(agent).join();
        automation.executeNow().join();

        assertEquals(1, automation.getResult().getRunCount());

        automation.stop().join();
    }

    @Test
    void testCustomVerifier() throws Exception {
        AtomicInteger verifierCalls = new AtomicInteger(0);

        Automation automation = Automation.builder()
                .name("test-verifier")
                .goal("Test goal")
                .intervalSeconds(3600)
                .customVerifier(result -> {
                    verifierCalls.incrementAndGet();
                    return result.finalResponse() != null && result.finalResponse().contains("success");
                })
                .build();

        // Add two responses: one for start() which triggers immediately (delay=0),
        // and one for executeNow()
        agent.addResponse("Task success!", 1);
        agent.addResponse("Task success!", 1);

        automation.start(agent).join();
        // Small delay to let the scheduled execution complete
        Thread.sleep(100);
        GoalResult result = automation.executeNow().join();

        // Check that the verifier was called
        assertTrue(verifierCalls.get() >= 1, "Custom verifier should have been called at least once");

        automation.stop().join();
    }

    @Test
    void testConfigValidation() {
        // Missing name - AutomationConfig validates this
        assertThrows(IllegalArgumentException.class, () ->
                AutomationConfig.builder()
                        .goal("Test")
                        .intervalSeconds(60)
                        .build());

        // Missing goal
        assertThrows(IllegalArgumentException.class, () ->
                AutomationConfig.builder()
                        .name("test")
                        .intervalSeconds(60)
                        .build());

        // Missing trigger (neither schedule nor interval)
        assertThrows(IllegalArgumentException.class, () ->
                AutomationConfig.builder()
                        .name("test")
                        .goal("Test")
                        .build());

        // Both schedule and interval
        assertThrows(IllegalArgumentException.class, () ->
                AutomationConfig.builder()
                        .name("test")
                        .goal("Test")
                        .schedule("0 9 * * *")
                        .intervalSeconds(60)
                        .build());
    }

    @Test
    void testResultTracking() throws Exception {
        Automation automation = Automation.builder()
                .name("test-result")
                .goal("Test goal")
                .intervalSeconds(3600) // Long interval so scheduled execution doesn't interfere
                .customVerifier(result -> true) // Simple verifier for testing
                .build();

        agent.addResponse("First", 1);
        agent.addResponse("Second", 1);

        automation.start(agent).join();

        // Execute twice manually
        automation.executeNow().join();
        automation.executeNow().join();

        AutomationResult result = automation.getResult();
        // Should have at least 2 runs from manual executions
        assertTrue(result.getRunCount() >= 2,
                "Expected at least 2 runs, got " + result.getRunCount());
        assertNotNull(result.getLastRun());

        automation.stop().join();
    }

    @Test
    void testStopWithoutStart() {
        Automation automation = Automation.builder()
                .name("test-stop")
                .goal("Test")
                .intervalSeconds(60)
                .build();

        // Should be safe to call stop without start
        automation.stop().join();
        assertEquals(AutomationStatus.STOPPED, automation.getStatus());
    }

    /**
     * Mock AgentRunner for testing.
     */
    private static class MockAgentRunner implements GoalLoop.AgentRunner {
        private final List<LoopResult> responses = new ArrayList<>();
        private int index = 0;

        void addResponse(String content, int iterations) {
            Session session = Session.create("test-session-" + index);
            responses.add(LoopResult.completed(
                    session,
                    content,
                    iterations,
                    new TokenUsage(100, 50)
            ));
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
            return run(prompt, sessionId, null);
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress) {
            if (index >= responses.size()) {
                Session session = Session.create(sessionId);
                return CompletableFuture.completedFuture(
                        LoopResult.completed(session, "Default", 1, new TokenUsage(100, 50))
                );
            }
            return CompletableFuture.completedFuture(responses.get(index++));
        }

        @Override
        public Session getSession(String sessionId) {
            return Session.create(sessionId);
        }

        @Override
        public int getContextWindow() {
            return 100000;
        }
    }
}
