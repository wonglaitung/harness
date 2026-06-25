package com.harness.core;

/**
 * Configuration for streaming handler.
 *
 * @param bufferSize Max chunks in buffer
 * @param backpressureThreshold Trigger backpressure at this ratio (0.0-1.0)
 * @param pauseOnBackpressure Pause upstream on backpressure
 * @param maxPauseDuration Max seconds to pause
 */
public record StreamingConfig(
    int bufferSize,
    double backpressureThreshold,
    boolean pauseOnBackpressure,
    double maxPauseDuration
) {

    public static final int DEFAULT_BUFFER_SIZE = 8192;
    public static final double DEFAULT_BACKPRESSURE_THRESHOLD = 0.9;
    public static final boolean DEFAULT_PAUSE_ON_BACKPRESSURE = true;
    public static final double DEFAULT_MAX_PAUSE_DURATION = 5.0;

    public StreamingConfig() {
        this(
            DEFAULT_BUFFER_SIZE,
            DEFAULT_BACKPRESSURE_THRESHOLD,
            DEFAULT_PAUSE_ON_BACKPRESSURE,
            DEFAULT_MAX_PAUSE_DURATION
        );
    }

    public static StreamingConfig defaults() {
        return new StreamingConfig();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int bufferSize = DEFAULT_BUFFER_SIZE;
        private double backpressureThreshold = DEFAULT_BACKPRESSURE_THRESHOLD;
        private boolean pauseOnBackpressure = DEFAULT_PAUSE_ON_BACKPRESSURE;
        private double maxPauseDuration = DEFAULT_MAX_PAUSE_DURATION;

        public Builder bufferSize(int bufferSize) {
            this.bufferSize = bufferSize;
            return this;
        }

        public Builder backpressureThreshold(double backpressureThreshold) {
            this.backpressureThreshold = backpressureThreshold;
            return this;
        }

        public Builder pauseOnBackpressure(boolean pauseOnBackpressure) {
            this.pauseOnBackpressure = pauseOnBackpressure;
            return this;
        }

        public Builder maxPauseDuration(double maxPauseDuration) {
            this.maxPauseDuration = maxPauseDuration;
            return this;
        }

        public StreamingConfig build() {
            return new StreamingConfig(bufferSize, backpressureThreshold, pauseOnBackpressure, maxPauseDuration);
        }
    }
}
