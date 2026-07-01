package com.harness.connectors;

import java.time.Instant;

/**
 * Result of an output operation.
 */
public class OutputResult {
    private final String channelName;
    private final boolean success;
    private final String message;
    private final String error;
    private final Instant timestamp;

    private OutputResult(Builder builder) {
        this.channelName = builder.channelName;
        this.success = builder.success;
        this.message = builder.message;
        this.error = builder.error;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
    }

    // Getters

    public String getChannelName() {
        return channelName;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public String getError() {
        return error;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for OutputResult.
     */
    public static class Builder {
        private String channelName;
        private boolean success;
        private String message;
        private String error;
        private Instant timestamp;

        public Builder channelName(String channelName) {
            this.channelName = channelName;
            return this;
        }

        public Builder success(boolean success) {
            this.success = success;
            return this;
        }

        public Builder message(String message) {
            this.message = message;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public OutputResult build() {
            return new OutputResult(this);
        }
    }

    @Override
    public String toString() {
        return "OutputResult{channelName='" + channelName + "', success=" + success + '}';
    }
}
