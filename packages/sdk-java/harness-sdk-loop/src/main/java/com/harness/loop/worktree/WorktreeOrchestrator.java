package com.harness.loop.worktree;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Top-level orchestrator for parallel goal execution in worktrees.
 *
 * <p>Integrates WorktreeManager for git worktree lifecycle and
 * provides a simple API for parallel goal execution.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GoalLoop.AgentRunner agent = ...;
 * WorktreeOrchestrator orchestrator = new WorktreeOrchestrator(agent, ".");
 *
 * // Define parallel goals
 * List<WorktreeConfig> goals = List.of(
 *     WorktreeConfig.builder()
 *         .name("feature-auth")
 *         .goal("Implement user authentication")
 *         .build(),
 *     WorktreeConfig.builder()
 *         .name("feature-api")
 *         .goal("Implement API endpoints")
 *         .build()
 * );
 *
 * // Execute in parallel
 * Map<String, WorktreeResult> results = orchestrator.runParallel(goals).join();
 *
 * // Check results
 * for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
 *     if (entry.getValue().isAchieved()) {
 *         System.out.println("✓ " + entry.getKey());
 *     } else {
 *         System.out.println("✗ " + entry.getKey());
 *     }
 * }
 * }</pre>
 */
public class WorktreeOrchestrator {
    private static final Logger logger = LoggerFactory.getLogger(WorktreeOrchestrator.class);

    private final GoalLoop.AgentRunner agent;
    private final String repoRoot;
    private final WorktreeManager worktreeManager;
    private final ReentrantLock createLock = new ReentrantLock();

    // Track active executions
    private final Map<String, ExecutionInfo> executions = new ConcurrentHashMap<>();

    /**
     * Create a new WorktreeOrchestrator.
     *
     * @param agent Agent runner for goal execution
     * @param repoRoot Path to git repository root
     */
    public WorktreeOrchestrator(GoalLoop.AgentRunner agent, String repoRoot) {
        this.agent = agent;
        this.repoRoot = repoRoot;
        this.worktreeManager = new WorktreeManager(repoRoot);
    }

    /**
     * Execute multiple goals in parallel with worktree isolation.
     *
     * <p>Each goal runs in its own git worktree, providing complete isolation.
     * Worktrees are created sequentially (to avoid index.lock conflicts)
     * but goals execute in parallel.</p>
     *
     * @param configs List of WorktreeConfig defining goals and git settings
     * @return CompletableFuture with map of goal names to WorktreeResult
     */
    public CompletableFuture<Map<String, WorktreeResult>> runParallel(List<WorktreeConfig> configs) {
        Map<String, WorktreeResult> results = new ConcurrentHashMap<>();

        // Phase 1: Create worktrees sequentially
        logger.info("Creating {} worktrees...", configs.size());

        List<CompletableFuture<Void>> createFutures = new ArrayList<>();
        for (WorktreeConfig config : configs) {
            createFutures.add(spawnGoal(config, results));
        }

        // Wait for all worktrees to be created, then execute in parallel
        return CompletableFuture.allOf(createFutures.toArray(new CompletableFuture[0]))
                .thenCompose(v -> {
                    logger.info("Starting parallel goal execution...");

                    // Phase 2: Execute all goals in parallel
                    List<CompletableFuture<Void>> executeFutures = new ArrayList<>();
                    for (WorktreeConfig config : configs) {
                        if (executions.containsKey(config.getName())) {
                            executeFutures.add(executeGoal(config, results));
                        }
                    }

                    return CompletableFuture.allOf(executeFutures.toArray(new CompletableFuture[0]));
                })
                .thenCompose(v -> {
                    // Phase 3: Optional auto-cleanup
                    List<CompletableFuture<Void>> cleanupFutures = new ArrayList<>();
                    for (WorktreeConfig config : configs) {
                        WorktreeResult result = results.get(config.getName());
                        if (config.isAutoCleanup() && result != null && result.isAchieved()) {
                            cleanupFutures.add(
                                    worktreeManager.cleanupWorktree(config.getName(), false)
                                            .thenAccept(cleaned -> {
                                                if (cleaned) {
                                                    // Update result to reflect cleanup
                                                    WorktreeResult updated = WorktreeResult.builder()
                                                            .name(result.getName())
                                                            .goalResult(result.getGoalResult())
                                                            .worktreePath(result.getWorktreePath())
                                                            .branchName(result.getBranchName())
                                                            .commitsMade(result.getCommitsMade())
                                                            .cleanupDone(true)
                                                            .createdAt(result.getCreatedAt())
                                                            .completedAt(result.getCompletedAt())
                                                            .build();
                                                    results.put(config.getName(), updated);
                                                    logger.info("Auto-cleaned worktree: {}", config.getName());
                                                }
                                            })
                            );
                        }
                    }
                    return CompletableFuture.allOf(cleanupFutures.toArray(new CompletableFuture[0]));
                })
                .thenApply(v -> results);
    }

    private CompletableFuture<Void> spawnGoal(WorktreeConfig config, Map<String, WorktreeResult> results) {
        return CompletableFuture.runAsync(() -> {
            createLock.lock();
            try {
                WorktreeManager.WorktreeInfo info = worktreeManager
                        .createWorktree(config.getName(), config.getBaseBranch(), config.isCreateBranch())
                        .join();

                executions.put(config.getName(), new ExecutionInfo(
                        info.path(),
                        info.branchName(),
                        Instant.now()
                ));

                logger.info("Spawned goal '{}' in worktree {}", config.getName(), info.path());

            } catch (WorktreeError e) {
                // Record failed spawn
                results.put(config.getName(), WorktreeResult.builder()
                        .name(config.getName())
                        .branchName(config.getEffectiveBranchName())
                        .createdAt(Instant.now())
                        .completedAt(Instant.now())
                        .build());
                logger.error("Failed to spawn goal '{}': {}", config.getName(), e.getMessage());
            } finally {
                createLock.unlock();
            }
        });
    }

    private CompletableFuture<Void> executeGoal(WorktreeConfig config, Map<String, WorktreeResult> results) {
        ExecutionInfo execution = executions.get(config.getName());
        if (execution == null) {
            return CompletableFuture.completedFuture(null);
        }

        // Build goal config
        GoalConfig.Builder configBuilder = new GoalConfig.Builder()
                .description(config.getGoal())
                .workspaceDir(execution.worktreePath)
                .maxIterations(config.getMaxIterations())
                .timeoutSeconds(config.getTimeoutSeconds());

        if (config.getCustomVerifier() != null) {
            configBuilder.verificationMethod(VerificationMethod.CUSTOM);
            configBuilder.customVerifier(config.getCustomVerifier());
        }

        GoalConfig goalConfig = configBuilder.build();
        GoalLoop loop = new GoalLoop(agent, goalConfig);

        return loop.run().thenAccept(goalResult -> {
            // Get commit count
            int commits = worktreeManager.getCommitCount(config.getName(), config.getBaseBranch()).join();

            WorktreeResult result = WorktreeResult.builder()
                    .name(config.getName())
                    .goalResult(goalResult)
                    .worktreePath(execution.worktreePath)
                    .branchName(execution.branchName)
                    .commitsMade(commits)
                    .createdAt(execution.createdAt)
                    .completedAt(Instant.now())
                    .build();

            results.put(config.getName(), result);
            executions.remove(config.getName());
        });
    }

    /**
     * Merge successful goal branches into target branch.
     *
     * @param results Results from runParallel()
     * @param targetBranch Target branch to merge into
     * @return CompletableFuture with MergeResult
     */
    public CompletableFuture<MergeResult> mergeSuccessful(Map<String, WorktreeResult> results, String targetBranch) {
        return worktreeManager.isDirty().thenCompose(dirty -> {
            if (dirty) {
                return CompletableFuture.completedFuture(
                        MergeResult.builder()
                                .error("Main repository has uncommitted changes. Please commit or stash before merging.")
                                .build()
                );
            }

            List<String> merged = new ArrayList<>();
            List<String> conflicts = new ArrayList<>();
            List<String> skipped = new ArrayList<>();

            List<CompletableFuture<Void>> mergeFutures = new ArrayList<>();

            for (Map.Entry<String, WorktreeResult> entry : results.entrySet()) {
                WorktreeResult result = entry.getValue();

                if (!result.isAchieved()) {
                    skipped.add(result.getBranchName());
                    logger.info("Skipped merge for failed goal: {}", entry.getKey());
                    continue;
                }

                mergeFutures.add(mergeBranch(result.getBranchName(), merged, conflicts));
            }

            return CompletableFuture.allOf(mergeFutures.toArray(new CompletableFuture[0]))
                    .thenApply(v -> MergeResult.builder()
                            .merged(merged)
                            .conflicts(conflicts)
                            .skipped(skipped)
                            .mergedAt(Instant.now())
                            .build());
        });
    }

    private CompletableFuture<Void> mergeBranch(String branchName, List<String> merged, List<String> conflicts) {
        return CompletableFuture.runAsync(() -> {
            logger.info("Merging branch: {}", branchName);

            try {
                ProcessBuilder pb = new ProcessBuilder("git", "merge", branchName, "--no-edit");
                pb.directory(new java.io.File(repoRoot));
                pb.redirectErrorStream(true);
                Process process = pb.start();

                int exitCode = process.waitFor();

                if (exitCode == 0) {
                    merged.add(branchName);
                    logger.info("Successfully merged: {}", branchName);
                } else {
                    conflicts.add(branchName);
                    logger.warn("Merge conflict in: {}", branchName);

                    // Abort the merge
                    ProcessBuilder abortPb = new ProcessBuilder("git", "merge", "--abort");
                    abortPb.directory(new java.io.File(repoRoot));
                    Process abortProcess = abortPb.start();
                    abortProcess.waitFor();
                }

            } catch (Exception e) {
                conflicts.add(branchName);
                logger.warn("Failed to merge {}: {}", branchName, e.getMessage());
            }
        });
    }

    /**
     * Clean up all tracked worktrees.
     */
    public CompletableFuture<Integer> cleanupAll(boolean force) {
        return worktreeManager.cleanupAll(force)
                .thenApply(count -> {
                    executions.clear();
                    return count;
                });
    }

    /**
     * List all tracked worktrees.
     */
    public List<String> listWorktrees() {
        return worktreeManager.listWorktrees();
    }

    /**
     * Get the underlying WorktreeManager.
     */
    public WorktreeManager getWorktreeManager() {
        return worktreeManager;
    }

    private record ExecutionInfo(String worktreePath, String branchName, Instant createdAt) {}

    @Override
    public String toString() {
        return "WorktreeOrchestrator{repoRoot='" + repoRoot + "', worktrees=" + listWorktrees().size() + "}";
    }
}
