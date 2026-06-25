package com.harness.core;

/**
 * Configuration for stuck detection.
 *
 * @param enableSemantic Enable semantic similarity detection
 * @param similarityThreshold Cosine similarity threshold (0.0-1.0)
 * @param consecutiveRounds Consecutive similar rounds to trigger stuck
 * @param windowSize Number of recent embeddings to compare against
 * @param minChars Minimum characters for embedding (shorter texts are skipped)
 */
public record StuckDetectorConfig(
    boolean enableSemantic,
    double similarityThreshold,
    int consecutiveRounds,
    int windowSize,
    int minChars
) {

    public static final boolean DEFAULT_ENABLE_SEMANTIC = false;
    public static final double DEFAULT_SIMILARITY_THRESHOLD = 0.92;
    public static final int DEFAULT_CONSECUTIVE_ROUNDS = 3;
    public static final int DEFAULT_WINDOW_SIZE = 6;
    public static final int DEFAULT_MIN_CHARS = 30;

    public StuckDetectorConfig() {
        this(
            DEFAULT_ENABLE_SEMANTIC,
            DEFAULT_SIMILARITY_THRESHOLD,
            DEFAULT_CONSECUTIVE_ROUNDS,
            DEFAULT_WINDOW_SIZE,
            DEFAULT_MIN_CHARS
        );
    }

    public static StuckDetectorConfig defaults() {
        return new StuckDetectorConfig();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean enableSemantic = DEFAULT_ENABLE_SEMANTIC;
        private double similarityThreshold = DEFAULT_SIMILARITY_THRESHOLD;
        private int consecutiveRounds = DEFAULT_CONSECUTIVE_ROUNDS;
        private int windowSize = DEFAULT_WINDOW_SIZE;
        private int minChars = DEFAULT_MIN_CHARS;

        public Builder enableSemantic(boolean enableSemantic) {
            this.enableSemantic = enableSemantic;
            return this;
        }

        public Builder similarityThreshold(double similarityThreshold) {
            this.similarityThreshold = similarityThreshold;
            return this;
        }

        public Builder consecutiveRounds(int consecutiveRounds) {
            this.consecutiveRounds = consecutiveRounds;
            return this;
        }

        public Builder windowSize(int windowSize) {
            this.windowSize = windowSize;
            return this;
        }

        public Builder minChars(int minChars) {
            this.minChars = minChars;
            return this;
        }

        public StuckDetectorConfig build() {
            return new StuckDetectorConfig(
                enableSemantic, similarityThreshold, consecutiveRounds, windowSize, minChars
            );
        }
    }
}
