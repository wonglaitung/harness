package com.harness.orchestrator;

import com.harness.loop.types.GoalResult;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Single workflow step configuration.
 *
 * <p>Each step is a Goal execution unit. Supports template variables
 * in the goal description to reference outputs from previous steps.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * WorkflowStep step = WorkflowStep.builder()
 *     .name("analyze")
 *     .goal("Analyze code changes and identify issues")
 *     .addSkill("code-analysis")
 *     .build();
 * }</pre>
 */
public class WorkflowStep {
    private final String name;
    private final String goal;
    private final ExecutionMode mode;
    private final List<String> dependsOn;
    private final String workspaceDir;
    private final int maxIterations;
    private final int timeoutSeconds;
    private final Function<GoalResult, Boolean> customVerifier;
    private final List<String> skills;
    private final String condition;
    private final Map<String, String> exports;
    private final int maxRetries;
    private final double retryDelay;

    private WorkflowStep(Builder builder) {
        this.name = builder.name;
        this.goal = builder.goal;
        this.mode = builder.mode;
        this.dependsOn = new ArrayList<>(builder.dependsOn);
        this.workspaceDir = builder.workspaceDir;
        this.maxIterations = builder.maxIterations;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.customVerifier = builder.customVerifier;
        this.skills = new ArrayList<>(builder.skills);
        this.condition = builder.condition;
        this.exports = new HashMap<>(builder.exports);
        this.maxRetries = builder.maxRetries;
        this.retryDelay = builder.retryDelay;

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("step name cannot be empty");
        }

        if (goal == null || goal.isEmpty()) {
            throw new IllegalArgumentException("step goal cannot be empty");
        }

        if (maxIterations < 1) {
            throw new IllegalArgumentException("max_iterations must be at least 1");
        }

        if (timeoutSeconds < 1) {
            throw new IllegalArgumentException("timeout_seconds must be at least 1");
        }
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getGoal() {
        return goal;
    }

    public ExecutionMode getMode() {
        return mode;
    }

    public List<String> getDependsOn() {
        return new ArrayList<>(dependsOn);
    }

    public String getWorkspaceDir() {
        return workspaceDir;
    }

    public int getMaxIterations() {
        return maxIterations;
    }

    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    public Function<GoalResult, Boolean> getCustomVerifier() {
        return customVerifier;
    }

    public List<String> getSkills() {
        return new ArrayList<>(skills);
    }

    public String getCondition() {
        return condition;
    }

    public Map<String, String> getExports() {
        return new HashMap<>(exports);
    }

    public int getMaxRetries() {
        return maxRetries;
    }

    public double getRetryDelay() {
        return retryDelay;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for WorkflowStep.
     */
    public static class Builder {
        private String name;
        private String goal;
        private ExecutionMode mode = ExecutionMode.SEQUENTIAL;
        private List<String> dependsOn = new ArrayList<>();
        private String workspaceDir = ".";
        private int maxIterations = 50;
        private int timeoutSeconds = 3600;
        private Function<GoalResult, Boolean> customVerifier;
        private List<String> skills = new ArrayList<>();
        private String condition;
        private Map<String, String> exports = new HashMap<>();
        private int maxRetries = 0;
        private double retryDelay = 5.0;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder goal(String goal) {
            this.goal = goal;
            return this;
        }

        public Builder mode(ExecutionMode mode) {
            this.mode = mode;
            return this;
        }

        public Builder dependsOn(List<String> dependsOn) {
            this.dependsOn = new ArrayList<>(dependsOn);
            return this;
        }

        public Builder addDependsOn(String stepName) {
            this.dependsOn.add(stepName);
            return this;
        }

        public Builder workspaceDir(String workspaceDir) {
            this.workspaceDir = workspaceDir;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public Builder timeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
            return this;
        }

        public Builder customVerifier(Function<GoalResult, Boolean> customVerifier) {
            this.customVerifier = customVerifier;
            return this;
        }

        public Builder skills(List<String> skills) {
            this.skills = new ArrayList<>(skills);
            return this;
        }

        public Builder addSkill(String skill) {
            this.skills.add(skill);
            return this;
        }

        public Builder condition(String condition) {
            this.condition = condition;
            return this;
        }

        public Builder exports(Map<String, String> exports) {
            this.exports = new HashMap<>(exports);
            return this;
        }

        public Builder addExport(String key, String value) {
            this.exports.put(key, value);
            return this;
        }

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public Builder retryDelay(double retryDelay) {
            this.retryDelay = retryDelay;
            return this;
        }

        public WorkflowStep build() {
            return new WorkflowStep(this);
        }
    }

    @Override
    public String toString() {
        return "WorkflowStep{name='" + name + "', goal='" + goal + "'}";
    }
}
