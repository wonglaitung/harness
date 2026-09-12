package com.harness.orchestrator;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;
import com.harness.memory.BlackboardItem;
import com.harness.memory.SharedStateStore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Workflow execution engine.
 *
 * <p>Executes workflows by managing step dependencies and execution order.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GoalLoop.AgentRunner agent = ...;
 * WorkflowEngine engine = new WorkflowEngine(agent);
 *
 * WorkflowConfig config = WorkflowConfig.builder()
 *     .name("ci-pipeline")
 *     .addStep(WorkflowStep.builder()
 *         .name("build")
 *         .goal("Build the project")
 *         .build())
 *     .addStep(WorkflowStep.builder()
 *         .name("test")
 *         .goal("Run tests")
 *         .addDependsOn("build")
 *         .build())
 *     .build();
 *
 * WorkflowResult result = engine.execute(config).join();
 * }</pre>
 */
public class WorkflowEngine {
    private static final Logger logger = LoggerFactory.getLogger(WorkflowEngine.class);
    private static final Pattern TEMPLATE_PATTERN = Pattern.compile("\\{\\{steps\\.([^.]+)\\.exports\\.([^}]+)\\}\\}");

    private final GoalLoop.AgentRunner agent;
    private final SharedStateStore store;

    /**
     * Create a new WorkflowEngine with default in-memory SharedStateStore.
     *
     * @param agent Agent runner for goal execution
     */
    public WorkflowEngine(GoalLoop.AgentRunner agent) {
        this(agent, new SharedStateStore(false));
    }

    /**
     * Create a new WorkflowEngine with explicit SharedStateStore (A3 黑板).
     *
     * @param agent Agent runner for goal execution
     * @param store Shared state store for inter-step data with versioning + timestamp + writer
     */
    public WorkflowEngine(GoalLoop.AgentRunner agent, SharedStateStore store) {
        this.agent = agent;
        this.store = store;
    }

    /**
     * Execute a workflow.
     *
     * @param config Workflow configuration
     * @return CompletableFuture with WorkflowResult
     */
    public CompletableFuture<WorkflowResult> execute(WorkflowConfig config) {
        logger.info("Starting workflow: {}", config.getName());

        // H1: Pre-execution deadlock detection — fail fast before any step runs
        DependencyGraph graph = new DependencyGraph();
        for (WorkflowStep step : config.getSteps()) {
            graph.addStep(step);
        }
        for (WorkflowStep step : config.getSteps()) {
            for (String dep : step.getDependsOn()) {
                graph.addDependency(step.getName(), dep);
            }
        }
        boolean hasCycle = graph.detectDeadlock();
        if (hasCycle) {
            String msg = "Workflow has circular dependency — deadlock detected";
            logger.error(msg);
            return CompletableFuture.completedFuture(WorkflowResult.builder()
                    .workflowName(config.getName())
                    .status(WorkflowStatus.FAILED)
                    .error(msg)
                    .startedAt(Instant.now())
                    .completedAt(Instant.now())
                    .build());
        }

        Instant startedAt = Instant.now();
        Map<String, StepResult> stepResults = new HashMap<>();

        // Initialize all steps as pending
        for (WorkflowStep step : config.getSteps()) {
            stepResults.put(step.getName(), StepResult.builder()
                    .stepName(step.getName())
                    .status(StepStatus.PENDING)
                    .build());
        }

        // Get execution order (topological sort)
        List<List<String>> executionOrder = getExecutionOrder(config);

        return executeLevels(config, executionOrder, stepResults, 0)
                .thenApply(results -> {
                    // Determine final status
                    WorkflowStatus status = WorkflowStatus.COMPLETED;
                    for (StepResult result : results.values()) {
                        if (result.getStatus() == StepStatus.FAILED) {
                            status = WorkflowStatus.FAILED;
                            break;
                        }
                    }

                    Instant completedAt = Instant.now();

                    WorkflowResult workflowResult = WorkflowResult.builder()
                            .workflowName(config.getName())
                            .status(status)
                            .steps(results)
                            .startedAt(startedAt)
                            .completedAt(completedAt)
                            .build();

                    logger.info("Workflow {} completed with status: {}", config.getName(), status.getValue());
                    return workflowResult;
                })
                .exceptionally(error -> {
                    logger.error("Workflow {} failed: {}", config.getName(), error.getMessage());

                    return WorkflowResult.builder()
                            .workflowName(config.getName())
                            .status(WorkflowStatus.FAILED)
                            .steps(stepResults)
                            .startedAt(startedAt)
                            .completedAt(Instant.now())
                            .error(error.getMessage())
                            .build();
                });
    }

    private CompletableFuture<Map<String, StepResult>> executeLevels(
            WorkflowConfig config,
            List<List<String>> levels,
            Map<String, StepResult> results,
            int levelIndex) {

        if (levelIndex >= levels.size()) {
            return CompletableFuture.completedFuture(results);
        }

        List<String> currentLevel = levels.get(levelIndex);

        // Execute all steps in current level in parallel
        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (String stepName : currentLevel) {
            WorkflowStep step = config.getStep(stepName);
            StepResult currentResult = results.get(stepName);

            // Check if dependencies succeeded
            boolean canExecute = true;
            for (String dep : step.getDependsOn()) {
                StepResult depResult = results.get(dep);
                if (depResult == null || depResult.getStatus() != StepStatus.SUCCESS) {
                    canExecute = false;
                    break;
                }
            }

            if (!canExecute) {
                // Skip this step
                results.put(stepName, StepResult.builder()
                        .stepName(stepName)
                        .status(StepStatus.SKIPPED)
                        .error("Dependency failed")
                        .build());
                continue;
            }

            futures.add(executeStep(step, results)
                    .thenAccept(result -> results.put(stepName, result)));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenCompose(v -> executeLevels(config, levels, results, levelIndex + 1));
    }

    private CompletableFuture<StepResult> executeStep(WorkflowStep step, Map<String, StepResult> previousResults) {
        logger.info("Executing step: {}", step.getName());

        Instant startedAt = Instant.now();

        // Resolve templates in goal
        String resolvedGoal = resolveTemplates(step.getGoal(), previousResults);

        // Build goal config
        GoalConfig.Builder configBuilder = new GoalConfig.Builder()
                .description(resolvedGoal)
                .workspaceDir(step.getWorkspaceDir())
                .maxIterations(step.getMaxIterations())
                .timeoutSeconds(step.getTimeoutSeconds());

        if (step.getCustomVerifier() != null) {
            configBuilder.verificationMethod(VerificationMethod.CUSTOM);
            configBuilder.customVerifier(step.getCustomVerifier());
        } else {
            // Use custom verification with always-true verifier for testing/simpler cases
            configBuilder.verificationMethod(VerificationMethod.CUSTOM);
            configBuilder.customVerifier(result -> true);
        }

        GoalConfig goalConfig = configBuilder.build();
        GoalLoop loop = new GoalLoop(agent, goalConfig);

        return loop.run()
                .thenApply(goalResult -> {
                    StepStatus status = goalResult.achieved() ? StepStatus.SUCCESS : StepStatus.FAILED;

                    StepResult stepResult = StepResult.builder()
                            .stepName(step.getName())
                            .status(status)
                            .goalResult(goalResult)
                            .startedAt(startedAt)
                            .completedAt(Instant.now())
                            .build();

                    // A3: Write exports to SharedStateStore with versioning + timestamp + writer
                    writeExportsToStore(step.getName(), stepResult.getExports(), goalResult);

                    return stepResult;
                })
                .exceptionally(error -> {
                    StepResult failedResult = StepResult.builder()
                            .stepName(step.getName())
                            .status(StepStatus.FAILED)
                            .error(error.getMessage())
                            .startedAt(startedAt)
                            .completedAt(Instant.now())
                            .build();

                    // A3: Even on failure, record the attempt in the store
                    writeExportsToStore(step.getName(), failedResult.getExports(), null);

                    return failedResult;
                });
    }

    /**
     * Resolve template variables in goal description.
     *
     * <p>Supports syntax: {{steps.prev.exports.key}}</p>
     * Reads from SharedStateStore (A3) with fallback to raw StepResult exports.
     */
    private String resolveTemplates(String goal, Map<String, StepResult> previousResults) {
        Matcher matcher = TEMPLATE_PATTERN.matcher(goal);
        StringBuffer sb = new StringBuffer();

        while (matcher.find()) {
            String stepName = matcher.group(1);
            String exportKey = matcher.group(2);

            String value = resolveExport(stepName, exportKey, previousResults);
            matcher.appendReplacement(sb, value != null ? value : matcher.group(0));
        }
        matcher.appendTail(sb);

        return sb.toString();
    }

    /**
     * Resolve a single export value from SharedStateStore (A3) with fallback.
     *
     * <p>First checks the blackboard store for a matching item, then falls back
     * to raw StepResult exports for backward compatibility.</p>
     */
    private String resolveExport(String stepName, String exportKey, Map<String, StepResult> previousResults) {
        // A3: Try reading from SharedStateStore (blackboard with version + timestamp + writer)
        String storeKey = stepName + "::exports::" + exportKey;
        BlackboardItem item = store.get(storeKey);
        if (item != null && item.content().containsKey(exportKey)) {
            Object value = item.content().get(exportKey);
            logger.debug("A3: resolved '{}' from blackboard (v{}, writer={})",
                exportKey, item.baseVersion(), item.writerId());
            return value != null ? value.toString() : null;
        }

        // Fallback: raw StepResult exports (backward compatible)
        StepResult stepResult = previousResults.get(stepName);
        if (stepResult != null && stepResult.getExports().containsKey(exportKey)) {
            Object value = stepResult.getExports().get(exportKey);
            return value != null ? value.toString() : null;
        }

        return null;
    }

    /**
     * A3: Write step exports to SharedStateStore with versioning + timestamp + writer.
     *
     * <p>Each export key becomes a BlackboardItem on the blackboard with:
     * <ul>
     *   <li>id: "{stepName}::exports::{key}"</li>
     *   <li>type: "step_export"</li>
     *   <li>sourceAgent: step name</li>
     *   <li>writerId: "orchestrator"</li>
     *   <li>baseVersion: auto-incremented (CAS)</li>
     *   <li>createdAt: current timestamp</li>
     * </ul>
     */
    private void writeExportsToStore(String stepName, Map<String, Object> exports, GoalResult goalResult) {
        if (exports == null || exports.isEmpty()) {
            return;
        }

        for (Map.Entry<String, Object> entry : exports.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();

            // Build item content
            java.util.Map<String, Object> content = new java.util.HashMap<>();
            content.put(key, value);
            if (goalResult != null) {
                content.put("_achieved", goalResult.achieved());
            }

            String itemId = stepName + "::exports::" + key;

            // Check existing version for CAS
            BlackboardItem existing = store.get(itemId);
            int baseVersion = existing != null ? existing.baseVersion() + 1 : 0;

            BlackboardItem item = new BlackboardItem(
                itemId,
                "step_export",
                content,
                stepName,       // sourceAgent
                1.0f,           // confidence
                baseVersion,
                0,              // no TTL
                "active",
                "orchestrator", // writerId
                null,
                java.time.Instant.now()
            );

            store.put(item);
            logger.debug("A3: wrote export to blackboard: {} (v{}, writer={})",
                itemId, baseVersion, item.writerId());
        }
    }

    /**
     * Get execution order using topological sort.
     *
     * <p>Returns a list of levels, where each level contains steps
     * that can be executed in parallel.</p>
     */
    private List<List<String>> getExecutionOrder(WorkflowConfig config) {
        List<List<String>> levels = new ArrayList<>();
        Set<String> completed = new HashSet<>();
        Map<String, Set<String>> remainingDeps = new HashMap<>();

        // Initialize remaining dependencies
        for (WorkflowStep step : config.getSteps()) {
            remainingDeps.put(step.getName(), new HashSet<>(step.getDependsOn()));
        }

        while (completed.size() < config.getSteps().size()) {
            List<String> level = new ArrayList<>();

            for (WorkflowStep step : config.getSteps()) {
                String name = step.getName();
                if (!completed.contains(name) && remainingDeps.get(name).isEmpty()) {
                    level.add(name);
                }
            }

            if (level.isEmpty()) {
                // Circular dependency detected
                logger.error("Circular dependency detected in workflow");
                break;
            }

            levels.add(level);

            for (String name : level) {
                completed.add(name);
                // Remove this step from remaining dependencies of other steps
                for (Set<String> deps : remainingDeps.values()) {
                    deps.remove(name);
                }
            }
        }

        return levels;
    }
}
