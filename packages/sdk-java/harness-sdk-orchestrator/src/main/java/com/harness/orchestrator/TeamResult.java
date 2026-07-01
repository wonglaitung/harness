package com.harness.orchestrator;

import com.harness.loop.types.GoalResult;

import java.util.HashMap;
import java.util.Map;

/**
 * Team execution result.
 *
 * <p>Contains the outcome of a team task execution,
 * including results from each agent role.</p>
 */
public class TeamResult {
    private final String teamName;
    private final boolean success;
    private final Map<String, GoalResult> agentResults;
    private final int totalIterations;
    private final int totalTokens;
    private final double durationSeconds;
    private final String error;

    private TeamResult(Builder builder) {
        this.teamName = builder.teamName;
        this.success = builder.success;
        this.agentResults = new HashMap<>(builder.agentResults);
        this.totalIterations = builder.totalIterations;
        this.totalTokens = builder.totalTokens;
        this.durationSeconds = builder.durationSeconds;
        this.error = builder.error;
    }

    /**
     * Get result for a specific agent role.
     */
    public GoalResult getAgentResult(String roleName) {
        return agentResults.get(roleName);
    }

    // Getters

    public String getTeamName() {
        return teamName;
    }

    public boolean isSuccess() {
        return success;
    }

    public Map<String, GoalResult> getAgentResults() {
        return new HashMap<>(agentResults);
    }

    public int getTotalIterations() {
        return totalIterations;
    }

    public int getTotalTokens() {
        return totalTokens;
    }

    public double getDurationSeconds() {
        return durationSeconds;
    }

    public String getError() {
        return error;
    }

    /**
     * Serialize to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("team_name", teamName);
        map.put("success", success);
        map.put("total_iterations", totalIterations);
        map.put("total_tokens", totalTokens);
        map.put("duration_seconds", durationSeconds);
        map.put("error", error);
        return map;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for TeamResult.
     */
    public static class Builder {
        private String teamName;
        private boolean success;
        private Map<String, GoalResult> agentResults = new HashMap<>();
        private int totalIterations;
        private int totalTokens;
        private double durationSeconds;
        private String error;

        public Builder teamName(String teamName) {
            this.teamName = teamName;
            return this;
        }

        public Builder success(boolean success) {
            this.success = success;
            return this;
        }

        public Builder agentResults(Map<String, GoalResult> agentResults) {
            this.agentResults = new HashMap<>(agentResults);
            return this;
        }

        public Builder addAgentResult(String roleName, GoalResult result) {
            this.agentResults.put(roleName, result);
            return this;
        }

        public Builder totalIterations(int totalIterations) {
            this.totalIterations = totalIterations;
            return this;
        }

        public Builder totalTokens(int totalTokens) {
            this.totalTokens = totalTokens;
            return this;
        }

        public Builder durationSeconds(double durationSeconds) {
            this.durationSeconds = durationSeconds;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public TeamResult build() {
            return new TeamResult(this);
        }
    }

    @Override
    public String toString() {
        return "TeamResult{teamName='" + teamName + "', success=" + success + '}';
    }
}
