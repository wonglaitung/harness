package com.harness.loop;

import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeManager.WorktreeInfo;
import com.harness.loop.ParallelGoalExecutor.WorktreeProvider;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ParallelGoalExecutor.
 */
class ParallelGoalExecutorTest {

    private MockAgentRunner mockRunner;
    private MockWorktreeProvider mockWorktree;
    private ParallelGoalExecutor executor;

    @BeforeEach
    void setUp() {
        mockRunner = new MockAgentRunner();
        mockWorktree = new MockWorktreeProvider();
        executor = new ParallelGoalExecutor(mockRunner, mockWorktree);
    }

    @Test
    void testSpawnGoal() {
        mockRunner.addResponse(true, 1);

        WorktreeConfig config = new WorktreeConfig.Builder()
                .name("test-goal")
                .goal("Test goal")
                .build();

        String result = executor.spawnGoal(config).join();

        assertEquals("test-goal", result);
        assertEquals(1, executor.listExecutions().size());
        assertTrue(executor.listExecutions().contains("test-goal"));
    }

    @Test
    void testSpawnDuplicateGoal() {
        mockRunner.addResponse(true, 1);

        WorktreeConfig config = new WorktreeConfig.Builder()
                .name("test-goal")
                .goal("Test goal")
                .build();

        executor.spawnGoal(config).join();

        // Should fail for duplicate
        assertThrows(Exception.class, () ->
                executor.spawnGoal(config).join());
    }

    @Test
    void testRunAll() {
        mockRunner.addResponse(true, 1);
        mockRunner.addResponse(true, 2);

        WorktreeConfig config1 = new WorktreeConfig.Builder()
                .name("goal-1")
                .goal("Goal 1")
                .build();

        WorktreeConfig config2 = new WorktreeConfig.Builder()
                .name("goal-2")
                .goal("Goal 2")
                .build();

        executor.spawnGoal(config1).join();
        executor.spawnGoal(config2).join();

        Map<String, GoalResult> results = executor.runAll().join();

        assertEquals(2, results.size());
        assertTrue(results.containsKey("goal-1"));
        assertTrue(results.containsKey("goal-2"));
    }

    @Test
    void testRunAllEmpty() {
        Map<String, GoalResult> results = executor.runAll().join();

        assertTrue(results.isEmpty());
    }

    @Test
    void testCancel() {
        mockRunner.addResponse(true, 1);

        WorktreeConfig config = new WorktreeConfig.Builder()
                .name("test-goal")
                .goal("Test goal")
                .build();

        executor.spawnGoal(config).join();

        assertTrue(executor.cancel("test-goal"));
        assertFalse(executor.listExecutions().contains("test-goal"));
    }

    @Test
    void testCancelNotFound() {
        assertFalse(executor.cancel("non-existent"));
    }

    @Test
    void testGetExecution() {
        mockRunner.addResponse(true, 1);

        WorktreeConfig config = new WorktreeConfig.Builder()
                .name("test-goal")
                .goal("Test goal")
                .build();

        executor.spawnGoal(config).join();

        ParallelGoalExecutor.GoalExecution execution = executor.getExecution("test-goal");

        assertNotNull(execution);
        assertEquals("Test goal", execution.config.getGoal());
        assertNotNull(execution.goalConfig);
        assertNotNull(execution.worktreePath);
        assertNotNull(execution.createdAt);
    }

    @Test
    void testClear() {
        mockRunner.addResponse(true, 1);

        WorktreeConfig config = new WorktreeConfig.Builder()
                .name("test-goal")
                .goal("Test goal")
                .build();

        executor.spawnGoal(config).join();
        executor.clear();

        assertTrue(executor.listExecutions().isEmpty());
    }

    /**
     * Mock AgentRunner for testing.
     */
    private static class MockAgentRunner implements GoalLoop.AgentRunner {
        private java.util.List<MockResponse> responses = new java.util.ArrayList<>();
        private int index = 0;

        void addResponse(boolean achieved, int iterations) {
            responses.add(new MockResponse(achieved, iterations));
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

            return CompletableFuture.completedFuture(
                    LoopResult.completed(session, "Response", response.iterations, new TokenUsage(100, 50))
            );
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

    private record MockResponse(boolean achieved, int iterations) {}

    /**
     * Mock WorktreeProvider for testing.
     */
    private static class MockWorktreeProvider implements WorktreeProvider {
        private int callCount = 0;

        @Override
        public CompletableFuture<WorktreeInfo> createWorktree(String name, String baseBranch, boolean createBranch) {
            callCount++;
            return CompletableFuture.completedFuture(new WorktreeInfo("/tmp/worktree-" + name, name));
        }
    }
}
