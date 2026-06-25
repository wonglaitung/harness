package com.harness.types;

/**
 * Cost control configuration.
 *
 * Implements multi-level budget management to prevent runaway costs.
 *
 * Session Level:
 * - maxTokensPerSession: Maximum tokens allowed per session
 * - maxToolCallsPerSession: Maximum tool calls per session
 * - maxIterationsPerRequest: Maximum iterations per request
 *
 * User Level:
 * - dailyTokenLimit: Maximum tokens per user per day
 * - hourlyRequestLimit: Maximum requests per user per hour
 *
 * Global Level:
 * - globalDailyBudgetUsd: Global daily budget in USD
 * - autoThrottle: Enable automatic throttling when budget is low
 * - fallbackModel: Model to switch to when budget is tight
 */
public record CostConfig(
    // Session level
    int maxTokensPerSession,
    int maxToolCallsPerSession,
    int maxIterationsPerRequest,

    // User level
    int dailyTokenLimit,
    int hourlyRequestLimit,

    // Global level
    double globalDailyBudgetUsd,
    boolean autoThrottle,
    String fallbackModel,
    double contextReductionRatio,

    // Common settings
    double warningThreshold,
    String actionOnExceed
) {

    // Session level defaults
    public static final int DEFAULT_MAX_TOKENS_PER_SESSION = 1_000_000;
    public static final int DEFAULT_MAX_TOOL_CALLS_PER_SESSION = 500;
    public static final int DEFAULT_MAX_ITERATIONS_PER_REQUEST = 20;

    // User level defaults
    public static final int DEFAULT_DAILY_TOKEN_LIMIT = 10_000_000;
    public static final int DEFAULT_HOURLY_REQUEST_LIMIT = 100;

    // Global level defaults
    public static final double DEFAULT_GLOBAL_DAILY_BUDGET_USD = 100.0;
    public static final boolean DEFAULT_AUTO_THROTTLE = true;
    public static final String DEFAULT_FALLBACK_MODEL = "claude-haiku-4-5";
    public static final double DEFAULT_CONTEXT_REDUCTION_RATIO = 0.5;

    // Common defaults
    public static final double DEFAULT_WARNING_THRESHOLD = 0.8;
    public static final String DEFAULT_ACTION_ON_EXCEED = "stop";

    public CostConfig() {
        this(
            DEFAULT_MAX_TOKENS_PER_SESSION,
            DEFAULT_MAX_TOOL_CALLS_PER_SESSION,
            DEFAULT_MAX_ITERATIONS_PER_REQUEST,
            DEFAULT_DAILY_TOKEN_LIMIT,
            DEFAULT_HOURLY_REQUEST_LIMIT,
            DEFAULT_GLOBAL_DAILY_BUDGET_USD,
            DEFAULT_AUTO_THROTTLE,
            DEFAULT_FALLBACK_MODEL,
            DEFAULT_CONTEXT_REDUCTION_RATIO,
            DEFAULT_WARNING_THRESHOLD,
            DEFAULT_ACTION_ON_EXCEED
        );
    }

    public static CostConfig defaults() {
        return new CostConfig();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int maxTokensPerSession = DEFAULT_MAX_TOKENS_PER_SESSION;
        private int maxToolCallsPerSession = DEFAULT_MAX_TOOL_CALLS_PER_SESSION;
        private int maxIterationsPerRequest = DEFAULT_MAX_ITERATIONS_PER_REQUEST;
        private int dailyTokenLimit = DEFAULT_DAILY_TOKEN_LIMIT;
        private int hourlyRequestLimit = DEFAULT_HOURLY_REQUEST_LIMIT;
        private double globalDailyBudgetUsd = DEFAULT_GLOBAL_DAILY_BUDGET_USD;
        private boolean autoThrottle = DEFAULT_AUTO_THROTTLE;
        private String fallbackModel = DEFAULT_FALLBACK_MODEL;
        private double contextReductionRatio = DEFAULT_CONTEXT_REDUCTION_RATIO;
        private double warningThreshold = DEFAULT_WARNING_THRESHOLD;
        private String actionOnExceed = DEFAULT_ACTION_ON_EXCEED;

        public Builder maxTokensPerSession(int maxTokensPerSession) {
            this.maxTokensPerSession = maxTokensPerSession;
            return this;
        }

        public Builder maxToolCallsPerSession(int maxToolCallsPerSession) {
            this.maxToolCallsPerSession = maxToolCallsPerSession;
            return this;
        }

        public Builder maxIterationsPerRequest(int maxIterationsPerRequest) {
            this.maxIterationsPerRequest = maxIterationsPerRequest;
            return this;
        }

        public Builder dailyTokenLimit(int dailyTokenLimit) {
            this.dailyTokenLimit = dailyTokenLimit;
            return this;
        }

        public Builder hourlyRequestLimit(int hourlyRequestLimit) {
            this.hourlyRequestLimit = hourlyRequestLimit;
            return this;
        }

        public Builder globalDailyBudgetUsd(double globalDailyBudgetUsd) {
            this.globalDailyBudgetUsd = globalDailyBudgetUsd;
            return this;
        }

        public Builder autoThrottle(boolean autoThrottle) {
            this.autoThrottle = autoThrottle;
            return this;
        }

        public Builder fallbackModel(String fallbackModel) {
            this.fallbackModel = fallbackModel;
            return this;
        }

        public Builder contextReductionRatio(double contextReductionRatio) {
            this.contextReductionRatio = contextReductionRatio;
            return this;
        }

        public Builder warningThreshold(double warningThreshold) {
            this.warningThreshold = warningThreshold;
            return this;
        }

        public Builder actionOnExceed(String actionOnExceed) {
            this.actionOnExceed = actionOnExceed;
            return this;
        }

        public CostConfig build() {
            if (!actionOnExceed.equals("stop") && !actionOnExceed.equals("compress")
                && !actionOnExceed.equals("warn") && !actionOnExceed.equals("downgrade")) {
                throw new IllegalArgumentException("Invalid actionOnExceed: " + actionOnExceed);
            }
            return new CostConfig(
                maxTokensPerSession, maxToolCallsPerSession, maxIterationsPerRequest,
                dailyTokenLimit, hourlyRequestLimit, globalDailyBudgetUsd,
                autoThrottle, fallbackModel, contextReductionRatio,
                warningThreshold, actionOnExceed
            );
        }
    }
}
