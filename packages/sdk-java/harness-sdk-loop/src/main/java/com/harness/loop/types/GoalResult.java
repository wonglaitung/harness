package com.harness.loop.types;

import com.harness.types.Session;
import com.harness.types.TokenUsage;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Result of goal-driven execution.
 *
 * <p>Contains comprehensive information about the execution including
 * status, statistics, and verification history.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GoalResult result = agent.runGoal("Fix type errors");
 *
 * if (result.status() == GoalStatus.ACHIEVED) {
 *     System.out.println("Goal achieved in " + result.totalIterations() + " iterations");
 * } else if (result.status() == GoalStatus.VERIFIER_FAULT) {
 *     System.out.println("Verifier failed: " + result.error());
 * }
 * }</pre>
 */
public class GoalResult {
    private final String goal;
    private final GoalStatus status;
    private final int totalIterations;
    private final int contextResets;
    private final Map<String, Integer> totalTokens;
    private final double durationSeconds;
    private final String finalResponse;
    private final Session session;
    private final List<VerificationRecord> verificationLog;
    private final String error;

    private GoalResult(Builder builder) {
        this.goal = builder.goal;
        this.status = builder.status;
        this.totalIterations = builder.totalIterations;
        this.contextResets = builder.contextResets;
        this.totalTokens = builder.totalTokens != null ? new HashMap<>(builder.totalTokens) : new HashMap<>();
        this.durationSeconds = builder.durationSeconds;
        this.finalResponse = builder.finalResponse;
        this.session = builder.session;
        this.verificationLog = builder.verificationLog != null ?
                new ArrayList<>(builder.verificationLog) : new ArrayList<>();
        this.error = builder.error;

        // Ensure token map has default values
        if (!this.totalTokens.containsKey("input")) {
            this.totalTokens.put("input", 0);
        }
        if (!this.totalTokens.containsKey("output")) {
            this.totalTokens.put("output", 0);
        }
    }

    // Getters

    /**
     * Original goal description.
     */
    public String goal() {
        return goal;
    }

    /**
     * Final status of goal execution.
     */
    public GoalStatus status() {
        return status;
    }

    /**
     * Total number of iterations executed.
     */
    public int totalIterations() {
        return totalIterations;
    }

    /**
     * Number of context resets performed.
     */
    public int contextResets() {
        return contextResets;
    }

    /**
     * Total token usage (map with "input" and "output" keys).
     */
    public Map<String, Integer> totalTokens() {
        return Collections.unmodifiableMap(totalTokens);
    }

    /**
     * Total execution duration in seconds.
     */
    public double durationSeconds() {
        return durationSeconds;
    }

    /**
     * Final response from the agent.
     */
    public String finalResponse() {
        return finalResponse;
    }

    /**
     * Complete session data.
     */
    public Session session() {
        return session;
    }

    /**
     * History of verification attempts.
     */
    public List<VerificationRecord> verificationLog() {
        return Collections.unmodifiableList(verificationLog);
    }

    /**
     * Error message if execution failed.
     */
    public String error() {
        return error;
    }

    /**
     * Check if the goal was achieved.
     */
    public boolean achieved() {
        return status == GoalStatus.ACHIEVED;
    }

    /**
     * Check if the goal execution failed (any non-achieved terminal state).
     */
    public boolean failed() {
        return status != GoalStatus.ACHIEVED;
    }

    /**
     * Get a summary of verification attempts.
     */
    public String getVerificationSummary() {
        if (verificationLog.isEmpty()) {
            return "No verification attempts";
        }

        int achievedCount = 0;
        for (VerificationRecord record : verificationLog) {
            if (record.isAchieved()) {
                achievedCount++;
            }
        }

        return achievedCount + "/" + verificationLog.size() + " verifications passed";
    }

    /**
     * Serialize to map for logging/storage.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> result = new HashMap<>();
        result.put("goal", goal);
        result.put("status", status.getValue());
        result.put("total_iterations", totalIterations);
        result.put("context_resets", contextResets);
        result.put("total_tokens", totalTokens);
        result.put("duration_seconds", durationSeconds);
        result.put("final_response", finalResponse != null && finalResponse.length() > 500 ?
                finalResponse.substring(0, 500) : finalResponse);
        result.put("verification_count", verificationLog.size());
        result.put("error", error);
        return result;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        GoalResult that = (GoalResult) o;
        return totalIterations == that.totalIterations &&
                contextResets == that.contextResets &&
                Double.compare(that.durationSeconds, durationSeconds) == 0 &&
                Objects.equals(goal, that.goal) &&
                status == that.status &&
                Objects.equals(totalTokens, that.totalTokens) &&
                Objects.equals(finalResponse, that.finalResponse) &&
                Objects.equals(session, that.session) &&
                Objects.equals(verificationLog, that.verificationLog) &&
                Objects.equals(error, that.error);
    }

    @Override
    public int hashCode() {
        return Objects.hash(goal, status, totalIterations, contextResets, totalTokens,
                durationSeconds, finalResponse, session, verificationLog, error);
    }

    @Override
    public String toString() {
        return "GoalResult{" +
                "goal='" + goal + '\'' +
                ", status=" + status +
                ", totalIterations=" + totalIterations +
                ", contextResets=" + contextResets +
                ", durationSeconds=" + durationSeconds +
                '}';
    }

    /**
     * Create a builder for GoalResult.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for GoalResult.
     */
    public static class Builder {
        private String goal;
        private GoalStatus status = GoalStatus.MAX_ITERATIONS;
        private int totalIterations = 0;
        private int contextResets = 0;
        private Map<String, Integer> totalTokens = new HashMap<>();
        private double durationSeconds = 0.0;
        private String finalResponse = "";
        private Session session = null;
        private List<VerificationRecord> verificationLog = new ArrayList<>();
        private String error = null;

        public Builder goal(String goal) {
            this.goal = goal;
            return this;
        }

        public Builder status(GoalStatus status) {
            this.status = status;
            return this;
        }

        public Builder totalIterations(int totalIterations) {
            this.totalIterations = totalIterations;
            return this;
        }

        public Builder contextResets(int contextResets) {
            this.contextResets = contextResets;
            return this;
        }

        public Builder totalTokens(Map<String, Integer> totalTokens) {
            this.totalTokens = totalTokens;
            return this;
        }

        public Builder totalTokens(int inputTokens, int outputTokens) {
            this.totalTokens = new HashMap<>();
            this.totalTokens.put("input", inputTokens);
            this.totalTokens.put("output", outputTokens);
            return this;
        }

        public Builder durationSeconds(double durationSeconds) {
            this.durationSeconds = durationSeconds;
            return this;
        }

        public Builder finalResponse(String finalResponse) {
            this.finalResponse = finalResponse;
            return this;
        }

        public Builder session(Session session) {
            this.session = session;
            return this;
        }

        public Builder verificationLog(List<VerificationRecord> verificationLog) {
            this.verificationLog = verificationLog;
            return this;
        }

        public Builder addVerificationRecord(VerificationRecord record) {
            this.verificationLog.add(record);
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public GoalResult build() {
            return new GoalResult(this);
        }
    }
}
