package com.harness.types;

/**
 * Token usage statistics.
 */
public record TokenUsage(
    int inputTokens,
    int outputTokens,
    int cacheReadTokens,
    int cacheWriteTokens,
    int toolCalls
) {

    public TokenUsage() {
        this(0, 0, 0, 0, 0);
    }

    public TokenUsage(int inputTokens, int outputTokens) {
        this(inputTokens, outputTokens, 0, 0, 0);
    }

    /**
     * Total tokens used.
     */
    public int totalTokens() {
        return inputTokens + outputTokens;
    }

    /**
     * Add another TokenUsage.
     */
    public TokenUsage add(TokenUsage other) {
        return new TokenUsage(
            this.inputTokens + other.inputTokens,
            this.outputTokens + other.outputTokens,
            this.cacheReadTokens + other.cacheReadTokens,
            this.cacheWriteTokens + other.cacheWriteTokens,
            this.toolCalls + other.toolCalls
        );
    }

    /**
     * Add input tokens.
     */
    public TokenUsage addInputTokens(int tokens) {
        return new TokenUsage(this.inputTokens + tokens, outputTokens, cacheReadTokens, cacheWriteTokens, toolCalls);
    }

    /**
     * Add output tokens.
     */
    public TokenUsage addOutputTokens(int tokens) {
        return new TokenUsage(inputTokens, this.outputTokens + tokens, cacheReadTokens, cacheWriteTokens, toolCalls);
    }

    /**
     * Add tool call.
     */
    public TokenUsage addToolCall() {
        return new TokenUsage(inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens, toolCalls + 1);
    }

    /**
     * Check budget against config.
     *
     * @param config Cost configuration
     * @return array of [isWithinBudget, warningMessage]
     */
    public Object[] checkBudget(CostConfig config) {
        String warning = null;

        if (totalTokens() > config.maxTokensPerSession()) {
            warning = String.format("Token budget exceeded: %d/%d", totalTokens(), config.maxTokensPerSession());
            return new Object[]{false, warning};
        }

        if (toolCalls > config.maxToolCallsPerSession()) {
            warning = String.format("Tool call budget exceeded: %d/%d", toolCalls, config.maxToolCallsPerSession());
            return new Object[]{false, warning};
        }

        double usageRatio = (double) totalTokens() / config.maxTokensPerSession();
        if (usageRatio >= config.warningThreshold()) {
            warning = String.format("Token usage at %.0f%% of session limit", usageRatio * 100);
        }

        return new Object[]{true, warning};
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int inputTokens;
        private int outputTokens;
        private int cacheReadTokens;
        private int cacheWriteTokens;
        private int toolCalls;

        public Builder inputTokens(int inputTokens) {
            this.inputTokens = inputTokens;
            return this;
        }

        public Builder outputTokens(int outputTokens) {
            this.outputTokens = outputTokens;
            return this;
        }

        public Builder cacheReadTokens(int cacheReadTokens) {
            this.cacheReadTokens = cacheReadTokens;
            return this;
        }

        public Builder cacheWriteTokens(int cacheWriteTokens) {
            this.cacheWriteTokens = cacheWriteTokens;
            return this;
        }

        public Builder toolCalls(int toolCalls) {
            this.toolCalls = toolCalls;
            return this;
        }

        public TokenUsage build() {
            return new TokenUsage(inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens, toolCalls);
        }
    }
}
