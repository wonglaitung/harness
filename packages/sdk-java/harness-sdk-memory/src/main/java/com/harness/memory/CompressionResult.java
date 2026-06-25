package com.harness.memory;

import java.util.List;

import com.harness.types.Message;

/**
 * Result of context compression.
 */
public record CompressionResult(
    List<Message> originalMessages,
    List<Message> compressedMessages,
    String summary,
    int tokensBefore,
    int tokensAfter,
    int messagesRemoved
) {

    /**
     * Tokens saved by compression.
     */
    public int compressionSaved() {
        return tokensBefore - tokensAfter;
    }

    /**
     * Compression ratio achieved.
     */
    public double achievedRatio() {
        if (tokensBefore == 0) return 1.0;
        return (double) tokensAfter / tokensBefore;
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private List<Message> originalMessages;
        private List<Message> compressedMessages;
        private String summary;
        private int tokensBefore;
        private int tokensAfter;
        private int messagesRemoved;

        public Builder originalMessages(List<Message> value) {
            this.originalMessages = value;
            return this;
        }

        public Builder compressedMessages(List<Message> value) {
            this.compressedMessages = value;
            return this;
        }

        public Builder summary(String value) {
            this.summary = value;
            return this;
        }

        public Builder tokensBefore(int value) {
            this.tokensBefore = value;
            return this;
        }

        public Builder tokensAfter(int value) {
            this.tokensAfter = value;
            return this;
        }

        public Builder messagesRemoved(int value) {
            this.messagesRemoved = value;
            return this;
        }

        public CompressionResult build() {
            return new CompressionResult(
                originalMessages,
                compressedMessages,
                summary,
                tokensBefore,
                tokensAfter,
                messagesRemoved
            );
        }
    }
}
