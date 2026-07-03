package com.harness.loop.types;

import com.harness.types.LoopResult;

import java.util.function.Function;

/**
 * Configuration for goal-driven execution.
 *
 * <p>This configuration defines how a goal should be executed and verified.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GoalConfig config = GoalConfig.builder()
 *     .description("Fix all type errors in src/")
 *     .workspaceDir("/tmp/worktree-feature-a")
 *     .maxIterations(50)
 *     .customVerifier(result -> result.content().contains("All tests passed"))
 *     .build();
 * }</pre>
 */
public class GoalConfig {
    private final String description;
    private final String sessionId;
    private final String successCriteria;
    private final String workspaceDir;
    private final int maxIterations;
    private final int maxContextResets;
    private final int timeoutSeconds;
    private final VerificationMethod verificationMethod;
    private final Function<GoalResult, Boolean> customVerifier;
    private final int verifierMaxRetries;
    private final double verifierRetryDelay;
    private final double verifierRetryBackoff;
    private final Integer maxTokens;
    private final Double maxCostUsd;
    private final double contextResetThreshold;
    private final int preserveMessages;
    private final ToolVerificationConfig toolVerificationConfig;

    private GoalConfig(Builder builder) {
        this.description = builder.description;
        this.sessionId = builder.sessionId;
        this.successCriteria = builder.successCriteria;
        this.workspaceDir = builder.workspaceDir;
        this.maxIterations = builder.maxIterations;
        this.maxContextResets = builder.maxContextResets;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.verificationMethod = builder.verificationMethod;
        this.customVerifier = builder.customVerifier;
        this.verifierMaxRetries = builder.verifierMaxRetries;
        this.verifierRetryDelay = builder.verifierRetryDelay;
        this.verifierRetryBackoff = builder.verifierRetryBackoff;
        this.maxTokens = builder.maxTokens;
        this.maxCostUsd = builder.maxCostUsd;
        this.contextResetThreshold = builder.contextResetThreshold;
        this.preserveMessages = builder.preserveMessages;
        this.toolVerificationConfig = builder.toolVerificationConfig;

        validate();
    }

    private void validate() {
        if (description == null || description.isEmpty()) {
            throw new IllegalArgumentException("Goal description cannot be empty");
        }
        if (maxIterations < 1) {
            throw new IllegalArgumentException("maxIterations must be at least 1");
        }
        if (maxContextResets < 0) {
            throw new IllegalArgumentException("maxContextResets cannot be negative");
        }
        if (timeoutSeconds < 1) {
            throw new IllegalArgumentException("timeoutSeconds must be at least 1");
        }
        if (contextResetThreshold <= 0.0 || contextResetThreshold > 1.0) {
            throw new IllegalArgumentException("contextResetThreshold must be between 0 and 1");
        }
        if (verificationMethod == VerificationMethod.CUSTOM && customVerifier == null) {
            throw new IllegalArgumentException("customVerifier is required when verificationMethod is CUSTOM");
        }
        if (verificationMethod == VerificationMethod.TOOL && toolVerificationConfig == null) {
            throw new IllegalArgumentException("toolVerificationConfig is required when verificationMethod is TOOL");
        }
    }

    // Getters

    /**
     * Human-readable description of the goal.
     */
    public String getDescription() {
        return description;
    }

    /**
     * Optional session ID for conversation continuity.
     */
    public String getSessionId() {
        return sessionId;
    }

    /**
     * Optional specific criteria for success.
     */
    public String getSuccessCriteria() {
        return successCriteria;
    }

    /**
     * Working directory for execution.
     */
    public String getWorkspaceDir() {
        return workspaceDir;
    }

    /**
     * Maximum iterations per context window.
     */
    public int getMaxIterations() {
        return maxIterations;
    }

    /**
     * Maximum context reset attempts.
     */
    public int getMaxContextResets() {
        return maxContextResets;
    }

    /**
     * Total execution timeout in seconds.
     */
    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    /**
     * Method for verifying goal achievement.
     */
    public VerificationMethod getVerificationMethod() {
        return verificationMethod;
    }

    /**
     * Optional custom verification function.
     */
    public Function<GoalResult, Boolean> getCustomVerifier() {
        return customVerifier;
    }

    /**
     * Maximum retries for verifier failures.
     */
    public int getVerifierMaxRetries() {
        return verifierMaxRetries;
    }

    /**
     * Initial retry delay in seconds.
     */
    public double getVerifierRetryDelay() {
        return verifierRetryDelay;
    }

    /**
     * Backoff multiplier for retries.
     */
    public double getVerifierRetryBackoff() {
        return verifierRetryBackoff;
    }

    /**
     * Optional token budget limit.
     */
    public Integer getMaxTokens() {
        return maxTokens;
    }

    /**
     * Optional cost budget in USD.
     */
    public Double getMaxCostUsd() {
        return maxCostUsd;
    }

    /**
     * Context usage threshold for reset (0.0-1.0).
     */
    public double getContextResetThreshold() {
        return contextResetThreshold;
    }

    /**
     * Number of messages to preserve on context reset.
     */
    public int getPreserveMessages() {
        return preserveMessages;
    }

    /**
     * Configuration for tool-based verification.
     */
    public ToolVerificationConfig getToolVerificationConfig() {
        return toolVerificationConfig;
    }

    /**
     * Create a builder for GoalConfig.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Create a builder from an existing GoalConfig.
     */
    public static Builder builder(GoalConfig config) {
        return new Builder()
                .description(config.description)
                .sessionId(config.sessionId)
                .successCriteria(config.successCriteria)
                .workspaceDir(config.workspaceDir)
                .maxIterations(config.maxIterations)
                .maxContextResets(config.maxContextResets)
                .timeoutSeconds(config.timeoutSeconds)
                .verificationMethod(config.verificationMethod)
                .customVerifier(config.customVerifier)
                .verifierMaxRetries(config.verifierMaxRetries)
                .verifierRetryDelay(config.verifierRetryDelay)
                .verifierRetryBackoff(config.verifierRetryBackoff)
                .maxTokens(config.maxTokens)
                .maxCostUsd(config.maxCostUsd)
                .contextResetThreshold(config.contextResetThreshold)
                .preserveMessages(config.preserveMessages)
                .toolVerificationConfig(config.toolVerificationConfig);
    }

    /**
     * Builder for GoalConfig.
     */
    public static class Builder {
        private String description;
        private String sessionId = null;
        private String successCriteria = null;
        private String workspaceDir = ".";
        private int maxIterations = 50;
        private int maxContextResets = 5;
        private int timeoutSeconds = 3600;
        private VerificationMethod verificationMethod = VerificationMethod.LLM;
        private Function<GoalResult, Boolean> customVerifier = null;
        private int verifierMaxRetries = 3;
        private double verifierRetryDelay = 1.0;
        private double verifierRetryBackoff = 2.0;
        private Integer maxTokens = null;
        private Double maxCostUsd = null;
        private double contextResetThreshold = 0.7;
        private int preserveMessages = 2;
        private ToolVerificationConfig toolVerificationConfig = null;

        /**
         * Set the goal description (required).
         */
        public Builder description(String description) {
            this.description = description;
            return this;
        }

        /**
         * Set the session ID for conversation continuity.
         */
        public Builder sessionId(String sessionId) {
            this.sessionId = sessionId;
            return this;
        }

        /**
         * Set the success criteria.
         */
        public Builder successCriteria(String successCriteria) {
            this.successCriteria = successCriteria;
            return this;
        }

        /**
         * Set the working directory.
         */
        public Builder workspaceDir(String workspaceDir) {
            this.workspaceDir = workspaceDir;
            return this;
        }

        /**
         * Set the maximum iterations.
         */
        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        /**
         * Set the maximum context resets.
         */
        public Builder maxContextResets(int maxContextResets) {
            this.maxContextResets = maxContextResets;
            return this;
        }

        /**
         * Set the timeout in seconds.
         */
        public Builder timeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
            return this;
        }

        /**
         * Set the verification method.
         */
        public Builder verificationMethod(VerificationMethod verificationMethod) {
            this.verificationMethod = verificationMethod;
            return this;
        }

        /**
         * Set the custom verifier function.
         */
        public Builder customVerifier(Function<GoalResult, Boolean> customVerifier) {
            this.customVerifier = customVerifier;
            return this;
        }

        /**
         * Set the maximum verifier retries.
         */
        public Builder verifierMaxRetries(int verifierMaxRetries) {
            this.verifierMaxRetries = verifierMaxRetries;
            return this;
        }

        /**
         * Set the verifier retry delay.
         */
        public Builder verifierRetryDelay(double verifierRetryDelay) {
            this.verifierRetryDelay = verifierRetryDelay;
            return this;
        }

        /**
         * Set the verifier retry backoff.
         */
        public Builder verifierRetryBackoff(double verifierRetryBackoff) {
            this.verifierRetryBackoff = verifierRetryBackoff;
            return this;
        }

        /**
         * Set the maximum tokens.
         */
        public Builder maxTokens(Integer maxTokens) {
            this.maxTokens = maxTokens;
            return this;
        }

        /**
         * Set the maximum cost in USD.
         */
        public Builder maxCostUsd(Double maxCostUsd) {
            this.maxCostUsd = maxCostUsd;
            return this;
        }

        /**
         * Set the context reset threshold.
         */
        public Builder contextResetThreshold(double contextResetThreshold) {
            this.contextResetThreshold = contextResetThreshold;
            return this;
        }

        /**
         * Set the number of messages to preserve.
         */
        public Builder preserveMessages(int preserveMessages) {
            this.preserveMessages = preserveMessages;
            return this;
        }

        /**
         * Set the tool verification configuration.
         *
         * Required when verificationMethod is TOOL.
         */
        public Builder toolVerificationConfig(ToolVerificationConfig toolVerificationConfig) {
            this.toolVerificationConfig = toolVerificationConfig;
            return this;
        }

        /**
         * Build the GoalConfig.
         */
        public GoalConfig build() {
            return new GoalConfig(this);
        }
    }
}
