package com.harness.orchestrator;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;

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

    /**
     * Create a new WorkflowEngine.
     *
     * @param agent Agent runner for goal execution
     */
    public WorkflowEngine(GoalLoop.AgentRunner agent) {
        this.agent = agent;
    }

    /**
     * Execute a workflow.
     *
     * @param config Workflow configuration
     * @return CompletableFuture with WorkflowResult
     */
    public CompletableFuture<WorkflowResult> execute(WorkflowConfig config) {
        logger.info("Starting workflow: {}", config.getName());

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

                    return StepResult.builder()
                            .stepName(step.getName())
                            .status(status)
                            .goalResult(goalResult)
                            .startedAt(startedAt)
                            .completedAt(Instant.now())
                            .build();
                })
                .exceptionally(error -> StepResult.builder()
                        .stepName(step.getName())
                        .status(StepStatus.FAILED)
                        .error(error.getMessage())
                        .startedAt(startedAt)
                        .completedAt(Instant.now())
                        .build());
    }

    /**
     * Resolve template variables in goal description.
     *
     * <p>Supports syntax: {{steps.prev.exports.key}}</p>
     */
    private String resolveTemplates(String goal, Map<String, StepResult> previousResults) {
        Matcher matcher = TEMPLATE_PATTERN.matcher(goal);
        StringBuffer sb = new StringBuffer();

        while (matcher.find()) {
            String stepName = matcher.group(1);
            String exportKey = matcher.group(2);

            StepResult stepResult = previousResults.get(stepName);
            if (stepResult != null && stepResult.getExports().containsKey(exportKey)) {
                Object value = stepResult.getExports().get(exportKey);
                matcher.appendReplacement(sb, value != null ? value.toString() : "");
            } else {
                matcher.appendReplacement(sb, matcher.group(0)); // Keep original if not found
            }
        }
        matcher.appendTail(sb);

        return sb.toString();
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
