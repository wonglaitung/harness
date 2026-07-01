package com.harness.loop.automation;

import com.harness.loop.types.GoalResult;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/**
 * Configuration for an Automation.
 *
 * <p>An Automation combines a trigger with a goal, providing a simple
 * way to set up scheduled or periodic goal execution.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Cron-based automation
 * AutomationConfig config = AutomationConfig.builder()
 *     .name("daily-report")
 *     .goal("Generate daily report")
 *     .schedule("0 9 * * *")  // Daily at 9:00
 *     .build();
 *
 * // Interval-based automation
 * AutomationConfig config = AutomationConfig.builder()
 *     .name("health-check")
 *     .goal("Check system health")
 *     .intervalSeconds(300)  // Every 5 minutes
 *     .build();
 * }</pre>
 */
public class AutomationConfig {
    private final String name;
    private final String goal;

    // Trigger configuration (one required)
    private final String schedule;        // Cron expression
    private final Integer intervalSeconds;

    // Goal configuration
    private final String workspaceDir;
    private final int maxIterations;
    private final int timeoutSeconds;
    private final Function<GoalResult, Boolean> customVerifier;

    // Skills and output
    private final List<String> skills;
    private final List<String> outputChannels;

    // Retry
    private final int maxRetries;
    private final double retryDelaySeconds;

    private AutomationConfig(Builder builder) {
        this.name = builder.name;
        this.goal = builder.goal;
        this.schedule = builder.schedule;
        this.intervalSeconds = builder.intervalSeconds;
        this.workspaceDir = builder.workspaceDir;
        this.maxIterations = builder.maxIterations;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.customVerifier = builder.customVerifier;
        this.skills = new ArrayList<>(builder.skills);
        this.outputChannels = new ArrayList<>(builder.outputChannels);
        this.maxRetries = builder.maxRetries;
        this.retryDelaySeconds = builder.retryDelaySeconds;

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("name is required");
        }

        if (goal == null || goal.isEmpty()) {
            throw new IllegalArgumentException("goal is required");
        }

        // Ensure exactly one trigger is specified
        int triggerCount = 0;
        if (schedule != null) triggerCount++;
        if (intervalSeconds != null) triggerCount++;

        if (triggerCount == 0) {
            throw new IllegalArgumentException(
                    "One of schedule or intervalSeconds is required");
        }
        if (triggerCount > 1) {
            throw new IllegalArgumentException(
                    "Only one of schedule or intervalSeconds can be specified");
        }
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getGoal() {
        return goal;
    }

    public String getSchedule() {
        return schedule;
    }

    public Integer getIntervalSeconds() {
        return intervalSeconds;
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

    public List<String> getOutputChannels() {
        return new ArrayList<>(outputChannels);
    }

    public int getMaxRetries() {
        return maxRetries;
    }

    public double getRetryDelaySeconds() {
        return retryDelaySeconds;
    }

    /**
     * Check if this is a cron-based automation.
     */
    public boolean isCronBased() {
        return schedule != null;
    }

    /**
     * Check if this is an interval-based automation.
     */
    public boolean isIntervalBased() {
        return intervalSeconds != null;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for AutomationConfig.
     */
    public static class Builder {
        private String name;
        private String goal;
        private String schedule;
        private Integer intervalSeconds;
        private String workspaceDir = ".";
        private int maxIterations = 50;
        private int timeoutSeconds = 3600;
        private Function<GoalResult, Boolean> customVerifier;
        private List<String> skills = new ArrayList<>();
        private List<String> outputChannels = new ArrayList<>();
        private int maxRetries = 3;
        private double retryDelaySeconds = 5.0;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder goal(String goal) {
            this.goal = goal;
            return this;
        }

        public Builder schedule(String schedule) {
            this.schedule = schedule;
            return this;
        }

        public Builder intervalSeconds(Integer intervalSeconds) {
            this.intervalSeconds = intervalSeconds;
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

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public Builder retryDelaySeconds(double retryDelaySeconds) {
            this.retryDelaySeconds = retryDelaySeconds;
            return this;
        }

        public AutomationConfig build() {
            return new AutomationConfig(this);
        }
    }
}
