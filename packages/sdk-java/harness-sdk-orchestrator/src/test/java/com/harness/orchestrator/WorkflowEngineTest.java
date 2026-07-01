package com.harness.orchestrator;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for WorkflowEngine.
 */
class WorkflowEngineTest {

    private MockAgentRunner agent;
    private WorkflowEngine engine;

    @BeforeEach
    void setUp() {
        agent = new MockAgentRunner();
        engine = new WorkflowEngine(agent);
    }

    @Test
    void testSingleStepWorkflow() {
        agent.addResponse("Done", 1, true);

        WorkflowConfig config = WorkflowConfig.builder()
                .name("single-step")
                .addStep(WorkflowStep.builder()
                        .name("step1")
                        .goal("Do something")
                        .build())
                .build();

        WorkflowResult result = engine.execute(config).join();

        assertTrue(result.isSuccess());
        assertEquals(WorkflowStatus.COMPLETED, result.getStatus());
        assertEquals(1, result.getSteps().size());

        StepResult stepResult = result.getStepResult("step1");
        assertNotNull(stepResult);
        assertEquals(StepStatus.SUCCESS, stepResult.getStatus());
    }

    @Test
    void testSequentialSteps() {
        agent.addResponse("Step 1 done", 1, true);
        agent.addResponse("Step 2 done", 1, true);

        WorkflowConfig config = WorkflowConfig.builder()
                .name("sequential-workflow")
                .addStep(WorkflowStep.builder()
                        .name("step1")
                        .goal("First step")
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("step2")
                        .goal("Second step")
                        .addDependsOn("step1")
                        .build())
                .build();

        WorkflowResult result = engine.execute(config).join();

        assertTrue(result.isSuccess());
        assertEquals(2, result.getSteps().size());
        assertEquals(2, result.getSuccessfulSteps().size());
    }

    @Test
    void testParallelSteps() {
        agent.addResponse("Step A done", 1, true);
        agent.addResponse("Step B done", 1, true);

        WorkflowConfig config = WorkflowConfig.builder()
                .name("parallel-workflow")
                .addStep(WorkflowStep.builder()
                        .name("stepA")
                        .goal("Parallel step A")
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("stepB")
                        .goal("Parallel step B")
                        .build())
                .build();

        WorkflowResult result = engine.execute(config).join();

        assertTrue(result.isSuccess());
        assertEquals(2, result.getSuccessfulSteps().size());
    }

    @Test
    void testFailedStep() {
        // Use custom verifier that always returns false
        WorkflowConfig config = WorkflowConfig.builder()
                .name("failed-workflow")
                .addStep(WorkflowStep.builder()
                        .name("step1")
                        .goal("Will fail")
                        .customVerifier(result -> false) // Always fail
                        .build())
                .build();

        WorkflowResult result = engine.execute(config).join();

        assertFalse(result.isSuccess());
        assertEquals(WorkflowStatus.FAILED, result.getStatus());
        assertEquals(1, result.getFailedSteps().size());
    }

    @Test
    void testDependencyFailureSkipsDependent() {
        WorkflowConfig config = WorkflowConfig.builder()
                .name("dependency-failure")
                .addStep(WorkflowStep.builder()
                        .name("step1")
                        .goal("Will fail")
                        .customVerifier(result -> false) // Always fail
                        .build())
                .addStep(WorkflowStep.builder()
                        .name("step2")
                        .goal("Should be skipped")
                        .addDependsOn("step1")
                        .build())
                .build();

        WorkflowResult result = engine.execute(config).join();

        assertFalse(result.isSuccess());
        assertEquals(StepStatus.FAILED, result.getStepResult("step1").getStatus());
        assertEquals(StepStatus.SKIPPED, result.getStepResult("step2").getStatus());
    }

    @Test
    void testWorkflowConfigValidation() {
        // Empty name
        assertThrows(IllegalArgumentException.class, () ->
                WorkflowConfig.builder().build());

        // Duplicate step names
        assertThrows(IllegalArgumentException.class, () ->
                WorkflowConfig.builder()
                        .name("test")
                        .addStep(WorkflowStep.builder()
                                .name("duplicate")
                                .goal("Goal 1")
                                .build())
                        .addStep(WorkflowStep.builder()
                                .name("duplicate")
                                .goal("Goal 2")
                                .build())
                        .build());
    }

    @Test
    void testWorkflowStepValidation() {
        // Empty name
        assertThrows(IllegalArgumentException.class, () ->
                WorkflowStep.builder()
                        .goal("Test goal")
                        .build());

        // Empty goal
        assertThrows(IllegalArgumentException.class, () ->
                WorkflowStep.builder()
                        .name("test")
                        .build());
    }

    @Test
    void testWorkflowResultMethods() {
        WorkflowResult result = WorkflowResult.builder()
                .workflowName("test")
                .status(WorkflowStatus.COMPLETED)
                .addStepResult("step1", StepResult.builder()
                        .stepName("step1")
                        .status(StepStatus.SUCCESS)
                        .build())
                .addStepResult("step2", StepResult.builder()
                        .stepName("step2")
                        .status(StepStatus.FAILED)
                        .build())
                .addStepResult("step3", StepResult.builder()
                        .stepName("step3")
                        .status(StepStatus.SKIPPED)
                        .build())
                .startedAt(java.time.Instant.now())
                .completedAt(java.time.Instant.now())
                .build();

        assertEquals(1, result.getSuccessfulSteps().size());
        assertEquals(1, result.getFailedSteps().size());
        assertEquals(1, result.getSkippedSteps().size());
        assertTrue(result.getSuccessfulSteps().contains("step1"));
        assertTrue(result.getFailedSteps().contains("step2"));
        assertTrue(result.getSkippedSteps().contains("step3"));
    }

    /**
     * Mock AgentRunner for testing.
     */
    private static class MockAgentRunner implements GoalLoop.AgentRunner {
        private final List<MockResponse> responses = new ArrayList<>();
        private int index = 0;

        void addResponse(String content, int iterations, boolean achieved) {
            responses.add(new MockResponse(content, iterations, achieved));
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

            MockResponse response = responses.get(index++);
            Session session = Session.create(sessionId);

            if (response.achieved) {
                return CompletableFuture.completedFuture(
                        LoopResult.completed(session, response.content, response.iterations,
                                new TokenUsage(100, 50))
                );
            } else {
                return CompletableFuture.completedFuture(
                        LoopResult.completed(session, response.content, response.iterations,
                                new TokenUsage(100, 50))
                );
            }
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

    private record MockResponse(String content, int iterations, boolean achieved) {}
}
