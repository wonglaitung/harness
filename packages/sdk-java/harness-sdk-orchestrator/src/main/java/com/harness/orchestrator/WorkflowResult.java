package com.harness.orchestrator;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Workflow execution result.
 *
 * <p>Contains comprehensive information about workflow execution
 * including all step results and overall status.</p>
 */
public class WorkflowResult {
    private final String workflowName;
    private final WorkflowStatus status;
    private final Map<String, StepResult> steps;
    private final Instant startedAt;
    private final Instant completedAt;
    private final String error;

    private WorkflowResult(Builder builder) {
        this.workflowName = builder.workflowName;
        this.status = builder.status;
        this.steps = new HashMap<>(builder.steps);
        this.startedAt = builder.startedAt;
        this.completedAt = builder.completedAt;
        this.error = builder.error;
    }

    /**
     * Check if workflow completed successfully.
     */
    public boolean isSuccess() {
        return status == WorkflowStatus.COMPLETED;
    }

    /**
     * Calculate total workflow duration in seconds.
     */
    public double getDurationSeconds() {
        if (completedAt != null) {
            return Duration.between(startedAt, completedAt).toMillis() / 1000.0;
        }
        return 0.0;
    }

    /**
     * Get result for a specific step.
     */
    public StepResult getStepResult(String stepName) {
        return steps.get(stepName);
    }

    /**
     * Get names of successfully completed steps.
     */
    public List<String> getSuccessfulSteps() {
        List<String> result = new ArrayList<>();
        for (Map.Entry<String, StepResult> entry : steps.entrySet()) {
            if (entry.getValue().getStatus() == StepStatus.SUCCESS) {
                result.add(entry.getKey());
            }
        }
        return result;
    }

    /**
     * Get names of failed steps.
     */
    public List<String> getFailedSteps() {
        List<String> result = new ArrayList<>();
        for (Map.Entry<String, StepResult> entry : steps.entrySet()) {
            if (entry.getValue().getStatus() == StepStatus.FAILED) {
                result.add(entry.getKey());
            }
        }
        return result;
    }

    /**
     * Get names of skipped steps.
     */
    public List<String> getSkippedSteps() {
        List<String> result = new ArrayList<>();
        for (Map.Entry<String, StepResult> entry : steps.entrySet()) {
            if (entry.getValue().getStatus() == StepStatus.SKIPPED) {
                result.add(entry.getKey());
            }
        }
        return result;
    }

    /**
     * Serialize to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("workflow_name", workflowName);
        map.put("status", status.getValue());
        map.put("started_at", startedAt != null ? startedAt.toString() : null);
        map.put("completed_at", completedAt != null ? completedAt.toString() : null);
        map.put("duration_seconds", getDurationSeconds());
        map.put("successful_steps", getSuccessfulSteps().size());
        map.put("failed_steps", getFailedSteps().size());
        map.put("error", error);
        return map;
    }

    // Getters

    public String getWorkflowName() {
        return workflowName;
    }

    public WorkflowStatus getStatus() {
        return status;
    }

    public Map<String, StepResult> getSteps() {
        return new HashMap<>(steps);
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public String getError() {
        return error;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for WorkflowResult.
     */
    public static class Builder {
        private String workflowName;
        private WorkflowStatus status = WorkflowStatus.PENDING;
        private Map<String, StepResult> steps = new HashMap<>();
        private Instant startedAt;
        private Instant completedAt;
        private String error;

        public Builder workflowName(String workflowName) {
            this.workflowName = workflowName;
            return this;
        }

        public Builder status(WorkflowStatus status) {
            this.status = status;
            return this;
        }

        public Builder steps(Map<String, StepResult> steps) {
            this.steps = new HashMap<>(steps);
            return this;
        }

        public Builder addStepResult(String stepName, StepResult result) {
            this.steps.put(stepName, result);
            return this;
        }

        public Builder startedAt(Instant startedAt) {
            this.startedAt = startedAt;
            return this;
        }

        public Builder completedAt(Instant completedAt) {
            this.completedAt = completedAt;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public WorkflowResult build() {
            return new WorkflowResult(this);
        }
    }

    @Override
    public String toString() {
        return "WorkflowResult{workflowName='" + workflowName + "', status=" + status + '}';
    }
}
