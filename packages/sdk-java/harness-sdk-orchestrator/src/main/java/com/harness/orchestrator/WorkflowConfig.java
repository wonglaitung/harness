package com.harness.orchestrator;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Complete workflow configuration.
 *
 * <p>A workflow consists of multiple steps with dependencies and
 * execution modes.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * WorkflowConfig workflow = WorkflowConfig.builder()
 *     .name("code-review")
 *     .addStep(WorkflowStep.builder()
 *         .name("analyze")
 *         .goal("Analyze code")
 *         .build())
 *     .addStep(WorkflowStep.builder()
 *         .name("review")
 *         .goal("Review code")
 *         .addDependsOn("analyze")
 *         .build())
 *     .build();
 * }</pre>
 */
public class WorkflowConfig {
    private final String name;
    private final String description;
    private final List<WorkflowStep> steps;
    private final ExecutionMode defaultMode;
    private final int maxParallelSteps;
    private final String workspaceDir;
    private final String triggerOn;
    private final List<String> outputChannels;

    private WorkflowConfig(Builder builder) {
        this.name = builder.name;
        this.description = builder.description;
        this.steps = new ArrayList<>(builder.steps);
        this.defaultMode = builder.defaultMode;
        this.maxParallelSteps = builder.maxParallelSteps;
        this.workspaceDir = builder.workspaceDir;
        this.triggerOn = builder.triggerOn;
        this.outputChannels = new ArrayList<>(builder.outputChannels);

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("workflow name cannot be empty");
        }

        if (maxParallelSteps < 1) {
            throw new IllegalArgumentException("max_parallel_steps must be at least 1");
        }

        // Validate step names are unique
        Set<String> stepNames = new HashSet<>();
        for (WorkflowStep step : steps) {
            if (!stepNames.add(step.getName())) {
                throw new IllegalArgumentException("step names must be unique: " + step.getName());
            }
        }
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public List<WorkflowStep> getSteps() {
        return new ArrayList<>(steps);
    }

    public ExecutionMode getDefaultMode() {
        return defaultMode;
    }

    public int getMaxParallelSteps() {
        return maxParallelSteps;
    }

    public String getWorkspaceDir() {
        return workspaceDir;
    }

    public String getTriggerOn() {
        return triggerOn;
    }

    public List<String> getOutputChannels() {
        return new ArrayList<>(outputChannels);
    }

    /**
     * Get a step by name.
     */
    public WorkflowStep getStep(String name) {
        for (WorkflowStep step : steps) {
            if (step.getName().equals(name)) {
                return step;
            }
        }
        return null;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for WorkflowConfig.
     */
    public static class Builder {
        private String name;
        private String description = "";
        private List<WorkflowStep> steps = new ArrayList<>();
        private ExecutionMode defaultMode = ExecutionMode.SEQUENTIAL;
        private int maxParallelSteps = 5;
        private String workspaceDir = ".";
        private String triggerOn;
        private List<String> outputChannels = new ArrayList<>();

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder description(String description) {
            this.description = description;
            return this;
        }

        public Builder steps(List<WorkflowStep> steps) {
            this.steps = new ArrayList<>(steps);
            return this;
        }

        public Builder addStep(WorkflowStep step) {
            this.steps.add(step);
            return this;
        }

        public Builder defaultMode(ExecutionMode defaultMode) {
            this.defaultMode = defaultMode;
            return this;
        }

        public Builder maxParallelSteps(int maxParallelSteps) {
            this.maxParallelSteps = maxParallelSteps;
            return this;
        }

        public Builder workspaceDir(String workspaceDir) {
            this.workspaceDir = workspaceDir;
            return this;
        }

        public Builder triggerOn(String triggerOn) {
            this.triggerOn = triggerOn;
            return this;
        }

        public Builder outputChannels(List<String> outputChannels) {
            this.outputChannels = new ArrayList<>(outputChannels);
            return this;
        }

        public Builder addOutputChannel(String channel) {
            this.outputChannels.add(channel);
            return this;
        }

        public WorkflowConfig build() {
            return new WorkflowConfig(this);
        }
    }

    @Override
    public String toString() {
        return "WorkflowConfig{name='" + name + "', steps=" + steps.size() + '}';
    }
}
