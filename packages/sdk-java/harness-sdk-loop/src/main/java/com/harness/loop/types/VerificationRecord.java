package com.harness.loop.types;

import java.time.Instant;
import java.util.Objects;

/**
 * Record of a single verification attempt.
 *
 * <p>Tracks the result and reasoning of each verification during goal execution.</p>
 */
public class VerificationRecord {
    private final int iteration;
    private final boolean achieved;
    private final double confidence;
    private final String reasoning;
    private final Instant timestamp;
    private final VerificationMethod method;
    private final String error;

    private VerificationRecord(Builder builder) {
        this.iteration = builder.iteration;
        this.achieved = builder.achieved;
        this.confidence = builder.confidence;
        this.reasoning = builder.reasoning;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
        this.method = builder.method != null ? builder.method : VerificationMethod.LLM;
        this.error = builder.error;
    }

    /**
     * The iteration number when verification occurred.
     */
    public int getIteration() {
        return iteration;
    }

    /**
     * Whether the goal was achieved.
     */
    public boolean isAchieved() {
        return achieved;
    }

    /**
     * Confidence level (0.0-1.0).
     */
    public double getConfidence() {
        return confidence;
    }

    /**
     * Explanation of the verification result.
     */
    public String getReasoning() {
        return reasoning;
    }

    /**
     * When the verification occurred.
     */
    public Instant getTimestamp() {
        return timestamp;
    }

    /**
     * Method used for verification.
     */
    public VerificationMethod getMethod() {
        return method;
    }

    /**
     * Error message if verification failed.
     */
    public String getError() {
        return error;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        VerificationRecord that = (VerificationRecord) o;
        return iteration == that.iteration &&
                achieved == that.achieved &&
                Double.compare(that.confidence, confidence) == 0 &&
                Objects.equals(reasoning, that.reasoning) &&
                Objects.equals(timestamp, that.timestamp) &&
                method == that.method &&
                Objects.equals(error, that.error);
    }

    @Override
    public int hashCode() {
        return Objects.hash(iteration, achieved, confidence, reasoning, timestamp, method, error);
    }

    @Override
    public String toString() {
        return "VerificationRecord{" +
                "iteration=" + iteration +
                ", achieved=" + achieved +
                ", confidence=" + confidence +
                ", reasoning='" + reasoning + '\'' +
                ", timestamp=" + timestamp +
                ", method=" + method +
                ", error='" + error + '\'' +
                '}';
    }

    /**
     * Builder for VerificationRecord.
     */
    public static class Builder {
        private int iteration;
        private boolean achieved;
        private double confidence;
        private String reasoning;
        private Instant timestamp;
        private VerificationMethod method;
        private String error;

        public Builder iteration(int iteration) {
            this.iteration = iteration;
            return this;
        }

        public Builder achieved(boolean achieved) {
            this.achieved = achieved;
            return this;
        }

        public Builder confidence(double confidence) {
            this.confidence = confidence;
            return this;
        }

        public Builder reasoning(String reasoning) {
            this.reasoning = reasoning;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder method(VerificationMethod method) {
            this.method = method;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public VerificationRecord build() {
            return new VerificationRecord(this);
        }
    }
}
