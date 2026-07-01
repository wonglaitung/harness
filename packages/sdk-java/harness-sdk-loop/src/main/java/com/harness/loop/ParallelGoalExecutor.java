package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.worktree.WorktreeConfig;
import com.harness.loop.worktree.WorktreeManager;
import com.harness.loop.worktree.WorktreeManager.WorktreeInfo;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Parallel Goal execution across worktrees.
 *
 * <p>Manages spawning and executing multiple goals in parallel,
 * each in its own isolated git worktree.</p>
 *
 * <h2>Key features</h2>
 * <ul>
 *   <li>Concurrent goal execution</li>
 *   <li>Worktree isolation for each goal</li>
 *   <li>Exception isolation (one goal failure doesn't affect others)</li>
 *   <li>Result aggregation</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * ParallelGoalExecutor executor = new ParallelGoalExecutor(agentRunner, worktreeManager);
 *
 * // Spawn goals
 * executor.spawnGoal(new WorktreeConfig.Builder()
 *     .name("feature-a")
 *     .goal("Implement feature A")
 *     .build());
 *
 * executor.spawnGoal(new WorktreeConfig.Builder()
 *     .name("feature-b")
 *     .goal("Implement feature B")
 *     .build());
 *
 * // Execute all in parallel
 * Map<String, GoalResult> results = executor.runAll().join();
 * }</pre>
 */
public class ParallelGoalExecutor {
    private static final Logger logger = LoggerFactory.getLogger(ParallelGoalExecutor.class);

    private final GoalLoop.AgentRunner agentRunner;
    private final WorktreeProvider worktreeProvider;
    private final Map<String, GoalExecution> executions = new ConcurrentHashMap<>();
    private final ExecutorService executor;

    /**
     * Interface for worktree creation.
     */
    @FunctionalInterface
    public interface WorktreeProvider {
        CompletableFuture<WorktreeInfo> createWorktree(String name, String baseBranch, boolean createBranch);
    }

    /**
     * Create a new ParallelGoalExecutor.
     *
     * @param agentRunner Agent runner for goal execution
     * @param worktreeProvider Worktree provider for worktree lifecycle
     */
    public ParallelGoalExecutor(GoalLoop.AgentRunner agentRunner, WorktreeProvider worktreeProvider) {
        this.agentRunner = agentRunner;
        this.worktreeProvider = worktreeProvider;
        this.executor = Executors.newCachedThreadPool();
    }

    /**
     * Create a new ParallelGoalExecutor with a WorktreeManager.
     *
     * @param agentRunner Agent runner for goal execution
     * @param worktreeManager Worktree manager for worktree lifecycle
     */
    public ParallelGoalExecutor(GoalLoop.AgentRunner agentRunner, WorktreeManager worktreeManager) {
        this(agentRunner, (name, baseBranch, createBranch) -> worktreeManager.createWorktree(name, baseBranch, createBranch));
    }

    /**
     * Spawn a goal execution in an isolated worktree.
     *
     * <p>Creates the worktree and prepares the goal for execution.
     * The goal won't start executing until runAll() is called.</p>
     *
     * @param config Worktree configuration including goal and git settings
     * @return The worktree name (same as config.name)
     */
    public CompletableFuture<String> spawnGoal(WorktreeConfig config) {
        if (executions.containsKey(config.getName())) {
            return CompletableFuture.failedFuture(
                    new IllegalArgumentException("Goal already spawned: " + config.getName()));
        }

        return worktreeProvider.createWorktree(
                config.getName(),
                config.getBaseBranch(),
                config.isCreateBranch()
        ).thenApply(worktreeInfo -> {
            // Build GoalConfig
            GoalConfig goalConfig = new GoalConfig.Builder()
                    .description(config.getGoal())
                    .workspaceDir(worktreeInfo.path())
                    .maxIterations(config.getMaxIterations())
                    .timeoutSeconds(config.getTimeoutSeconds())
                    .build();

            // Track execution
            GoalExecution execution = new GoalExecution(
                    config,
                    goalConfig,
                    worktreeInfo.path(),
                    Instant.now()
            );

            executions.put(config.getName(), execution);
            logger.info("Spawned goal '{}' in worktree {}", config.getName(), worktreeInfo.path());

            return config.getName();
        });
    }

    /**
     * Execute all spawned goals in parallel.
     *
     * <p>Uses CompletableFuture for parallel execution.
     * One goal's failure doesn't affect others.</p>
     *
     * @return Map mapping goal names to their GoalResult
     */
    public CompletableFuture<Map<String, GoalResult>> runAll() {
        if (executions.isEmpty()) {
            return CompletableFuture.completedFuture(new HashMap<>());
        }

        logger.info("Starting parallel execution of {} goals", executions.size());

        List<CompletableFuture<Map.Entry<String, GoalResult>>> futures = new ArrayList<>();

        for (Map.Entry<String, GoalExecution> entry : executions.entrySet()) {
            String name = entry.getKey();
            GoalExecution execution = entry.getValue();

            futures.add(CompletableFuture.supplyAsync(() -> {
                try {
                    GoalLoop loop = new GoalLoop(agentRunner, execution.goalConfig);
                    GoalResult result = loop.run().join();
                    execution.completedAt = Instant.now();
                    return Map.entry(name, result);
                } catch (Exception e) {
                    logger.error("Goal '{}' failed with exception: {}", name, e.getMessage());
                    execution.completedAt = Instant.now();
                    return Map.entry(name, GoalResult.builder()
                            .goal(execution.config.getGoal())
                            .status(GoalStatus.ERROR)
                            .error(e.getMessage())
                            .build());
                }
            }, executor));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> {
                    Map<String, GoalResult> results = new HashMap<>();
                    for (CompletableFuture<Map.Entry<String, GoalResult>> future : futures) {
                        Map.Entry<String, GoalResult> entry = future.join();
                        results.put(entry.getKey(), entry.getValue());
                    }

                    // Log summary
                    long achieved = results.values().stream()
                            .filter(GoalResult::achieved)
                            .count();
                    logger.info("Parallel execution complete: {}/{} goals achieved", achieved, results.size());

                    return results;
                });
    }

    /**
     * Get execution details for a spawned goal.
     *
     * @param name Goal name
     * @return GoalExecution if found, null otherwise
     */
    public GoalExecution getExecution(String name) {
        return executions.get(name);
    }

    /**
     * List all spawned goal names.
     *
     * @return List of goal names
     */
    public List<String> listExecutions() {
        return new ArrayList<>(executions.keySet());
    }

    /**
     * Cancel a running goal.
     *
     * @param name Goal name to cancel
     * @return True if cancelled, false if not found
     */
    public boolean cancel(String name) {
        if (executions.containsKey(name)) {
            executions.remove(name);
            logger.info("Cancelled goal: {}", name);
            return true;
        }
        return false;
    }

    /**
     * Clear all tracked executions (does not cleanup worktrees).
     */
    public void clear() {
        executions.clear();
    }

    /**
     * Shutdown the executor.
     */
    public void shutdown() {
        executor.shutdown();
    }

    /**
     * Internal class for tracking a single goal execution.
     */
    public static class GoalExecution {
        public final WorktreeConfig config;
        public final GoalConfig goalConfig;
        public final String worktreePath;
        public final Instant createdAt;
        public Instant completedAt;

        public GoalExecution(WorktreeConfig config, GoalConfig goalConfig, String worktreePath, Instant createdAt) {
            this.config = config;
            this.goalConfig = goalConfig;
            this.worktreePath = worktreePath;
            this.createdAt = createdAt;
        }

        /**
         * Calculate execution duration in seconds.
         */
        public double getDurationSeconds() {
            if (createdAt != null && completedAt != null) {
                return java.time.Duration.between(createdAt, completedAt).toMillis() / 1000.0;
            }
            return 0.0;
        }
    }
}
