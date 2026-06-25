package com.harness.memory;

import java.nio.file.Path;

/**
 * Configuration for vector memory store.
 */
public record VectorMemoryConfig(
    String embeddingModel,
    Path persistDir,
    String collectionName,
    int embeddingDimension,
    double decayLambda,
    double minRetrievalStrength
) {

    public VectorMemoryConfig() {
        this("mock", null, "harness_memory", 384, 0.05, 0.3);
    }

    /**
     * Create default configuration.
     */
    public static VectorMemoryConfig defaults() {
        return new VectorMemoryConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String embeddingModel = "mock";
        private Path persistDir = null;
        private String collectionName = "harness_memory";
        private int embeddingDimension = 384;
        private double decayLambda = 0.05;
        private double minRetrievalStrength = 0.3;

        public Builder embeddingModel(String value) {
            this.embeddingModel = value;
            return this;
        }

        public Builder persistDir(Path value) {
            this.persistDir = value;
            return this;
        }

        public Builder collectionName(String value) {
            this.collectionName = value;
            return this;
        }

        public Builder embeddingDimension(int value) {
            this.embeddingDimension = value;
            return this;
        }

        public Builder decayLambda(double value) {
            this.decayLambda = value;
            return this;
        }

        public Builder minRetrievalStrength(double value) {
            this.minRetrievalStrength = value;
            return this;
        }

        public VectorMemoryConfig build() {
            return new VectorMemoryConfig(
                embeddingModel, persistDir, collectionName,
                embeddingDimension, decayLambda, minRetrievalStrength
            );
        }
    }
}
