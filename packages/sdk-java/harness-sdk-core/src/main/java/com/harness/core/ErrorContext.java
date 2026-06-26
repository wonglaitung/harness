package com.harness.core;

import java.util.List;

/**
 * Context for error handling decision.
 *
 * @param error The exception that occurred
 * @param iteration Current loop iteration
 * @param toolName Tool name if error occurred during tool execution
 * @param attempt Retry attempt number
 * @param contextTokens Current context token count
 * @param maxTokens Maximum allowed tokens
 * @param previousErrors List of previous errors in this session
 */
public record ErrorContext(
    Exception error,
    int iteration,
    String toolName,
    int attempt,
    int contextTokens,
    int maxTokens,
    List<Exception> previousErrors
) {

    /**
     * Check if error is due to context overflow.
     */
    public boolean isContextOverflow() {
        return contextTokens > maxTokens * 0.9;
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Exception error;
        private int iteration = 0;
        private String toolName = null;
        private int attempt = 1;
        private int contextTokens = 0;
        private int maxTokens = 200_000;
        private List<Exception> previousErrors = List.of();

        public Builder error(Exception error) {
            this.error = error;
            return this;
        }

        public Builder iteration(int iteration) {
            this.iteration = iteration;
            return this;
        }

        public Builder toolName(String toolName) {
            this.toolName = toolName;
            return this;
        }

        public Builder attempt(int attempt) {
            this.attempt = attempt;
            return this;
        }

        public Builder contextTokens(int contextTokens) {
            this.contextTokens = contextTokens;
            return this;
        }

        public Builder maxTokens(int maxTokens) {
            this.maxTokens = maxTokens;
            return this;
        }

        public Builder previousErrors(List<Exception> previousErrors) {
            this.previousErrors = previousErrors;
            return this;
        }

        public ErrorContext build() {
            return new ErrorContext(error, iteration, toolName, attempt, contextTokens, maxTokens, previousErrors);
        }
    }
}
