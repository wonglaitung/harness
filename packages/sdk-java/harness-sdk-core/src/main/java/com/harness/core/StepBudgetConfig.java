package com.harness.core;

/**
 * Configuration for step-based budget control.
 *
 * This differs from CostConfig which tracks token usage.
 * StepBudget tracks iteration and tool call counts per task.
 *
 * @param maxIterationsPerTask Maximum iterations allowed per task (default 50)
 * @param maxToolCallsPerStep Maximum tool calls per single LLM response (default 10)
 * @param maxToolCallsPerTask Maximum total tool calls per task (default 200)
 * @param warningThreshold Ratio to trigger warning (default 0.8)
 * @param criticalThreshold Ratio to trigger critical (default 0.95)
 * @param actionOnExceed Action when budget exceeded (stop | warn | throttle)
 * @param throttleRatio Ratio of budget to use when throttling (default 0.5)
 */
public record StepBudgetConfig(
    int maxIterationsPerTask,
    int maxToolCallsPerStep,
    int maxToolCallsPerTask,
    double warningThreshold,
    double criticalThreshold,
    String actionOnExceed,
    double throttleRatio
) {

    public static final int DEFAULT_MAX_ITERATIONS = 50;
    public static final int DEFAULT_MAX_TOOL_CALLS_PER_STEP = 10;
    public static final int DEFAULT_MAX_TOOL_CALLS_PER_TASK = 200;
    public static final double DEFAULT_WARNING_THRESHOLD = 0.8;
    public static final double DEFAULT_CRITICAL_THRESHOLD = 0.95;
    public static final String DEFAULT_ACTION_ON_EXCEED = "stop";
    public static final double DEFAULT_THROTTLE_RATIO = 0.5;

    public StepBudgetConfig() {
        this(
            DEFAULT_MAX_ITERATIONS,
            DEFAULT_MAX_TOOL_CALLS_PER_STEP,
            DEFAULT_MAX_TOOL_CALLS_PER_TASK,
            DEFAULT_WARNING_THRESHOLD,
            DEFAULT_CRITICAL_THRESHOLD,
            DEFAULT_ACTION_ON_EXCEED,
            DEFAULT_THROTTLE_RATIO
        );
    }

    public static StepBudgetConfig defaults() {
        return new StepBudgetConfig();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int maxIterationsPerTask = DEFAULT_MAX_ITERATIONS;
        private int maxToolCallsPerStep = DEFAULT_MAX_TOOL_CALLS_PER_STEP;
        private int maxToolCallsPerTask = DEFAULT_MAX_TOOL_CALLS_PER_TASK;
        private double warningThreshold = DEFAULT_WARNING_THRESHOLD;
        private double criticalThreshold = DEFAULT_CRITICAL_THRESHOLD;
        private String actionOnExceed = DEFAULT_ACTION_ON_EXCEED;
        private double throttleRatio = DEFAULT_THROTTLE_RATIO;

        public Builder maxIterationsPerTask(int maxIterationsPerTask) {
            this.maxIterationsPerTask = maxIterationsPerTask;
            return this;
        }

        public Builder maxToolCallsPerStep(int maxToolCallsPerStep) {
            this.maxToolCallsPerStep = maxToolCallsPerStep;
            return this;
        }

        public Builder maxToolCallsPerTask(int maxToolCallsPerTask) {
            this.maxToolCallsPerTask = maxToolCallsPerTask;
            return this;
        }

        public Builder warningThreshold(double warningThreshold) {
            this.warningThreshold = warningThreshold;
            return this;
        }

        public Builder criticalThreshold(double criticalThreshold) {
            this.criticalThreshold = criticalThreshold;
            return this;
        }

        public Builder actionOnExceed(String actionOnExceed) {
            this.actionOnExceed = actionOnExceed;
            return this;
        }

        public Builder throttleRatio(double throttleRatio) {
            this.throttleRatio = throttleRatio;
            return this;
        }

        public StepBudgetConfig build() {
            return new StepBudgetConfig(
                maxIterationsPerTask, maxToolCallsPerStep, maxToolCallsPerTask,
                warningThreshold, criticalThreshold, actionOnExceed, throttleRatio
            );
        }
    }
}
