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
