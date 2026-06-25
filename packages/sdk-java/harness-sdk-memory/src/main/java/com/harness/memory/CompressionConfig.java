package com.harness.memory;

/**
 * Configuration for context compression.
 */
public record CompressionConfig(
    int minMessagesBeforeCompress,
    int keepRecentMessages,
    boolean keepSystemMessages,
    int summaryMaxTokens,
    double compressionRatio
) {

    public CompressionConfig() {
        this(10, 5, true, 500, 0.5);
    }

    /**
     * Create default configuration.
     */
    public static CompressionConfig defaults() {
        return new CompressionConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int minMessagesBeforeCompress = 10;
        private int keepRecentMessages = 5;
        private boolean keepSystemMessages = true;
        private int summaryMaxTokens = 500;
        private double compressionRatio = 0.5;

        public Builder minMessagesBeforeCompress(int value) {
            this.minMessagesBeforeCompress = value;
            return this;
        }

        public Builder keepRecentMessages(int value) {
            this.keepRecentMessages = value;
            return this;
        }

        public Builder keepSystemMessages(boolean value) {
            this.keepSystemMessages = value;
            return this;
        }

        public Builder summaryMaxTokens(int value) {
            this.summaryMaxTokens = value;
            return this;
        }

        public Builder compressionRatio(double value) {
            this.compressionRatio = value;
            return this;
        }

        public CompressionConfig build() {
            return new CompressionConfig(
                minMessagesBeforeCompress,
                keepRecentMessages,
                keepSystemMessages,
                summaryMaxTokens,
                compressionRatio
            );
        }
    }
}
