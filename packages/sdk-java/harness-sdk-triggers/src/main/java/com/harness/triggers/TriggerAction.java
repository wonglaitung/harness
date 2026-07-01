package com.harness.triggers;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Action to take when a trigger fires.
 *
 * <p>This configuration maps directly to GoalConfig for goal-driven execution.</p>
 */
public class TriggerAction {
    private final String goal;
    private final String workspaceDir;
    private final int maxIterations;
    private final int timeoutSeconds;
    private final Function<GoalResult, Boolean> customVerifier;
    private final List<String> skills;
    private final List<String> outputChannels;
    private final String sessionId;
    private final int maxRetries;
    private final double retryDelaySeconds;

    private TriggerAction(Builder builder) {
        this.goal = builder.goal;
        this.workspaceDir = builder.workspaceDir;
        this.maxIterations = builder.maxIterations;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.customVerifier = builder.customVerifier;
        this.skills = builder.skills;
        this.outputChannels = builder.outputChannels;
        this.sessionId = builder.sessionId;
        this.maxRetries = builder.maxRetries;
        this.retryDelaySeconds = builder.retryDelaySeconds;
    }

    public String getGoal() {
        return goal;
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
        return skills;
    }

    public List<String> getOutputChannels() {
        return outputChannels;
    }

    public String getSessionId() {
        return sessionId;
    }

    public int getMaxRetries() {
        return maxRetries;
    }

    public double getRetryDelaySeconds() {
        return retryDelaySeconds;
    }

    /**
     * Convert to GoalConfig for goal-driven execution.
     *
     * @param event Optional trigger event to include context from
     * @return GoalConfig instance ready for execution
     */
    public GoalConfig toGoalConfig(TriggerEvent event) {
        String description = goal;
        if (event != null && !event.getPayload().isEmpty()) {
            StringBuilder sb = new StringBuilder(goal);
            sb.append("\n\nEvent context:\n");
            for (Map.Entry<String, Object> entry : event.getPayload().entrySet()) {
                sb.append("- ").append(entry.getKey()).append(": ").append(entry.getValue()).append("\n");
            }
            description = sb.toString();
        }

        GoalConfig.Builder builder = new GoalConfig.Builder()
                .description(description)
                .workspaceDir(workspaceDir)
                .maxIterations(maxIterations)
                .timeoutSeconds(timeoutSeconds);

        if (customVerifier != null) {
            builder.verificationMethod(VerificationMethod.CUSTOM)
                   .customVerifier(customVerifier);
        }

        return builder.build();
    }

    public static class Builder {
        private String goal;
        private String workspaceDir = ".";
        private int maxIterations = 50;
        private int timeoutSeconds = 3600;
        private Function<GoalResult, Boolean> customVerifier;
        private List<String> skills = new ArrayList<>();
        private List<String> outputChannels = new ArrayList<>();
        private String sessionId;
        private int maxRetries = 3;
        private double retryDelaySeconds = 5.0;

        public Builder goal(String goal) {
            this.goal = goal;
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

        public Builder outputChannels(List<String> outputChannels) {
            this.outputChannels = new ArrayList<>(outputChannels);
            return this;
        }

        public Builder addOutputChannel(String channel) {
            this.outputChannels.add(channel);
            return this;
        }

        public Builder sessionId(String sessionId) {
            this.sessionId = sessionId;
            return this;
        }

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public Builder retryDelaySeconds(double retryDelaySeconds) {
            this.retryDelaySeconds = retryDelaySeconds;
            return this;
        }

        public TriggerAction build() {
            if (goal == null || goal.isEmpty()) {
                throw new IllegalArgumentException("goal cannot be empty");
            }
            if (maxIterations < 1) {
                throw new IllegalArgumentException("maxIterations must be at least 1");
            }
            if (timeoutSeconds < 1) {
                throw new IllegalArgumentException("timeoutSeconds must be at least 1");
            }
            return new TriggerAction(this);
        }
    }
}
