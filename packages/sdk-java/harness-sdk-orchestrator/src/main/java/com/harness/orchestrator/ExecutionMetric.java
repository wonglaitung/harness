package com.harness.orchestrator;

import java.time.Instant;

/**
 * Execution metric for monitoring.
 *
 * <p>Records details about a single execution (workflow, team, or goal).</p>
 */
public class ExecutionMetric {
    private final String name;
    private final String type; // "workflow" | "team" | "goal"
    private final String status;
    private final double durationSeconds;
    private final int iterations;
    private final int tokensUsed;
    private final Instant timestamp;

    private ExecutionMetric(Builder builder) {
        this.name = builder.name;
        this.type = builder.type;
        this.status = builder.status;
        this.durationSeconds = builder.durationSeconds;
        this.iterations = builder.iterations;
        this.tokensUsed = builder.tokensUsed;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getType() {
        return type;
    }

    public String getStatus() {
        return status;
    }

    public double getDurationSeconds() {
        return durationSeconds;
    }

    public int getIterations() {
        return iterations;
    }

    public int getTokensUsed() {
        return tokensUsed;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for ExecutionMetric.
     */
    public static class Builder {
        private String name;
        private String type;
        private String status;
        private double durationSeconds;
        private int iterations;
        private int tokensUsed;
        private Instant timestamp;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder type(String type) {
            this.type = type;
            return this;
        }

        public Builder status(String status) {
            this.status = status;
            return this;
        }

        public Builder durationSeconds(double durationSeconds) {
            this.durationSeconds = durationSeconds;
            return this;
        }

        public Builder iterations(int iterations) {
            this.iterations = iterations;
            return this;
        }

        public Builder tokensUsed(int tokensUsed) {
            this.tokensUsed = tokensUsed;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public ExecutionMetric build() {
            return new ExecutionMetric(this);
        }
    }

    @Override
    public String toString() {
        return "ExecutionMetric{name='" + name + "', type='" + type + "', status='" + status + "'}";
    }
}
