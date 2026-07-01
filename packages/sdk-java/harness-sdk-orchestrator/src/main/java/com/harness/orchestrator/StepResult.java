package com.harness.orchestrator;

import com.harness.loop.types.GoalResult;

import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Step execution result.
 *
 * <p>Contains the outcome of a single workflow step execution,
 * including the goal result and any exported data.</p>
 */
public class StepResult {
    private final String stepName;
    private final StepStatus status;
    private final GoalResult goalResult;
    private final Map<String, Object> exports;
    private final String error;
    private final Instant startedAt;
    private final Instant completedAt;

    private StepResult(Builder builder) {
        this.stepName = builder.stepName;
        this.status = builder.status;
        this.goalResult = builder.goalResult;
        this.exports = new HashMap<>(builder.exports);
        this.error = builder.error;
        this.startedAt = builder.startedAt;
        this.completedAt = builder.completedAt;
    }

    /**
     * Calculate step duration in seconds.
     */
    public double getDurationSeconds() {
        if (startedAt != null && completedAt != null) {
            return Duration.between(startedAt, completedAt).toMillis() / 1000.0;
        }
        return 0.0;
    }

    // Getters

    public String getStepName() {
        return stepName;
    }

    public StepStatus getStatus() {
        return status;
    }

    public GoalResult getGoalResult() {
        return goalResult;
    }

    public Map<String, Object> getExports() {
        return new HashMap<>(exports);
    }

    public String getError() {
        return error;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    /**
     * Check if step succeeded.
     */
    public boolean isSuccess() {
        return status == StepStatus.SUCCESS;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for StepResult.
     */
    public static class Builder {
        private String stepName;
        private StepStatus status = StepStatus.PENDING;
        private GoalResult goalResult;
        private Map<String, Object> exports = new HashMap<>();
        private String error;
        private Instant startedAt;
        private Instant completedAt;

        public Builder stepName(String stepName) {
            this.stepName = stepName;
            return this;
        }

        public Builder status(StepStatus status) {
            this.status = status;
            return this;
        }

        public Builder goalResult(GoalResult goalResult) {
            this.goalResult = goalResult;
            return this;
        }

        public Builder exports(Map<String, Object> exports) {
            this.exports = new HashMap<>(exports);
            return this;
        }

        public Builder addExport(String key, Object value) {
            this.exports.put(key, value);
            return this;
        }

        public Builder error(String error) {
            this.error = error;
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

        public StepResult build() {
            return new StepResult(this);
        }
    }

    @Override
    public String toString() {
        return "StepResult{stepName='" + stepName + "', status=" + status + '}';
    }
}
