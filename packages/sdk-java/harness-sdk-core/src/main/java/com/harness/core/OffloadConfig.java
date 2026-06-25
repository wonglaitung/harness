package com.harness.core;

import java.nio.file.Path;

/**
 * Configuration for tool output offloading.
 */
public record OffloadConfig(
    int sizeThresholdChars,
    int maxOutputsPerSession,
    boolean cleanupOnSessionEnd,
    int previewLength,
    Path tempDir
) {

    public OffloadConfig() {
        this(5000, 50, false, 200, null);
    }

    /**
     * Create default configuration.
     */
    public static OffloadConfig defaults() {
        return new OffloadConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int sizeThresholdChars = 5000;
        private int maxOutputsPerSession = 50;
        private boolean cleanupOnSessionEnd = false;
        private int previewLength = 200;
        private Path tempDir = null;

        public Builder sizeThresholdChars(int value) {
            this.sizeThresholdChars = value;
            return this;
        }

        public Builder maxOutputsPerSession(int value) {
            this.maxOutputsPerSession = value;
            return this;
        }

        public Builder cleanupOnSessionEnd(boolean value) {
            this.cleanupOnSessionEnd = value;
            return this;
        }

        public Builder previewLength(int value) {
            this.previewLength = value;
            return this;
        }

        public Builder tempDir(Path value) {
            this.tempDir = value;
            return this;
        }

        public OffloadConfig build() {
            return new OffloadConfig(
                sizeThresholdChars,
                maxOutputsPerSession,
                cleanupOnSessionEnd,
                previewLength,
                tempDir
            );
        }
    }
}
