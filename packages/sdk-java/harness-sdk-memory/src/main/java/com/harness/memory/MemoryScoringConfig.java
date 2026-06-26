package com.harness.memory;

/**
 * Configuration for memory scoring and archival.
 *
 * Based on Bjork's New Theory of Disuse:
 * - Storage Strength (importance): Determines what to archive
 * - Retrieval Strength: Determines what to prioritize in context
 */
public record MemoryScoringConfig(
    double decayLambda,            // Decay speed (higher = faster decay)
    double minRetrievalStrength,   // Minimum retrieval strength (floor)
    int maxCoreMemoryTokens,       // Core Memory token limit
    boolean enableLlmEvaluation,   // Enable LLM importance evaluation
    ArchiveFallback archiveFallback // Archive fallback strategy
) {

    /**
     * Archive fallback strategy.
     */
    public enum ArchiveFallback {
        FILE,    // Archive to MEMORY_ARCHIVE.md (default, no data loss)
        DELETE,  // Delete directly (not recommended)
        NONE     // Disable archiving, Core Memory grows indefinitely
    }

    public MemoryScoringConfig() {
        this(0.05, 0.3, 2000, false, ArchiveFallback.FILE);
    }

    /**
     * Create default configuration.
     */
    public static MemoryScoringConfig defaults() {
        return new MemoryScoringConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private double decayLambda = 0.05;
        private double minRetrievalStrength = 0.3;
        private int maxCoreMemoryTokens = 2000;
        private boolean enableLlmEvaluation = false;
        private ArchiveFallback archiveFallback = ArchiveFallback.FILE;

        public Builder decayLambda(double decayLambda) {
            this.decayLambda = decayLambda;
            return this;
        }

        public Builder minRetrievalStrength(double minRetrievalStrength) {
            this.minRetrievalStrength = minRetrievalStrength;
            return this;
        }

        public Builder maxCoreMemoryTokens(int maxCoreMemoryTokens) {
            this.maxCoreMemoryTokens = maxCoreMemoryTokens;
            return this;
        }

        public Builder enableLlmEvaluation(boolean enableLlmEvaluation) {
            this.enableLlmEvaluation = enableLlmEvaluation;
            return this;
        }

        public Builder archiveFallback(ArchiveFallback archiveFallback) {
            this.archiveFallback = archiveFallback;
            return this;
        }

        public MemoryScoringConfig build() {
            return new MemoryScoringConfig(decayLambda, minRetrievalStrength, maxCoreMemoryTokens, enableLlmEvaluation, archiveFallback);
        }
    }
}
