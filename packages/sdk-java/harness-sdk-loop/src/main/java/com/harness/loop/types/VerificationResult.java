package com.harness.loop.types;

import java.util.Objects;

/**
 * Result of a verification attempt.
 *
 * <p>Returned by GoalVerifier.verify() to indicate goal achievement status.</p>
 */
public class VerificationResult {
    private final boolean achieved;
    private final double confidence;
    private final String reasoning;
    private final boolean shouldRetry;
    private final String error;

    private VerificationResult(Builder builder) {
        this.achieved = builder.achieved;
        this.confidence = builder.confidence;
        this.reasoning = builder.reasoning;
        this.shouldRetry = builder.shouldRetry;
        this.error = builder.error;
    }

    /**
     * Whether the goal has been achieved.
     */
    public boolean isAchieved() {
        return achieved;
    }

    /**
     * Confidence level of the result (0.0-1.0).
     */
    public double getConfidence() {
        return confidence;
    }

    /**
     * Explanation of why the goal is/isn't achieved.
     */
    public String getReasoning() {
        return reasoning;
    }

    /**
     * Whether to retry verification (for VERIFIER_FAULT).
     */
    public boolean shouldRetry() {
        return shouldRetry;
    }

    /**
     * Error message if verification failed.
     */
    public String getError() {
        return error;
    }

    /**
     * Create a successful verification result.
     *
     * @param reasoning Explanation of success
     * @param confidence Confidence level (0.0-1.0)
     * @return VerificationResult indicating success
     */
    public static VerificationResult success(String reasoning, double confidence) {
        return new Builder()
                .achieved(true)
                .confidence(confidence)
                .reasoning(reasoning)
                .build();
    }

    /**
     * Create a successful verification result with default confidence.
     *
     * @param reasoning Explanation of success
     * @return VerificationResult indicating success
     */
    public static VerificationResult success(String reasoning) {
        return success(reasoning, 1.0);
    }

    /**
     * Create a failure verification result.
     *
     * @param reasoning Explanation of failure
     * @param confidence Confidence level (0.0-1.0)
     * @return VerificationResult indicating failure
     */
    public static VerificationResult failure(String reasoning, double confidence) {
        return new Builder()
                .achieved(false)
                .confidence(confidence)
                .reasoning(reasoning)
                .build();
    }

    /**
     * Create a failure verification result with default confidence.
     *
     * @param reasoning Explanation of failure
     * @return VerificationResult indicating failure
     */
    public static VerificationResult failure(String reasoning) {
        return failure(reasoning, 0.0);
    }

    /**
     * Create a verifier fault result.
     *
     * @param error Error message
     * @param shouldRetry Whether to retry
     * @return VerificationResult indicating verifier fault
     */
    public static VerificationResult fault(String error, boolean shouldRetry) {
        return new Builder()
                .achieved(false)
                .confidence(0.0)
                .reasoning("Verifier fault: " + error)
                .shouldRetry(shouldRetry)
                .error(error)
                .build();
    }

    /**
     * Create a verifier fault result with retry enabled.
     *
     * @param error Error message
     * @return VerificationResult indicating verifier fault
     */
    public static VerificationResult fault(String error) {
        return fault(error, true);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        VerificationResult that = (VerificationResult) o;
        return achieved == that.achieved &&
                Double.compare(that.confidence, confidence) == 0 &&
                shouldRetry == that.shouldRetry &&
                Objects.equals(reasoning, that.reasoning) &&
                Objects.equals(error, that.error);
    }

    @Override
    public int hashCode() {
        return Objects.hash(achieved, confidence, reasoning, shouldRetry, error);
    }

    @Override
    public String toString() {
        return "VerificationResult{" +
                "achieved=" + achieved +
                ", confidence=" + confidence +
                ", reasoning='" + reasoning + '\'' +
                ", shouldRetry=" + shouldRetry +
                ", error='" + error + '\'' +
                '}';
    }

    /**
     * Builder for VerificationResult.
     */
    public static class Builder {
        private boolean achieved = false;
        private double confidence = 0.5;
        private String reasoning = "";
        private boolean shouldRetry = false;
        private String error = null;

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

        public Builder shouldRetry(boolean shouldRetry) {
            this.shouldRetry = shouldRetry;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public VerificationResult build() {
            return new VerificationResult(this);
        }
    }
}
