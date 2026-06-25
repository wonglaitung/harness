package com.harness.core;

import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Controller for step-based budget management.
 *
 * Features:
 * - Per-task iteration limits
 * - Per-step tool call limits (prevents LLM from calling too many tools at once)
 * - Per-task tool call limits
 * - Warning and critical thresholds
 * - Throttling support for graceful degradation
 *
 * Example:
 * <pre>
 * StepBudgetController budget = new StepBudgetController();
 * budget.startTask();
 *
 * // Before each tool call
 * BudgetCheckResult check = budget.checkBeforeToolCall("read");
 * if (check.shouldStop()) {
 *     // Stop execution
 * }
 *
 * // Record tool call
 * budget.recordToolCall("read");
 *
 * // Advance iteration
 * budget.advanceIteration();
 *
 * // End task
 * StepUsage usage = budget.endTask();
 * </pre>
 */
public class StepBudgetController {

    private static final Logger logger = LoggerFactory.getLogger(StepBudgetController.class);

    private final StepBudgetConfig config;
    private StepUsage usage = new StepUsage();
    private boolean taskActive = false;
    private boolean warned = false;

    public StepBudgetController() {
        this(StepBudgetConfig.defaults());
    }

    public StepBudgetController(StepBudgetConfig config) {
        this.config = config;
    }

    /**
     * Start a new task.
     *
     * Resets all counters and marks task as active.
     */
    public void startTask() {
        usage = new StepUsage();
        taskActive = true;
        warned = false;
        logger.debug("Step budget: Task started");
    }

    /**
     * End the current task.
     *
     * @return Final usage statistics
     */
    public StepUsage endTask() {
        taskActive = false;
        logger.debug("Step budget: Task ended with {} iterations, {} tool calls",
            usage.iterations(), usage.toolCallsTotal());
        return usage;
    }

    /**
     * Advance iteration count and check budget.
     *
     * Should be called after each iteration completes.
     *
     * @return BudgetCheckResult with current status
     */
    public BudgetCheckResult advanceIteration() {
        if (!taskActive) {
            logger.warn("Step budget: advanceIteration called without active task");
            return BudgetCheckResult.normal("No active task");
        }

        usage = usage.incrementIterations();
        usage = usage.resetStep();  // Reset step counters for new iteration

        return checkBudget();
    }

    /**
     * Record a tool call and check budget.
     *
     * @param toolName Name of the tool being called
     * @return BudgetCheckResult with current status
     */
    public BudgetCheckResult recordToolCall(String toolName) {
        if (!taskActive) {
            logger.warn("Step budget: recordToolCall called without active task");
            return BudgetCheckResult.normal("No active task");
        }

        usage = usage.recordToolCall(toolName);
        return checkBudget();
    }

    /**
     * Check budget before executing a tool call.
     *
     * This is a pre-check that doesn't increment counters.
     * Use this to decide whether to proceed with a tool call.
     *
     * @param toolName Name of the tool to be called (optional, for logging)
     * @return BudgetCheckResult with projection based on current usage
     */
    public BudgetCheckResult checkBeforeToolCall(String toolName) {
        if (!taskActive) {
            logger.warn("Step budget: checkBeforeToolCall called without active task");
            return BudgetCheckResult.normal("No active task");
        }

        // Project next call
        int projectedTotal = usage.toolCallsTotal() + 1;
        int projectedStep = usage.toolCallsThisStep() + 1;

        logger.info("Step budget check: tool={}, projected_step={}/{}, projected_total={}/{}",
            toolName, projectedStep, config.maxToolCallsPerStep(),
            projectedTotal, config.maxToolCallsPerTask());

        // Check step limit first (more restrictive)
        if (projectedStep > config.maxToolCallsPerStep()) {
            logger.warn("Step budget exceeded: {}/{}", projectedStep, config.maxToolCallsPerStep());
            return BudgetCheckResult.exceeded(
                String.format("Step tool call limit exceeded: %d/%d", projectedStep, config.maxToolCallsPerStep()),
                true
            );
        }

        // Check total limit
        return checkBudgetProjected(projectedTotal);
    }

    /**
     * Get current usage.
     */
    public StepUsage getUsage() {
        return usage;
    }

    /**
     * Get detailed usage report.
     */
    public Map<String, Object> getUsageReport() {
        int remainingIterations = config.maxIterationsPerTask() - usage.iterations();
        int remainingToolCalls = config.maxToolCallsPerTask() - usage.toolCallsTotal();

        Map<String, Object> iterations = new HashMap<>();
        iterations.put("used", usage.iterations());
        iterations.put("limit", config.maxIterationsPerTask());
        iterations.put("remaining", remainingIterations);
        iterations.put("percentage", (double) usage.iterations() / config.maxIterationsPerTask() * 100);

        Map<String, Object> toolCalls = new HashMap<>();
        toolCalls.put("used", usage.toolCallsTotal());
        toolCalls.put("limit", config.maxToolCallsPerTask());
        toolCalls.put("remaining", remainingToolCalls);
        toolCalls.put("percentage", (double) usage.toolCallsTotal() / config.maxToolCallsPerTask() * 100);
        toolCalls.put("thisStep", usage.toolCallsThisStep());
        toolCalls.put("stepLimit", config.maxToolCallsPerStep());

        Map<String, Object> report = new HashMap<>();
        report.put("iterations", iterations);
        report.put("toolCalls", toolCalls);
        report.put("byTool", usage.toolCallsByTool());
        report.put("taskActive", taskActive);

        Map<String, Object> configMap = new HashMap<>();
        configMap.put("maxIterationsPerTask", config.maxIterationsPerTask());
        configMap.put("maxToolCallsPerStep", config.maxToolCallsPerStep());
        configMap.put("maxToolCallsPerTask", config.maxToolCallsPerTask());
        configMap.put("actionOnExceed", config.actionOnExceed());
        report.put("config", configMap);

        return report;
    }

    // === Private Methods ===

    private BudgetCheckResult checkBudget() {
        // Check iteration limit
        double iterationRatio = (double) usage.iterations() / config.maxIterationsPerTask();
        double toolRatio = (double) usage.toolCallsTotal() / config.maxToolCallsPerTask();
        double stepRatio = (double) usage.toolCallsThisStep() / config.maxToolCallsPerStep();

        // Determine level (use the highest ratio)
        double maxRatio = Math.max(iterationRatio, Math.max(toolRatio, stepRatio));

        BudgetLevel level;
        if (maxRatio >= 1.0) {
            level = BudgetLevel.EXCEEDED;
        } else if (maxRatio >= config.criticalThreshold()) {
            level = BudgetLevel.CRITICAL;
        } else if (maxRatio >= config.warningThreshold()) {
            level = BudgetLevel.WARNING;
        } else {
            level = BudgetLevel.NORMAL;
        }

        // Determine action
        int remainingIterations = config.maxIterationsPerTask() - usage.iterations();
        int remainingToolCalls = config.maxToolCallsPerTask() - usage.toolCallsTotal();

        boolean shouldStop = false;
        Integer throttleLimit = null;

        if (level == BudgetLevel.EXCEEDED) {
            if ("stop".equals(config.actionOnExceed())) {
                shouldStop = true;
            } else if ("throttle".equals(config.actionOnExceed())) {
                throttleLimit = Math.max(1, (int) (remainingToolCalls * config.throttleRatio()));
            }
        }

        // Generate message
        String message;
        if (level == BudgetLevel.NORMAL) {
            message = String.format("Budget OK: %d/%d iterations, %d/%d tool calls",
                usage.iterations(), config.maxIterationsPerTask(),
                usage.toolCallsTotal(), config.maxToolCallsPerTask());
        } else if (level == BudgetLevel.WARNING) {
            message = String.format("Budget warning: %.0f%% used", maxRatio * 100);
        } else if (level == BudgetLevel.CRITICAL) {
            message = String.format("Budget critical: %.0f%% used, consider stopping", maxRatio * 100);
        } else {
            message = String.format("Budget exceeded: iterations=%d, tool_calls=%d",
                usage.iterations(), usage.toolCallsTotal());
        }

        boolean isWithinBudget = level != BudgetLevel.EXCEEDED || !"stop".equals(config.actionOnExceed());

        return new BudgetCheckResult(
            level, isWithinBudget, message, remainingIterations, remainingToolCalls,
            shouldStop, throttleLimit
        );
    }

    private BudgetCheckResult checkBudgetProjected(int projectedToolCalls) {
        double iterationRatio = (double) usage.iterations() / config.maxIterationsPerTask();
        double toolRatio = (double) projectedToolCalls / config.maxToolCallsPerTask();

        double maxRatio = Math.max(iterationRatio, toolRatio);

        BudgetLevel level;
        if (maxRatio >= 1.0) {
            level = BudgetLevel.EXCEEDED;
        } else if (maxRatio >= config.criticalThreshold()) {
            level = BudgetLevel.CRITICAL;
        } else if (maxRatio >= config.warningThreshold()) {
            level = BudgetLevel.WARNING;
        } else {
            level = BudgetLevel.NORMAL;
        }

        int remainingIterations = config.maxIterationsPerTask() - usage.iterations();
        int remainingToolCalls = config.maxToolCallsPerTask() - projectedToolCalls;

        boolean shouldStop = false;
        Integer throttleLimit = null;

        if (level == BudgetLevel.EXCEEDED) {
            if ("stop".equals(config.actionOnExceed())) {
                shouldStop = true;
            } else if ("throttle".equals(config.actionOnExceed())) {
                throttleLimit = Math.max(1, (int) (remainingToolCalls * config.throttleRatio()));
            }
        }

        String message = String.format("Projected budget: %d/%d tool calls",
            projectedToolCalls, config.maxToolCallsPerTask());

        boolean isWithinBudget = level != BudgetLevel.EXCEEDED || !"stop".equals(config.actionOnExceed());

        return new BudgetCheckResult(
            level, isWithinBudget, message, remainingIterations, remainingToolCalls,
            shouldStop, throttleLimit
        );
    }
}
